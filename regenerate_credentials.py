#!/usr/bin/env python3
"""
Script to regenerate Google API credentials and tokens for the Email Management System
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Define the scopes your application needs
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets'
]

def regenerate_credentials():
    """Regenerate Google API credentials and tokens"""
    
    creds = None
    credentials_file = 'credentials.json'
    token_file = 'token.json'
    
    # Check if credentials file exists
    if not os.path.exists(credentials_file):
        print(f"Error: {credentials_file} not found!")
        return False
    
    # Load existing token if available
    if os.path.exists(token_file):
        print(f"Found existing token file: {token_file}")
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            print("Loaded existing credentials")
        except Exception as e:
            print(f"Error loading existing token: {e}")
            creds = None
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired, attempting to refresh...")
            try:
                creds.refresh(Request())
                print("Successfully refreshed token!")
            except Exception as e:
                print(f"Error refreshing token: {e}")
                print("Will need to re-authenticate...")
                creds = None
        
        if not creds:
            print("Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
            print("Successfully authenticated!")
    
    # Save the credentials for the next run
    with open(token_file, 'w') as token:
        token.write(creds.to_json())
        print(f"Saved new token to {token_file}")
    
    # Display token info
    if creds.expiry:
        print(f"Token expires: {creds.expiry}")
    else:
        print("Token expiry: Not set")
    
    print("Scopes granted:")
    for scope in creds.scopes or []:
        print(f"  - {scope}")
    
    return True

def test_credentials():
    """Test the credentials by making a simple API call"""
    try:
        from googleapiclient.discovery import build
        
        # Load the credentials
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # Test Gmail API
        print("\nTesting Gmail API...")
        gmail_service = build('gmail', 'v1', credentials=creds)
        profile = gmail_service.users().getProfile(userId='me').execute()
        print(f"✓ Gmail API working - Email: {profile.get('emailAddress')}")
        print(f"  Total messages: {profile.get('messagesTotal')}")
        
        # Test Calendar API
        print("\nTesting Calendar API...")
        calendar_service = build('calendar', 'v3', credentials=creds)
        calendar_list = calendar_service.calendarList().list().execute()
        print(f"✓ Calendar API working - Found {len(calendar_list.get('items', []))} calendars")
        
        # Test Sheets API
        print("\nTesting Sheets API...")
        sheets_service = build('sheets', 'v4', credentials=creds)
        # Just test if we can build the service (no actual API call needed)
        print("✓ Sheets API service created successfully")
        
        print("\n🎉 All API tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing credentials: {e}")
        return False

if __name__ == "__main__":
    print("=== Google API Credentials Regeneration ===\n")
    
    # Remove old token files to force fresh authentication
    old_files = ['token.json', 'sheets_token.json']
    for file in old_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"Removed old token file: {file}")
    
    print("\nRegenerating credentials...")
    if regenerate_credentials():
        print("\n" + "="*50)
        print("Testing the new credentials...")
        test_credentials()
    else:
        print("❌ Failed to regenerate credentials")