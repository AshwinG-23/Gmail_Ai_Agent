import json
import re
from bs4 import BeautifulSoup
import pandas as pd

def clean_email_text(text):
    """Clean email text by removing HTML, unicode chars, and normalizing whitespace"""
    if not text:
        return ''
    
    # Step 1: Remove HTML tags
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    
    # Step 2: Remove URLs
    text = re.sub(r'http[s]?://\S+', '[URL]', text)
    
    # Step 3: Remove email addresses in body (keep sender field separate)
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    
    # Step 4: Remove unicode control characters
    text = re.sub(r'[\u0000-\u001F\u007F-\u009F]', '', text)
    text = re.sub(r'[\u2000-\u206F\u2E00-\u2E7F]', '', text)
    text = re.sub(r'[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]', ' ', text)
    
    # Step 5: Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\r\n', ' ', text)  # Windows line endings
    text = re.sub(r'\n+', ' ', text)   # Unix line endings
    
    # Step 6: Remove common email footers
    text = re.sub(r'--\s*$', '', text)
    text = re.sub(r'Sent from my iPhone.*$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Get Outlook for.*$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Unsubscribe.*$', '', text, flags=re.IGNORECASE)
    
    return text.strip()

def clean_sender_field(sender):
    """Clean sender field - extract just name and email"""
    if not sender:
        return ''
    
    # Remove extra whitespace and normalize
    sender = re.sub(r'\s+', ' ', sender.strip())
    
    # Handle cases like "Name <email@domain.com>"
    match = re.match(r'^(.*?)\s*<(.+?)>$', sender)
    if match:
        name = match.group(1).strip(' "\'')
        email = match.group(2).strip()
        return f"{name} <{email}>" if name else email
    
    return sender

def clean_email_dataset(input_filename, output_filename):
    """Clean email dataset and save cleaned version"""
    
    try:
        print(f"Loading emails from {input_filename}...")
        with open(input_filename, 'r', encoding='utf-8') as f:
            emails = json.load(f)
        
        print(f"Loaded {len(emails)} emails. Starting cleaning process...")
        
        cleaned_emails = []
        
        for i, email in enumerate(emails):
            if (i + 1) % 100 == 0:
                print(f"Processed {i+1}/{len(emails)} emails ({((i+1)/len(emails)*100):.1f}%)")
            
            # Clean each field
            cleaned_email = {
                'id': email.get('id', ''),
                'sender': clean_sender_field(email.get('sender', '')),
                'subject': clean_email_text(email.get('subject', '')),
                'body': clean_email_text(email.get('body', ''))
            }
            
            # Add body length for reference
            cleaned_email['body_length'] = len(cleaned_email['body'])
            
            cleaned_emails.append(cleaned_email)
        
        # Save cleaned dataset as JSON
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(cleaned_emails, f, indent=2, ensure_ascii=False)
        
        # Save as CSV for easy viewing
        df = pd.DataFrame(cleaned_emails)
        csv_filename = output_filename.replace('.json', '.csv')
        df.to_csv(csv_filename, index=False)
        
        print(f"\n✅ Cleaning completed!")
        print(f"📁 Files created:")
        print(f"   - {output_filename} (JSON format)")
        print(f"   - {csv_filename} (CSV format)")
        
        # Show sample of cleaned data
        print(f"\n📋 Sample cleaned emails:")
        for i, email in enumerate(cleaned_emails[:3], 1):
            print(f"\nSample {i}:")
            print(f"ID: {email['id']}")
            print(f"Sender: {email['sender']}")
            print(f"Subject: {email['subject']}")
            print(f"Body: {email['body'][:150]}...")
            print(f"Body Length: {email['body_length']} characters")
        
        # Show statistics
        print(f"\n📊 Dataset Statistics:")
        print(f"Total emails: {len(cleaned_emails)}")
        print(f"Average body length: {df['body_length'].mean():.0f} characters")
        print(f"Shortest body: {df['body_length'].min()} characters")
        print(f"Longest body: {df['body_length'].max()} characters")
        
        return cleaned_emails
        
    except FileNotFoundError:
        print(f"❌ Error: File '{input_filename}' not found!")
        print("Please make sure the file exists and the path is correct.")
        return None
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON format in '{input_filename}'!")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return None

def main():
    """Main function to run the cleaning process"""
    print("=== Email Dataset Cleaner ===\n")
    
    # Get input filename
    input_file = input("Enter your JSON filename (e.g., gmail_all_emails_1000.json): ").strip()
    if not input_file:
        print("No filename provided. Exiting...")
        return
    
    # Generate output filename
    base_name = input_file.replace('.json', '')
    output_file = f"{base_name}_cleaned.json"
    
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}\n")
    
    # Clean the dataset
    cleaned_data = clean_email_dataset(input_file, output_file)
    
    if cleaned_data:
        print("\n🎉 Dataset cleaning successful!")
        print(f"Your cleaned dataset is ready for classification.")
        print(f"Use '{output_file}' as input for your email classification script.")

if __name__ == '__main__':
    main()
