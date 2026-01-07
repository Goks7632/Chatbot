"""
Function Executor for Haibot API Integration.
Routes LLM function calls to the appropriate API service methods.
"""
import json
import logging
from typing import Dict, Any, Optional

from app.services.haibot_api_service import HaibotApiService
from app.services.session_context import SessionContext

logger = logging.getLogger(__name__)


class FunctionExecutor:
    """
    Executes LLM function calls by routing them to the Haibot API service.
    
    Handles data dependencies between endpoints by using the session context
    for profileId/tenantId and resolving names to IDs when necessary.
    """
    
    # Mapping of task names to task IDs (extend this based on available tasks)
    TASK_ID_MAP = {
        "bank reconciliation": "task-bank-recon",
        "payroll processing": "task-payroll",
        "invoice processing": "task-invoice",
        "transaction categorization": "task-categorization",
        "report generation": "task-report",
    }
    
    def __init__(
        self,
        api_service: HaibotApiService,
        session: SessionContext
    ):
        """
        Initialize the function executor.
        
        Args:
            api_service: HaibotApiService instance
            session: SessionContext with verified user data
        """
        self.api = api_service
        self.session = session
    
    def execute(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a function call and return the result as a string for the LLM.
        
        Args:
            function_name: Name of the function to execute
            arguments: Arguments passed by the LLM
            
        Returns:
            String result to be sent back to the LLM
        """
        try:
            if function_name == "get_all_clients":
                return self._get_all_clients(arguments.get("limit"))
            
            elif function_name == "get_client_details":
                return self._get_client_details(arguments.get("client_identifier", ""))
            
            elif function_name == "create_client":
                return self._create_client(
                    company_name=arguments.get("company_name", ""),
                    source_name=arguments.get("source_name")
                )
            
            elif function_name == "list_scheduled_tasks":
                return self._list_scheduled_tasks(arguments.get("limit"))
            
            elif function_name == "get_schedule_details":
                return self._get_schedule_details(arguments.get("schedule_identifier", ""))
            
            elif function_name == "schedule_task":
                return self._schedule_task(
                    task_name=arguments.get("task_name", ""),
                    date=arguments.get("date", ""),
                    time=arguments.get("time", "")
                )
            
            elif function_name == "run_task_now":
                return self._run_task_now(arguments.get("task_identifier", ""))
            
            elif function_name == "list_task_runs":
                return self._list_task_runs(arguments.get("limit"))
            
            elif function_name == "get_task_run_status":
                return self._get_task_run_status(arguments.get("run_id", ""))
            
            elif function_name == "import_clients":
                return self._import_clients(arguments.get("file_path", ""))
            
            elif function_name == "get_user_profile":
                return self._get_user_profile(arguments.get("include_details", True))
            
            else:
                return f"Unknown function: {function_name}"
                
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return f"Error executing {function_name}: {str(e)}"
    
    # ==================== Client Functions ====================
    
    def _get_all_clients(self, limit: Optional[int] = None, refresh: bool = False) -> str:
        """Get all clients and format for LLM."""
        # Ensure session is verified
        if not self.session.is_verified():
            try:
                result = self.api.verify_session(self.session.user_id)
                self.session.update_from_verification(result)
            except Exception as e:
                return f"Error: Unable to verify session. {str(e)}"
        
        # User confirmed profile_id is the same as session_id
        clients = self.api.get_all_clients(session_id=self.session.profile_id)
        
        if not clients:
            return "No clients found in the system."
            
        # Apply limit if provided
        if limit and limit > 0:
            clients = clients[:limit]
        
        client_list = []
        for client in clients:
            if not client: continue  # Skip null entries
            name = client.get("name", "Unknown")
            email = client.get("email", "N/A")
            status = client.get("status", "N/A")
            client_id = client.get("id", "N/A")
            client_list.append(f"- {name} (ID: {client_id}, Email: {email}, Status: {status})")
        
        return f"Found {len(clients)} clients:\n" + "\n".join(client_list)
    
    def _get_client_details(self, client_identifier: str) -> str:
        """Get detailed information about a specific client."""
        # Ensure session is verified
        if not self.session.is_verified():
            try:
                result = self.api.verify_session(self.session.user_id)
                self.session.update_from_verification(result)
            except Exception as e:
                return f"Error: Unable to verify session. {str(e)}"
        
        if not client_identifier:
            return "Please provide a client name or ID."
        
        # Try to get by ID first
        client = self.api.get_client_by_id(client_identifier)
        
        # If not found, try searching by name
        if not client:
            client = self.api.find_client_by_name(client_identifier)
        
        if not client:
            return f"Could not find client matching '{client_identifier}'"
        
        # Extract client data (unwrap if needed)
        if isinstance(client, dict) and "data" in client:
            client = client["data"]
        
        # Format detailed client information
        details = [
            f"Client: {client.get('company_name', 'Unknown')}",
            f"ID: {client.get('id', 'N/A')}",
            f"Source: {client.get('source_name', 'N/A')}",
            f"Published: {client.get('published', 'N/A')}",
            f"Date Range: {client.get('date_range', 'N/A')} days",
            f"Amount Tracking: Received={client.get('amount_received', 'N/A')}, Spent={client.get('amount_spent', 'N/A')}",
            f"Created: {client.get('created_at', 'N/A')}"
        ]
        
        return "\n".join(details)
    
    def _create_client(self, company_name: str, source_name: str = None, **kwargs) -> str:
        """Create a new client."""
        # Ensure session is verified
        if not self.session.is_verified():
            try:
                result = self.api.verify_session(self.session.user_id)
                self.session.update_from_verification(result)
            except Exception as e:
                return f"Error: Unable to verify session. {str(e)}"
        
        if not company_name:
            return "Please provide a company name for the new client."
        
        try:
            # Prepare optional fields
            optional_fields = {}
            if source_name:
                optional_fields["source_name"] = source_name
            optional_fields.update(kwargs)
            
            # Create client
            result = self.api.create_client(
                user_id=self.session.user_id,
                company_name=company_name,
                **optional_fields
            )
            
            # Extract created client
            created_client = result.get("data", result)
            client_id = created_client.get("id", "unknown")
            
            return f"Successfully created client '{company_name}' (ID: {client_id})"
            
        except Exception as e:
            return f"Failed to create client: {str(e)}"
    
    # ... (skipping client details) ...

    # ==================== Schedule Functions ====================
    
    def _list_scheduled_tasks(self, limit: Optional[int] = None, refresh: bool = False) -> str:
        """Get all scheduled tasks and format for LLM."""
        # Ensure session is verified
        if not self.session.is_verified():
            try:
                result = self.api.verify_session(self.session.user_id)
                self.session.update_from_verification(result)
            except Exception as e:
                return f"Error: Unable to verify session. {str(e)}"
        
        schedules = self.api.get_all_task_schedules(session_id=self.session.profile_id)
        
        if not schedules:
            return "No scheduled tasks found."
            
        # Apply limit if provided
        if limit and limit > 0:
            schedules = schedules[:limit]
        
        schedule_list = []
        for sched in schedules:
            if not sched: continue
            sched_id = sched.get("id", "N/A")
            scheduled_time = sched.get("scheduled_time", "N/A")
            priority = sched.get("priority", "N/A")
            recurring = sched.get("recurring", False)
            frequency = sched.get("frequency", "N/A") if recurring else "one-time"
            schedule_list.append(f"- Schedule ID: {sched_id}, Time: {scheduled_time}, Priority: {priority}, Type: {frequency}")
            
        return f"Found {len(schedules)} schedules:\n" + "\n".join(schedule_list)
    
    def _get_schedule_details(self, schedule_identifier: str) -> str:
        """Get detailed information about a specific schedule."""
        # Ensure session is verified
        if not self.session.is_verified():
            try:
                result = self.api.verify_session(self.session.user_id)
                self.session.update_from_verification(result)
            except Exception as e:
                return f"Error: Unable to verify session. {str(e)}"
        
        if not schedule_identifier:
            return "Please provide a schedule name or ID."
        
        # Try to get by ID first
        schedule = self.api.get_task_schedule_by_id(schedule_identifier)
        
        # If not found, try searching by name  
        if not schedule:
            schedule = self.api.find_schedule_by_name(schedule_identifier)
        
        if not schedule:
            return f"Could not find schedule matching '{schedule_identifier}'"
        
        # Extract schedule data (unwrap if needed)
        if isinstance(schedule, dict) and "data" in schedule:
            schedule = schedule["data"]
        
        # Format detailed schedule information
        details = [
            f"Schedule ID: {schedule.get('id', 'N/A')}",
            f"Scheduled Time: {schedule.get('scheduled_time', 'N/A')}",
            f"Priority: {schedule.get('priority', 'N/A')}",
            f"Recurring: {'Yes' if schedule.get('recurring') else 'No'}",
        ]
        
        if schedule.get('recurring'):
            details.append(f"Frequency: {schedule.get('frequency', 'N/A')}")
        
        if schedule.get('started'):
            details.append(f"Started: {schedule.get('started')}")
        
        return "\n".join(details)
    
    # ...

    # ==================== Task Run Functions ====================
    
    def _list_task_runs(self, limit: Optional[int] = None, refresh: bool = False) -> str:
        """Get all task runs and format for LLM."""
        # Ensure session is verified
        if not self.session.is_verified():
            try:
                result = self.api.verify_session(self.session.user_id)
                self.session.update_from_verification(result)
            except Exception as e:
                return f"Error: Unable to verify session. {str(e)}"
        
        runs = self.api.get_all_task_runs(session_id=self.session.profile_id)
        
        if not runs:
            return "No task runs found."
            
        # Apply limit if provided
        if limit and limit > 0:
            runs = runs[:limit]
        
        run_list = []
        for run in runs:
            if not run: continue
            run_id = run.get("id", "N/A")
            status = run.get("status", "Unknown")
            started = run.get("started_at", "N/A")
            run_list.append(f"- Run {run_id}: {status} (Started: {started})")
            
        return f"Found {len(runs)} runs:\n" + "\n".join(run_list)
    
    def _get_task_run_status(self, run_id: str) -> str:
        """Get task run status by ID."""
        run = self.api.get_task_run_by_id(run_id)
        
        if not run:
            return f"Could not find task run with ID '{run_id}'"
        
        details = [
            f"Run ID: {run.get('id', 'N/A')}",
            f"Status: {run.get('status', 'N/A')}",
            f"Started: {run.get('started_at', 'N/A')}",
            f"Completed: {run.get('completed_at', 'N/A')}",
            f"Result: {run.get('result', 'No result yet')}",
        ]
        
        return "\n".join(details)
    
    def _run_task_now(self, identifier: str) -> str:
        """Trigger immediate execution of a scheduled task."""
        if not self.session.is_verified():
            return "Session not verified. Please provide your user ID first."
        
        # Find the schedule
        schedule = self.api.find_schedule_by_name(identifier)
        if not schedule:
            schedule = self.api.get_task_schedule_by_id(identifier)
        
        if not schedule:
            return f"Could not find scheduled task matching '{identifier}'"
        
        try:
            result = self.api.create_task_run(
                scheduled_id=schedule["id"],
                profile_id=self.session.profile_id
            )
            
            run_id = result.get("id", "unknown")
            return f"Task execution triggered successfully. Run ID: {run_id}"
            
        except Exception as e:
            return f"Failed to trigger task execution: {str(e)}"
    
    # ==================== Import Functions ====================
    
    def _import_clients(self, file_path: str) -> str:
        """Import clients from an Excel file."""
        if not file_path:
            return "No file path provided. Please specify the path to the Excel file."
        
        if not self.session.is_verified():
            return "Session not verified. Please provide your user ID first."
        
        try:
            result = self.api.import_clients_from_file(
                file_path=file_path,
                user_id=self.session.user_id
            )
            
            imported = result.get("imported", 0)
            failed = result.get("failed", 0)
            
            if imported > 0:
                return f"Successfully imported {imported} clients from {file_path}. Failed: {failed}"
            else:
                return f"Import completed but no clients were imported. Check the file format."
                
        except Exception as e:
            return f"Failed to import clients: {str(e)}"
    
    # ==================== Profile Functions ====================
    
    def _get_user_profile(self, include_details: bool = True, refresh: bool = False) -> str:
        """Get the current user's profile information."""
        if not self.session.is_verified():
            # Try to verify first
            try:
                result = self.api.verify_session(self.session.user_id)
                self.session.update_from_verification(result)
            except Exception as e:
                return f"Could not retrieve profile. Session verification failed: {str(e)}"
        
        # Now fetch the full profile
        try:
            result = self.api.verify_session(self.session.user_id)
            user = result.get("user", {})
            profile = user.get("profile", {})
            
            details = [
                f"User ID: {user.get('id', 'N/A')}",
                f"Email: {user.get('email', 'N/A')}",
                f"Company: {profile.get('company_name', 'N/A')}",
                f"Address: {profile.get('company_address', 'N/A')}",
                f"Country: {profile.get('country', 'N/A')}",
                f"Phone: {profile.get('mobile_phone', 'N/A')}",
                f"Role: {profile.get('role', 'N/A')}",
                f"Onboarded: {profile.get('onboarded', False)}",
                f"Free Trial Until: {profile.get('free_trial_date', 'N/A')}",
            ]
            
            return "User Profile:\n" + "\n".join(details)
            
        except Exception as e:
            return f"Failed to retrieve profile: {str(e)}"
    
    # ==================== Helper Methods ====================
    
    def _resolve_task_id(self, task_name: str) -> str:
        """
        Resolve a task name to a task ID.
        
        Args:
            task_name: Human-readable task name
            
        Returns:
            Task ID string
        """
        task_name_lower = task_name.lower()
        
        for name, task_id in self.TASK_ID_MAP.items():
            if name in task_name_lower or task_name_lower in name:
                return task_id
        
        # If not found, use the task name as ID (might be a direct ID)
        return task_name.replace(" ", "-").lower()
