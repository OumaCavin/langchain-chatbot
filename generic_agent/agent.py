"""
Generic Chat Agent Module using LangChain

Implements a generic chat agent using LangChain for AI orchestration.
Supports both OpenAI and Google Gemini APIs with streaming support.
Includes intent-based routing with specialized handlers.

Author: Cavin Otieno
"""

import os
import re
import json
import hashlib
from typing import Any, AsyncIterator, Literal, Optional, Dict, List
from enum import Enum

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


class IntentType(str, Enum):
    """Supported intent types for routing."""
    CHAT = "chat"
    CODE = "code"
    ANALYSIS = "analysis"
    WRITING = "writing"
    CALCULATOR = "calculator"
    UNKNOWN = "unknown"


class IntentResult:
    """Result of intent identification."""
    def __init__(self, intent: str, reasoning: str):
        self.intent = intent
        self.reasoning = reasoning


def create_llm(
    provider: Literal["openai", "gemini"] = "openai",
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.7,
    streaming: bool = True,
) -> BaseChatModel:
    """
    Factory function to create an LLM instance based on the provider.

    Args:
        provider: Either "openai" or "gemini"
        model_name: Model name (optional, uses default if not provided)
        api_key: API key (optional, falls back to env var)
        base_url: Base URL for OpenAI API (optional)
        temperature: Temperature for generation
        streaming: Whether to enable streaming

    Returns:
        Configured LLM instance
    """
    if provider == "gemini":
        gemini_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        gemini_model = model_name or os.environ.get("GEMINI_MODEL_NAME", "gemini-2.0-flash")

        return ChatGoogleGenerativeAI(
            model=gemini_model,
            api_key=gemini_key,
            temperature=temperature,
            streaming=streaming,
        )
    else:
        openai_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        openai_model = model_name or os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini")
        openai_base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

        return ChatOpenAI(
            model=openai_model,
            api_key=openai_key,
            base_url=openai_base_url,
            temperature=temperature,
            streaming=streaming,
        )


class GenericChatAgent:
    """
    Generic chat agent using LangChain for orchestration.

    Supports both OpenAI and Google Gemini models with conversation history.
    Includes intent-based routing with specialized handlers and idempotent file validation.
    """

    # System prompt constraints for calculator action
    CALCULATOR_CONSTRAINTS = """You are a mathematical calculator assistant. You MUST:
1. Only perform mathematical operations: addition, subtraction, multiplication, division, exponents, roots
2. For expressions, clearly state the formula and show steps
3. Format numbers appropriately (2 decimal places for money, etc.)
4. If a calculation is too complex, explain what would be needed
5. NEVER execute arbitrary code or system commands
6. If the input is not a valid math expression, respond with "INVALID_EXPRESSION"
7. Convert units when requested (km to miles, etc.)

Supported operations:
- Basic: +, -, *, /, **
- Roots: sqrt(n), root(n, m)
- Trigonometry: sin, cos, tan (use degrees)
- Logarithms: log(n), log10(n), ln(n)
- Constants: pi, e
"""

    # Intent identification prompt
    INTENT_PROMPT = """Analyze the user's message and identify the most appropriate action.

Available Actions:
- chat: General conversation, casual chat, greetings, general questions, opinions, explanations of concepts.
- code: Code generation, debugging, code review, explaining code, programming questions.
- analysis: Data analysis, charts, graphs, statistics, trends, insights, reports.
- writing: Writing, editing, summarizing, translating, content creation, proofreading.
- calculator: Mathematical calculations, equations, computations, solving math problems, number conversions.

User Message: {user_message}

Respond with ONLY a JSON object in this exact format:
{{"intent": "action_name", "reasoning": "brief explanation of why this action was selected"}}

Select the action that best matches the user's intent. If the message is ambiguous, default to "chat"."""

    def __init__(
        self,
        provider: Literal["openai", "gemini"] = "openai",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        streaming: bool = True,
    ):
        """
        Initialize the generic chat agent.

        Args:
            provider: AI provider - "openai" or "gemini"
            model_name: Model name (defaults based on provider)
            api_key: API key (optional, falls back to env var)
            base_url: Base URL for OpenAI API (optional)
            temperature: Temperature for response generation
            streaming: Whether to enable streaming responses
        """
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.streaming = streaming
        self._llm = None
        self._chain = None

        # Full response buffer for unified response handling
        self._full_response: str = ""

        # Idempotent file hash validation
        self._uploaded_file_hashes: Dict[str, str] = {}

        # Current intent tracking
        self._current_intent: Optional[IntentResult] = None

    def _initialize_llm(self) -> BaseChatModel:
        """Initialize and configure the LLM instance."""
        if self._llm is not None:
            return self._llm

        self._llm = create_llm(
            provider=self.provider,
            model_name=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            streaming=self.streaming,
        )

        return self._llm

    def _build_chain(self) -> Any:
        """Build the LangChain prompt and chain."""
        if self._chain is not None:
            return self._chain

        prompt = ChatPromptTemplate.from_messages([
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", "{input}"),
        ])

        self._chain = prompt | self._llm | StrOutputParser()

        return self._chain

    def _build_messages(
        self,
        user_message: str,
        history: list[dict],
        system_prompt: Optional[str] = None
    ) -> list[BaseMessage]:
        """Build message list from history and current message."""
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_message))

        return messages

    # =========================================================================
    # Intent Detection Methods
    # =========================================================================

    async def identify_intent(self, user_message: str) -> IntentResult:
        """
        Identify the intent of a user message using LLM.

        Args:
            user_message: The user's message

        Returns:
            IntentResult with intent type and reasoning
        """
        llm = self._initialize_llm()

        prompt = self.INTENT_PROMPT.format(user_message=user_message)

        try:
            response = await llm.ainvoke([
                SystemMessage(content=prompt),
                HumanMessage(content=user_message)
            ])

            content = response.content if hasattr(response, "content") else str(response)

            # Parse JSON response
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                intent = data.get("intent", "chat")
                reasoning = data.get("reasoning", "")
                self._current_intent = IntentResult(intent, reasoning)
                return self._current_intent

            return IntentResult("chat", "Could not parse intent, defaulting to chat")

        except Exception as e:
            return IntentResult("chat", f"Error identifying intent: {str(e)}, defaulting to chat")

    def get_current_intent(self) -> Optional[IntentResult]:
        """Get the current intent result."""
        return self._current_intent

    def _get_intent_system_prompt(self, intent: str) -> Optional[str]:
        """Get specialized system prompt for intent."""
        prompts = {
            IntentType.CODE: """You are an expert programmer and code assistant. When generating code:
1. Write clean, well-documented code with comments
2. Follow best practices for the language
3. Include error handling where appropriate
4. Use meaningful variable and function names
5. Format code properly with appropriate indentation
6. Provide a brief explanation of how the code works

For debugging requests, explain the issue and provide the fixed code.""",

            IntentType.ANALYSIS: """You are a data analysis expert. When analyzing data or creating insights:
1. Provide clear, actionable insights
2. Use appropriate statistical methods
3. Explain your reasoning
4. Format tables and data clearly
5. Highlight key trends and patterns
6. Suggest follow-up analyses if relevant""",

            IntentType.WRITING: """You are a professional writer and editor. When creating or editing content:
1. Write clear, engaging content appropriate for the audience
2. Use proper grammar, spelling, and punctuation
3. Structure content logically with appropriate headings
4. Maintain consistent tone and style
5. Provide the requested format (email, article, summary, etc.)
6. If editing, suggest improvements while preserving the author's voice""",
        }

        return prompts.get(intent)

    # =========================================================================
    # Idempotent File Validation Methods
    # =========================================================================

    def register_file_hash(self, file_hash: str, file_id: str) -> bool:
        """
        Register a file hash for idempotent upload validation.

        Args:
            file_hash: Hash of the file content
            file_id: Unique identifier for this file

        Returns:
            True if this is a new file, False if duplicate
        """
        if file_hash in self._uploaded_file_hashes:
            return False  # Duplicate upload
        self._uploaded_file_hashes[file_hash] = file_id
        return True  # New upload

    def is_file_uploaded(self, file_hash: str) -> bool:
        """Check if a file has already been uploaded."""
        return file_hash in self._uploaded_file_hashes

    def get_existing_file_id(self, file_hash: str) -> Optional[str]:
        """Get the existing file ID for a hash."""
        return self._uploaded_file_hashes.get(file_hash)

    def compute_file_hash(self, content: bytes) -> str:
        """Compute SHA256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    # =========================================================================
    # Full Response Buffer Methods
    # =========================================================================

    def append_to_response(self, content: str) -> None:
        """Append content to the unified response buffer."""
        self._full_response += content

    def clear_response_buffer(self) -> None:
        """Clear the unified response buffer."""
        self._full_response = ""

    def get_full_response(self) -> str:
        """Get the current unified response."""
        return self._full_response

    # =========================================================================
    # Chat Methods
    # =========================================================================

    async def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[list[dict]] = None,
        intent: Optional[str] = None
    ) -> str:
        """
        Generate a non-streaming chat response.

        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            history: Conversation history
            intent: Optional explicit intent type

        Returns:
            The generated response string
        """
        llm = self._initialize_llm()
        history = history or []
        self.clear_response_buffer()

        # Identify intent if not provided
        if intent is None:
            intent_result = await self.identify_intent(user_message)
            intent = intent_result.intent

        # Get intent-specific system prompt
        if system_prompt is None:
            intent_prompt = self._get_intent_system_prompt(intent)
            if intent_prompt:
                system_prompt = intent_prompt
            else:
                system_prompt = "You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user questions."

        # Handle calculator intent specially
        if intent == IntentType.CALCULATOR:
            system_prompt = self.CALCULATOR_CONSTRAINTS
            user_message = f"Calculate or evaluate: {user_message}"

        messages = self._build_messages(user_message, history, system_prompt)

        response = await llm.ainvoke(messages)
        full_response = response.content if hasattr(response, "content") else str(response)

        # Validate calculator response
        if intent == IntentType.CALCULATOR and "INVALID_EXPRESSION" in full_response:
            full_response = "I couldn't understand that as a mathematical expression. Please provide a valid math expression like '2 + 3' or 'sqrt(16)'."

        self.append_to_response(full_response)
        return full_response

    async def chat_stream(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[list[dict]] = None,
        intent: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Generate a streaming chat response.

        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            history: Conversation history
            intent: Optional explicit intent type

        Yields:
            Response tokens as they are generated
        """
        llm = self._initialize_llm()
        history = history or []
        self.clear_response_buffer()

        # Identify intent if not provided
        if intent is None:
            intent_result = await self.identify_intent(user_message)
            intent = intent_result.intent

        # Get intent-specific system prompt
        if system_prompt is None:
            intent_prompt = self._get_intent_system_prompt(intent)
            if intent_prompt:
                system_prompt = intent_prompt
            else:
                system_prompt = "You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user questions."

        # Handle calculator intent specially
        if intent == IntentType.CALCULATOR:
            system_prompt = self.CALCULATOR_CONSTRAINTS
            user_message = f"Calculate or evaluate: {user_message}"

        messages = self._build_messages(user_message, history, system_prompt)

        async for chunk in llm.astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                self.append_to_response(chunk.content)
                yield chunk.content
            elif isinstance(chunk, str):
                self.append_to_response(chunk)
                yield chunk

    async def get_agent_graph(self) -> str:
        """Generate a Mermaid flowchart for the agent."""
        provider_name = "Google Gemini" if self.provider == "gemini" else "OpenAI"
        model_name = self.model_name or (
            os.environ.get("GEMINI_MODEL_NAME", "gemini-2.0-flash")
            if self.provider == "gemini"
            else os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini")
        )

        return f"""flowchart TB
    subgraph Input["Input Layer"]
        UserInput[User Message]
        SystemPrompt[System Prompt]
        History[Conversation History]
    end

    subgraph Intent["Intent Detection"]
        IntentLLM[Intent Identifier]
        IntentMap["Intent Types"]
    end

    subgraph Processing["Processing Layer"]
        Provider[{provider_name}]
        Model[Model: {model_name}]
        Chain[LangChain Chain]
    end

    subgraph Output["Output Layer"]
        StreamResponse[Streaming Response]
        DirectResponse[Direct Response]
    end

    UserInput --> IntentLLM
    IntentLLM --> IntentMap
    IntentMap --> SystemPrompt
    SystemPrompt --> Chain
    History --> Chain
    Chain --> Model
    Model --> Provider
    Provider --> StreamResponse
    Provider --> DirectResponse"""


def create_generic_chat_agent(
    provider: Literal["openai", "gemini"] = "openai",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.7,
    streaming: bool = True,
) -> GenericChatAgent:
    """
    Factory function to create a GenericChatAgent instance.

    Args:
        provider: AI provider
        api_key: API key
        model_name: Model name
        base_url: Base URL for OpenAI API
        temperature: Response temperature
        streaming: Enable streaming

    Returns:
        Configured GenericChatAgent instance
    """
    return GenericChatAgent(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        streaming=streaming,
    )
