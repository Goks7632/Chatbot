"""
Function Definitions for Haibot API Integration.
These functions are used by the LLM to determine which API operations to perform.
"""

# OpenAI/Groq-compatible function definitions
HAIBOT_FUNCTIONS = [
    {
        "name": "get_all_clients",
        "description": "Get a list of all clients/businesses managed in the system. Use this when the user asks to see their clients, list clients, or view client information.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Optional limit on the number of clients to return"
                }
            },
            "required": []
        }

    },
    {
        "name": "get_available_tasks",
        "description": "Get a list of all available task templates that can be scheduled.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_client_details",
        "description": "Get detailed information about a specific client by their name or ID. Use when the user asks for details about a particular client.",
        "parameters": {
            "type": "object",
            "properties": {
                "client_identifier": {
                    "type": "string",
                    "description": "The name or ID of the client to look up"
                }
            },
            "required": ["client_identifier"]
        }
    },
    {
        "name": "create_client",
        "description": "Create a new client/business in the system. Use when user wants to add a new client.",
        "parameters": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Name of the client company"
                },
                "source_name": {
                    "type": "string",
                    "description": "Source system (e.g., Hubdoc, Xero, Manual, Chatbot). Defaults to 'Chatbot'"
                }
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "list_scheduled_tasks",
        "description": "Get a list of all scheduled automation tasks. Use when the user asks about scheduled tasks, what's scheduled, or upcoming automation.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Optional limit on the number of tasks to return"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_schedule_details",
        "description": "Get details of a specific scheduled task by name or ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "schedule_identifier": {
                    "type": "string",
                    "description": "The name or ID of the scheduled task"
                }
            },
            "required": ["schedule_identifier"]
        }
    },
    {
        "name": "list_task_runs",
        "description": "Get a list of all task execution runs (history). Use when the user asks about task history, recent runs, or execution status.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Optional limit on the number of runs to return"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_task_run_status",
        "description": "Get the status and details of a specific task run by ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "The ID of the task run to check"
                }
            },
            "required": ["run_id"]
        }
    },
    {
        "name": "import_clients",
        "description": "Import clients from an Excel file. Use when the user wants to bulk import clients from a spreadsheet.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the Excel file (.xlsx) containing client data"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "get_user_profile",
        "description": "Get the current user's profile information including company name, email, and subscription status.",
        "parameters": {
            "type": "object",
            "properties": {
                "include_details": {
                    "type": "boolean",
                    "description": "Whether to include full profile details"
                }
            },
            "required": []
        }
    },
    {
        "name": "create_task_run",
        "description": "Trigger a new run for a specific task schedule. Use when the user wants to run a scheduled task immediately.",
        "parameters": {
            "type": "object",
            "properties": {
                "schedule_id": {
                    "type": "string",
                    "description": "The ID of the schedule to execute"
                }
            },
            "required": ["schedule_id"]
        }
    },
    {
        "name": "get_task_run_by_id",
        "description": "Get detailed information about a specific task run by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "The ID of the task run to retrieve"
                }
            },
            "required": ["run_id"]
        }
    },
    {
        "name": "get_task_schedule_by_id",
        "description": "Get detailed information about a specific task schedule by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "schedule_id": {
                    "type": "string",
                    "description": "The ID of the schedule to retrieve"
                }
            },
            "required": ["schedule_id"]
        }

    },
    {
        "name": "schedule_task",
        "description": "Schedule a task to run at a specific date and time. Use when the user wants to set up a future or recurring automation.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_identifier": {
                    "type": "string",
                    "description": "The name or ID of the task template to schedule (e.g., 'Bank Reconciliation')"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format"
                },
                "time": {
                    "type": "string",
                    "description": "Time in HH:MM format (24-hour)"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level (low, medium, high). Defaults to 'medium'"
                },
                "recurring": {
                    "type": "boolean",
                    "description": "Whether the task should repeat"
                },
                "frequency": {
                    "type": "string",
                    "description": "Frequency if recurring (daily, weekly, monthly)"
                }
            },
            "required": ["task_identifier", "date", "time"]
        }
    }
]


# Map of function names to their display-friendly descriptions
FUNCTION_DESCRIPTIONS = {
    "get_all_clients": "Fetching all clients...",
    "get_available_tasks": "Fetching available task templates...",
    "get_client_details": "Looking up client details...",
    "create_client": "Creating new client...",
    "list_scheduled_tasks": "Fetching scheduled tasks...",
    "get_schedule_details": "Looking up schedule details...",
    "list_task_runs": "Fetching task run history...",
    "get_task_run_status": "Checking task run status...",
    "import_clients": "Importing clients from Excel...",
    "get_user_profile": "Fetching user profile...",
    "create_task_run": "Triggering task execution...",
    "get_task_run_by_id": "Retrieving task run details...",
    "get_task_run_by_id": "Retrieving task run details...",
    "get_task_schedule_by_id": "Retrieving schedule details...",
    "schedule_task": "Scheduling new task..."
}

