"""
Configuration for the AI Email Agent
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the AI email agent"""
    
    # Gemini API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Gmail API Configuration
    GMAIL_CREDENTIALS_FILE: str = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    GMAIL_TOKEN_FILE: str = os.getenv("GMAIL_TOKEN_FILE", "token.json")
    GMAIL_SCOPES: list = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    # Google Calendar API Configuration
    CALENDAR_CREDENTIALS_FILE: str = os.getenv("CALENDAR_CREDENTIALS_FILE", "credentials.json")
    CALENDAR_TOKEN_FILE: str = os.getenv("CALENDAR_TOKEN_FILE", "calendar_token.json")
    CALENDAR_SCOPES: list = [
        'https://www.googleapis.com/auth/calendar'
    ]
    
    # Google Sheets API Configuration
    SHEETS_CREDENTIALS_FILE: str = os.getenv("SHEETS_CREDENTIALS_FILE", "credentials.json")
    SHEETS_TOKEN_FILE: str = os.getenv("SHEETS_TOKEN_FILE", "sheets_token.json")
    SHEETS_SCOPES: list = [
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    
    # Job Tracking Sheet
    JOB_TRACKING_SHEET_ID: str = os.getenv("JOB_TRACKING_SHEET_ID", "")
    
    # Agent Configuration
    EMAIL_CHECK_INTERVAL: int = int(os.getenv("EMAIL_CHECK_INTERVAL", "300"))  # 5 minutes
    MAX_EMAILS_PER_BATCH: int = int(os.getenv("MAX_EMAILS_PER_BATCH", "10"))
    AGENT_LOG_FILE: str = os.getenv("AGENT_LOG_FILE", "data/agent_logs.json")
    
    # Model Paths
    EMAIL_CLASSIFIER_MODEL: str = os.getenv("EMAIL_CLASSIFIER_MODEL", "Model_1/my-final-email-classifier")
    DATA_EXTRACTOR_MODEL: str = os.getenv("DATA_EXTRACTOR_MODEL", "Model_2/my-final-llama3-extractor")
    
    # Notification Configuration
    NOTIFICATION_EMAIL: str = os.getenv("NOTIFICATION_EMAIL", "")
    URGENT_NOTIFICATION_WEBHOOK: str = os.getenv("URGENT_NOTIFICATION_WEBHOOK", "")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # Development
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate_required_configs(cls) -> list:
        """Validate that required configurations are present"""
        missing = []
        
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        
        if not os.path.exists(cls.GMAIL_CREDENTIALS_FILE):
            missing.append(f"GMAIL_CREDENTIALS_FILE: {cls.GMAIL_CREDENTIALS_FILE}")
        
        return missing
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """Get a summary of current configuration (excluding sensitive data)"""
        return {
            "email_check_interval": cls.EMAIL_CHECK_INTERVAL,
            "max_emails_per_batch": cls.MAX_EMAILS_PER_BATCH,
            "debug": cls.DEBUG,
            "log_level": cls.LOG_LEVEL,
            "models_configured": {
                "email_classifier": os.path.exists(cls.EMAIL_CLASSIFIER_MODEL),
                "data_extractor": os.path.exists(cls.DATA_EXTRACTOR_MODEL)
            },
            "api_files_present": {
                "gmail_credentials": os.path.exists(cls.GMAIL_CREDENTIALS_FILE),
                "gmail_token": os.path.exists(cls.GMAIL_TOKEN_FILE),
                "calendar_token": os.path.exists(cls.CALENDAR_TOKEN_FILE),
                "sheets_token": os.path.exists(cls.SHEETS_TOKEN_FILE)
            }
        }