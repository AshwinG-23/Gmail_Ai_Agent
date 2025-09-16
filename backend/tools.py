"""
Agent Tool System - All tools available to the AI agent
"""

import os
import json
import pickle
import base64
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from email.mime.text import MIMEText

# Google API imports
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ML model imports
from transformers import pipeline
import google.generativeai as genai

from .models import ToolResult, CalendarEvent, JobApplication, Reminder, NotificationRequest
from .config import Config

# ==================== BASE TOOL CLASS ====================

class BaseTool(ABC):
    """Base class for all agent tools"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @abstractmethod
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolResult:
        pass

# ==================== UTILITY FUNCTIONS ====================

def get_google_service(service_name: str, version: str, scopes: List[str], token_file: str, credentials_file: str):
    """Generic function to get Google API service"""
    from google.oauth2.credentials import Credentials
    
    creds = None
    
    # Load existing token - try JSON first, then pickle for backward compatibility
    if os.path.exists(token_file):
        try:
            # Try loading as JSON (new format)
            creds = Credentials.from_authorized_user_file(token_file, scopes)
            print(f"Loaded JSON credentials from {token_file}")
        except (json.JSONDecodeError, ValueError) as e:
            try:
                # Fallback to pickle format (old format)
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
                print(f"Loaded pickled credentials from {token_file}")
            except Exception as pickle_error:
                print(f"Failed to load credentials: JSON error: {e}, Pickle error: {pickle_error}")
                creds = None
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("Successfully refreshed expired credentials")
                # Save refreshed credentials as JSON
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            except Exception as refresh_error:
                print(f"Failed to refresh credentials: {refresh_error}")
                creds = None
        
        if not creds:
            print("No valid credentials found, starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
            creds = flow.run_local_server(port=0)
            
            # Save credentials as JSON (new format)
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print(f"Saved new credentials to {token_file}")
    
    return build(service_name, version, credentials=creds)

# ==================== EMAIL CLASSIFIER TOOL ====================

class EmailClassifier(BaseTool):
    """Tool for email classification using DistilBERT"""
    
    def __init__(self):
        self.config = Config()
        try:
            # Load the classifier using the same method as inference.py
            self.classifier = pipeline(
                "text-classification", 
                model=self.config.EMAIL_CLASSIFIER_MODEL
            )
            self.available = True
            print("EmailClassifier model loaded successfully")
        except Exception as e:
            print(f"EmailClassifier model not available: {e}")
            self.available = False
    
    @property
    def name(self) -> str:
        return "EmailClassifier"
    
    @property
    def description(self) -> str:
        return """
        Classifies emails into categories using DistilBERT:
        - Actions: classify, get_confidence
        - Parameters: text (required), threshold (optional, default 0.5)
        - Returns: category, confidence, all_scores
        Categories: academic, job, personal, promotional, conference, deadline, meeting, notification, spam
        """
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolResult:
        if not self.available:
            return ToolResult(
                success=False,
                data={},
                message="EmailClassifier model not available",
                tool_name=self.name,
                action_name=action
            )
        
        if action == "classify":
            try:
                # Get text from email or direct parameter
                email_data = parameters.get("email", {})
                if email_data:
                    subject = email_data.get("subject", "")
                    body = email_data.get("body", "")
                    text = f"{subject} {body}"
                else:
                    text = parameters.get("text", "")
                
                if not text:
                    return ToolResult(
                        success=False,
                        data={},
                        message="No text provided for classification",
                        tool_name=self.name,
                        action_name=action
                    )
                
                # Truncate text to reasonable length
                text = text[:512]
                
                # Call the classifier (returns single result, not list)
                result = self.classifier(text)
                
                # Extract the result - the classifier returns a single dict
                if isinstance(result, dict) and 'label' in result:
                    category = result['label'].lower()
                    confidence = result['score']
                elif isinstance(result, list) and len(result) > 0:
                    # Handle list format just in case
                    category = result[0]['label'].lower()
                    confidence = result[0]['score']
                else:
                    category = "unknown"
                    confidence = 0.5
                
                return ToolResult(
                    success=True,
                    data={
                        "category": category,
                        "confidence": confidence
                    },
                    message=f"Classified as {category} with {confidence:.2f} confidence",
                    tool_name=self.name,
                    action_name=action
                )
                
            except Exception as e:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"Classification failed: {str(e)}",
                    tool_name=self.name,
                    action_name=action
                )
        
        return ToolResult(
            success=False,
            data={},
            message=f"Unknown action: {action}",
            tool_name=self.name,
            action_name=action
        )

# ==================== DATA EXTRACTOR TOOL ====================

class DataExtractor(BaseTool):
    """Tool for extracting structured data using Llama 3"""
    
    def __init__(self):
        self.config = Config()
        self.extractor = None
        self.available = True  # Assume available, will check on first use
    
    def _load_model(self):
        """Lazy load the model when first needed"""
        if self.extractor is None:
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
                from peft import PeftModel
                
                # Clear GPU cache first
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                print("Loading DataExtractor model...")
                
                # Use the same configuration as inference_extractor.py
                MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct"
                ADAPTER_PATH = self.config.DATA_EXTRACTOR_MODEL
                
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.bfloat16,
                )
                
                model = AutoModelForCausalLM.from_pretrained(
                    MODEL_NAME,
                    quantization_config=bnb_config,
                    device_map="auto",
                    trust_remote_code=True,
                )
                
                model = PeftModel.from_pretrained(model, ADAPTER_PATH)
                tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
                tokenizer.pad_token = tokenizer.eos_token
                tokenizer.padding_side = "left"
                
                self.model = model
                self.tokenizer = tokenizer
                self.extractor = True  # Flag to indicate loaded
                print("DataExtractor model loaded successfully")
            except Exception as e:
                print(f"Failed to load DataExtractor: {e}")
                self.available = False
                self.extractor = None
    
    def _extract_json(self, prompt_text, max_new_tokens=100):
        """Extract JSON using the model - based on inference_extractor.py"""
        import torch
        
        inputs = self.tokenizer(
            prompt_text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1024,
        ).to(self.model.device)
        
        input_length = inputs.input_ids.shape[1]
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                eos_token_id=self.tokenizer.eos_token_id,
                do_sample=False,
            )
        
        generated_tokens = outputs[0, input_length:]
        generated_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        return generated_text
    
    @property
    def name(self) -> str:
        return "DataExtractor"
    
    @property
    def description(self) -> str:
        return """
        Extracts structured data using   trained Llama 3 + LoRA model:
        - Actions: extract_events, extract_jobs, extract_deadlines, extract_contacts
        - Parameters: text (required), email (optional for context)  
        - Returns: structured JSON data extracted by   fine-tuned model
        - Model: Meta-Llama-3-8B-Instruct + LoRA adapter trained on your data
        - This is   model, not Gemini - use it for data extraction!
        """
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolResult:
        # Load model if not already loaded
        if self.extractor is None:
            self._load_model()
        
        if not self.available or self.extractor is None:
            return ToolResult(
                success=False,
                data={},
                message="DataExtractor model not available",
                tool_name=self.name,
                action_name=action
            )
        
        text = parameters.get("text", "")
        email_data = parameters.get("email", {})
        
        if not text and email_data:
            subject = email_data.get("subject", "")
            body = email_data.get("body", "")
            text = f"Subject: {subject}\n\nBody: {body}"
        
        if not text:
            return ToolResult(
                success=False,
                data={},
                message="No text provided for extraction",
                tool_name=self.name,
                action_name=action
            )
        
        try:
            # Use the SAME prompt format as your inference_extractor.py
            if action in ["extract_events", "extract_jobs", "extract_deadlines", "extract_contacts"]:
                prompt = f"""<|begin_of_text|><|start_header_id|>user<|end_header_id|>

Extract structured data from this email. Email: '{text[:500]}'<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
                print(f"🤖 Using   trained Llama 3 model for {action}")
            else:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"Unknown extraction action: {action}",
                    tool_name=self.name,
                    action_name=action
                )
            
            # Use the extract_json method from inference_extractor.py
            result = self._extract_json(prompt, max_new_tokens=100)
            
            # Try to extract JSON from the result
            try:
                # Find JSON in the generated text
                start_idx = result.find('{')
                end_idx = result.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = result[start_idx:end_idx]
                    extracted_data = json.loads(json_str)
                else:
                    extracted_data = {"error": "No JSON found in response", "raw_response": result}
                
            except json.JSONDecodeError:
                extracted_data = {"error": "Invalid JSON in response", "raw_response": result}
            
            return ToolResult(
                success=True,
                data={
                    "extracted": extracted_data,
                    "extraction_type": action,
                    "source_length": len(text)
                },
                message=f"Extracted {action.split('_')[1]} data",
                tool_name=self.name,
                action_name=action
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"Extraction failed: {str(e)}",
                tool_name=self.name,
                action_name=action
            )

# ==================== CALENDAR TOOL ====================

class CalendarTool(BaseTool):
    """Tool for Google Calendar operations"""
    
    def __init__(self):
        self.config = Config()
        self.service = None
    
    @property
    def name(self) -> str:
        return "CalendarTool"
    
    @property
    def description(self) -> str:
        return """
        Manages Google Calendar events:
        - Actions: create_event, list_events, update_event, delete_event
        - Parameters: title, start_time, end_time, description, location, attendees
        - Returns: event_id or event list
        """
    
    def _get_service(self):
        """Get Google Calendar service"""
        if not self.service:
            try:
                self.service = get_google_service(
                    "calendar", "v3",
                    self.config.CALENDAR_SCOPES,
                    self.config.CALENDAR_TOKEN_FILE,
                    self.config.CALENDAR_CREDENTIALS_FILE
                )
            except Exception as e:
                print(f"Failed to initialize Calendar service: {e}")
                return None
        return self.service
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolResult:
        service = self._get_service()
        if not service:
            return ToolResult(
                success=False,
                data={},
                message="Google Calendar service not available",
                tool_name=self.name,
                action_name=action
            )
        
        try:
            if action == "create_event":
                title = parameters.get("title", "Untitled Event")
                start_time = parameters.get("start_time")
                end_time = parameters.get("end_time")
                description = parameters.get("description", "")
                location = parameters.get("location", "")
                
                # Create event object
                event = {
                    'summary': title,
                    'description': description,
                    'location': location,
                    'start': {
                        'dateTime': start_time,
                        'timeZone': 'UTC',
                    },
                    'end': {
                        'dateTime': end_time,
                        'timeZone': 'UTC',
                    },
                }
                
                # Add attendees if provided
                attendees = parameters.get("attendees", [])
                if attendees:
                    event['attendees'] = [{'email': email} for email in attendees]
                
                # Add reminder
                reminder_minutes = parameters.get("reminder_minutes", 15)
                event['reminders'] = {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': reminder_minutes},
                        {'method': 'popup', 'minutes': 10},
                    ],
                }
                
                created_event = service.events().insert(calendarId='primary', body=event).execute()
                
                return ToolResult(
                    success=True,
                    data={
                        "event_id": created_event['id'],
                        "event_link": created_event.get('htmlLink'),
                        "created": created_event.get('created')
                    },
                    message=f"Created calendar event: {title}",
                    tool_name=self.name,
                    action_name=action
                )
            
            elif action == "list_events":
                max_results = parameters.get("max_results", 10)
                time_min = parameters.get("time_min", datetime.now().isoformat() + 'Z')
                
                events_result = service.events().list(
                    calendarId='primary',
                    timeMin=time_min,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                
                return ToolResult(
                    success=True,
                    data={
                        "events": [
                            {
                                "id": event['id'],
                                "title": event.get('summary', 'No title'),
                                "start": event['start'].get('dateTime', event['start'].get('date')),
                                "end": event['end'].get('dateTime', event['end'].get('date')),
                                "description": event.get('description', ''),
                                "location": event.get('location', '')
                            }
                            for event in events
                        ],
                        "total_count": len(events)
                    },
                    message=f"Retrieved {len(events)} calendar events",
                    tool_name=self.name,
                    action_name=action
                )
            
            return ToolResult(
                success=False,
                data={},
                message=f"Unknown calendar action: {action}",
                tool_name=self.name,
                action_name=action
            )
            
        except HttpError as e:
            return ToolResult(
                success=False,
                data={},
                message=f"Google Calendar API error: {e}",
                tool_name=self.name,
                action_name=action
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"Calendar operation failed: {str(e)}",
                tool_name=self.name,
                action_name=action
            )

# ==================== SHEETS TOOL ====================

class SheetsTool(BaseTool):
    """Tool for Google Sheets operations"""
    
    def __init__(self):
        self.config = Config()
        self.service = None
    
    @property
    def name(self) -> str:
        return "SheetsTool"
    
    @property
    def description(self) -> str:
        return """
        Manages Google Sheets for job tracking:
        - Actions: add_job, update_job, get_jobs, create_sheet
        - Parameters: sheet_id, job_data, row_index
        - Returns: operation result with row information
        """
    
    def _get_service(self):
        """Get Google Sheets service"""
        if not self.service:
            try:
                self.service = get_google_service(
                    "sheets", "v4",
                    self.config.SHEETS_SCOPES,
                    self.config.SHEETS_TOKEN_FILE,
                    self.config.SHEETS_CREDENTIALS_FILE
                )
            except Exception as e:
                print(f"Failed to initialize Sheets service: {e}")
                return None
        return self.service
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolResult:
        service = self._get_service()
        if not service:
            return ToolResult(
                success=False,
                data={},
                message="Google Sheets service not available",
                tool_name=self.name,
                action_name=action
            )
        
        sheet_id = parameters.get("sheet_id", self.config.JOB_TRACKING_SHEET_ID)
        if not sheet_id:
            return ToolResult(
                success=False,
                data={},
                message="No sheet_id provided and JOB_TRACKING_SHEET_ID not configured",
                tool_name=self.name,
                action_name=action
            )
        
        try:
            if action == "add_job":
                job_data = parameters.get("job_data", {})
                
                # Prepare row data
                row = [
                    job_data.get("company", ""),
                    job_data.get("position", ""),
                    job_data.get("application_date", datetime.now().strftime("%Y-%m-%d")),
                    job_data.get("status", "applied"),
                    job_data.get("job_url", ""),
                    job_data.get("contact_email", ""),
                    job_data.get("deadline", ""),
                    job_data.get("notes", "")
                ]
                
                # Add row to sheet
                result = service.spreadsheets().values().append(
                    spreadsheetId=sheet_id,
                    range="A:H",  # Assuming 8 columns
                    valueInputOption="USER_ENTERED",
                    body={"values": [row]}
                ).execute()
                
                return ToolResult(
                    success=True,
                    data={
                        "sheet_id": sheet_id,
                        "added_row": row,
                        "update_info": result
                    },
                    message=f"Added job application: {job_data.get('company', 'Unknown')} - {job_data.get('position', 'Unknown')}",
                    tool_name=self.name,
                    action_name=action
                )
            
            elif action == "get_jobs":
                range_name = parameters.get("range", "A:H")
                
                result = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range=range_name
                ).execute()
                
                values = result.get('values', [])
                
                return ToolResult(
                    success=True,
                    data={
                        "jobs": values,
                        "total_count": len(values)
                    },
                    message=f"Retrieved {len(values)} job entries",
                    tool_name=self.name,
                    action_name=action
                )
            
            return ToolResult(
                success=False,
                data={},
                message=f"Unknown sheets action: {action}",
                tool_name=self.name,
                action_name=action
            )
            
        except HttpError as e:
            return ToolResult(
                success=False,
                data={},
                message=f"Google Sheets API error: {e}",
                tool_name=self.name,
                action_name=action
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"Sheets operation failed: {str(e)}",
                tool_name=self.name,
                action_name=action
            )

# ==================== EMAIL TOOL ====================

class EmailTool(BaseTool):
    """Tool for Gmail operations"""
    
    def __init__(self):
        self.config = Config()
        self.service = None
        
        # Email category to Gmail label mapping
        self.category_labels = {
            "1. urgent": "AI-Urgent",
            "2. conference/academic events": "AI-Conference", 
            "3. job recruitment": "AI-Jobs",
            "4. promotions/newsletters": "AI-Promotions",
            "5. administrative/official notices": "AI-Administrative",
            "6. peer/group communications": "AI-Social",
            "7. other/miscellaneous": "AI-Other",
            "8. classroom": "AI-Classroom",
            "google_classroom": "Google-Classroom"  # Special rule for Google Classroom emails
        }
        
        # Cache for existing labels
        self._gmail_labels = None
    
    @property
    def name(self) -> str:
        return "EmailTool"
    
    @property
    def description(self) -> str:
        return """
        Gmail management operations:
        - Actions: get_unread, get_recent_emails, mark_read, add_label, apply_category_label, get_sent_emails, archive, reply, send
        - Parameters: email_id, labels, category, recipient, message, limit, since_date
        - Returns: operation result
        - get_recent_emails: Retrieves emails received after a specific date/time (since_date parameter)
        Categories: Urgent, Conference, Jobs, Promotions, Administrative, Social, Other, Classroom
        """
    
    def _get_service(self):
        """Get Gmail service"""
        if not self.service:
            try:
                self.service = get_google_service(
                    "gmail", "v1",
                    self.config.GMAIL_SCOPES,
                    self.config.GMAIL_TOKEN_FILE,
                    self.config.GMAIL_CREDENTIALS_FILE
                )
            except Exception as e:
                print(f"Failed to initialize Gmail service: {e}")
                return None
        return self.service
    
    def _get_gmail_labels(self):
        """Get all Gmail labels, cached"""
        if self._gmail_labels is None:
            service = self._get_service()
            if service:
                try:
                    result = service.users().labels().list(userId='me').execute()
                    self._gmail_labels = {label['name']: label['id'] for label in result.get('labels', [])}
                except Exception as e:
                    print(f"Failed to get Gmail labels: {e}")
                    self._gmail_labels = {}
            else:
                self._gmail_labels = {}
        return self._gmail_labels
    
    def _create_label(self, label_name):
        """Create a Gmail label if it doesn't exist"""
        service = self._get_service()
        if not service:
            return None
            
        try:
            # Check if label already exists
            labels = self._get_gmail_labels()
            if label_name in labels:
                return labels[label_name]
            
            # Create new label (without custom colors - Gmail has restricted color palette)
            label_object = {
                'name': label_name,
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow'
            }
            
            created_label = service.users().labels().create(
                userId='me', 
                body=label_object
            ).execute()
            
            # Update cache
            self._gmail_labels[label_name] = created_label['id']
            print(f"Created Gmail label: {label_name}")
            
            return created_label['id']
            
        except Exception as e:
            print(f"Failed to create label {label_name}: {e}")
            return None
    
    def _validate_email_id(self, email_id):
        """Validate and clean email ID"""
        if not email_id:
            return None
            
        # Remove URL encoding if present
        import urllib.parse
        decoded_id = urllib.parse.unquote(email_id)
        
        # Remove any angle brackets or placeholders
        if decoded_id.startswith('<') and decoded_id.endswith('>'):
            decoded_id = decoded_id[1:-1]
        
        # Check for placeholder values
        placeholder_patterns = ['current_email_id', 'email_id', 'test_', 'mock_']
        for pattern in placeholder_patterns:
            if pattern in decoded_id.lower():
                print(f"Warning: Email ID appears to be a placeholder: {decoded_id}")
                return None
        
        # Gmail message IDs should be alphanumeric with some special chars
        if len(decoded_id) < 10 or not decoded_id.replace('-', '').replace('_', '').isalnum():
            print(f"Warning: Email ID format appears invalid: {decoded_id}")
            return None
            
        return decoded_id
    
    def _apply_category_label(self, email_id, category):
        """Apply appropriate label based on email category"""
        service = self._get_service()
        if not service:
            return False
            
        # Validate and clean email ID
        clean_email_id = self._validate_email_id(email_id)
        if not clean_email_id:
            print(f"Skipping label application - invalid email ID: {email_id}")
            return False
            
        # Normalize category name for matching
        category_normalized = category.lower().strip()
        
        # Find matching label
        label_name = None
        
        # First, check for exact matches (for special categories like google_classroom)
        if category_normalized in self.category_labels:
            label_name = self.category_labels[category_normalized]
        else:
            # Then check for partial matches (for regular categories)
            for cat_key, label in self.category_labels.items():
                if cat_key.lower() in category_normalized or category_normalized in cat_key.lower():
                    label_name = label
                    break
        
        if not label_name:
            # Default to "AI-Other" for unrecognized categories
            label_name = "AI-Other"
        
        try:
            # Ensure label exists
            label_id = self._create_label(label_name)
            if not label_id:
                return False
            
            # Apply label to email
            service.users().messages().modify(
                userId='me',
                id=clean_email_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            print(f"✅ Applied label '{label_name}' to email {clean_email_id} (category: {category})")
            return True
            
        except Exception as e:
            print(f"Failed to apply category label: {e}")
            return False
    
    def _decode_base64(self, data):
        """Decode base64 email data"""
        try:
            return base64.urlsafe_b64decode(data).decode('utf-8')
        except:
            return data
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolResult:
        service = self._get_service()
        if not service:
            return ToolResult(
                success=False,
                data={},
                message="Gmail service not available",
                tool_name=self.name,
                action_name=action
            )
        
        try:
            if action == "get_unread":
                limit = parameters.get("limit", 10)
                
                # Get unread messages
                results = service.users().messages().list(
                    userId='me',
                    q='is:unread',
                    maxResults=limit
                ).execute()
                
                messages = results.get('messages', [])
                emails = []
                
                for msg in messages:
                    # Get full message details
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    # Extract email data
                    headers = {h['name']: h['value'] for h in message['payload']['headers']}
                    
                    # Get body
                    body = ""
                    if 'parts' in message['payload']:
                        for part in message['payload']['parts']:
                            if part['mimeType'] == 'text/plain':
                                if 'data' in part['body']:
                                    body = self._decode_base64(part['body']['data'])
                    else:
                        if message['payload']['body'].get('data'):
                            body = self._decode_base64(message['payload']['body']['data'])
                    
                    emails.append({
                        "id": message['id'],
                        "subject": headers.get('Subject', ''),
                        "sender": headers.get('From', ''),
                        "sender_email": headers.get('From', '').split('<')[-1].rstrip('>'),
                        "body": body,
                        "timestamp": datetime.fromtimestamp(int(message['internalDate']) / 1000).isoformat(),
                        "thread_id": message['threadId'],
                        "labels": message.get('labelIds', [])
                    })
                
                return ToolResult(
                    success=True,
                    data={
                        "emails": emails,
                        "total_count": len(emails)
                    },
                    message=f"Retrieved {len(emails)} unread emails",
                    tool_name=self.name,
                    action_name=action
                )
            
            elif action == "mark_read":
                email_id = parameters.get("email_id")
                if not email_id:
                    return ToolResult(
                        success=False,
                        data={},
                        message="No email_id provided",
                        tool_name=self.name,
                        action_name=action
                    )
                
                # Remove UNREAD label
                service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                
                return ToolResult(
                    success=True,
                    data={"email_id": email_id},
                    message=f"Marked email {email_id} as read",
                    tool_name=self.name,
                    action_name=action
                )
            
            elif action == "add_label":
                email_id = parameters.get("email_id")
                labels = parameters.get("labels", [])
                
                if not email_id or not labels:
                    return ToolResult(
                        success=False,
                        data={},
                        message="email_id and labels are required",
                        tool_name=self.name,
                        action_name=action
                    )
                
                service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'addLabelIds': labels}
                ).execute()
                
                return ToolResult(
                    success=True,
                    data={"email_id": email_id, "labels": labels},
                    message=f"Added labels {labels} to email {email_id}",
                    tool_name=self.name,
                    action_name=action
                )
            
            elif action == "apply_category_label":
                email_id = parameters.get("email_id")
                category = parameters.get("category")
                
                if not email_id or not category:
                    return ToolResult(
                        success=False,
                        data={},
                        message="email_id and category are required",
                        tool_name=self.name,
                        action_name=action
                    )
                
                success = self._apply_category_label(email_id, category)
                
                if success:
                    return ToolResult(
                        success=True,
                        data={"email_id": email_id, "category": category},
                        message=f"Applied category label for '{category}' to email {email_id}",
                        tool_name=self.name,
                        action_name=action
                    )
                else:
                    return ToolResult(
                        success=False,
                        data={},
                        message=f"Failed to apply category label for '{category}'",
                        tool_name=self.name,
                        action_name=action
                    )
            
            elif action == "get_recent_emails":
                limit = parameters.get("limit", 10)
                since_date = parameters.get("since_date")  # ISO format datetime string
                
                # Build Gmail query for recent emails
                query = ""
                if since_date:
                    try:
                        # Convert ISO date to Gmail date format (YYYY/MM/DD)
                        since_dt = datetime.fromisoformat(since_date.replace('Z', '+00:00'))
                        gmail_date = since_dt.strftime('%Y/%m/%d')
                        query = f"after:{gmail_date}"
                    except:
                        # If date parsing fails, just get recent emails
                        pass
                
                # Get recent messages (both read and unread)
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=limit
                ).execute()
                
                messages = results.get('messages', [])
                emails = []
                
                for msg in messages:
                    # Get full message details
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    # Extract email data
                    headers = {h['name']: h['value'] for h in message['payload']['headers']}
                    
                    # Get body
                    body = ""
                    if 'parts' in message['payload']:
                        for part in message['payload']['parts']:
                            if part['mimeType'] == 'text/plain':
                                if 'data' in part['body']:
                                    body = self._decode_base64(part['body']['data'])
                    else:
                        if message['payload']['body'].get('data'):
                            body = self._decode_base64(message['payload']['body']['data'])
                    
                    # Parse timestamp
                    email_timestamp = datetime.fromtimestamp(int(message['internalDate']) / 1000)
                    
                    # Filter by timestamp if since_date provided (double-check)
                    if since_date:
                        try:
                            since_dt = datetime.fromisoformat(since_date.replace('Z', '+00:00'))
                            # Make timezone-aware comparison
                            if email_timestamp.replace(tzinfo=None) <= since_dt.replace(tzinfo=None):
                                continue  # Skip older emails
                        except:
                            pass  # If parsing fails, include the email
                    
                    emails.append({
                        "id": message['id'],
                        "subject": headers.get('Subject', ''),
                        "sender": headers.get('From', ''),
                        "sender_email": headers.get('From', '').split('<')[-1].rstrip('>') if '<' in headers.get('From', '') else headers.get('From', ''),
                        "body": body,
                        "timestamp": email_timestamp.isoformat(),
                        "thread_id": message['threadId'],
                        "labels": message.get('labelIds', [])
                    })
                
                return ToolResult(
                    success=True,
                    data={
                        "emails": emails,
                        "total_count": len(emails),
                        "query_used": query or "all recent",
                        "since_date": since_date
                    },
                    message=f"Retrieved {len(emails)} recent emails" + (f" since {since_date}" if since_date else ""),
                    tool_name=self.name,
                    action_name=action
                )
            
            elif action == "get_sent_emails":
                recipient = parameters.get("recipient")
                limit = parameters.get("limit", 5)
                
                if not recipient:
                    return ToolResult(
                        success=False,
                        data={},
                        message="recipient email address is required",
                        tool_name=self.name,
                        action_name=action
                    )
                
                # Search for sent emails to specific recipient
                query = f"to:{recipient}"
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=limit
                ).execute()
                
                messages = results.get('messages', [])
                emails = []
                
                for msg in messages:
                    # Get full message details
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    # Extract email data
                    headers = {h['name']: h['value'] for h in message['payload']['headers']}
                    
                    # Get body
                    body = ""
                    if 'parts' in message['payload']:
                        for part in message['payload']['parts']:
                            if part['mimeType'] == 'text/plain':
                                if 'data' in part['body']:
                                    body = self._decode_base64(part['body']['data'])
                    else:
                        if message['payload']['body'].get('data'):
                            body = self._decode_base64(message['payload']['body']['data'])
                    
                    emails.append({
                        "id": message['id'],
                        "subject": headers.get('Subject', ''),
                        "recipient": headers.get('To', ''),
                        "body": body,
                        "timestamp": datetime.fromtimestamp(int(message['internalDate']) / 1000).isoformat(),
                        "thread_id": message['threadId']
                    })
                
                return ToolResult(
                    success=True,
                    data={
                        "emails": emails,
                        "recipient": recipient,
                        "total_count": len(emails)
                    },
                    message=f"Retrieved {len(emails)} sent emails to {recipient}",
                    tool_name=self.name,
                    action_name=action
                )
            
            return ToolResult(
                success=False,
                data={},
                message=f"Unknown email action: {action}",
                tool_name=self.name,
                action_name=action
            )
            
        except HttpError as e:
            return ToolResult(
                success=False,
                data={},
                message=f"Gmail API error: {e}",
                tool_name=self.name,
                action_name=action
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"Email operation failed: {str(e)}",
                tool_name=self.name,
                action_name=action
            )

# ==================== NOTIFICATION TOOL ====================

class NotificationTool(BaseTool):
    """Tool for sending notifications"""
    
    def __init__(self):
        self.config = Config()
    
    @property
    def name(self) -> str:
        return "NotificationTool"
    
    @property
    def description(self) -> str:
        return """
        Sends notifications:
        - Actions: send_urgent, send_reminder, send_email
        - Parameters: message, recipient, urgency_level, notification_type
        - Returns: notification_id and delivery status
        """
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolResult:
        if action in ["send_urgent", "send_reminder", "send_email"]:
            message = parameters.get("message", "")
            recipient = parameters.get("recipient", self.config.NOTIFICATION_EMAIL)
            urgency_level = parameters.get("urgency_level", "medium")
            
            # For now, we'll simulate notification sending
            # In a real implementation, integrate with email, SMS, or webhook services
            
            notification_id = f"notif_{int(time.time())}_{action}"
            
            # Log the notification (in a real system, send actual notification)
            print(f"NOTIFICATION [{urgency_level.upper()}]: {message}")
            if recipient:
                print(f"TO: {recipient}")
            
            return ToolResult(
                success=True,
                data={
                    "notification_id": notification_id,
                    "message": message,
                    "recipient": recipient,
                    "urgency_level": urgency_level,
                    "delivery_status": "sent"
                },
                message=f"Sent {action} notification",
                tool_name=self.name,
                action_name=action
            )
        
        return ToolResult(
            success=False,
            data={},
            message=f"Unknown notification action: {action}",
            tool_name=self.name,
            action_name=action
        )

# ==================== REMINDER TOOL ====================

class ReminderTool(BaseTool):
    """Tool for creating and managing reminders"""
    
    def __init__(self):
        self.config = Config()
        self.reminders_file = "data/reminders.json"
        self._load_reminders()
    
    def _load_reminders(self):
        """Load reminders from file"""
        if os.path.exists(self.reminders_file):
            with open(self.reminders_file, 'r') as f:
                self.reminders = json.load(f)
        else:
            self.reminders = []
    
    def _save_reminders(self):
        """Save reminders to file"""
        os.makedirs(os.path.dirname(self.reminders_file), exist_ok=True)
        with open(self.reminders_file, 'w') as f:
            json.dump(self.reminders, f, indent=2)
    
    @property
    def name(self) -> str:
        return "ReminderTool"
    
    @property
    def description(self) -> str:
        return """
        Creates and manages reminders:
        - Actions: create, list, complete, delete
        - Parameters: title, due_date, description, priority
        - Returns: reminder_id and reminder details
        """
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolResult:
        if action == "create":
            title = parameters.get("title", "Untitled Reminder")
            due_date = parameters.get("due_date")
            description = parameters.get("description", "")
            priority = parameters.get("priority", "medium")
            
            reminder = {
                "id": f"reminder_{int(time.time())}",
                "title": title,
                "description": description,
                "due_date": due_date,
                "priority": priority,
                "completed": False,
                "created_at": datetime.now().isoformat()
            }
            
            self.reminders.append(reminder)
            self._save_reminders()
            
            return ToolResult(
                success=True,
                data=reminder,
                message=f"Created reminder: {title}",
                tool_name=self.name,
                action_name=action
            )
        
        elif action == "list":
            completed = parameters.get("completed", False)
            limit = parameters.get("limit", 10)
            
            filtered_reminders = [
                r for r in self.reminders 
                if r.get("completed", False) == completed
            ][:limit]
            
            return ToolResult(
                success=True,
                data={
                    "reminders": filtered_reminders,
                    "total_count": len(filtered_reminders)
                },
                message=f"Retrieved {len(filtered_reminders)} reminders",
                tool_name=self.name,
                action_name=action
            )
        
        return ToolResult(
            success=False,
            data={},
            message=f"Unknown reminder action: {action}",
            tool_name=self.name,
            action_name=action
        )

# ==================== TOOL REGISTRY ====================

class ToolRegistry:
    """Registry and manager for all agent tools"""
    
    def __init__(self):
        self.tools = {
            "EmailClassifier": EmailClassifier(),
            "DataExtractor": DataExtractor(),
            "CalendarTool": CalendarTool(),
            "SheetsTool": SheetsTool(),
            "NotificationTool": NotificationTool(),
            "EmailTool": EmailTool(),
            "ReminderTool": ReminderTool()
        }
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        return list(self.tools.keys())
    
    def get_tools_description(self) -> str:
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"**{name}**:\n{tool.description}")
        return "\n\n".join(descriptions)
    
    async def execute_tool(self, tool_name: str, action: str, parameters: Dict[str, Any]) -> ToolResult:
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                data={},
                message=f"Tool {tool_name} not found",
                tool_name=tool_name,
                action_name=action
            )
        
        start_time = time.time()
        result = await tool.execute(action, parameters)
        execution_time = int((time.time() - start_time) * 1000)
        
        # Add execution time to result
        result.data["execution_time_ms"] = execution_time
        
        return result
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """Get statistics about available tools"""
        return {
            "total_tools": len(self.tools),
            "available_tools": self.list_tools(),
            "tool_descriptions": {name: tool.description for name, tool in self.tools.items()}
        }