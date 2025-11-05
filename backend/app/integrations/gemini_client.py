import os
from typing import Optional, List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
try:
    from langchain.schema import HumanMessage, SystemMessage, AIMessage
except ImportError:
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from ..config import Config

class GeminiClient:
    """
    Gemini AI client using LangChain integration.
    Primary LLM for the Sentinel voice assistant.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google Gemini API key (defaults to config)
            model: Model name (default: gemini-pro)
        """
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model = model
        
        if not self.api_key:
            raise ValueError("Gemini API key not provided")
        
        self.llm = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=self.api_key,
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
        )
    
    def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate response from Gemini.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            conversation_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
            
        Returns:
            Generated response text
        """
        messages = []
        
        # Add system message if provided
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        # Add current prompt
        messages.append(HumanMessage(content=prompt))
        
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    def generate_with_tools(
        self,
        prompt: str,
        tools: List[Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response with function calling/tools.
        
        Args:
            prompt: User prompt
            tools: List of LangChain tools
            system_prompt: Optional system instructions
            
        Returns:
            Dict with response and tool calls
        """
        # This will be enhanced with LangGraph for tool orchestration
        messages = []
        
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        messages.append(HumanMessage(content=prompt))
        
        try:
            # Bind tools to the model
            llm_with_tools = self.llm.bind_tools(tools)
            response = llm_with_tools.invoke(messages)
            
            return {
                "response": response.content,
                "tool_calls": response.tool_calls if hasattr(response, 'tool_calls') else []
            }
        except Exception as e:
            raise Exception(f"Gemini tool calling error: {str(e)}")
    
    def health_check(self) -> bool:
        """
        Check if Gemini API is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self.llm.invoke([HumanMessage(content="ping")])
            return bool(response.content)
        except:
            return False
