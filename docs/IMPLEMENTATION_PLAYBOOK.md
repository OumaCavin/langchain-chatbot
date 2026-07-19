# Generic Chatbot Implementation Playbook

**Author:** Cavin Otieno
**Version:** 1.0.0
**Last Updated:** 2024-07-19
**Status:** Production Ready

---

## Executive Summary

This implementation playbook documents the development, deployment, and maintenance of two parallel chatbot implementations: one built with the PyBotchi framework and another built with LangChain. Both implementations provide a production-ready Stateless Document-Aware AI Assistant featuring WebSocket streaming, conversation memory, user authentication, search functionality, session export, and multi-format document support.

The project demonstrates a comparative approach to building AI-powered conversational interfaces, showcasing how different frameworks can achieve similar functionality through distinct architectural patterns. The PyBotchi implementation leverages the framework's Action and Agent base classes for AI orchestration, while the LangChain implementation utilizes LangChain's chain-based architecture for LLM integration.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [System Architecture](#3-system-architecture)
4. [Implementation Details](#4-implementation-details)
5. [Key Features](#5-key-features)
6. [Challenges and Solutions](#6-challenges-and-solutions)
7. [Testing Strategy](#7-testing-strategy)
8. [Deployment Guide](#8-deployment-guide)
9. [Maintenance and Support](#9-maintenance-and-support)
10. [Future Enhancements](#10-future-enhancements)

---

## 1. Project Overview

### 1.1 Project Description

The Generic Chatbot project is a comprehensive implementation of a Stateless Document-Aware AI Assistant that provides real-time conversational capabilities with support for document processing, conversation memory, and extensible intent orchestration. The project consists of two separate implementations that share common features but use different underlying frameworks for LLM integration.

### 1.2 Repository Structure

```
Generic-Chatbot/
├── pybotchi/                  # PyBotchi Framework Implementation
│   ├── pybotchi-chatbot/     # Standalone PyBotchi repository
│   │   ├── generic_agent/
│   │   │   ├── agent.py      # Core agent with GenericChatAction
│   │   │   ├── intents.py    # Intent Orchestrator
│   │   │   ├── router.py     # FastAPI endpoints
│   │   │   ├── database.py   # SQLite storage
│   │   │   └── orchestrator.py # Agentic Orchestrator Pattern
│   │   ├── main.py           # Application entry point
│   │   ├── requirements.txt  # Dependencies
│   │   └── docs/             # Documentation
│
├── langchain/                 # LangChain Framework Implementation
│   ├── langchain-chatbot/    # Standalone LangChain repository
│   │   ├── generic_agent/
│   │   │   ├── agent.py      # Core agent with LangChain
│   │   │   ├── router.py     # FastAPI endpoints
│   │   │   ├── database.py   # SQLite storage
│   │   │   ├── config.py     # Configuration
│   │   │   └── file_processor.py # Document processing
│   │   ├── main.py           # Application entry point
│   │   ├── requirements.txt  # Dependencies
│   │   └── docs/             # Documentation
│
├── scripts/                   # Utility scripts
├── templates/                 # Configuration templates
└── data/                      # Shared data directory
```

### 1.3 Technology Stack

Both implementations utilize a consistent technology stack to ensure feature parity and facilitate comparison:

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | FastAPI | REST API and WebSocket endpoints |
| ASGI Server | Uvicorn | Production-grade ASGI server |
| Database | SQLite | Persistent conversation storage |
| AI Integration | OpenAI GPT-4o-mini | Language model provider |
| Alternative AI | Google Gemini | Fallback AI provider |
| File Processing | PyPDF2, python-docx | Document text extraction |
| Authentication | JWT | Stateless authentication |
| Deployment | Docker | Containerized deployment |

### 1.4 Repository URLs

| Repository | GitHub URL |
|------------|------------|
| PyBotchi | https://github.com/OumaCavin/pybotchi-chatbot |
| LangChain | https://github.com/OumaCavin/langchain-chatbot |

---

## 2. Problem Statement

### 2.1 Business Requirements

The project addresses the following business requirements:

The need for an intelligent chatbot system that can engage users in natural language conversations while maintaining awareness of uploaded documents. The system must support real-time streaming responses for an enhanced user experience, handle multiple file formats for document ingestion, provide persistent conversation memory across sessions, and offer export capabilities for conversation records.

### 2.2 Technical Challenges

Several technical challenges were identified and addressed during implementation:

**Streaming Response Architecture:** Implementing token-by-token streaming requires careful handling of async generators and WebSocket connections. The system must buffer tokens efficiently while maintaining connection stability.

**Document Context Injection:** When users upload documents, the system must extract text content and inject it into the LLM context without overwhelming the model's context window. This requires intelligent content chunking and prioritization.

**Stateless Design:** The architecture must support stateless request processing where each request contains all necessary context, enabling horizontal scaling without sticky sessions.

**Intent Orchestration:** The PyBotchi implementation includes autonomous intent identification using the LLM to route requests to specialized handlers, requiring careful prompt engineering and error handling.

### 2.3 Framework Comparison Objective

By implementing the same feature set using two different frameworks, the project enables direct comparison of:

- Code complexity and maintainability
- Performance characteristics
- Extensibility patterns
- Community support and documentation

---

## 3. System Architecture

### 3.1 High-Level Architecture

Both implementations follow a consistent high-level architecture that separates concerns into distinct layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Web UI    │  │ Mobile App  │  │   Third-Party Clients   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API Gateway Layer                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              FastAPI + Uvicorn ASGI Server                   ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ ││
│  │  │  REST API   │  │  WebSocket  │  │   OpenAPI/Swagger   │ ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Business Logic Layer                        │
│  ┌─────────────────────┐       ┌─────────────────────────────┐  │
│  │  PyBotchi/LangChain │       │     Intent Orchestrator     │  │
│  │      Agent          │       │  (Autonomous Intent Routing)│  │
│  └─────────────────────┘       └─────────────────────────────┘  │
│           │                              │                       │
│           ▼                              ▼                       │
│  ┌─────────────────────┐       ┌─────────────────────────────┐  │
│  │   Action Handlers   │       │   Specialized Sub-Actions    │  │
│  │  - GenericChatAction│       │  - CalculatorAction         │  │
│  │  - FileUploadAction │       │  - CodeAction               │  │
│  └─────────────────────┘       │  - AnalysisAction          │  │
│                                │  - WritingAction            │  │
│                                └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
│  ┌─────────────────────┐       ┌─────────────────────────────┐  │
│  │   SQLite Database  │       │     File System Storage      │  │
│  │  - Sessions        │       │  - Uploaded Documents        │  │
│  │  - Messages        │       │  - Session Exports          │  │
│  │  - Files           │       │                             │  │
│  │  - Prompts         │       │                             │  │
│  └─────────────────────┘       └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     External Services                            │
│  ┌─────────────────────┐       ┌─────────────────────────────┐  │
│  │    OpenAI API       │       │    Google Gemini API        │  │
│  │   (Primary LLM)     │       │    (Alternative LLM)       │  │
│  └─────────────────────┘       └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Interactions

The system comprises several interacting components that work together to provide a seamless user experience:

**API Router (router.py):** Handles incoming HTTP and WebSocket requests, validates input, and dispatches to appropriate handlers. The router manages authentication, rate limiting, and CORS policies.

**Agent Core (agent.py):** The central orchestration component that manages conversation state, invokes the LLM, and coordinates response generation. In the PyBotchi implementation, this uses the GenericChatAction pattern; in the LangChain implementation, it uses LLMChain.

**Intent Orchestrator (intents.py - PyBotchi only):** An advanced feature that uses the LLM to autonomously identify user intent and delegate to specialized sub-actions. This enables dynamic routing based on semantic understanding of user messages.

**Database Manager (database.py):** Handles all persistence operations including session management, message storage, file metadata, and full-text search indexing.

**File Processor (file_processor.py - LangChain):** Specialized component for extracting text from uploaded documents including PDF, TXT, MD, and DOCX formats.

### 3.3 Data Flow

The following sequence diagrams illustrate the data flow for different operations:

**Chat Message Flow:**

```
User ──► WebSocket ──► Router ──► Agent.chat()
                                   │
                                   ▼
                              Context Creation
                              (prompts, history)
                                   │
                                   ▼
                              LLM Invocation
                              (streaming tokens)
                                   │
                                   ▼
                              Token Buffering
                              (full_response)
                                   │
                                   ▼
                              WebSocket ──► User
```

**Document Upload Flow:**

```
User ──► REST API ──► Router ──► File Processor
                                 │
                                 ▼
                            Text Extraction
                            (PDF, DOCX, TXT)
                                 │
                                 ▼
                            Database Storage
                            (file content)
                                 │
                                 ▼
                         Context Injection Ready
```

---

## 4. Implementation Details

### 4.1 PyBotchi Implementation

#### 4.1.1 Framework Overview

The PyBotchi implementation leverages the PyBotchi framework's Action and Agent base classes for AI orchestration. PyBotchi provides a structured approach to building AI agents through the definition of Actions with lifecycle methods (pre, execute, post) and Context management.

#### 4.1.2 Core Components

**GenericChatAction Class:**

The GenericChatAction class extends the base Action class and implements the core chat functionality:

```python
class GenericChatAction(Action):
    """
    Generic chat action that handles user messages and generates LLM responses.
    This action demonstrates proper LLM invocation within the PyBotchi framework.
    """

    async def pre(self, context: Context) -> ActionReturn:
        """
        Pre-execution phase: Extract user message from context.
        Validates input and prepares the action for LLM invocation.
        """
        # Extract the last user message from context.prompts
        last_user_message = ""
        for msg in reversed(context.prompts):
            if isinstance(msg, HumanMessage):
                last_user_message = msg.content if isinstance(msg.content, str) else str(msg.content)
                break

        if not last_user_message:
            self.response = "Hello! How can I assist you today?"
            return ActionReturn.GO

        return ActionReturn.GO

    async def execute(self, context: Context) -> ActionReturn:
        """
        Execution phase: Invoke the LLM and generate response.
        This is where the actual LLM call happens.
        """
        messages = self._build_messages(context.prompts)
        response = await self.llm.ainvoke(messages)
        self.response = response.content
        return ActionReturn.GO

    async def post(self, context: Context) -> ActionReturn:
        """
        Post-execution phase: Add response to context history.
        """
        await context.add_response(self, self.response)
        return ActionReturn.GO
```

**Critical Fix Applied:** The original implementation had a significant issue where the GenericChatAction.pre() method would return a greeting without actually calling the LLM. This was resolved by ensuring that the LLM is invoked in the execute() method and that context.prompts is properly set before execution.

**IntentOrchestrator Pattern:**

The IntentOrchestrator implements autonomous intent identification using a specialized Action that analyzes user messages and delegates to appropriate sub-actions:

```python
class IntentOrchestrator:
    """
    Orchestrator that uses LLM for intent identification and routing.
    Demonstrates the Agentic Orchestrator Pattern with nested child actions.
    """

    async def chat(self, message: str, prompts: list, history: list) -> tuple:
        """
        Main entry point for orchestrated chat.
        """
        # Build context with prompts
        context = Context()
        context.prompts = prompts  # Critical: Explicitly set prompts

        # Initialize orchestrator action
        orchestrator_action = IntentRouterAction(self.llm)

        # Execute orchestration
        result = await context.start(IntentRouterAction)

        return orchestrator_action, result
```

### 4.2 LangChain Implementation

#### 4.2.1 Framework Overview

The LangChain implementation uses LangChain's chain-based architecture for LLM integration. LangChain provides abstractions for prompts, chains, and agents that simplify the development of LLM-powered applications.

#### 4.2.2 Core Components

**GenericChatAgent Class:**

```python
class GenericChatAgent:
    """
    Core chat agent using LangChain for LLM integration.
    Provides streaming support and conversation memory.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize the agent with LLM configuration."""
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.7,
            streaming=True,
            api_key=api_key
        )

        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

    async def chat(self, message: str, system_prompt: str, history: list) -> str:
        """
        Process a chat message and return the response.
        """
        # Build prompt with system message and history
        messages = self._build_messages(message, system_prompt, history)

        # Invoke LLM
        response = await self.llm.ainvoke(messages)

        return response.content
```

**File Processing Integration:**

The LangChain implementation includes a FileProcessor class for document text extraction:

```python
class FileProcessor:
    """Handles extraction of text from various document formats."""

    SUPPORTED_FORMATS = {".pdf", ".txt", ".md", ".docx"}

    def extract_text(self, file_path: str) -> str:
        """Extract text content from a document."""
        ext = Path(file_path).suffix.lower()

        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext == ".docx":
            return self._extract_docx(file_path)
        elif ext in {".txt", ".md"}:
            return self._extract_text(file_path)
        else:
            raise ValueError(f"Unsupported format: {ext}")
```

### 4.3 Common Features

Both implementations share common features implemented through consistent patterns:

**Unified Response Buffer:**

Both implementations use a `_full_response` buffer to accumulate streaming tokens before finalization:

```python
_full_response: str = PrivateAttr(default_factory=str)

def add_token(self, token: str):
    """Add a token to the response buffer."""
    self._full_response += token
```

**Idempotent File Validation:**

File uploads use content hashing to prevent duplicate processing:

```python
_uploaded_file_hashes: dict = PrivateAttr(default_factory=dict)

def is_file_uploaded(self, file_hash: str) -> bool:
    """Check if a file has already been uploaded."""
    return file_hash in self._uploaded_file_hashes

def compute_file_hash(self, content: bytes) -> str:
    """Compute SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()
```

**Context History Sync:**

Both implementations sync conversation history to the prompts list:

```python
def add_to_history(self, role: str, content: str):
    """Add a message to conversation history and sync to prompts."""
    self.history.append({"role": role, "content": content})
    self.prompts.append(HumanMessage(content=content))
```

---

## 5. Key Features

### 5.1 Feature Matrix

The following table summarizes feature implementation across both implementations:

| Feature | PyBotchi | LangChain | Status |
|---------|----------|-----------|--------|
| Generic Chat Agent | ✅ | ✅ | Implemented |
| Streaming Response | ✅ | ✅ | Implemented |
| WebSocket Support | ✅ | ✅ | Implemented |
| PDF Upload | ✅ | ✅ | Implemented |
| Document Context | ✅ | ✅ | Implemented |
| Intent Orchestration | ✅ | ❌ | PyBotchi Only |
| Calculator Engine | ✅ | ✅ | Implemented |
| System Prompts | ✅ | ✅ | Implemented |
| Session Export | ✅ | ✅ | Implemented |
| Conversation Search | ✅ | ✅ | Implemented |
| JWT Authentication | ✅ | ✅ | Implemented |
| Idempotent Validation | ✅ | ✅ | Implemented |

### 5.2 Intent Orchestrator (PyBotchi)

The Intent Orchestrator is a unique feature of the PyBotchi implementation that enables autonomous intent identification and routing. This feature uses the LLM to analyze user messages and delegate to specialized sub-actions.

**Available Intents:**

| Intent | Sub-Action | Description |
|--------|------------|-------------|
| chat | ChatAction | General conversation and greetings |
| code | CodeAction | Programming assistance and code examples |
| analysis | AnalysisAction | Data analysis and insights |
| writing | WritingAction | Content creation and editing |
| calculator | CalculatorAction | Mathematical computations |

**Implementation:**

```python
class IntentRouterAction(Action):
    """Routes user requests to appropriate sub-actions based on intent."""

    async def _identify_intent(self, message: str) -> IntentType:
        """Use LLM to identify user intent."""
        intent_prompt = f"""
        Analyze this message and identify the primary intent:
        Message: {message}

        Options: chat, code, analysis, writing, calculator
        Return only the intent type, nothing else.
        """

        response = await self.llm.ainvoke([HumanMessage(content=intent_prompt)])
        intent_str = response.content.strip().lower()

        return IntentType(intent_str) if intent_str in IntentType._value2member_map_ else IntentType.CHAT
```

### 5.3 Calculator Engine

Both implementations include a specialized Calculator engine that handles mathematical computations:

```python
CALCULATOR_CONSTRAINTS = """You are a calculator assistant.
Rules:
1. Only perform mathematical operations
2. Show step-by-step calculations
3. Explain each step clearly
4. If input is not a math problem, respond: "I can only help with calculations."
"""

class CalculatorAction(Action):
    """Handles mathematical computation requests."""

    async def execute(self, context: Context) -> ActionReturn:
        """Execute calculator logic with constraints."""
        # Build prompt with calculator constraints
        messages = [SystemMessage(content=CALCULATOR_CONSTRAINTS)]
        messages.extend(context.prompts)

        # Invoke LLM with constraints
        response = await self.llm.ainvoke(messages)

        return ActionReturn(result=response.content)
```

---

## 6. Challenges and Solutions

### 6.1 Challenge: Greeting Response Issue

**Problem:** The chatbot always returned "Hello! How can I assist you today?" regardless of user input.

**Root Cause:** The GenericChatAction.pre() method was returning a greeting without calling the LLM. The action was echoing user messages or returning hardcoded responses instead of invoking the language model.

**Analysis:**

```python
# Original problematic code
async def pre(self, context: Context) -> ActionReturn:
    last_user_message = ""
    for msg in reversed(context.prompts):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break

    if not last_user_message:
        # This was returning the greeting without LLM call
        self.response = "Hello! How can I assist you today?"
        return ActionReturn.GO

    # This was just echoing, not generating AI response
    self.response = f"You said: {last_user_message}"
    return ActionReturn.GO
```

**Solution:** The fix involved three key changes:

1. Ensuring context.prompts is explicitly set before invoking the action:

```python
# In IntentOrchestrator.chat()
context = Context()
context.prompts = prompts  # Explicitly set prompts
```

2. Moving LLM invocation to the execute() method:

```python
async def execute(self, context: Context) -> ActionReturn:
    messages = self._build_messages(context.prompts)
    response = await self.llm.ainvoke(messages)
    self.response = response.content
    return ActionReturn.GO
```

3. Ensuring the LLM is properly initialized and accessible:

```python
class GenericChatAction(Action):
    def __init__(self, llm=None):
        super().__init__()
        self.llm = llm  # Store LLM reference
```

### 6.2 Challenge: Streaming Response Buffering

**Problem:** Token-by-token streaming over WebSocket was causing performance issues due to excessive network overhead.

**Solution:** Implemented a unified response buffer that accumulates tokens and sends them in batches:

```python
_full_response: str = PrivateAttr(default_factory=str)

async def stream_response(self, token: str):
    """Buffer tokens and send in batches."""
    self._full_response += token

    # Send in batches of 10 tokens
    if len(self._full_response) >= 10:
        await self.websocket.send_json({
            "type": "token",
            "content": self._full_response
        })
        self._full_response = ""

async def flush_buffer(self):
    """Send remaining buffered tokens."""
    if self._full_response:
        await self.websocket.send_json({
            "type": "token",
            "content": self._full_response
        })
        self._full_response = ""
```

### 6.3 Challenge: Document Context Window Limits

**Problem:** Large document uploads could exceed the LLM context window, causing errors or truncated responses.

**Solution:** Implemented intelligent content chunking and prioritization:

```python
MAX_CONTEXT_TOKENS = 6000  # Leave room for prompt and response

def truncate_context(self, content: str, max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
    """Truncate content to fit within context window."""
    # Estimate token count (rough approximation)
    estimated_tokens = len(content) // 4

    if estimated_tokens <= max_tokens:
        return content

    # Truncate and add indicator
    truncated = content[:max_tokens * 4]
    return truncated + "\n\n[Document truncated due to length...]"
```

### 6.4 Challenge: Message Role Mismatch

**Problem:** Database stored messages with role "assistant" but the code was checking for role "user" when reconstructing prompts.

**Solution:** Normalized role handling across the codebase:

```python
def normalize_role(role: str) -> str:
    """Normalize role strings to standard format."""
    role = role.lower().strip()

    if role in {"user", "human"}:
        return "user"
    elif role in {"assistant", "ai", "bot"}:
        return "assistant"
    elif role in {"system"}:
        return "system"
    else:
        return "user"  # Default to user for unknown roles

def create_message(role: str, content: str):
    """Create appropriate message type based on role."""
    role = normalize_role(role)

    if role == "user":
        return HumanMessage(content=content)
    elif role == "assistant":
        return AIMessage(content=content)
    else:
        return SystemMessage(content=content)
```

---

## 7. Testing Strategy

### 7.1 Unit Testing

Each component should have unit tests covering:

| Component | Test Coverage |
|-----------|---------------|
| Agent | LLM invocation, message building, error handling |
| Router | Endpoint validation, authentication, response formats |
| Database | CRUD operations, search functionality, file handling |
| File Processor | Text extraction, format support, error cases |
| Intent Orchestrator | Intent identification, routing logic, fallback behavior |

**Example Test:**

```python
def test_generic_chat_agent_llm_invocation():
    """Test that GenericChatAction properly invokes the LLM."""
    # Arrange
    agent = GenericChatAgent(api_key="test-key")
    context = Context()
    context.prompts = [HumanMessage(content="Hello")]

    action = GenericChatAction(llm=agent.llm)

    # Act
    result = asyncio.run(action.execute(context))

    # Assert
    assert result == ActionReturn.GO
    assert action.response != "Hello! How can I assist you today?"
    assert action.response != ""
```

### 7.2 Integration Testing

Integration tests verify end-to-end functionality:

```python
def test_chat_streaming_flow():
    """Test complete chat streaming flow."""
    # Start server
    # Connect WebSocket
    # Send message
    # Verify streaming tokens received
    # Verify final response
    pass
```

### 7.3 Deployment Testing

Both applications should be tested after deployment:

```bash
# Health check
curl https://deployed-url.com/api/v1/health

# Chat endpoint
curl -X POST https://deployed-url.com/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"message": "Hello"}'

# WebSocket
# Use JavaScript client to test streaming
```

---

## 8. Deployment Guide

### 8.1 Prerequisites

Before deployment, ensure you have:

- Python 3.10 or higher
- OpenAI API key (or Google API key for Gemini)
- Git
- Docker (optional for containerized deployment)
- Domain name and SSL certificate (for production)

### 8.2 Local Development Setup

```bash
# Clone the repository
git clone https://github.com/OumaCavin/pybotchi-chatbot.git
cd pybotchi-chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 8.3 Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p data uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t chatbot .
docker run -d -p 8000:8000 -e OPENAI_API_KEY=your_key chatbot
```

### 8.4 Cloud Platform Deployment

#### Railway

1. Create Railway account at railway.app
2. Connect GitHub repository
3. Add environment variables:
   - OPENAI_API_KEY
   - AI_PROVIDER
   - OPENAI_MODEL_NAME
4. Deploy with auto-detected settings

#### Render

1. Create Render account at render.com
2. Create Web Service
3. Configure:
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn main:app --host 0.0.0.0 --port 10000
4. Add environment variables

#### Fly.io

```bash
fly auth login
fly launch
fly secrets set OPENAI_API_KEY=your_key
fly deploy
```

### 8.5 Production Checklist

| Item | Status | Notes |
|------|--------|-------|
| HTTPS enabled | Required | Use Let's Encrypt or Cloudflare |
| API key secured | Required | Use environment variables, never hardcode |
| Rate limiting | Required | Prevent abuse and cost overruns |
| CORS configured | Required | Restrict to allowed origins |
| Logging enabled | Required | For debugging and monitoring |
| Health endpoint | Required | For load balancer checks |
| Backup strategy | Required | Regular database backups |
| Monitoring | Recommended | Use Prometheus, DataDog, or similar |
| Error tracking | Recommended | Use Sentry or similar |

---

## 9. Maintenance and Support

### 9.1 Monitoring

Monitor the following metrics:

- **API Latency:** Time from request to response
- **Error Rate:** Percentage of failed requests
- **Token Usage:** API calls and associated costs
- **Session Count:** Active and total sessions
- **File Uploads:** Volume and size of uploads

### 9.2 Logging

Both implementations support structured logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

### 9.3 Troubleshooting Guide

**Common Issues:**

| Issue | Symptom | Solution |
|-------|---------|----------|
| Greeting Response | Chatbot returns "Hello! How can I assist you today?" | Check LLM initialization and context.prompts setting |
| Module Not Found | ImportError for pybotchi or langchain | Activate virtual environment and reinstall dependencies |
| WebSocket Failed | Cannot connect to WebSocket | Check firewall settings and proxy configuration |
| API Errors | Invalid API Key or Rate Limit | Verify API key and check OpenAI dashboard |
| File Upload Fails | Upload errors | Check directory permissions and file size limits |

### 9.4 Backup and Recovery

```bash
# Backup database
sqlite3 data/conversations.db ".backup data/backup_$(date +%Y%m%d).db"

# Restore database
sqlite3 data/conversations.db ".restore data/backup_20240101.db"
```

---

## 10. Future Enhancements

### 10.1 Planned Features

The following enhancements are planned for future releases:

- **Multi-language Support:** Extend the system to support multiple languages with appropriate model selection
- **Voice Integration:** Add speech-to-text and text-to-speech capabilities
- **Advanced Analytics:** Implement conversation analytics and user behavior tracking
- **Plugin System:** Create an extensible plugin architecture for custom functionality
- **Knowledge Base Integration:** Connect to external knowledge bases for enhanced responses

### 10.2 Framework Comparison Insights

Based on implementation experience:

**PyBotchi Advantages:**

- Structured Action lifecycle provides clear execution flow
- Native support for intent orchestration patterns
- Context management is built into the framework
- Better suited for complex multi-step agent behaviors

**LangChain Advantages:**

- Simpler initial setup and configuration
- Extensive library of pre-built chains and tools
- Strong community support and documentation
- Better for rapid prototyping and standard patterns

**Recommendation:** Choose PyBotchi for complex agent behaviors with multiple sub-actions. Choose LangChain for standard chatbot functionality with quicker development time.

---

## Appendix A: API Reference

### A.1 REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/health | Health check |
| POST | /api/v1/chat | Send chat message |
| POST | /api/v1/chat/stream | Streaming chat response |
| POST | /api/v1/upload/documents | Upload documents |
| GET | /api/v1/files | List uploaded files |
| GET | /api/v1/files/{file_id} | Get file content |
| POST | /api/v1/search | Search conversations |
| GET | /api/v1/export/{session_id}/json | Export as JSON |
| GET | /api/v1/export/{session_id}/text | Export as text |
| GET | /api/v1/prompts | List system prompts |
| POST | /api/v1/prompts | Create system prompt |
| DELETE | /api/v1/prompts/{prompt_id} | Delete system prompt |
| POST | /api/v1/auth/register | Register user |
| POST | /api/v1/auth/login | Login user |
| GET | /api/v1/sessions | List sessions |
| DELETE | /api/v1/sessions/{session_id} | Delete session |

### A.2 WebSocket Endpoint

**Endpoint:** ws://host:port/api/v1/ws/chat

**Message Format:**

```json
{
  "type": "message",
  "content": "Hello, how are you?",
  "session_id": "optional-session-id",
  "system_prompt": "optional-custom-prompt"
}
```

**Response Format:**

```json
{
  "type": "token",
  "content": "Hello!"
}
```

---

## Appendix B: Environment Variables

### B.1 Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| OPENAI_API_KEY | OpenAI API key | sk-... |
| AI_PROVIDER | AI provider (openai or google) | openai |
| OPENAI_MODEL_NAME | Model name | gpt-4o-mini |

### B.2 Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| HOST | Server host | 0.0.0.0 |
| PORT | Server port | 8000 |
| DEBUG | Debug mode | false |
| SECRET_KEY | JWT secret key | auto-generated |
| DB_PATH | Database path | data/conversations.db |
| MAX_UPLOAD_SIZE | Max upload size in MB | 10 |

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| Action | In PyBotchi, a unit of work with pre/execute/post lifecycle |
| Agent | In LangChain, an entity that uses an LLM to determine actions |
| Chain | In LangChain, a sequence of components that process inputs |
| Context | PyBotchi construct that holds execution state and prompts |
| Intent | Semantic classification of user message purpose |
| Streaming | Token-by-token response delivery for real-time UX |
| Stateless | Architecture where each request contains all necessary context |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2024-07-19 | Cavin Otieno | Initial version |

---

## License

MIT License

Copyright (c) 2024 Cavin Otieno

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
