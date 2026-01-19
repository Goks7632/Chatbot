"""
Haibot API Service.
Handles all communication with the Haibot Vercel API endpoints.
"""
import logging
import httpx
import uuid
from typing import List, Dict, Optional, Any, Union

logger = logging.getLogger(__name__)


class HaibotApiService:
    """
    Service for interacting with Haibot Vercel API.
    
    Endpoints covered:
    - Authentication: /api/auth/verify
    - Clients: /api/clients, /api/clients/{id}
    - Task Schedules: /api/task-schedules, /api/task-schedules/{id}
    - Task Runs: /api/task-runs, /api/task-runs/{id}
    """
    
    BASE_URL = "https://haibot.vercel.app/api"
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize the Haibot API service.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client = None
    
    @property
    def client(self) -> httpx.Client:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
        return self._client
    
    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None
    
    # ==================== Authentication ====================
    
    def verify_session(self, user_id: str) -> Dict[str, Any]:
        """
        Verify user session and get profile information.
        
        Args:
            user_id: The user's ID (passcode)
            
        Returns:
            dict with profileId, tenantId, and verification status
            
        Raises:
            Exception if verification fails
        """
        try:
            response = self.client.post(
                "/auth/verify",
                json={"userId": user_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Session verification failed: {e}")
            raise Exception(f"Failed to verify session: {e.response.text}")
        except Exception as e:
            logger.error(f"Session verification error: {e}")
            raise
    
    # ==================== Clients ====================
    
    def get_all_clients(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all clients.
        
        Args:
            session_id: Optional user ID (passed as userId query param)
            
        Returns:
            List of client objects
        """
        params = {}
        if session_id:
            params["user_id"] = session_id  # Changed to user_id (snake_case) per Swagger
            
        try:
            response = self.client.get("/clients", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Handle wrapped response {success: true, data: [...]}
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data if isinstance(data, list) else []
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get clients: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting clients: {e}")
            return []
    
    def get_client_by_id(self, client_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific client by ID.
        
        Args:
            client_id: The client's ID
            user_id: Optional user ID for authorization
            
        Returns:
            Client object or None if not found
        """
        try:
            params = {"user_id": user_id} if user_id else {}
            response = self.client.get(f"/clients/{client_id}", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get client {client_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting client: {e}")
            return None
    
    def import_clients_from_file(
        self,
        file_path: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Import clients from an Excel file.
        
        Args:
            file_path: Path to the Excel file (.xlsx)
            user_id: User ID for authentication
            
        Returns:
            Import result with success/failure details
            
        Raises:
            Exception if import fails
        """
        try:
            # Use a separate client for multipart upload
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.split('/')[-1], f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                data = {'userId': user_id}
                
                with httpx.Client(base_url=self.BASE_URL, timeout=self.timeout) as upload_client:
                    response = upload_client.post(
                        "/clients/import",
                        files=files,
                        data=data
                    )
                    response.raise_for_status()
                    return response.json()
        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to import clients: {e}")
            raise Exception(f"Failed to import clients: {e.response.text}")
        except Exception as e:
            logger.error(f"Error importing clients: {e}")
            raise
    
    def create_client(
        self,
        profile_id: str,
        company_name: str,
        **optional_fields
    ) -> Dict[str, Any]:
        """
        Create a new client.
        
        Args:
            profile_id: The user's Profile ID
            company_name: Name of the client company
            **optional_fields: Additional client fields (published, source_name, etc.)
            
        Returns:
            Created client object
            
        Raises:
            Exception if creation fails
        """
        # Build client data with defaults
        client_data = {
            "company_name": company_name,
            "published": optional_fields.get("published", "Yes"),
            "source_name": optional_fields.get("source_name", "Chatbot"),
            "use_date_range": optional_fields.get("use_date_range", "Yes"),
            "date_range": optional_fields.get("date_range", "360"),
            "amount_received": optional_fields.get("amount_received", "Yes"),
            "amount_spent": optional_fields.get("amount_spent", "Yes"),
        }
        
        # Add any additional optional fields
        for key, value in optional_fields.items():
            if key not in client_data:
                client_data[key] = value
        
        payload = {
            "profile_id": profile_id,
            "clientData": client_data
        }
        
        try:
            response = self.client.post(
                "/clients",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create client: {e}")
            raise Exception(f"Failed to create client: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            raise
    
    # ==================== Task Templates ====================
    
    def get_all_tasks(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all available task templates.
        
        Args:
            user_id: Optional user ID for filtering tasks
        
        Returns:
            List of task objects
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            
            response = self.client.get("/tasks", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get tasks: {e}")
            return []
    
    # ==================== Task Schedules ====================
    
    def get_all_task_schedules(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all task schedules."""
        params = {}
        if session_id:
            params["user_id"] = session_id
            
        try:
            response = self.client.get("/task-schedules", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Handle wrapped response
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data if isinstance(data, list) else []
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get task schedules: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting task schedules: {e}")
            return []
    
    def get_task_schedule_by_id(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific task schedule by ID.
        
        Args:
            schedule_id: The schedule ID
            
        Returns:
            Task schedule object or None if not found
        """
        try:
            response = self.client.get(f"/task-schedules/{schedule_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get task schedule {schedule_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting task schedule: {e}")
            return None
    
    def create_task_schedule(
        self,
        task_id: str,
        time: str,
        date: str,
        profile_id: str,
        priority: str = "medium",
        recurring: bool = False,
        frequency: str = "daily",
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Create a new task schedule.
        
        Args:
            task_id: ID of the task template to schedule
            time: Time to run (format: "HH:MM")
            date: Date to run (format: "YYYY-MM-DD")
            profile_id: Profile ID from session context
            priority: Priority (low, medium, high)
            recurring: Whether the task repeats
            frequency: Frequency if recurring (daily, weekly, etc.)
            timezone: Timezone string (default UTC)
            
        Returns:
            Created schedule object
            
        Raises:
            Exception if creation fails
        """
        try:
            response = self.client.post(
                "/task-schedules",
                json={
                    "task_id": task_id,
                    "time": time,
                    "date": date,
                    "profile_id": profile_id,
                    "priority": priority,
                    "recurring": recurring,
                    "frequency": frequency,
                    "timezone": timezone
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create task schedule: {e}")
            raise Exception(f"Failed to create task schedule: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating task schedule: {e}")
            raise
    
    # ==================== Task Runs ====================
    
    def get_all_task_runs(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all task runs (execution history).
        
        Args:
            session_id: Optional user ID (passed as userId query param)
        
        Returns:
            List of task run objects
        """
        params = {}
        if session_id:
            params["user_id"] = session_id
            
        try:
            response = self.client.get("/task-runs", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Handle wrapped response {success: true, data: [...]}
            if isinstance(data, dict) and "data" in data:
                result = data["data"]
                # Handle None response
                return result if result is not None else []
            return data if isinstance(data, list) else []
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get task runs: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting task runs: {e}")
            return []
    
    def get_task_run_by_id(self, run_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific task run by ID.
        
        Args:
            run_id: The task run ID
            user_id: Optional user ID for authorization
            
        Returns:
            Task run object or None if not found
        """
        try:
            params = {"user_id": user_id} if user_id else {}
            response = self.client.get(f"/task-runs/{run_id}", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", data)
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get task run {run_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting task run: {e}")
            return None

    def get_task_schedule_by_id(self, schedule_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific task schedule by ID.
        
        Args:
            schedule_id: The task schedule ID
            user_id: Optional user ID for authorization
            
        Returns:
            Task schedule object or None if not found
        """
        try:
            # Validate UUID format to prevent API 500/404 on bad IDs
            try:
                uuid.UUID(str(schedule_id))
            except ValueError:
                return None
                
            params = {"user_id": user_id} if user_id else {}
            response = self.client.get(f"/task-schedules/{schedule_id}", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # This is normal behavior when checking if a schedule exists
                return None
            logger.error(f"Failed to get task schedule {schedule_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting task schedule: {e}")
            return None

    def create_task_run(
        self,
        schedule_id: str,
        profile_id: str
    ) -> Dict[str, Any]:
        """
        Create a new task run (trigger execution).
        
        Args:
            schedule_id: ID of the schedule to execute
            profile_id: Profile ID from session context
            
        Returns:
            Created task run object
            
        Raises:
            Exception if creation fails
        """
        try:
            response = self.client.post(
                "/task-runs",
                json={
                    "schedule_id": schedule_id,
                    "profile_id": profile_id
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create task run: {e}")
            raise Exception(f"Failed to create task run: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating task run: {e}")
            raise
    
    # ==================== Helper Methods ====================
    
    def find_schedule_by_name(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a schedule by task name (fuzzy match).
        
        Args:
            task_name: Name to search for
            
        Returns:
            Matching schedule or None
        """
        schedules = self.get_all_task_schedules()
        task_name_lower = task_name.lower()
        
        for schedule in schedules:
            # Handle nested task object or flat task_name
            task_obj = schedule.get("task", {})
            if isinstance(task_obj, dict):
                schedule_name = task_obj.get("name", "").lower()
            else:
                schedule_name = schedule.get("task_name", "").lower()
                
            if task_name_lower in schedule_name or schedule_name in task_name_lower:
                return schedule
        
        return None
    
    def find_client_by_name(self, client_name: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find a client by name (fuzzy match).
        
        Args:
            client_name: Name to search for
            user_id: Optional user ID for context
            
        Returns:
            Matching client or None
        """
        clients = self.get_all_clients(session_id=user_id)
        client_name_lower = client_name.lower()
        
        for client in clients:
            name = client.get("company_name", "").lower()
            if client_name_lower in name or name in client_name_lower:
                return client
        
        return None
