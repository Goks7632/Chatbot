"""
Function Executor for Haibot API Integration.
Routes LLM function calls to the appropriate API service methods.
"""
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta

from app.services.haibot_api_service import HaibotApiService
from app.services.session_context import SessionContext

logger = logging.getLogger(__name__)


class FunctionExecutor:
    """
    Executes LLM function calls by routing them to the Haibot API service.
    
    Handles data dependencies between endpoints by using the session context
    for profileId/tenantId and resolving names to IDs when necessary.
    """
    
    TASK_ID_MAP = {
        "bank reconciliation": "task-bank-recon",
        "payroll processing": "task-payroll",
        "invoice processing": "task-invoice",
        "transaction categorization": "task-categorization",
        "report generation": "task-report",
    }
    
    FUNCTION_MAPPINGS = {
        "get_all_clients": "_get_all_clients",
        "get_client_details": "_get_client_details",
        "create_client": "_create_client",
        "list_scheduled_tasks": "_list_scheduled_tasks",
        "get_available_tasks": "_get_available_tasks",
        "schedule_task": "_schedule_task",
        "get_schedule_details": "_get_task_schedule_by_id_wrapper",
        "run_task_now": "_run_task_now",
        "list_task_runs": "_list_task_runs",
        "get_task_run_status": "_get_task_run_status",
        "import_clients": "_import_clients",
        "get_user_profile": "_get_user_profile",
        "create_task_run": "_run_task_now",
        "get_task_run_by_id": "_get_task_run_by_id_wrapper",
        "get_task_schedule_by_id": "_get_task_schedule_by_id_wrapper"
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
            print(f"DEBUG_EXECUTE: Calling {function_name} with args={arguments}")
            if function_name == "get_all_clients":
                return self._get_all_clients(arguments.get("limit"))
            
            
            # Special handling for get_all_clients? (Optional, but keeping it simple)
            # Dynamic execution for all mapped functions
            method_name = self.FUNCTION_MAPPINGS.get(function_name)
            if not method_name or not hasattr(self, method_name):
                print(f"DEBUG_EXECUTE: Function {function_name} not found in mapping")
                return f"Function {function_name} is not implemented."
            
            method = getattr(self, method_name)
            result = method(**arguments)
            print(f"DEBUG_EXECUTE: {function_name} returned: {str(result)[:200]}...")
            return result
                
        except Exception as e:
            print(f"DEBUG_EXECUTE: Error executing {function_name}: {e}")
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
        
        # Ensure boolean/null conversion for recurring/frequency
        if str(recurring).lower() in ("false", "no", "0"):
            recurring = False
        elif str(recurring).lower() in ("true", "yes", "1"):
            recurring = True
            
        if str(frequency).lower() in ("none", "null", ""):
            frequency = None
            
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
        resolve_result = self._resolve_task_id(target_task)
        
        # Handle multiple matches (Ambiguity)
        if isinstance(resolve_result, list):
            options = [f"{m['name']} ({m['bot']})" for m in resolve_result]
            options_str = ", ".join(options)
            return f"I found multiple tasks matching '{target_task}': {options_str}. Please specify which bot you would like to use (e.g. 'Use Dext', 'Use Xero')."
            
        final_task_id = resolve_result

        # If it's a direct ID, verify it exists (optional but good practice)
        # Note: _resolve_task_id returns the input string if no match found, which might be a valid ID.
        if final_task_id == target_task.replace(" ", "-").lower() and len(final_task_id) < 30:
             # It was a name, but no match found in API or static map
             return f"Could not find task template matching '{target_task}' or any valid ID."

        try:
            result = self.api.create_task_schedule(
                task_id=final_task_id,
                time=time,
                date=date,
                profile_id=self.session.profile_id,
                priority=priority.lower(),
                recurring=recurring,
                frequency=frequency
            )
            
            # Handle nested response: {data: {schedule: {id: ...}}}
            sched_data = result.get("data", {})
            if "schedule" in sched_data:
                sched_id = sched_data["schedule"].get("id")
            else:
                sched_id = result.get("id", "unknown")
                
            return f"Successfully scheduled task (ID: {sched_id}) for {date} at {time}."
            
        except Exception as e:
            print(f"DEBUG_SCHEDULE_TASK ERROR: {str(e)}")
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
            task_name = sched.get("task", {}).get("name", "Unknown")
            schedule_list.append(f"- Task: {task_name}, Schedule ID: {sched_id}, Time: {scheduled_time}, Priority: {priority}, Type: {frequency}")
            
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
    
    def _get_task_run_status(self, run_id: str = None, task_name: str = None, identifier: str = None) -> str:
        """Get task run status by ID or Task Name."""
        # Handle aliases from LLM
        run_id = run_id or task_name or identifier
        
        if not run_id:
            return "Please provide a run ID or task name."
            
        # Handle "latest" or "last" request
        # Handle "last" or "latest" keyword
        if run_id.lower() in ["last", "latest"]:
            runs = self.api.get_all_task_runs(session_id=self.session.profile_id)
            # Unwrap if needed
            if isinstance(runs, dict) and "data" in runs:
                runs = runs["data"]
            
            if not runs:
                return "No task runs found."
            # API returns newest first
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
            # Find first run matching the name OR matching task ID OR matching schedule ID
            # The user might have passed the task TEMPLATE ID (e.g. e417670...) thinking it's the run ID.
            # We should check if run_id matches task['id'] or task['schedule_id'] in the run history.
            
            matching_runs = []
            for r in all_runs:
                task_name = r.get("task", {}).get("name", "").lower()
                t_id = r.get("task", {}).get("id", "")
                # Note: 'schedule_id' might not be directly on the run object depending on API version,
                # but let's check top-level and inside task.
                s_id = r.get("schedule_id") 
                
                # Check 1: Name substring match
                if run_id.lower() in task_name:
                    matching_runs.append(r)
                    continue
                    
                # Check 2: Task Template ID match
                if run_id == t_id:
                    matching_runs.append(r)
                    continue
                    
                # Check 3: Schedule ID match
                if s_id and run_id == s_id:
                    matching_runs.append(r)
                    continue

            # If matches found, we want to return the latest status for EACH unique task/schedule found
            # instead of just the single latest run overall.
            results_by_task = {}
            for r in matching_runs:
                # Group by Task Name (or ID) to ensure we show one entry per task type
                t_name = r.get("task", {}).get("name", "Unknown Task")
                t_bot = r.get("task", {}).get("bot", {}).get("name", "Unknown Bot")
                key = f"{t_name} ({t_bot})"
                
                # We want the latest run for this task
                current_latest = results_by_task.get(key)
                if not current_latest:
                     results_by_task[key] = r
                else:
                     # Compare started_at
                     curr_start = current_latest.get("started_at") or ""
                     new_start = r.get("started_at") or ""
                     if new_start > curr_start:
                         results_by_task[key] = r

            if not results_by_task:
                 return f"Could not find any task runs matching '{run_id}'"

            # Format output for all found tasks
            output_parts = []
            for name, run in results_by_task.items():
                 details = [
                    f"--- {name} ---",
                    f"Run ID: {run.get('id', 'N/A')}",
                    f"Status: {run.get('status', 'N/A')}",
                    f"Started: {run.get('started_at', 'N/A')}",
                    f"Result: {run.get('result', 'No result yet')}"
                 ]
                 output_parts.append("\n".join(details))
            
            return f"Found matching runs for '{run_id}':\n\n" + "\n\n".join(output_parts)

        
        details = [
            f"Run ID: {run.get('id', 'N/A')}",
            f"Status: {run.get('status', 'N/A')}",
            f"Started: {run.get('started_at', 'N/A')}",
            f"Completed: {run.get('completed_at', 'N/A')}",
            f"Result: {run.get('result', 'No result yet')}",
        ]
        
        return "\n".join(details)
    
    def _run_task_now(self, identifier: str = None, schedule_id: str = None) -> str:
        """Trigger immediate execution of a scheduled task."""
        # Handle parameter alias from LLM (create_task_run sends schedule_id)
        identifier = identifier or schedule_id
        
        if not identifier:
            return "Please provide a task name or schedule ID."
            
        if not self.session.is_verified():
            return "Session not verified. Please provide your user ID first."
        
        # 1. Check if a SCHEDULE already exists for this task
        # We need to fetch all schedules to check for ambiguity here too
        # Use correct API method name
        all_schedules = self.api.get_all_task_schedules(session_id=self.session.profile_id)
        
        if isinstance(all_schedules, dict) and "data" in all_schedules:
            all_schedules = all_schedules["data"]
            
        matching_schedules = []
        if all_schedules:
            for sched in all_schedules:
                t_name = sched.get("task", {}).get("name", "").lower()
                t_bot = sched.get("task", {}).get("bot", {}).get("name", "")
                s_id = sched.get("id")
                
                # Check if identifier matches matches task name or Schedule ID
                if identifier.lower() in t_name or t_name in identifier.lower() or identifier == s_id:
                     matching_schedules.append({
                        "id": s_id,
                        "name": sched.get("task", {}).get("name"),
                        "bot": t_bot
                    })

        # Filter schedule matches if user specified bot name
        if len(matching_schedules) > 1:
            refined = []
            for m in matching_schedules:
                if m["bot"].lower() in identifier.lower():
                    refined.append(m)
            if refined:
                matching_schedules = refined

        # If duplicate schedules found
        if len(matching_schedules) > 1:
             # Group by bot to handle duplicates (e.g. 18 Xero schedules)
             unique_bots = {}
             for m in matching_schedules:
                 bot_name = m["bot"]
                 if bot_name not in unique_bots:
                     unique_bots[bot_name] = []
                 unique_bots[bot_name].append(m)
                 
             # If multiple bots found, ask for clarification
             if len(unique_bots) > 1:
                 options = [f"{bot} ({len(items)})" for bot, items in unique_bots.items()]
                 options_str = ", ".join(options)
                 return f"I found schedules for multiple bots: {options_str}. Please specify which bot you would like to run (e.g. 'Run Invoice Upload Xero')."

             # If all duplicates belong to one bot, proceed with the first one
             if len(unique_bots) == 1:
                 # Auto-select the first one
                 matching_schedules = [matching_schedules[0]]

        # Fallback ambiguity check
        if len(matching_schedules) > 1:
             options = [f"{m['name']} ({m['bot']})" for m in matching_schedules]
             options_str = ", ".join(options)
             return f"I found multiple schedules for '{identifier}': {options_str}. Please specify which bot you would like to run."
             
        # If exactly one schedule found, use it
        if len(matching_schedules) == 1:
            schedule_id = matching_schedules[0]["id"]
            try:
                result = self.api.create_task_run(schedule_id=schedule_id, profile_id=self.session.profile_id)
                # handle if result is a string (error)
                if isinstance(result, str): return result
                
                # Handle nested response: {data: {taskRun: {id: ...}}}
                run_data = result.get("data", {})
                if "taskRun" in run_data:
                     run_id = run_data["taskRun"].get("id", "unknown")
                else:
                     run_id = result.get("id", "unknown")
                return f"Successfully triggered run for schedule '{identifier}' (Run ID: {run_id})."
            except Exception as e:
                return f"Failed to trigger task run: {str(e)}"

        # 2. If NO schedule found, find the TASK TEMPLATE
        resolve_result = self._resolve_task_id(identifier)
        
        # Handle ambiguity in templates
        if isinstance(resolve_result, list):
            options = [f"{m['name']} ({m['bot']})" for m in resolve_result]
            options_str = ", ".join(options)
            return f"I found multiple tasks matching '{identifier}': {options_str}. Please specify which bot you would like to use."
            
        task_id = resolve_result
        if task_id == identifier.replace(" ", "-").lower() and len(task_id) < 30:
             return f"Could not find any schedule or task template matching '{identifier}'."
             
        # 3. Valid template found, but no schedule. Create one, then run.
        try:
             # Create a one-time schedule for immediate execution
             # Using a date far in the future or today? User logic implies just "schedule it".
             # We'll use today's date and current time + 1 min as a placeholder, 
             # but strictly we just need a schedule ID to run it.
             now = datetime.now()
             date_str = now.strftime("%Y-%m-%d")
             time_str = (now + timedelta(minutes=2)).strftime("%H:%M")
             
             sched_response = self.api.create_task_schedule(
                 task_id=task_id,
                 time=time_str,
                 date=date_str,
                 profile_id=self.session.profile_id,
                 priority="medium",
                 recurring=False
             )
             
             # Handle nested response: {data: {schedule: {id: ...}}}
             sched_data = sched_response.get("data", {})
             if "schedule" in sched_data:
                 new_sched_id = sched_data["schedule"].get("id")
             else:
                 new_sched_id = sched_response.get("id")
                 
             if not new_sched_id:
                  return f"Failed to create schedule. Response: {str(sched_response)}"
                  
             # Run it
             run_response = self.api.create_task_run(schedule_id=new_sched_id, profile_id=self.session.profile_id)
             if isinstance(run_response, str): return run_response
             
             # Handle nested run response
             run_data = run_response.get("data", {})
             if "taskRun" in run_data:
                  run_id = run_data["taskRun"].get("id", "unknown")
             else:
                  run_id = run_response.get("id", "unknown")
                  
             return f"Created one-time schedule '{identifier}' (ID: {new_sched_id}) and triggered run (Run ID: {run_id})."
             if "schedule" in sched_data:
                sched_id = sched_data["schedule"].get("id")
             else:
                sched_id = sched_response.get("id")
                
             if not sched_id:
                 return f"Failed to create schedule for '{identifier}'."
                 
             # Now run it
             run_response = self.api.create_task_run(schedule_id=sched_id, profile_id=self.session.profile_id)
             
             # Handle nested run response
             run_data = run_response.get("data", {})
             if "taskRun" in run_data:
                run_id = run_data["taskRun"].get("id", "unknown")
             else:
                run_id = run_response.get("id", "unknown")
                
             return f"No existing schedule found, so I created a new schedule for '{identifier}' and triggered it successfully (Run ID: {run_id})."
             
        except Exception as e:
            return f"Failed to schedule and run task: {str(e)}"

    
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
            error_str = str(e)
            if "404" in error_str or "Not Found" in error_str:
                return f"Failed to create task run: Scheduled task not found for ID '{schedule_id}'. Please ensure the task is scheduled first."
            return f"Failed to list task run: {error_str}"

    def _get_task_run_by_id_wrapper(self, run_id: str) -> str:
        """Get details of a specific task run by ID."""
        if not self.session.is_verified():
             return "Session not verified. Please provide your user ID first."
             
        if not run_id:
            return "Please provide a run ID."
            
        try:
            # Check for "latest" or "last" logical ID
            if run_id.lower() in ["latest", "last"]:
                 return self._get_task_run_status(run_id)
            
            # Prevent 500 errors: If not a UUID, treat as a name search
            if not self._is_uuid(run_id):
                 return self._get_task_run_status(run_id)

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

    def _get_task_schedule_by_id_wrapper(self, schedule_id: str = None, schedule_identifier: str = None) -> str:
        """Get details of a specific task schedule by ID or fuzzy name (Task/Bot)."""
        # Handle alias
        schedule_id = schedule_id or schedule_identifier

        if not self.session.is_verified():
             return "Session not verified. Please provide your user ID first."
             
        if not schedule_id:
            return "Please provide a schedule ID or task name."
            
        # 1. Try exact ID lookup first if it looks like a valid UUID
        # Note: self._is_uuid is checking if the string is a valid UUID
        if self._is_uuid(schedule_id):
            try:
                # API service method doesn't take user_id, it uses client config or context
                schedule = self.api.get_task_schedule_by_id(schedule_id)
                if schedule:
                    details = [
                        f"Schedule ID: {schedule.get('id', 'N/A')}",
                        f"Task: {schedule.get('task', {}).get('name', 'N/A')}",
                        f"Bot: {schedule.get('task', {}).get('bot', {}).get('name', 'N/A')}",
                        f"Time: {schedule.get('time', 'N/A')}", # Note: API might return 'time' or 'scheduled_time' depending on endpoint
                        f"Priority: {schedule.get('priority', 'N/A')}",
                        f"Recurring: {schedule.get('recurring', False)}"
                    ]
                    return "\n".join(details)
            except Exception:
                pass # Fallback to search

        # 2. Search all schedules for fuzzy match
        try:
             # Use the correct method to fetch task schedules
             all_schedules = self.api.get_all_task_schedules(session_id=self.session.profile_id)
             if isinstance(all_schedules, dict) and "data" in all_schedules:
                 all_schedules = all_schedules["data"]
                 
             matches = []
             target = schedule_id.lower()
             
             for sched in all_schedules:
                 s_id = sched.get("id")
                 t_name = sched.get("task", {}).get("name", "").lower()
                 t_bot = sched.get("task", {}).get("bot", {}).get("name", "").lower()
                 
                 # Check matches: exact ID, substring Task Name, substring Bot Name
                 if s_id == target:
                     matches.append(sched)
                 elif target in t_name:
                     matches.append(sched)
                 elif target in t_bot:
                     matches.append(sched)
            
             if not matches:
                 return f"Could not find schedule matching '{schedule_id}'."
            
             if not matches:
                 return f"Could not find schedule matching '{schedule_id}'."
            
             # Return ALL matches
             output_parts = []
             for schedule in matches:
                 details = [
                    f"--- Schedule ID: {schedule.get('id', 'N/A')} ---",
                    f"Task: {schedule.get('task', {}).get('name', 'N/A')}",
                    f"Bot: {schedule.get('task', {}).get('bot', {}).get('name', 'N/A')}",
                    f"Time: {schedule.get('time') or schedule.get('scheduled_time') or 'N/A'}",
                    f"Date: {schedule.get('date', 'N/A')}",
                    f"Priority: {schedule.get('priority', 'N/A')}",
                    f"Recurring: {schedule.get('recurring', False)}"
                ]
                 output_parts.append("\n".join(details))
             
             return f"Found {len(matches)} matching schedules for '{schedule_id}':\n\n" + "\n\n".join(output_parts)
             
        except Exception as e:
            return f"Error retrieving schedule: {str(e)}"

    # ==================== Helper Methods ====================
    
    def _resolve_task_id(self, task_name: str) -> Union[str, List[Dict[str, str]]]:
        """
        Resolve a task name to a task ID.
        Returns either a single ID string (if unique/exact) or a list of matches.
        """
        task_name_lower = task_name.lower()
        
        # Fetch all available tasks from API to get full context (bot names)
        all_tasks = self.api.get_all_tasks(user_id=self.session.user_id)
        
        # Unwrap if needed
        if isinstance(all_tasks, dict) and "data" in all_tasks:
            all_tasks = all_tasks["data"]
            
        matches = []
        
        for task in all_tasks:
            t_name = task.get("name", "").lower()
            # API inconsistency: /task-schedules uses 'bot', /tasks uses 'bots'
            t_bot_obj = task.get("bot") or task.get("bots") or {}
            t_bot = t_bot_obj.get("name", "")
            t_id = task.get("id")
            
            # Check if task name matches
            if task_name_lower in t_name or t_name in task_name_lower:
                matches.append({
                    "id": t_id,
                    "name": task.get("name"),
                    "bot": t_bot
                })
                
        # Filter matches if user specified bot name (e.g. "Invoice Upload Xero")
        if len(matches) > 1:
            refined_matches = []
            for m in matches:
                # If the user query contains the bot name, narrow down to that one
                if m["bot"].lower() in task_name_lower:
                    refined_matches.append(m)
            
            if refined_matches:
                matches = refined_matches

        # If we have exactly one match, return its ID
        if len(matches) == 1:
            return matches[0]["id"]
            
        # If multiple, return the list for the caller to handle
        if len(matches) > 1:
            return matches
            
        # Fallback to the static map or direct ID if no API match found
        for name, task_id in self.TASK_ID_MAP.items():
            if name in task_name_lower or task_name_lower in name:
                return task_id
                
        return task_name.replace(" ", "-").lower()
