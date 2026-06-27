"""
Generic Chat Agent Module

Provides a clean, modular architecture for generic chat agents
with streaming, WebSocket, and document processing support.

Author: Cavin Otieno
"""

from .agent import GenericChatAgent, create_generic_chat_agent

__version__ = "1.0.0"
__all__ = ["GenericChatAgent", "create_generic_chat_agent"]
