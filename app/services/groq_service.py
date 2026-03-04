from groq import Groq
from typing import List, Dict, Optional, Any
from app.core.config import settings


class GroqService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.client = Groq(api_key=self.api_key)
    
    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-oss-120b",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto"
    ):
        """
        Generate a chat completion with JSON mode support.
        
        Args:
            messages: List of message dicts with role and content
            model: Model to use for completion
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response
            tools: Ignored in JSON mode, kept for compatibility signature
            tool_choice: Ignored in JSON mode
        """
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "response_format": {"type": "json_object"}
        }
        
        # Tools are NOT passed to Groq when using JSON mode for gpt-oss-120b
        # We rely on the prompt to enforce tool usage structure
        
        response = self.client.chat.completions.create(**kwargs)
        
        response = self.client.chat.completions.create(**kwargs)
        return response
    
    def generate_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        model: str = "openai/gpt-oss-120b",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ):
        """
        Generate a chat completion with function calling enabled.
        
        Converts function definitions to the tools format expected by Groq.
        
        Args:
            messages: List of message dicts
            functions: List of function definitions (OpenAI format)
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Groq completion response
        """
        # Convert functions to tools format
        tools = [
            {
                "type": "function",
                "function": func
            }
            for func in functions
        ]
        
        return self.generate_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice="auto"
        )
    
    def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-oss-120b",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ):
        for chunk in self.generate_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        ):
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

