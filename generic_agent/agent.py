"""
Generic Chat Agent Module using LangChain

Implements a generic chat agent using LangChain for AI orchestration.
Supports both OpenAI and Google Gemini APIs with streaming support.

Author: Cavin Otieno
"""

import os
from typing import Any, AsyncIterator, Literal, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


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
    """

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
                messages.append(SystemMessage(content=content))

        messages.append(HumanMessage(content=user_message))

        return messages

    async def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[list[dict]] = None
    ) -> str:
        """
        Generate a non-streaming chat response.

        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            history: Conversation history

        Returns:
            The generated response string
        """
        llm = self._initialize_llm()
        history = history or []

        if system_prompt is None:
            system_prompt = "You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user questions."

        messages = self._build_messages(user_message, history, system_prompt)

        response = await llm.ainvoke(messages)
        return response.content

    async def chat_stream(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[list[dict]] = None
    ) -> AsyncIterator[str]:
        """
        Generate a streaming chat response.

        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            history: Conversation history

        Yields:
            Response tokens as they are generated
        """
        llm = self._initialize_llm()
        history = history or []

        if system_prompt is None:
            system_prompt = "You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user questions."

        messages = self._build_messages(user_message, history, system_prompt)

        async for chunk in llm.astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content
            elif isinstance(chunk, str):
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

    subgraph Processing["Processing Layer"]
        Provider[{provider_name}]
        Model[Model: {model_name}]
        Chain[LangChain Chain]
    end

    subgraph Output["Output Layer"]
        StreamResponse[Streaming Response]
        DirectResponse[Direct Response]
    end

    UserInput --> Chain
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
