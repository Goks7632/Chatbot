from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.groq_service import GroqService
from app.models.message import MessageRole
from app.prompts.chat_prompt import SYSTEM_PROMPT


class ChatService:
    def __init__(self, db: Session, groq_api_key: Optional[str] = None):
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.groq_api_key = groq_api_key
        self._groq_service = None
    
    @property
    def groq_service(self):
        if self._groq_service is None and self.groq_api_key:
            self._groq_service = GroqService(api_key=self.groq_api_key)
        return self._groq_service
    
    def create_conversation(self, user_id: str, tenant_id: str, title: Optional[str] = None):
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
        formatted_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
        # Prepend system prompt
        return [{"role": "system", "content": SYSTEM_PROMPT}] + formatted_messages
    
    def generate_response(
        self,
        conversation_id: str,
        user_message: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7
    ):
        if not self.groq_service:
            raise ValueError("Groq API key is not configured")
            
        self.add_message(conversation_id, MessageRole.USER, user_message)
        
        messages = self.get_conversation_messages(conversation_id)
        formatted_messages = self.format_messages_for_groq(messages)
        
        response = self.groq_service.generate_chat_completion(
            messages=formatted_messages,
            model=model,
            temperature=temperature
        )
        
        assistant_message = response.choices[0].message.content
        tokens_used = str(response.usage.total_tokens) if hasattr(response, 'usage') else None
        
        self.add_message(conversation_id, MessageRole.ASSISTANT, assistant_message, tokens_used)
        
        return assistant_message
    
    def stream_response(
        self,
        conversation_id: str,
        user_message: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7
    ):
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

