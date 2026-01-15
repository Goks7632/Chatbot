"""
Function Executor for Haibot API Integration.
Routes LLM function calls to the appropriate API service methods.
"""
import json
import logging
import uuid
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
    
    def _is_uuid(self, val: str) -> bool:
        try:
            uuid.UUID(str(val))
            return True
        except ValueError:
            return False
    
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
            
            elif function_name == "get_available_tasks":
                return self._get_available_tasks()
            
            elif function_name == "schedule_task":
                return self._schedule_task(
                    task_id=arguments.get("task_id", ""),
                    date=arguments.get("date", ""),
                    time=arguments.get("time", ""),
                    priority=arguments.get("priority", "medium"),
                    recurring=arguments.get("recurring", False),
                    frequency=arguments.get("frequency", "daily")
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
            
            elif function_name == "create_task_run":
                return self._create_task_run(arguments.get("schedule_id", ""))
                
            elif function_name == "get_task_run_by_id":
                return self._get_task_run_by_id_wrapper(arguments.get("run_id", ""))
                
            elif function_name == "get_task_schedule_by_id":
                return self._get_task_schedule_by_id_wrapper(arguments.get("schedule_id", ""))
            
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
                if result:
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
            name = client.get("company_name", "Unknown")
            client_id = client.get("id", "N/A")
            # Email and status are not top-level fields in this API response
            published = client.get("published", "N/A")
            source = client.get("source_name", "N/A")
            client_list.append(f"- {name} (ID: {client_id}, Published: {published}, Source: {source})")
        
        return f"Found {len(clients)} clients:\n" + "\n".join(client_list)
    
    def _get_client_details(self, client_identifier: str) -> str:
        """Get detailed information about a specific client."""
        # Ensure session is verified
        if not self.session.is_verified():
            try:
                result = self.api.verify_session(self.session.user_id)
                if result:
                    self.session.update_from_verification(result)
            except Exception as e:
                return f"Error: Unable to verify session. {str(e)}"
        
        if not client_identifier:
            return "Please provide a client name or ID."
        
        # Try to get by ID first IF it looks like a UUID
        client = None
        if self._is_uuid(client_identifier):
            client = self.api.get_client_by_id(client_identifier, user_id=self.session.profile_id)
        
        # If not found or not a UUID, try searching by name
        if not client:
            client = self.api.find_client_by_name(client_identifier, user_id=self.session.profile_id)
        
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
                if result:
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
                profile_id=self.session.profile_id,
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

    def _get_available_tasks(self) -> str:
        """Get list of available task templates."""
        tasks = self.api.get_all_tasks()
        
        # Handle wrapped response
        if isinstance(tasks, dict) and "data" in tasks:
            tasks = tasks["data"]
            
        if not tasks:
            return "No task templates found."
            
        task_list = []
        for t in tasks:
            if not t: continue
            name = t.get("name", "Unknown")
            tid = t.get("id", "N/A")
            desc = t.get("description", "")
            task_list.append(f"- {name} (ID: {tid}): {desc}")
            
        return "Available Task Templates:\n" + "\n".join(task_list)

    def _schedule_task(self, task_identifier: str = None, task_id: str = None, date: str = "", time: str = "", priority: str = "medium", recurring: bool = False, frequency: str = "daily") -> str:
        """Create a new task schedule."""
        # Handle parameter alias from LLM
        target_task = task_identifier or task_id
        
        if not self.session.is_verified():
            try:
                result = self.api.verify_session(self.session.user_id)
                if result:
                   self.session.update_from_verification(result)
            except Exception as e:
                return f"Session error: {e}"
        
        if not target_task:
            return "Please provide a valid task name or ID."

        # Try to resolve task ID from name if needed
        final_task_id = target_task
        # If it doesn't look like a UUID, try to find by name
        if len(target_task) < 30: 
             tasks = self.api.get_all_tasks()
             # Unwrap
             if isinstance(tasks, dict) and "data" in tasks:
                 tasks = tasks["data"]
             
             found = False
             if tasks:
                 for t in tasks:
                     if target_task.lower() in t.get("name", "").lower():
                         final_task_id = t.get("id")
                         found = True
                         break
             
             if not found:
                 return f"Could not find task template matching '{target_task}'"

        try:
            result = self.api.create_task_schedule(
                task_id=final_task_id,
                time=time,
                date=date,
                profile_id=self.session.profile_id,
                priority=priority,
                recurring=recurring,
                frequency=frequency
            )
            
            sched_id = result.get("id", "unknown")
            return f"Successfully scheduled task (ID: {sched_id}) for {date} at {time}."
            
        except Exception as e:
            return f"Failed to schedule task: {str(e)}"
    
    # ==================== Schedule Functions ====================
    
    def _list_scheduled_tasks(self, limit: Optional[int] = None, refresh: bool = False) -> str:
        """Get all scheduled tasks and format for LLM."""
        # Ensure session is verified
        if not self.session.is_verified():
            try:
                result = self.api.verify_session(self.session.user_id)
                if result:
                    self.session.update_from_verification(result)
            except Exception as e:
                return f"Error: Unable to verify session. {str(e)}"
        
        schedules = self.api.get_all_task_schedules(session_id=self.session.profile_id)
        
        # Unwrap if needed
        if isinstance(schedules, dict) and "data" in schedules:
            schedules = schedules["data"]
            
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
                if result:
                    self.session.update_from_verification(result)
            except Exception as e:
                return f"Error: Unable to verify session. {str(e)}"
        
        if not schedule_identifier:
            return "Please provide a schedule name or ID."
        
        # Try to get by ID first IF uuid
        schedule = None
        if self._is_uuid(schedule_identifier):
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
                if result:
                    self.session.update_from_verification(result)
            except Exception as e:
                return f"Error: Unable to verify session. {str(e)}"
        
        runs = self.api.get_all_task_runs(session_id=self.session.profile_id)
        
        # Unwrap if needed
        if isinstance(runs, dict) and "data" in runs:
            runs = runs["data"]
            
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
        """Get task run status by ID or Task Name."""
        if not run_id:
            return "Please provide a run ID or task name."
            
        # Handle "latest" or "last" request
        if run_id.lower() in ["latest", "last", "current"]:
            runs = self.api.get_all_task_runs(session_id=self.session.profile_id)
            # Unwrap if needed
            if isinstance(runs, dict) and "data" in runs:
                runs = runs["data"]
            
            if not runs:
                return "No task runs found."
            # Assuming API returns sorted or we pick first
            run = runs[0]
            run_id = run.get("id")
        
        # Try to get by ID first IF uuid
        run = None
        if self._is_uuid(run_id):
            run = self.api.get_task_run_by_id(run_id, user_id=self.session.profile_id)
        
        # If not found, try searching by task name
        if not run:
            all_runs = self.api.get_all_task_runs(session_id=self.session.profile_id)
             # Unwrap if needed
            if isinstance(all_runs, dict) and "data" in all_runs:
                all_runs = all_runs["data"]
                
            # Find first run matching the name
            for r in all_runs:
                task_name = r.get("task", {}).get("name", "").lower()
                if run_id.lower() in task_name:
                    run = r
                    break
        
        if not run:
            return f"Could not find task run matching '{run_id}'"
        
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
                if result:
                    self.session.update_from_verification(result)
            except Exception as e:
                return f"Could not retrieve profile. Session verification failed: {str(e)}"
        
        # Now fetch the full profile
        try:
            result = self.api.verify_session(self.session.user_id)
            if not result:
                return "Failed to retrieve profile: valid session data not returned."
            
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
    
    # ==================== Task Run Helper Functions ====================

    def _create_task_run(self, schedule_id: str) -> str:
        """Create a task run for a given schedule."""
        if not self.session.is_verified():
            return "Session not verified. Please provide your user ID first."
            
        if not schedule_id:
            return "Please provide a schedule ID."
            
        try:
            result = self.api.create_task_run(
                schedule_id=schedule_id,
                profile_id=self.session.profile_id
            )
            
            # The API returns nested data: {success: true, data: {message: "...", taskRun: {...}}}
            data = result.get("data", {})
            run_obj = data.get("taskRun", {})
            run_id = run_obj.get("id", "unknown")
            
            return f"Successfully triggered task run (Run ID: {run_id}). Status: {run_obj.get('status', 'unknown')}"
        except Exception as e:
            return f"Failed to list task run: {str(e)}"

    def _get_task_run_by_id_wrapper(self, run_id: str) -> str:
        """Get details of a specific task run by ID."""
        if not self.session.is_verified():
             return "Session not verified. Please provide your user ID first."
             
        if not run_id:
            return "Please provide a run ID."
            
        try:
            # Pass user_id for authorization
            run = self.api.get_task_run_by_id(run_id, user_id=self.session.user_id)
            if not run:
                return f"Could not find task run with ID '{run_id}'"
                
            details = [
                f"Run ID: {run.get('id', 'N/A')}",
                f"Status: {run.get('status', 'N/A')}",
                f"Started: {run.get('started_at', 'N/A')}",
                f"Completed: {run.get('completed_at', 'N/A')}",
                f"Result: {run.get('result', 'No result yet')}"
            ]
            return "\n".join(details)
        except Exception as e:
            return f"Error retrieving task run: {str(e)}"

    def _get_task_schedule_by_id_wrapper(self, schedule_id: str) -> str:
        """Get details of a specific task schedule by ID."""
        if not self.session.is_verified():
             return "Session not verified. Please provide your user ID first."
             
        if not schedule_id:
            return "Please provide a schedule ID."
            
        try:
            # Pass user_id for authorization
            schedule = self.api.get_task_schedule_by_id(schedule_id, user_id=self.session.user_id)
            if not schedule:
                 return f"Could not find schedule with ID '{schedule_id}'"
            
            details = [
                f"Schedule ID: {schedule.get('id', 'N/A')}",
                f"Time: {schedule.get('scheduled_time', 'N/A')}",
                f"Priority: {schedule.get('priority', 'N/A')}",
                f"Recurring: {schedule.get('recurring', False)}"
            ]
            return "\n".join(details)
        except Exception as e:
            return f"Error retrieving schedule: {str(e)}"

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
