import json
import pandas as pd
import google.generativeai as genai
import time
import re
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def log_message(message, logfile='classification_log.txt'):
    """Log messages with timestamp to both console and file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f'[{timestamp}] {message}'
    print(log_entry)
    with open(logfile, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

def is_classroom_email(sender):
    """Check if email is from Google Classroom"""
    classroom_patterns = [
        r'<no-reply@classroom\.google\.com>',
        r'no-reply@classroom\.google\.com',
        r'noreply@classroom\.google\.com'
    ]
    for pattern in classroom_patterns:
        if re.search(pattern, sender, re.IGNORECASE):
            return True
    return False

def create_precise_classification_prompt(email):
    """Create a very precise prompt for single email classification"""
    
    categories_text = """
CLASSIFICATION CATEGORIES (Choose ONE number):

1 = URGENT: Time-sensitive academic/personal matters requiring immediate action
   - Assignment deadlines within 48 hours
   - Quiz/exam postponement requests  
   - Meeting requests for today/tomorrow
   - Immediate academic issues needing resolution

2 = CONFERENCE/ACADEMIC EVENTS: Research and academic conferences
   - Call for Papers (CFPs)
   - Research conference announcements
   - Academic workshops and seminars
   - Research publication opportunities

3 = JOB RECRUITMENT: Career and employment opportunities
   - Job postings and internship offers
   - Company recruitment drives
   - Career fair announcements
   - Placement-related opportunities

4 = PROMOTIONS/NEWSLETTERS: Marketing and promotional content
   - Course promotions and advertisements
   - Commercial newsletters
   - Startup events and marketing
   - Educational platform promotions

5 = ADMINISTRATIVE/OFFICIAL: College administration and services
   - Library notices and fines
   - Hostel administration
   - IT services and technical notices
   - Financial and fee-related communications
   - General college announcements

6 = PEER/GROUP COMMUNICATIONS: Student-to-student interactions
   - Club event invitations and announcements
   - Student group activities
   - Classmate communications
   - Student-organized events and competitions

7 = OTHER/MISCELLANEOUS: Everything else not fitting above categories
"""

    prompt = f"""You are classifying a single email. Read it carefully and classify based on PRIMARY CONTENT.

DECISION RULES:
- Academic deadline/postponement requests → Category 1 (URGENT)
- Student club events/activities → Category 6 (PEER/GROUP)  
- Job/internship opportunities → Category 3 (JOB RECRUITMENT)
- Conference CFPs → Category 2 (CONFERENCE/ACADEMIC)
- Commercial promotions → Category 4 (PROMOTIONS)
- College admin notices → Category 5 (ADMINISTRATIVE)

{categories_text}

SPECIFIC EXAMPLES:
- "Request to postpone quiz due to interview" → 1 (URGENT academic matter)
- "Club organizing Antakshari night" → 6 (PEER/GROUP student activity)
- "Samsung R&D recruitment drive" → 3 (JOB RECRUITMENT)
- "Library fine payment due" → 5 (ADMINISTRATIVE)

EMAIL TO CLASSIFY:
Subject: {email.get('subject', 'No Subject')}
From: {email.get('sender', 'Unknown')}
Body: {email.get('body', '')[:1500]}

RESPOND WITH ONLY THE NUMBER (1-7) THAT BEST MATCHES THIS EMAIL'S PRIMARY PURPOSE:"""
    
    return prompt

def classify_single_email(model, email, email_num, total_emails):
    """Classify a single email with detailed logging"""
    
    log_message(f"Processing email {email_num}/{total_emails}")
    log_message(f"  Subject: {email['subject'][:80]}...")
    log_message(f"  From: {email['sender'][:50]}...")
    
    prompt = create_precise_classification_prompt(email)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            result = response.text.strip()
            
            # LOG THE RESPONSE
            log_message(f"  API Response (attempt {attempt + 1}): '{result}'")
            
            # Extract the number
            numbers = re.findall(r'\b[1-7]\b', result)
            
            if numbers:
                category_num = int(numbers[0])
                log_message(f"  Extracted number: {category_num}")
                
                # Map to category name
                category_map = {
                    1: '1. Urgent',
                    2: '2. Conference/Academic Events', 
                    3: '3. Job Recruitment',
                    4: '4. Promotions/Newsletters',
                    5: '5. Administrative/Official Notices',
                    6: '6. Peer/Group Communications',
                    7: '7. Other/Miscellaneous'
                }
                
                category_name = category_map[category_num]
                log_message(f"  Final Classification: {category_name}")
                
                return {
                    'id': email['id'],
                    'subject': email['subject'],
                    'sender': email['sender'],
                    'body': email['body'],
                    'classification': category_name,
                    'numeric_response': result,
                    'extracted_number': str(category_num),
                    'confidence': 'high' if len(result) <= 3 else 'medium'  # shorter response = higher confidence
                }
            else:
                log_message(f"  WARNING: No valid number found in response, retrying...")
                if attempt == max_retries - 1:
                    log_message(f"  FALLBACK: Using category 7 (Other)")
                    return {
                        'id': email['id'],
                        'subject': email['subject'], 
                        'sender': email['sender'],
                        'body': email['body'],
                        'classification': '7. Other/Miscellaneous',
                        'numeric_response': result,
                        'extracted_number': '7',
                        'confidence': 'low'
                    }
                time.sleep(1)  # Brief pause before retry
                
        except Exception as e:
            log_message(f"  ERROR in attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise e
            time.sleep(2)  # Longer pause on error

def save_progress(classified_emails, output_filename):
    """Save progress to JSON and CSV"""
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(classified_emails, f, indent=2, ensure_ascii=False)
    
    df = pd.DataFrame(classified_emails)
    csv_filename = output_filename.replace('.json', '.csv')
    df.to_csv(csv_filename, index=False)
    
    log_message(f"  Progress saved: {len(classified_emails)} emails classified")

def classify_full_dataset_single(input_filename, output_filename, delay_sec=3):
    """Main classification function - processes one email at a time"""
    
    # Get API key from environment
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        log_message("ERROR: GEMINI_API_KEY not found in .env file!")
        return None
    
    log_message("=== Starting Single Email Classification ===")
    log_message(f"Model: gemini-2.0-flash")
    log_message(f"Method: One email per API call")
    log_message(f"Delay: {delay_sec} seconds between calls")
    
    # Load input dataset
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            emails = json.load(f)
        log_message(f"Loaded {len(emails)} emails from {input_filename}")
    except Exception as e:
        log_message(f"ERROR loading input file: {str(e)}")
        return None
    
    # Load existing progress if any
    classified_emails = []
    processed_ids = set()
    
    if os.path.exists(output_filename):
        try:
            with open(output_filename, 'r', encoding='utf-8') as f:
                classified_emails = json.load(f)
            processed_ids = {email['id'] for email in classified_emails}
            log_message(f"Resuming: Found {len(classified_emails)} already processed emails")
        except Exception as e:
            log_message(f"ERROR loading existing results: {str(e)}")
    
    # Separate classroom vs API emails (only unprocessed ones)
    classroom_emails = []
    api_emails = []
    
    for email in emails:
        if email['id'] in processed_ids:
            continue  # Skip already processed
            
        if is_classroom_email(email['sender']):
            classroom_emails.append({
                'id': email['id'],
                'subject': email['subject'],
                'sender': email['sender'],
                'body': email['body'],
                'classification': '8. Classroom',
                'numeric_response': 'AUTO_CLASSIFIED',
                'extracted_number': '8',
                'confidence': 'auto'
            })
        else:
            api_emails.append(email)
    
    # Add new classroom emails
    classified_emails.extend(classroom_emails)
    
    log_message(f"Email processing summary:")
    log_message(f"  - Total in dataset: {len(emails)}")
    log_message(f"  - Already processed: {len(processed_ids)}")
    log_message(f"  - New classroom emails: {len(classroom_emails)}")
    log_message(f"  - New emails for API: {len(api_emails)}")
    
    if not api_emails:
        log_message("No new emails to process!")
        return classified_emails
    
    # Setup Gemini API
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    log_message("Gemini API configured successfully")
    
    # Process one email at a time
    successful_emails = 0
    total_emails = len(api_emails)
    
    log_message(f"Starting single email processing:")
    log_message(f"  - Total emails to process: {total_emails}")
    log_message(f"  - Estimated time: {(total_emails * delay_sec) / 60:.1f} minutes")
    
    for i, email in enumerate(api_emails):
        email_num = i + 1
        
        try:
            # Classify single email
            classification_result = classify_single_email(model, email, email_num, total_emails)
            classified_emails.append(classification_result)
            
            successful_emails += 1
            progress_pct = (successful_emails / total_emails) * 100
            log_message(f"  ✅ Email {email_num} completed ({progress_pct:.1f}% done)")
            
            # Save progress every 10 emails or at the end
            if successful_emails % 10 == 0 or successful_emails == total_emails:
                save_progress(classified_emails, output_filename)
                log_message(f"  💾 Progress checkpoint saved")
            
            # Rate limiting
            if i + 1 < len(api_emails):
                log_message(f"  ⏳ Waiting {delay_sec} seconds...")
                time.sleep(delay_sec)
                
        except Exception as e:
            log_message(f"  ❌ FATAL ERROR processing email {email_num}: {str(e)}")
            log_message(f"  Processing stopped. Resume by running script again.")
            break
    
    # Final summary
    log_message(f"Classification completed: {successful_emails}/{total_emails} emails processed")
    
    # Save final results
    df = pd.DataFrame(classified_emails)
    csv_filename = output_filename.replace('.json', '.csv')
    df.to_csv(csv_filename, index=False)
    
    # Show final distribution
    if not df.empty:
        log_message("Final distribution:")
        counts = df['classification'].value_counts()
        for classification, count in counts.items():
            log_message(f"  {classification}: {count}")
    
    return classified_emails

def main():
    """Main execution function"""
    print("=== Single Email Classification with Enhanced Precision ===\n")
    
    # Check .env file
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create a .env file with: GEMINI_API_KEY=your_actual_api_key_here")
        return
    
    # Get input file
    input_file = input("Enter cleaned email JSON filename: ").strip()
    
    if not os.path.exists(input_file):
        print(f"❌ File {input_file} not found!")
        return
    
    # Generate output filename
    output_file = input_file.replace('_cleaned.json', '_classified_single.json')
    if output_file == input_file:
        output_file = input_file.replace('.json', '_classified_single.json')
    
    print(f"\nConfiguration:")
    print(f"  Input: {input_file}")
    print(f"  Output: {output_file}")
    print(f"  Method: Single email per API call")
    print(f"  Features: Enhanced prompts + confidence scoring")
    print(f"  Logging: Detailed logs with all responses")
    
    confirm = input("\nStart classification? (y/n): ").lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    # Start classification
    result = classify_full_dataset_single(input_file, output_file)
    
    if result:
        print(f"\n✅ Classification completed!")
        print(f"📋 Check 'classification_log.txt' for detailed logs")
        print(f"📊 Results saved as {output_file}")
        print(f"🎯 Each email processed individually for maximum accuracy")

if __name__ == '__main__':
    main()