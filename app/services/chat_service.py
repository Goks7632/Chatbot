from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
import json
import logging
from datetime import datetime

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
        # Prepend system prompt with date context
        current_date_str = datetime.now().strftime('%Y-%m-%d')
        enhanced_system_prompt = f"{SYSTEM_PROMPT}\n\nCurrent Date: {current_date_str}"
        return [{"role": "system", "content": enhanced_system_prompt}] + formatted_messages
    
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
            if arguments is None:
                arguments = {}
        except (json.JSONDecodeError, TypeError):
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
        
        if user_message:
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
        
        # Tools are now handled via prompt instructions in JSON mode
        # so we don't pass tools=tools to the API
        
        try:
            response = self.groq_service.generate_chat_completion(**kwargs)
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise

        response_content = response.choices[0].message.content
        
        try:
            # Parse JSON response
            response_json = json.loads(response_content)
            response_type = response_json.get("type")
            
            if response_type == "function":
                func_data = response_json.get("function", {})
                function_name = func_data.get("name")
                arguments = func_data.get("arguments", {})
                
                # Execute tool
                # Create a mock tool_call object to reuse existing _execute_tool_call (or adapt it)
                # But _execute_tool_call expects a complex object. Let's send raw args instead.
                
                # Get session context for execution
                session = self.get_or_create_session(user_id)
                executor = FunctionExecutor(self.haibot_service, session)
                
                # Log execution
                logger.info(f"Executing function via JSON mode: {function_name} with args {arguments}")
                
                result = executor.execute(function_name, arguments)
                
                # Save Assistant's JSON message to DB so it appears in history
                self.add_message(conversation_id, MessageRole.ASSISTANT, response_content)
                
                # Save Function Result as USER message so model sees it contextually
                result_msg = f"Function '{function_name}' executed. Result:\n{result}"
                self.add_message(conversation_id, MessageRole.USER, result_msg)
                
                # Recursive call for final response
                return self.generate_response(
                    conversation_id=conversation_id, 
                    user_message=None, 
                    model=model,
                    temperature=temperature,
                    enable_functions=enable_functions
                )
             
            elif response_type == "message":
                assistant_message = response_json.get("content", "")
                tokens_used = str(response.usage.total_tokens) if hasattr(response, 'usage') else None
                self.add_message(conversation_id, MessageRole.ASSISTANT, assistant_message, tokens_used)
                return assistant_message
                
            else:
                # Fallback for unknown JSON structure
                logger.warning(f"Unknown JSON structure: {response_content}")
                assistant_message = str(response_content)
                self.add_message(conversation_id, MessageRole.ASSISTANT, assistant_message)
                return assistant_message
                
        except json.JSONDecodeError:
            # Fallback for non-JSON response (model failed to follow instructions)
            logger.warning(f"Failed to parse JSON response: {response_content}")
            assistant_message = response_content
            self.add_message(conversation_id, MessageRole.ASSISTANT, assistant_message)
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

