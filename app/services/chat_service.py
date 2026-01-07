from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
import json
import logging

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.groq_service import GroqService
from app.services.haibot_api_service import HaibotApiService
from app.services.session_context import SessionContext
from app.services.function_executor import FunctionExecutor
from app.models.message import MessageRole
from app.prompts.chat_prompt import SYSTEM_PROMPT
from app.prompts.functions import HAIBOT_FUNCTIONS

logger = logging.getLogger(__name__)


class ChatService:
    """
    Chat service with Haibot API function calling integration.
    
    Manages conversations, handles LLM responses, and executes
    function calls to interact with the Haibot API.
    """
    
    # Store session contexts by user_id
    _session_contexts: Dict[str, SessionContext] = {}
    
    def __init__(self, db: Session, groq_api_key: Optional[str] = None):
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.groq_api_key = groq_api_key
        self._groq_service = None
        self._haibot_service = None
    
    @property
    def groq_service(self) -> Optional[GroqService]:
        if self._groq_service is None and self.groq_api_key:
            self._groq_service = GroqService(api_key=self.groq_api_key)
        return self._groq_service
    
    @property
    def haibot_service(self) -> HaibotApiService:
        if self._haibot_service is None:
            self._haibot_service = HaibotApiService()
        return self._haibot_service
    
    def get_or_create_session(self, user_id: str) -> SessionContext:
        """
        Get existing session context or create a new one.
        
        Args:
            user_id: The user's ID
            
        Returns:
            SessionContext for the user
        """
        if user_id not in self._session_contexts:
            self._session_contexts[user_id] = SessionContext(user_id=user_id)
        return self._session_contexts[user_id]
    
    def verify_session(self, user_id: str) -> bool:
        """
        Verify user session with Haibot API.
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if verification successful
        """
        session = self.get_or_create_session(user_id)
        
        if session.is_verified():
            return True
        
        try:
            result = self.haibot_service.verify_session(user_id)
            session.update_from_verification(result)
            return True
        except Exception as e:
            logger.error(f"Session verification failed for {user_id}: {e}")
            return False
    
    def create_conversation(self, user_id: str, tenant_id: str, title: Optional[str] = None):
        """Create a new conversation and verify session."""
        # Attempt to verify session (non-blocking)
        self.verify_session(user_id)
        
        conversation_data = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "title": title or "New Conversation"
        }
        return self.conversation_repo.create(conversation_data)
    
    def get_conversation(self, conversation_id: str):
        return self.conversation_repo.get_by_id(conversation_id)
    
    def get_user_conversations(self, user_id: str, skip: int = 0, limit: int = 100):
        return self.conversation_repo.get_by_user(user_id, skip, limit)
    
    def add_message(self, conversation_id: str, role: MessageRole, content: str, tokens_used: Optional[str] = None):
        message_data = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "tokens_used": tokens_used
        }
        return self.message_repo.create(message_data)
    
    def get_conversation_messages(self, conversation_id: str):
        return self.message_repo.get_by_conversation(conversation_id)
    
    def format_messages_for_groq(self, messages: List) -> List[Dict[str, str]]:
        """Format conversation messages for Groq API."""
        formatted_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
        # Prepend system prompt
        return [{"role": "system", "content": SYSTEM_PROMPT}] + formatted_messages
    
    def _get_tools_definition(self) -> List[Dict[str, Any]]:
        """Convert function definitions to tools format for Groq."""
        return [
            {
                "type": "function",
                "function": func
            }
            for func in HAIBOT_FUNCTIONS
        ]
    
    def _execute_tool_call(self, user_id: str, tool_call: Any) -> str:
        """
        Execute a tool call from the LLM.
        
        Args:
            user_id: The user's ID for session context
            tool_call: The tool call object from Groq response
            
        Returns:
            String result from the function execution
        """
        function_name = tool_call.function.name
        
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            arguments = {}
        
        # Get session context and create executor
        session = self.get_or_create_session(user_id)
        executor = FunctionExecutor(self.haibot_service, session)
        
        # Execute the function
        result = executor.execute(function_name, arguments)
        
        return result
    
    def generate_response(
        self,
        conversation_id: str,
        user_message: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7,
        enable_functions: bool = True
    ) -> str:
        """
        Generate a response with optional function calling support.
        
        Args:
            conversation_id: The conversation ID
            user_message: The user's message
            model: LLM model to use
            temperature: Sampling temperature
            enable_functions: Whether to enable Haibot API function calling
            
        Returns:
            Assistant's response text
        """
        if not self.groq_service:
            raise ValueError("Groq API key is not configured")
        
        # Get conversation to find user_id
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        
        user_id = conversation.user_id
        
        # Add user message to history
        self.add_message(conversation_id, MessageRole.USER, user_message)
        
        # Get formatted messages
        messages = self.get_conversation_messages(conversation_id)
        formatted_messages = self.format_messages_for_groq(messages)
        
        # Prepare tools if functions are enabled
        tools = self._get_tools_definition() if enable_functions else None
        
        # First LLM call
        kwargs = {
            "messages": formatted_messages,
            "model": model,
            "temperature": temperature
        }
        
        if tools:
            kwargs["tools"] = tools
            # Don't set tool_choice, let it default
        
        try:
            response = self.groq_service.generate_chat_completion(**kwargs)
        except Exception as e:
            # Handle Groq tool calling errors (BadRequestError with tool_use_failed)
            error_str = str(e)
            if "tool_use_failed" in error_str or "Failed to call a function" in error_str:
                logger.warning(f"Groq tool calling failed, retrying without tools: {e}")
                # Retry without tools
                kwargs_no_tools = {
                    "messages": formatted_messages,
                    "model": model,
                    "temperature": temperature
                }
                response = self.groq_service.generate_chat_completion(**kwargs_no_tools)
            else:
                # Re-raise other errors
                raise
        
        response_message = response.choices[0].message
        
        # Check if LLM wants to call functions
        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            # Process tool calls
            tool_results = []
            
            for tool_call in response_message.tool_calls:
                result = self._execute_tool_call(user_id, tool_call)
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": result
                })
            
            # Add assistant message with tool calls to context
            formatted_messages.append({
                "role": "assistant",
                "content": response_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response_message.tool_calls
                ]
            })
            
            # Add tool results
            for result in tool_results:
                formatted_messages.append(result)
            
            # Second LLM call to generate final response (disable tools)
            final_response = self.groq_service.generate_chat_completion(
                messages=formatted_messages,
                model=model,
                temperature=temperature,
                tools=None  # Disable tools on second call
            )
            
            assistant_message = final_response.choices[0].message.content
            tokens_used = str(final_response.usage.total_tokens) if hasattr(final_response, 'usage') else None
        else:
            # No function calls, use direct response
            assistant_message = response_message.content
            tokens_used = str(response.usage.total_tokens) if hasattr(response, 'usage') else None
        
        # Save assistant response
        self.add_message(conversation_id, MessageRole.ASSISTANT, assistant_message, tokens_used)
        
        return assistant_message
    
    def stream_response(
        self,
        conversation_id: str,
        user_message: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7
    ):
        """Stream response (without function calling for now)."""
        if not self.groq_service:
            raise ValueError("Groq API key is not configured")
            
        self.add_message(conversation_id, MessageRole.USER, user_message)
        
        messages = self.get_conversation_messages(conversation_id)
        formatted_messages = self.format_messages_for_groq(messages)
        
        full_response = ""
        for chunk in self.groq_service.stream_chat_completion(
            messages=formatted_messages,
            model=model,
            temperature=temperature
        ):
            full_response += chunk
            yield chunk
        
        self.add_message(conversation_id, MessageRole.ASSISTANT, full_response)

