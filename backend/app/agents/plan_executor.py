from typing import List, Dict, Optional, Any
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain.agents import AgentExecutor
    create_tool_calling_agent = None
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
try:
    from langchain.tools import Tool
except ImportError:
    from langchain.tools import BaseTool as Tool
from ..integrations.gemini_client import GeminiClient
from ..integrations.groq_client import GroqClient
from ..memory.conversation_memory import ConversationMemory

class VoiceAssistantAgent:
    """
    AI orchestration layer for the Sentinel voice assistant.
    Uses LangChain for reasoning, planning, and tool execution.
    """
    
    def __init__(
        self,
        use_groq_fallback: bool = True,
        memory: Optional[ConversationMemory] = None
    ):
        """
        Initialize the voice assistant agent.
        
        Args:
            use_groq_fallback: Whether to use Groq as fallback if Gemini fails
            memory: Conversation memory instance
        """
        self.use_groq_fallback = use_groq_fallback
        self.memory = memory or ConversationMemory()
        
        # Initialize LLM clients
        try:
            self.gemini_client = GeminiClient()
            self.primary_llm = self.gemini_client.llm
            self.llm_name = "Gemini"
        except Exception as e:
            if use_groq_fallback:
                print(f"Gemini initialization failed: {e}. Using Groq.")
                self.groq_client = GroqClient()
                self.primary_llm = self.groq_client.llm
                self.llm_name = "Groq"
            else:
                raise
        
        # System prompt for the assistant
        self.system_prompt = """You are Sentinel, an intelligent voice assistant that helps with daily tasks.
You understand both Hindi and English (Hinglish). You are helpful, concise, and proactive.

Your capabilities include:
- Answering questions and having conversations
- Helping with email management
- Searching for product prices
- Providing weather information
- Booking flights and checking prices
- General task automation

When you need to use tools, explain what you're doing and provide helpful responses."""
        
        # Initialize tools (empty for now, will be populated)
        self.tools: List[Tool] = []
        
    def register_tool(self, tool: Tool):
        """
        Register a new tool for the agent to use.
        
        Args:
            tool: LangChain Tool instance
        """
        self.tools.append(tool)
    
    def register_tools(self, tools: List[Tool]):
        """
        Register multiple tools.
        
        Args:
            tools: List of LangChain Tool instances
        """
        self.tools.extend(tools)
    
    def process_query(
        self,
        query: str,
        include_context: bool = True,
        save_to_memory: bool = True
    ) -> Dict[str, Any]:
        """
        Process a user query and generate a response.
        
        Args:
            query: User's query text
            include_context: Whether to include conversation history
            save_to_memory: Whether to save this interaction to memory
        
        Returns:
            Dict with response and metadata
        """
        try:
            # Get conversation context
            context = ""
            conversation_history = []
            
            if include_context:
                context = self.memory.get_context_for_prompt(query)
                conversation_history = self.memory.get_recent_messages(limit=5)
            
            # If no tools are registered, use direct LLM response
            if not self.tools:
                response = self._generate_simple_response(
                    query, 
                    context,
                    conversation_history
                )
            else:
                response = self._generate_with_tools(
                    query,
                    context,
                    conversation_history
                )
            
            # Save to memory
            if save_to_memory:
                self.memory.add_message("user", query)
                self.memory.add_message("assistant", response)
            
            return {
                "response": response,
                "llm_used": self.llm_name,
                "tools_used": [],  # TODO: Track which tools were used
                "success": True
            }
            
        except Exception as e:
            # Try fallback if Gemini fails
            if self.use_groq_fallback and self.llm_name == "Gemini":
                try:
                    print(f"Gemini failed: {e}. Trying Groq fallback...")
                    self.groq_client = GroqClient()
                    self.primary_llm = self.groq_client.llm
                    self.llm_name = "Groq"
                    
                    # Retry with Groq
                    return self.process_query(query, include_context, save_to_memory)
                except Exception as fallback_error:
                    return {
                        "response": f"I'm having trouble processing your request. Error: {str(fallback_error)}",
                        "llm_used": "none",
                        "tools_used": [],
                        "success": False,
                        "error": str(fallback_error)
                    }
            
            return {
                "response": f"I encountered an error: {str(e)}",
                "llm_used": self.llm_name,
                "tools_used": [],
                "success": False,
                "error": str(e)
            }
    
    def _generate_simple_response(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Generate a response without tools using direct LLM call.
        
        Args:
            query: User query
            context: Conversation context
            conversation_history: Recent messages
        
        Returns:
            Generated response text
        """
        # Build the full prompt with context
        full_prompt = query
        if context:
            full_prompt = f"{context}\n\nCurrent query: {query}"
        
        # Use Gemini or Groq client
        if self.llm_name == "Gemini":
            response = self.gemini_client.generate_response(
                prompt=full_prompt,
                system_prompt=self.system_prompt,
                conversation_history=conversation_history
            )
        else:
            response = self.groq_client.generate_response(
                prompt=full_prompt,
                system_prompt=self.system_prompt,
                conversation_history=conversation_history
            )
        
        return response
    
    def _generate_with_tools(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Generate a response using tools via LangChain agent.
        
        Args:
            query: User query
            context: Conversation context
            conversation_history: Recent messages
        
        Returns:
            Generated response text
        """
        # For now, if tools are registered but agent creation is not available,
        # use simple response with tool descriptions in context
        if create_tool_calling_agent is None:
            # Fallback: describe available tools to the LLM
            tool_descriptions = "\n".join([
                f"- {tool.name}: {tool.description}" 
                for tool in self.tools
            ])
            enhanced_prompt = f"{query}\n\nAvailable tools:\n{tool_descriptions}"
            return self._generate_simple_response(enhanced_prompt, context, conversation_history)
        
        # Create the prompt template for the agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        try:
            # Create agent with tools
            agent = create_tool_calling_agent(self.primary_llm, self.tools, prompt)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                max_iterations=5,
                handle_parsing_errors=True
            )
            
            # Prepare input with context
            full_query = query
            if context:
                full_query = f"Context:\n{context}\n\nQuery: {query}"
            
            # Execute agent
            result = agent_executor.invoke({
                "input": full_query,
                "chat_history": self.memory.get_langchain_messages(limit=5)
            })
            
            return result.get("output", "I couldn't generate a response.")
        except Exception as e:
            # Fallback to simple response if agent fails
            print(f"Agent execution failed: {e}. Using simple response.")
            return self._generate_simple_response(query, context, conversation_history)
    
    def clear_memory(self):
        """Clear the conversation memory."""
        self.memory.clear_session()
