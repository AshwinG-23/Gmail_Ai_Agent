"""
Data models for the AI Email Agent
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

class Priority(str, Enum):
    """Email priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class EmailCategory(str, Enum):
    """Email categories for classification"""
    ACADEMIC = "academic"
    JOB = "job"
    PERSONAL = "personal"
    PROMOTIONAL = "promotional"
    CONFERENCE = "conference"
    DEADLINE = "deadline"
    MEETING = "meeting"
    NOTIFICATION = "notification"
    SPAM = "spam"
    UNKNOWN = "unknown"

class Email(BaseModel):
    """Email data model"""
    id: str
    subject: str
    sender: str
    sender_email: str
    body: str
    timestamp: datetime
    thread_id: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    is_read: bool = False
    has_attachments: bool = False
    message_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ExecutionStep(BaseModel):
    """Individual step in the agent's execution plan"""
    step: int
    tool: str
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rationale: str
    
class AgentDecision(BaseModel):
    """Agent's decision and execution plan for an email"""
    email_id: str
    reasoning: str
    priority: Priority
    category: EmailCategory
    execution_plan: List[ExecutionStep]
    expected_outcome: str
    timestamp: datetime
    confidence_score: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ToolExecution(BaseModel):
    """Result of executing a single tool action"""
    step: int
    tool: str
    action: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ToolResult(BaseModel):
    """Standardized result from any tool execution"""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tool_name: Optional[str] = None
    action_name: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AgentSession(BaseModel):
    """Complete agent processing session for an email"""
    session_id: str
    email: Email
    decision: AgentDecision
    executions: List[ToolExecution]
    final_status: str
    success_rate: float
    total_execution_time_ms: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CalendarEvent(BaseModel):
    """Calendar event model"""
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    reminder_minutes: Optional[int] = 15
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class JobApplication(BaseModel):
    """Job application tracking model"""
    company: str
    position: str
    application_date: datetime
    status: str = "applied"
    job_url: Optional[str] = None
    contact_email: Optional[str] = None
    deadline: Optional[datetime] = None
    notes: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Reminder(BaseModel):
    """Reminder/task model"""
    title: str
    description: Optional[str] = None
    due_date: datetime
    priority: Priority = Priority.MEDIUM
    category: str = "general"
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NotificationRequest(BaseModel):
    """Notification request model"""
    message: str
    recipient: Optional[str] = None
    urgency_level: Priority = Priority.MEDIUM
    notification_type: str = "email"  # email, webhook, sms
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExtractedData(BaseModel):
    """Model for data extracted from emails"""
    extraction_type: str  # events, jobs, deadlines, contacts
    confidence: float
    data: Dict[str, Any]
    source_text: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AgentStats(BaseModel):
    """Agent performance statistics"""
    total_emails_processed: int
    success_rate: float
    average_execution_time_ms: float
    most_common_category: EmailCategory
    tool_usage_stats: Dict[str, int]
    error_rates: Dict[str, float]
    last_updated: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Chrome Extension Models
class DraftRequest(BaseModel):
    """Request for generating email draft"""
    context: str
    tone: str = "professional"
    recipient: Optional[str] = None
    subject: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)

class DraftResponse(BaseModel):
    """Response with generated email draft"""
    draft: str
    subject_suggestion: Optional[str] = None
    generated_by: str = "AI Agent Brain"
    confidence: Optional[float] = None
    alternative_drafts: List[str] = Field(default_factory=list)

class AgentStatus(BaseModel):
    """Current status of the agent"""
    is_running: bool
    total_processed: int
    last_activity: Optional[datetime] = None
    current_task: Optional[str] = None
    available_tools: List[str] = Field(default_factory=list)
    system_health: str = "healthy"  # healthy, warning, error
    monitoring_since: Optional[str] = None  # ISO datetime when monitoring started
    processed_emails_count: Optional[int] = 0  # Number of emails processed this session
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }