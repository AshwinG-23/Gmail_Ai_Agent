import os
import base64
import json
import pandas as pd
from email import message_from_bytes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scope for read-only access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def gmail_authenticate():
    """Authenticate Gmail API"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def extract_email_content(email_msg):
    """Extract text content from email message"""
    body = ''
    if email_msg.is_multipart():
        for part in email_msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))
            
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
                        break
                except:
                    continue
    else:
        try:
            payload = email_msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')
        except:
            body = str(email_msg.get_payload())
    
    return body

def fetch_all_gmail_messages(service, max_results=None):
    """Fetch ALL emails from Gmail using pagination"""
    print("Starting to fetch ALL emails from your Gmail account...")
    print("This may take a while depending on how many emails you have.\n")
    
    all_messages = []
    page_token = None
    page_count = 0
    
    # Step 1: Get ALL message IDs using pagination
    while True:
        try:
            page_count += 1
            print(f"Fetching page {page_count}...")
            
            if page_token:
                results = service.users().messages().list(
                    userId='me',
                    maxResults=500,  # Gmail API max per request
                    pageToken=page_token
                ).execute()
            else:
                results = service.users().messages().list(
                    userId='me',
                    maxResults=500
                ).execute()
            
            messages = results.get('messages', [])
            all_messages.extend(messages)
            
            print(f"Total message IDs collected: {len(all_messages)}")
            
            # Check if there are more pages
            page_token = results.get('nextPageToken')
            if not page_token:
                print(f"\nReached end of Gmail account!")
                print(f"Total emails found: {len(all_messages)}")
                break
            
            # Optional: Stop at max_results if specified
            if max_results and len(all_messages) >= max_results:
                all_messages = all_messages[:max_results]
                print(f"\nReached requested limit of {max_results} emails")
                break
                
        except Exception as e:
            print(f"Error fetching message list: {str(e)}")
            break
    
    print(f"\nStarting to process {len(all_messages)} emails...")
    
    # Step 2: Get full content for each email
    email_data = []
    for i, msg in enumerate(all_messages):
        try:
            # Progress indicator
            if (i + 1) % 50 == 0 or i == 0:
                print(f"Processing email {i+1}/{len(all_messages)} ({((i+1)/len(all_messages)*100):.1f}%)")
            
            msg_data = service.users().messages().get(
                userId='me', 
                id=msg['id'], 
                format='raw'
            ).execute()
            
            # Decode raw email
            raw = base64.urlsafe_b64decode(msg_data['raw'])
            email_msg = message_from_bytes(raw)
            
            subject = email_msg.get('subject', '')
            sender = email_msg.get('from', '')
            date = email_msg.get('date', '')
            
            body = extract_email_content(email_msg)
            
            email_data.append({
                'id': msg['id'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': body,
                'body_length': len(body)
            })
            
        except Exception as e:
            print(f"Error processing email {i+1}: {str(e)}")
            continue
    
    return email_data

def save_emails(emails, filename='gmail_emails.json'):
    """Save emails to JSON and CSV files"""
    # Save as JSON
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)
    
    # Save as CSV for easy viewing
    df = pd.DataFrame(emails)
    csv_filename = filename.replace('.json', '.csv')
    df.to_csv(csv_filename, index=False)
    
    print(f"\nEmails saved as:")
    print(f"- {filename}")
    print(f"- {csv_filename}")

def main():
    """Main function to fetch all emails"""
    print("=== Gmail Complete Email Fetcher ===\n")
    
    # Step 1: Authenticate Gmail
    print("1. Authenticating Gmail API...")
    service = gmail_authenticate()
    print("Gmail authentication successful!\n")
    
    # Step 2: Ask user preference
    choice = input("Type 'all' to fetch ALL emails, or enter a number (e.g., 1000): ").lower()
    
    if choice == 'all':
        max_results = None
        print("Fetching ALL emails from your Gmail account...")
    else:
        try:
            max_results = int(choice)
            print(f"Fetching up to {max_results} emails...")
        except ValueError:
            max_results = 1000
            print("Invalid input. Using default: 1000 emails")
    
    # Step 3: Fetch emails
    emails = fetch_all_gmail_messages(service, max_results=max_results)
    print(f"\nSuccessfully processed {len(emails)} emails!\n")
    
    # Step 4: Save emails
    save_emails(emails, f'gmail_all_emails_{len(emails)}.json')
    
    # Step 5: Show summary
    if emails:
        print("\n=== Email Summary ===")
        print(f"Total emails fetched: {len(emails)}")
        
        # Show first 3 email subjects as preview
        print("\nFirst 3 emails:")
        for i, email in enumerate(emails[:3]):
            print(f"{i+1}. Subject: {email['subject'][:60]}...")
            print(f"   From: {email['sender']}")
            print(f"   Date: {email['date']}\n")
        
        # Show statistics
        df = pd.DataFrame(emails)
        print(f"Email statistics:")
        print(f"- Average body length: {df['body_length'].mean():.0f} characters")
        print(f"- Shortest email: {df['body_length'].min()} characters")
        print(f"- Longest email: {df['body_length'].max()} characters")
        
        print("\nTop 10 senders:")
        sender_counts = df['sender'].value_counts().head(10)
        for i, (sender, count) in enumerate(sender_counts.items(), 1):
            print(f"{i:2d}. {sender[:50]}: {count} emails")
        
        # Show date range
        print(f"\nDate range:")
        print(f"- Oldest: {df['date'].min()}")
        print(f"- Newest: {df['date'].max()}")

if __name__ == '__main__':
    main()
