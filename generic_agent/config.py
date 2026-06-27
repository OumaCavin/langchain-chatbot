"""
Configuration Module for Generic Chat Agent

Centralized configuration management using Pydantic settings.

Author: Cavin Otieno
"""

import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class ServerConfig(BaseSettings):
    """Server configuration."""
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")


class OpenAIConfig(BaseSettings):
    """OpenAI configuration."""
    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    model_name: str = Field(default="gpt-4o-mini", description="Model name")
    base_url: str = Field(default="https://api.openai.com/v1", description="API base URL")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature")


class GeminiConfig(BaseSettings):
    """Google Gemini configuration."""
    api_key: Optional[str] = Field(default=None, description="Gemini API key")
    model_name: str = Field(default="gemini-2.0-flash", description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature")


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    path: str = Field(default="data/conversations.db", description="Database path")


class SecurityConfig(BaseSettings):
    """Security configuration."""
    api_key_enabled: bool = Field(default=False, description="Enable API key auth")
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")


class Config(BaseSettings):
    """Main configuration."""
    server: ServerConfig = Field(default_factory=ServerConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    ai_provider: Literal["openai", "gemini"] = Field(default="openai", description="AI provider")


_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get the singleton config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
