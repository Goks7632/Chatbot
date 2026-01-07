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
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto"
    ):
        """
        Generate a chat completion with optional function calling support.
        
        Args:
            messages: List of message dicts with role and content
            model: Model to use for completion
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response
            tools: Optional list of tool/function definitions for function calling
            tool_choice: How to select tools - "auto", "none", or specific tool
        """
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        # Add tools if provided (function calling)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        
        response = self.client.chat.completions.create(**kwargs)
        return response
    
    def generate_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 1024
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
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 1024
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

