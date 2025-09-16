"""
AI Email Agent - Autonomous Agent with Tool System
The Gemini brain plans and executes using available tools
"""

import os
import json
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import uvicorn

from .tools import ToolRegistry, ToolResult
from .config import Config
from .models import (
    Email, AgentDecision, ToolExecution, ExecutionStep, Priority, 
    EmailCategory, DraftRequest, DraftResponse, AgentStatus, AgentSession
)

# ==================== CONFIGURATION ====================
config = Config()
genai.configure(api_key=config.GEMINI_API_KEY)

# ==================== AGENT BRAIN ====================
class AgentBrain:
    """The Gemini-powered agent brain that reasons, plans, and executes"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.tools = ToolRegistry()
        
    async def analyze_and_plan(self, email: Email) -> AgentDecision:
        """
        The agent brain analyzes the email and creates an execution plan
        Uses trained classifier FIRST, then Gemini for planning
        """
        
        # STEP 1: Use   trained classifier to categorize the email
        print(f"🤖 STEP 1: Running   trained EmailClassifier...")
        classification_result = await self.tools.execute_tool(
            "EmailClassifier",
            "classify", 
            {"email": email.dict()}
        )
        
        if classification_result.success:
            predicted_category = classification_result.data.get("category", "unknown")
            confidence = classification_result.data.get("confidence", 0.0)
            print(f"✅   model classified email as: {predicted_category} (confidence: {confidence:.2f})")
        else:
            predicted_category = "unknown"
            confidence = 0.0
            print(f"⚠️ Classifier failed: {classification_result.message}")
        
        # Get available tools description
        tools_description = self.tools.get_tools_description()
        
        # STEP 2: Use Gemini for PLANNING (not classification) based on   model's prediction
        prompt = f"""
You are an autonomous AI email agent. Create an execution plan for this email.

EMAIL CONTENT:
Subject: {email.subject}
From: {email.sender}
Body: {email.body[:2000]}  
Received: {email.timestamp}

PRE-CLASSIFIED CATEGORY: {predicted_category.upper()} (confidence: {confidence:.2f})
^^^ This category was determined by a trained DistilBERT model on personal email data ^^^

AVAILABLE TOOLS:
{tools_description}

TASK: Create a JSON execution plan with the following structure:
{{
    "reasoning": "Your analysis of the email and why you chose these actions",
    "priority": "high|medium|low",
    "category": "academic|job|personal|promotional|conference|deadline|meeting|notification|spam|unknown",
    "confidence_score": 0.95,
    "execution_plan": [
        {{
            "step": 1,
            "tool": "tool_name",
            "action": "specific_action",
            "parameters": {{"param": "value"}},
            "rationale": "why this step is needed"
        }}
    ],
    "expected_outcome": "what should happen after execution"
}}

EXAMPLE RESPONSES:

## Example 1: Job Application Email
{{
    "reasoning": "This is a job application confirmation email that should be tracked",
    "priority": "medium",
    "category": "job",
    "confidence_score": 0.9,
    "execution_plan": [
        {{
            "step": 1,
            "tool": "EmailClassifier",
            "action": "classify",
            "parameters": {{"text": "email body text here"}},
            "rationale": "Classify the email to confirm category"
        }},
        {{
            "step": 2,
            "tool": "DataExtractor",
            "action": "extract_job_info",
            "parameters": {{}},
            "rationale": "Extract job details for tracking"
        }},
        {{
            "step": 3,
            "tool": "EmailTool",
            "action": "add_label",
            "parameters": {{"label_name": "AI-Jobs"}},
            "rationale": "Label email for organization"
        }}
    ],
    "expected_outcome": "Email classified, job info extracted and tracked"
}}

## Example 2: Conference Invitation
{{
    "reasoning": "Conference invitation with event details to be scheduled",
    "priority": "medium",
    "category": "conference",
    "confidence_score": 0.85,
    "execution_plan": [
        {{
            "step": 1,
            "tool": "EmailClassifier",
            "action": "classify",
            "parameters": {{"text": "conference invitation text"}},
            "rationale": "Confirm this is a conference email"
        }},
        {{
            "step": 2,
            "tool": "DataExtractor",
            "action": "extract_event_info",
            "parameters": {{}},
            "rationale": "Extract event details for calendar"
        }},
        {{
            "step": 3,
            "tool": "EmailTool",
            "action": "add_label",
            "parameters": {{"label_name": "AI-Conference"}},
            "rationale": "Label for easy identification"
        }}
    ],
    "expected_outcome": "Conference details extracted and labeled"
}}

GUIDELINES:
1. TRUST THE PRE-CLASSIFIED CATEGORY - it comes from a trained model on personal data
2. Do NOT classify again - the category is already determined above
3. Use   DataExtractor model for structured data extraction (NOT Gemini analysis):
   - Job emails: Use "DataExtractor" with "extract_jobs" action
   - Conference/Event emails: Use "DataExtractor" with "extract_events" action
   - Deadline emails: Use "DataExtractor" with "extract_deadlines" action
   - Contact info: Use "DataExtractor" with "extract_contacts" action
4. Choose actions based on the PRE-CLASSIFIED category:
   - job: DataExtractor → SheetsTool → Add "AI-Jobs" label
   - conference: DataExtractor → CalendarTool → Add "AI-Conference" label
   - urgent: Add "AI-Urgent" label → NotificationTool
   - academic: Add "AI-Academic" label
   - personal: Add "AI-Personal" label
5. For parameters, only include values you can extract from email content
6. DO NOT include email_id, message_id in parameters - added automatically
7. Always add appropriate EmailTool labeling step
8. Let   trained models do the heavy lifting, not Gemini analysis

IMPORTANT: 
- Return ONLY valid JSON, no additional text or explanation
- DO NOT generate placeholder values like <email_id> or email_id_placeholder
- Only include parameters with actual values from the email content
"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                plan_data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
            
            # Create execution steps
            execution_steps = []
            for step_data in plan_data.get("execution_plan", []):
                step = ExecutionStep(
                    step=step_data["step"],
                    tool=step_data["tool"],
                    action=step_data["action"],
                    parameters=step_data.get("parameters", {}),
                    rationale=step_data["rationale"]
                )
                execution_steps.append(step)
            
            return AgentDecision(
                email_id=email.id,
                reasoning=plan_data["reasoning"],
                priority=Priority(plan_data["priority"]),
                category=self._map_category(predicted_category),  # Use   model's classification
                execution_plan=execution_steps,
                expected_outcome=plan_data["expected_outcome"],
                confidence_score=confidence,  # Use   model's confidence
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"Planning failed: {e}")
            # Fallback to simple labeling if planning fails (classification already done)
            fallback_steps = [
                ExecutionStep(
                    step=1,
                    tool="EmailTool",
                    action="apply_category_label",
                    parameters={"category": predicted_category},
                    rationale=f"Apply label based on   model's classification: {predicted_category}"
                ),
                ExecutionStep(
                    step=2,
                    tool="EmailTool",
                    action="mark_read",
                    parameters={},
                    rationale="Mark email as processed"
                )
            ]
            
            return AgentDecision(
                email_id=email.id,
                reasoning=f"Planning failed: {str(e)}. Using   model's classification: {predicted_category}",
                priority=Priority.MEDIUM,
                category=self._map_category(predicted_category),
                execution_plan=fallback_steps,
                expected_outcome=f"Email labeled as {predicted_category} and marked as read",
                confidence_score=confidence,
                timestamp=datetime.now()
            )
    
    def _map_category(self, predicted_category: str) -> EmailCategory:
        """Map your model's categories to EmailCategory enum"""
        category_mapping = {
            "job": EmailCategory.JOB,
            "academic": EmailCategory.ACADEMIC,
            "conference": EmailCategory.CONFERENCE,
            "personal": EmailCategory.PERSONAL,
            "promotional": EmailCategory.PROMOTIONAL,
            "deadline": EmailCategory.DEADLINE,
            "meeting": EmailCategory.MEETING,
            "notification": EmailCategory.NOTIFICATION,
            "spam": EmailCategory.SPAM,
        }
        return category_mapping.get(predicted_category.lower(), EmailCategory.UNKNOWN)
    
    def _replace_placeholders(self, parameters: Dict[str, Any], email: Email, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace AI-generated placeholders with actual values from email context
        """
        import re
        
        def replace_value(value):
            if isinstance(value, str):
                # Store original value for debugging
                original_value = value
                
                # Replace all variations of email ID placeholders
                email_id_patterns = [
                    r'\b<current_email_id>\b',
                    r'\b%3Ccurrent_email_id%3E\b',
                    r'\b<email_id>\b',
                    r'\b%3Cemail_id%3E\b',
                    r'\b<message_id>\b', 
                    r'\b%3Cmessage_id%3E\b',
                    r'\bcurrent_email_id\b',
                    r'\bemail_id_placeholder\b',
                    r'\bCURRENT_EMAIL_ID\b',
                    r'\bEMAIL_ID\b'
                ]
                
                # Replace all email ID patterns
                for pattern in email_id_patterns:
                    value = re.sub(pattern, email.id, value, flags=re.IGNORECASE)
                
                # Replace other common placeholders
                other_replacements = {
                    r'\b<sender>\b|\b%3Csender%3E\b': email.sender,
                    r'\b<subject>\b|\b%3Csubject%3E\b': email.subject,
                    r'\b<recipient>\b|\b%3Crecipient%3E\b': email.sender,  # For reply context
                    r'\b<from_email>\b|\b%3Cfrom_email%3E\b': email.sender,
                }
                
                for pattern, replacement in other_replacements.items():
                    value = re.sub(pattern, str(replacement), value, flags=re.IGNORECASE)
                
                # Handle any remaining angle bracket placeholders
                value = re.sub(r'<([^>]+)>', r'\1', value)
                value = re.sub(r'%3C([^%]+)%3E', r'\1', value, flags=re.IGNORECASE)
                
                # Log replacement if it occurred
                if original_value != value:
                    print(f"🔄 PLACEHOLDER REPLACED: '{original_value}' -> '{value}'")
                
            elif isinstance(value, dict):
                return {k: replace_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [replace_value(item) for item in value]
            
            return value
        
        replaced_params = {k: replace_value(v) for k, v in parameters.items()}
        
        # Debug logging
        if replaced_params != parameters:
            print(f"📋 PARAMETERS BEFORE: {parameters}")
            print(f"📋 PARAMETERS AFTER:  {replaced_params}")
        
        return replaced_params
    
    async def execute_plan(self, decision: AgentDecision, email: Email) -> List[ToolExecution]:
        """
        Execute the planned steps using available tools
        """
        executions = []
        context = {"email": email, "previous_results": {}}
        
        for step in decision.execution_plan:
            start_time = datetime.now()
            
            try:
                tool_name = step.tool
                action = step.action
                parameters = step.parameters.copy()
                
                # Replace AI-generated placeholders with actual email data
                parameters = self._replace_placeholders(parameters, email, context)
                
                # Automatically add email_id for EmailTool operations that need it
                if tool_name == "EmailTool":
                    email_tool_actions_needing_id = ["add_label", "remove_label", "mark_read", "mark_unread", "archive", "delete"]
                    if action in email_tool_actions_needing_id and "email_id" not in parameters:
                        parameters["email_id"] = email.id
                        print(f"🔧 AUTO-ADDED email_id: {email.id} for {tool_name}.{action}")
                    elif action in email_tool_actions_needing_id:
                        print(f"✅ EXISTING email_id: {parameters.get('email_id')} for {tool_name}.{action}")
                
                # Add email context to parameters if needed for other tools
                if "email" not in parameters and tool_name != "EmailTool":
                    parameters["email"] = email.dict()
                
                # Add previous results to context for dependent operations
                parameters["context"] = context["previous_results"]
                
                # Execute the tool
                result = await self.tools.execute_tool(tool_name, action, parameters)
                
                execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                execution = ToolExecution(
                    step=step.step,
                    tool=tool_name,
                    action=action,
                    parameters=parameters,
                    result=result.dict(),
                    success=result.success,
                    execution_time_ms=execution_time_ms,
                    timestamp=datetime.now()
                )
                
                if not result.success:
                    execution.error_message = result.message
                
                executions.append(execution)
                
                # Store result for next steps
                context["previous_results"][f"step_{step.step}"] = result.data
                
                # If classification happened, update the category
                if tool_name == "EmailClassifier" and result.success:
                    decision.category = EmailCategory(result.data.get("category", decision.category.value))
                
                # Add delay between operations to be respectful to APIs
                await asyncio.sleep(0.1)
                
            except Exception as e:
                execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                execution = ToolExecution(
                    step=step.step,
                    tool=step.tool,
                    action=step.action,
                    parameters=step.parameters,
                    result={"error": str(e)},
                    success=False,
                    error_message=str(e),
                    execution_time_ms=execution_time_ms,
                    timestamp=datetime.now()
                )
                executions.append(execution)
        
        return executions
    
    async def generate_email_draft(self, request: DraftRequest) -> DraftResponse:
        """Generate email draft using the agent brain"""
        
        prompt = f"""
Generate a professional email draft based on this request:

Context: {request.context}
Tone: {request.tone}
Recipient: {request.recipient or 'Unknown'}
Subject: {request.subject or 'To be determined'}

Key Points:
{chr(10).join(f"- {point}" for point in request.key_points)}

REQUIREMENTS:
1. Create a well-structured email that matches the requested tone
2. Include all key points naturally
3. Make it professional and appropriate for the context
4. Suggest a subject line if not provided
5. Keep it concise but complete

Return ONLY the email content, no additional formatting or explanations.
"""
        
        try:
            response = self.model.generate_content(prompt)
            draft_content = response.text.strip()
            
            # Extract subject if suggested in the draft
            subject_suggestion = request.subject
            if not subject_suggestion:
                # Try to extract a subject line from the draft
                lines = draft_content.split('\n')
                for line in lines:
                    if line.lower().startswith('subject:'):
                        subject_suggestion = line.replace('subject:', '').strip()
                        # Remove the subject line from draft content
                        draft_content = '\n'.join(l for l in lines if not l.lower().startswith('subject:'))
                        break
            
            return DraftResponse(
                draft=draft_content,
                subject_suggestion=subject_suggestion,
                confidence=0.9
            )
            
        except Exception as e:
            return DraftResponse(
                draft=f"I apologize, but I encountered an error generating the email draft: {str(e)}",
                subject_suggestion=request.subject or "Email Draft",
                confidence=0.1
            )

# ==================== EMAIL AGENT ====================
class EmailAgent:
    """The main autonomous email agent"""
    
    def __init__(self):
        self.brain = AgentBrain()
        self.database = AgentDatabase()
        self.is_running = False
        self.current_task = None
        self.start_time = None  # Track when monitoring started
        self.processed_emails = set()  # Keep track of already processed email IDs
        
    async def process_email(self, email: Email) -> Dict[str, Any]:
        """
        Main agent processing pipeline
        """
        session_id = str(uuid.uuid4())
        start_time = datetime.now()
        self.current_task = f"Processing email: {email.subject[:50]}..."
        
        try:
            # Step 0: Apply custom pre-processing rules
            await self._apply_custom_rules(email)
            
            # Step 1: Agent analyzes and plans
            decision = await self.brain.analyze_and_plan(email)
            
            # Step 2: Execute the plan using tools
            executions = await self.brain.execute_plan(decision, email)
            
            # Step 3: Calculate metrics
            end_time = datetime.now()
            total_time = int((end_time - start_time).total_seconds() * 1000)
            success_rate = sum(1 for ex in executions if ex.success) / len(executions) if executions else 0
            
            # Step 4: Create session record
            session = AgentSession(
                session_id=session_id,
                email=email,
                decision=decision,
                executions=executions,
                final_status="completed",
                success_rate=success_rate,
                total_execution_time_ms=total_time,
                created_at=start_time,
                completed_at=end_time
            )
            
            # Step 5: Log the complete agent decision and execution
            self.database.log_agent_session(session)
            
            self.current_task = None
            
            return {
                "session_id": session_id,
                "email_id": email.id,
                "agent_decision": decision.dict(),
                "tool_executions": [ex.dict() for ex in executions],
                "success_count": sum(1 for ex in executions if ex.success),
                "total_steps": len(executions),
                "success_rate": success_rate,
                "execution_time_ms": total_time
            }
            
        except Exception as e:
            self.current_task = None
            error_session = AgentSession(
                session_id=session_id,
                email=email,
                decision=AgentDecision(
                    email_id=email.id,
                    reasoning=f"Processing failed: {str(e)}",
                    priority=Priority.MEDIUM,
                    category=EmailCategory.UNKNOWN,
                    execution_plan=[],
                    expected_outcome="Error occurred",
                    timestamp=datetime.now()
                ),
                executions=[],
                final_status="error",
                success_rate=0.0,
                total_execution_time_ms=0,
                created_at=start_time,
                completed_at=datetime.now()
            )
            
            self.database.log_agent_session(error_session)
            raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")
    
    async def _apply_custom_rules(self, email: Email):
        """
        Apply custom pre-processing rules before main agent analysis
        """
        try:
            # Rule 1: Google Classroom emails
            if email.sender_email and email.sender_email.lower() == "no-reply@classroom.google.com":
                print(f"📚 Detected Google Classroom email: {email.subject}")
                
                # Apply Google Classroom label immediately
                result = await self.brain.tools.execute_tool(
                    "EmailTool",
                    "apply_category_label",
                    {
                        "email_id": email.id,
                        "category": "google_classroom"  # Special category for classroom
                    }
                )
                
                if result.success:
                    print(f"✅ Applied Google Classroom label to email {email.id}")
                else:
                    print(f"⚠️ Failed to apply Classroom label: {result.message}")
            
            # Add more custom rules here in the future
            # Rule 2: Example - Urgent emails based on subject keywords
            # if any(keyword in email.subject.lower() for keyword in ['urgent', 'asap', 'emergency']):
            #     # Apply urgent processing
            #     pass
            
        except Exception as e:
            print(f"Error applying custom rules: {e}")
    
    async def monitor_emails(self):
        """Background email monitoring for NEW emails only (since server start)"""
        self.is_running = True
        self.start_time = datetime.now()
        
        print(f"🚀 Started monitoring for NEW emails received after: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📧 Email check interval: {config.EMAIL_CHECK_INTERVAL} seconds")
        
        while self.is_running:
            try:
                self.current_task = "Checking for new emails..."
                
                # Get recent emails (including read/unread) since monitoring started
                result = await self.brain.tools.execute_tool(
                    "EmailTool", 
                    "get_recent_emails", 
                    {
                        "limit": config.MAX_EMAILS_PER_BATCH,
                        "since_date": self.start_time.isoformat()
                    }
                )
                
                if result.success:
                    all_emails = result.data.get("emails", [])
                    
                    # Filter for truly NEW emails (not already processed)
                    new_emails = []
                    for email_data in all_emails:
                        email_id = email_data.get("id")
                        if email_id and email_id not in self.processed_emails:
                            new_emails.append(email_data)
                    
                    if new_emails:
                        print(f"📬 Found {len(new_emails)} NEW emails to process (out of {len(all_emails)} recent emails)")
                        
                        for email_data in new_emails:
                            try:
                                email = Email(**email_data)
                                print(f"🔥 Processing NEW email: '{email.subject}' from {email.sender}")
                                
                                # Mark as being processed
                                self.processed_emails.add(email.id)
                                
                                # Process the email
                                await self.process_email(email)
                                
                                # Add small delay between emails
                                await asyncio.sleep(1)
                                
                            except Exception as e:
                                print(f"❌ Error processing email {email_data.get('id', 'unknown')}: {e}")
                                continue
                    else:
                        print(f"✅ No new emails found (checked {len(all_emails)} recent emails)")
                else:
                    print(f"⚠️ Failed to fetch recent emails: {result.message}")
                
                self.current_task = None
                
            except Exception as e:
                print(f"💥 Error in email monitoring: {e}")
                self.current_task = None
            
            # Wait before checking for new emails
            await asyncio.sleep(config.EMAIL_CHECK_INTERVAL)
    
    def get_status(self) -> AgentStatus:
        """Get current agent status with monitoring details"""
        stats = self.database.get_stats()
        
        return AgentStatus(
            is_running=self.is_running,
            total_processed=stats.get("total_processed", 0),
            last_activity=datetime.fromisoformat(stats.get("last_activity")) if stats.get("last_activity") else None,
            current_task=self.current_task,
            available_tools=self.brain.tools.list_tools(),
            system_health="healthy" if self.is_running else "stopped",
            monitoring_since=self.start_time.isoformat() if self.start_time else None,
            processed_emails_count=len(self.processed_emails)
        )
    
    def reset_monitoring(self):
        """Reset monitoring state - useful for testing or restarting"""
        self.start_time = datetime.now()
        self.processed_emails.clear()
        print(f"🔄 Monitoring reset - now tracking emails since: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

# ==================== SIMPLE DATABASE ====================
class AgentDatabase:
    """Simple JSON database for agent logs and sessions"""
    
    def __init__(self, filepath=None):
        self.filepath = filepath or config.AGENT_LOG_FILE
        self.data = self.load()
    
    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return {
            "sessions": [], 
            "tool_stats": {}, 
            "performance": {},
            "last_updated": datetime.now().isoformat()
        }
    
    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self.data["last_updated"] = datetime.now().isoformat()
        
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def log_agent_session(self, session: AgentSession):
        """Log a complete agent session"""
        session_dict = session.dict()
        
        # Convert datetime objects to strings for JSON serialization
        for key, value in session_dict.items():
            if isinstance(value, datetime):
                session_dict[key] = value.isoformat()
        
        # Ensure sessions key exists
        if "sessions" not in self.data:
            self.data["sessions"] = []
        
        self.data["sessions"].append(session_dict)
        self.update_stats(session)
        self.save()
    
    def update_stats(self, session: AgentSession):
        """Update performance statistics"""
        # Ensure required keys exist
        if "tool_stats" not in self.data:
            self.data["tool_stats"] = {}
        if "performance" not in self.data:
            self.data["performance"] = {}
            
        category = session.decision.category.value
        
        if category not in self.data["tool_stats"]:
            self.data["tool_stats"][category] = {
                "count": 0,
                "success_rate": 0,
                "avg_execution_time": 0,
                "avg_steps": 0
            }
        
        stats = self.data["tool_stats"][category]
        stats["count"] += 1
        
        # Update running averages
        old_count = stats["count"] - 1
        stats["success_rate"] = (stats["success_rate"] * old_count + session.success_rate) / stats["count"]
        stats["avg_execution_time"] = (stats["avg_execution_time"] * old_count + session.total_execution_time_ms) / stats["count"]
        stats["avg_steps"] = (stats["avg_steps"] * old_count + len(session.executions)) / stats["count"]
        
        # Update tool usage stats
        for execution in session.executions:
            tool_name = execution.tool
            if tool_name not in self.data["performance"]:
                self.data["performance"][tool_name] = {
                    "usage_count": 0,
                    "success_count": 0,
                    "avg_execution_time": 0
                }
            
            perf = self.data["performance"][tool_name]
            perf["usage_count"] += 1
            if execution.success:
                perf["success_count"] += 1
            
            if execution.execution_time_ms:
                old_usage = perf["usage_count"] - 1
                perf["avg_execution_time"] = (perf["avg_execution_time"] * old_usage + execution.execution_time_ms) / perf["usage_count"]
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent agent sessions"""
        return self.data["sessions"][-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        total_sessions = len(self.data["sessions"])
        
        if total_sessions == 0:
            return {
                "total_processed": 0,
                "average_success_rate": 0,
                "last_activity": None
            }
        
        recent_sessions = self.data["sessions"][-10:]
        avg_success_rate = sum(s.get("success_rate", 0) for s in recent_sessions) / len(recent_sessions)
        
        return {
            "total_processed": total_sessions,
            "average_success_rate": avg_success_rate,
            "last_activity": self.data["sessions"][-1].get("completed_at") if self.data["sessions"] else None,
            "tool_stats": self.data["tool_stats"],
            "performance": self.data["performance"]
        }

# ==================== FASTAPI APPLICATION ====================
app = FastAPI(
    title="AI Email Agent - Autonomous Tool-Based System",
    description="Intelligent email processing agent powered by Gemini AI",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent
agent = EmailAgent()

# ==================== STARTUP ====================
@app.on_event("startup")
async def startup():
    """Start the autonomous agent"""
    print("Starting AI Email Agent...")
    print(f"Email check interval: {config.EMAIL_CHECK_INTERVAL} seconds")
    print(f"Available tools: {', '.join(agent.brain.tools.list_tools())}")
    
    # Validate configuration
    missing_configs = Config.validate_required_configs()
    if missing_configs:
        print(f"WARNING: Missing configurations: {', '.join(missing_configs)}")
    
    # Start email monitoring in background
    if config.GEMINI_API_KEY:
        asyncio.create_task(agent.monitor_emails())
        print("AI Email Agent started successfully!")
    else:
        print("ERROR: GEMINI_API_KEY not configured. Agent will not start monitoring.")

@app.on_event("shutdown")
async def shutdown():
    """Shutdown the agent gracefully"""
    agent.is_running = False
    print("AI Email Agent stopped")

# ==================== API ENDPOINTS ====================

@app.get("/")
def home():
    return {
        "status": "running",
        "agent_type": "Autonomous AI Email Agent",
        "brain": "Gemini 1.5 Pro",
        "tools": agent.brain.tools.list_tools(),
        "capabilities": [
            "Autonomous email analysis",
            "Intelligent planning",
            "Tool-based execution",
            "Performance monitoring",
            "Chrome extension integration"
        ],
        "version": "2.0.0",
        "config_status": Config.get_config_summary()
    }

@app.post("/agent/process")
async def process_email(email: Email):
    """Let the agent autonomously process an email"""
    return await agent.process_email(email)

@app.get("/agent/status")
def get_agent_status():
    """Get current agent status"""
    return agent.get_status().dict()

@app.get("/agent/sessions")
def get_recent_sessions(limit: int = 10):
    """Get recent agent processing sessions"""
    return {
        "sessions": agent.database.get_recent_sessions(limit),
        "total_sessions": len(agent.database.data["sessions"])
    }

@app.get("/agent/performance")
def get_agent_performance():
    """Get agent performance statistics"""
    stats = agent.database.get_stats()
    
    return {
        "summary": {
            "total_processed": stats["total_processed"],
            "average_success_rate": stats["average_success_rate"],
            "last_activity": stats["last_activity"]
        },
        "category_stats": stats["tool_stats"],
        "tool_performance": stats["performance"],
        "recent_sessions": [
            {
                "session_id": session.get("session_id"),
                "email_subject": session.get("email", {}).get("subject", "Unknown"),
                "success_rate": session.get("success_rate", 0),
                "execution_time_ms": session.get("total_execution_time_ms", 0),
                "completed_at": session.get("completed_at")
            }
            for session in agent.database.get_recent_sessions(10)
        ]
    }

@app.post("/agent/ask")
async def ask_agent(question: str):
    """Ask the agent brain a question"""
    prompt = f"""
    You are an AI email management agent. Answer this question based on your capabilities:
    
    Question: {question}
    
    Available tools: {', '.join(agent.brain.tools.list_tools())}
    Tool descriptions:
    {agent.brain.tools.get_tools_description()}
    
    Provide a helpful response about what you can do or how you would handle the situation.
    """
    
    try:
        response = agent.brain.model.generate_content(prompt)
        return {
            "question": question,
            "agent_response": response.text,
            "available_tools": agent.brain.tools.list_tools()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")

@app.post("/agent/manual-check")
async def manual_email_check(background_tasks: BackgroundTasks):
    """Manually trigger email check for NEW emails only"""
    if not agent.is_running:
        raise HTTPException(status_code=400, detail="Agent is not running")
    
    async def check_emails():
        try:
            # Use the new get_recent_emails instead of get_unread
            result = await agent.brain.tools.execute_tool(
                "EmailTool", 
                "get_recent_emails", 
                {
                    "limit": 5,
                    "since_date": agent.start_time.isoformat() if agent.start_time else None
                }
            )
            if result.success:
                all_emails = result.data.get("emails", [])
                new_emails = [e for e in all_emails if e.get("id") not in agent.processed_emails]
                
                for email_data in new_emails:
                    email = Email(**email_data)
                    agent.processed_emails.add(email.id)
                    await agent.process_email(email)
                    
                print(f"Manual check: processed {len(new_emails)} new emails")
        except Exception as e:
            print(f"Manual email check failed: {e}")
    
    background_tasks.add_task(check_emails)
    
    return {"message": "Manual email check started (NEW emails only)", "background_task": True}

@app.post("/agent/reset-monitoring")
def reset_monitoring():
    """Reset monitoring state to start tracking new emails from now"""
    agent.reset_monitoring()
    return {
        "message": "Monitoring reset successfully",
        "new_start_time": agent.start_time.isoformat() if agent.start_time else None,
        "processed_emails_cleared": True
    }

# ==================== CHROME EXTENSION API ====================
@app.post("/api/chrome/draft-ai")
async def generate_draft(request: DraftRequest):
    """Generate email draft using the agent brain"""
    response = await agent.brain.generate_email_draft(request)
    return response.dict()

@app.get("/api/chrome/agent-status")
def get_chrome_agent_status():
    """Get current agent status for Chrome extension"""
    status = agent.get_status()
    recent_sessions = agent.database.get_recent_sessions(5)
    
    return {
        "is_running": status.is_running,
        "total_processed": status.total_processed,
        "last_activity": status.last_activity.isoformat() if status.last_activity else None,
        "current_task": status.current_task,
        "system_health": status.system_health,
        "recent_activity": [
            {
                "email_subject": session.get("email", {}).get("subject", "Unknown")[:50],
                "category": session.get("decision", {}).get("category", "unknown"),
                "success_rate": session.get("success_rate", 0),
                "completed_at": session.get("completed_at")
            }
            for session in recent_sessions
        ],
        "available_tools": status.available_tools
    }

@app.get("/api/chrome/tools")
def get_chrome_tools_info():
    """Get tools information for Chrome extension"""
    return {
        "tools": agent.brain.tools.get_tool_stats(),
        "descriptions": {
            name: tool.description.strip()
            for name, tool in agent.brain.tools.tools.items()
        }
    }

@app.post("/api/chrome/analyze-style")
async def analyze_writing_style(request: Dict[str, Any]):
    """Analyze writing style from past emails and generate matching draft"""
    try:
        recipient = request.get("recipient")
        intent = request.get("intent")
        
        if not recipient or not intent:
            raise HTTPException(
                status_code=400, 
                detail="Both 'recipient' and 'intent' are required"
            )
        
        # Fetch last 5 emails sent to this person
        email_result = await agent.brain.tools.execute_tool(
            "EmailTool", 
            "get_sent_emails", 
            {"recipient": recipient, "limit": 5}
        )
        
        if not email_result.success:
            return {
                "error": "Failed to fetch past emails",
                "fallback_draft": await _generate_generic_draft(intent, recipient),
                "style_analysis": "Using generic professional style due to no past email history",
                "confidence": 0.3
            }
        
        past_emails = email_result.data.get("emails", [])
        
        if len(past_emails) < 2:
            # Use generic style if we have too few emails
            return {
                "style_analysis": f"Only {len(past_emails)} past email(s) found. Using general style.",
                "generated_draft": await _generate_generic_draft(intent, recipient),
                "confidence": 0.4,
                "past_email_count": len(past_emails)
            }
        
        # Analyze writing style with Gemini
        style_analysis = await _analyze_email_style(past_emails, intent, recipient)
        
        return {
            "style_analysis": style_analysis["analysis"],
            "generated_draft": style_analysis["draft"],
            "confidence": style_analysis["confidence"],
            "past_email_count": len(past_emails),
            "detected_patterns": style_analysis["patterns"],
            "recipient": recipient
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Style analysis failed: {str(e)}"
        )

async def _analyze_email_style(past_emails: List[Dict], intent: str, recipient: str) -> Dict[str, Any]:
    """Analyze writing style using Gemini"""
    
    # Prepare email samples for analysis
    email_samples = []
    for i, email in enumerate(past_emails[:5]):
        email_samples.append(f"Email {i+1}: {email.get('body', '')[:500]}")
    
    style_prompt = f"""
Analyze the writing style from these {len(past_emails)} past emails to {recipient}:

{chr(10).join(email_samples)}

Extract writing patterns:
1. Greeting style (Dear/Hi/Hello/etc.)
2. Formality level (formal/casual/mixed)
3. Sentence structure (short/medium/long)
4. Closing style (Best regards/Thanks/Cheers/etc.)
5. Tone (professional/friendly/direct/academic)
6. Common phrases and expressions used
7. Overall communication style

Then generate a new email for: "{intent}"

IMPORTANT: Match the EXACT style patterns found above. Use the same:
- Greeting format
- Level of formality
- Sentence structure
- Closing style
- Common phrases
- Overall tone

Return your response in this JSON format:
{{
    "style_patterns": {{
        "greeting": "detected greeting pattern",
        "formality": "formal/casual/mixed",
        "tone": "detected tone",
        "closing": "detected closing style",
        "common_phrases": ["phrase1", "phrase2"],
        "sentence_style": "short/medium/long"
    }},
    "confidence_score": 0.85,
    "generated_email": "the new email matching the style"
}}
"""
    
    try:
        response = agent.brain.model.generate_content(style_prompt)
        response_text = response.text.strip()
        
        # Extract JSON from response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            analysis_data = json.loads(json_str)
            
            return {
                "analysis": f"Detected {analysis_data.get('style_patterns', {}).get('formality', 'mixed')} style with {analysis_data.get('style_patterns', {}).get('tone', 'neutral')} tone",
                "draft": analysis_data.get("generated_email", ""),
                "confidence": analysis_data.get("confidence_score", 0.7),
                "patterns": analysis_data.get("style_patterns", {})
            }
        else:
            # Fallback if JSON parsing fails
            return {
                "analysis": "Style analysis completed",
                "draft": response_text,
                "confidence": 0.6,
                "patterns": {}
            }
            
    except Exception as e:
        print(f"Style analysis error: {e}")
        # Return generic draft on error
        return {
            "analysis": f"Style analysis failed: {str(e)}. Using generic style.",
            "draft": await _generate_generic_draft(intent, recipient),
            "confidence": 0.3,
            "patterns": {}
        }

async def _generate_generic_draft(intent: str, recipient: str) -> str:
    """Generate a generic professional email draft"""
    
    # Determine formality based on recipient domain
    if recipient.endswith('.edu') or 'professor' in recipient.lower() or 'dr.' in recipient.lower():
        greeting = "Dear Professor" if 'professor' in recipient.lower() else "Dear Dr." if 'dr.' in recipient.lower() else "Dear Sir/Madam"
        closing = "Best regards"
        tone = "formal academic"
    else:
        greeting = "Hi there"
        closing = "Best regards"
        tone = "professional"
    
    generic_prompt = f"""
Generate a {tone} email for: "{intent}"
Recipient: {recipient}

Use this format:
{greeting},

[Email body matching the intent]

{closing},
[Your name]

Keep it concise, professional, and appropriate for the context.
"""
    
    try:
        response = agent.brain.model.generate_content(generic_prompt)
        return response.text.strip()
    except:
        return f"""{greeting},

I hope this email finds you well. I wanted to reach out regarding: {intent}

I would appreciate your assistance with this matter.

{closing},
[Your name]"""

@app.get("/api/chrome/style-suggestions")
def get_style_suggestions():
    """Get available style adjustment options for Chrome extension"""
    return {
        "adjustments": [
            {"id": "more_formal", "label": "More formal", "description": "Increase formality level"},
            {"id": "more_casual", "label": "More casual", "description": "Decrease formality level"},
            {"id": "add_urgency", "label": "Add urgency", "description": "Make the email more urgent"},
            {"id": "more_polite", "label": "More polite", "description": "Increase politeness"},
            {"id": "shorter", "label": "Make shorter", "description": "Reduce email length"},
            {"id": "longer", "label": "More detailed", "description": "Add more details"}
        ],
        "templates": {
            "academic": "Formal academic communication style",
            "business": "Professional business communication",
            "casual": "Friendly casual communication",
            "urgent": "Direct urgent communication"
        }
    }

# ==================== HEALTH CHECK ====================
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_running": agent.is_running,
        "database_accessible": os.path.exists(agent.database.filepath),
        "tools_count": len(agent.brain.tools.tools)
    }

# ==================== DEV ENDPOINTS ====================
if config.DEBUG:
    @app.post("/dev/test-email")
    async def test_email_processing():
        """Test endpoint with sample email"""
        sample_email = Email(
            id="test_" + str(int(datetime.now().timestamp())),
            subject="Test Job Application Deadline - Software Engineer at TechCorp",
            sender="hr@techcorp.com",
            sender_email="hr@techcorp.com",
            body="""Dear Student,

We are pleased to inform you about an exciting opportunity at TechCorp.

Position: Software Engineer
Location: San Francisco, CA
Application Deadline: December 31, 2024

To apply, please visit: https://techcorp.com/careers/apply

Please submit your application by the deadline mentioned above.

Best regards,
HR Team
TechCorp""",
            timestamp=datetime.now(),
            is_read=False
        )
        
        return await agent.process_email(sample_email)
    
    @app.get("/dev/reset-database")
    def reset_database():
        """Reset the agent database (dev only)"""
        agent.database.data = {
            "sessions": [], 
            "tool_stats": {}, 
            "performance": {},
            "last_updated": datetime.now().isoformat()
        }
        agent.database.save()
        return {"message": "Database reset successfully"}

# ==================== MAIN ====================
if __name__ == "__main__":
    print("🚀 Starting AI Email Agent Server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )