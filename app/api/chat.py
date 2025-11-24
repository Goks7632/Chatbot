from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import get_db
from app.core.config import settings
from app.services.chat_service import ChatService
from app.repositories.conversation_repository import ConversationRepository

router = APIRouter(tags=["Chat"])


@router.post("/chat/start")
def start_chat(id: str, db: Session = Depends(get_db)):
    chat_service = ChatService(db, settings.GROQ_API_KEY)
    
    conversation = chat_service.create_conversation(
        user_id=id,
        tenant_id=id,
        title="Chat"
    )
    
    return {
        "conversation_id": conversation.id
    }


@router.post("/chat/message")
def send_message(id: str, conversation_id: str, content: str, db: Session = Depends(get_db)):
    chat_service = ChatService(db, settings.GROQ_API_KEY)
    
    conversation = chat_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    response = chat_service.generate_response(
        conversation_id=conversation_id,
        user_message=content
    )
    
    return {"response": response}


@router.get("/chat/messages")
def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    chat_service = ChatService(db)
    
    conversation = chat_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = chat_service.get_conversation_messages(conversation_id)
    
    return [
        {
            "role": msg.role.value,
            "content": msg.content,
            "created_at": msg.created_at
        }
        for msg in messages
    ]


@router.get("/chat/conversations")
def get_conversations(id: str, db: Session = Depends(get_db)):
    chat_service = ChatService(db)
    conversations = chat_service.get_user_conversations(id)
    
    return [
        {
            "conversation_id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at
        }
        for conv in conversations
    ]


