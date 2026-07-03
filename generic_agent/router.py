"""
FastAPI Router Module for Generic Chat Agent

Provides WebSocket streaming, REST chat, document upload, user authentication,
search, export, and system prompt management endpoints.

Author: Cavin Otieno
"""

import os
import tempfile
import uuid
import json
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    Body,
    Header,
    Depends,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .agent import GenericChatAgent, create_generic_chat_agent
from .database import get_database
from .security import (
    verify_api_key,
    check_rate_limit,
    get_rate_limiter,
    InputValidator,
)
from .file_processor import get_file_processor, FileProcessor

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

router = APIRouter(prefix="/api/v1", tags=["Generic Chat Agent"])

security = HTTPBearer(auto_error=False)
_agents: dict[str, GenericChatAgent] = {}


def _get_or_create_agent(api_key: Optional[str] = None) -> GenericChatAgent:
    """Get or create an agent with optional API key."""
    cache_key = api_key or "default"

    if cache_key not in _agents:
        provider = os.environ.get("AI_PROVIDER", "openai")
        key = api_key or os.environ.get("OPENAI_API_KEY")
        model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini")
        base_url = os.environ.get("OPENAI_BASE_URL")
        temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))

        _agents[cache_key] = create_generic_chat_agent(
            provider=provider,
            api_key=key,
            model_name=model_name,
            base_url=base_url,
            temperature=temperature,
            streaming=True,
        )
    return _agents[cache_key]


# ============ Request/Response Models ============

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = Field(None, max_length=100)
    system_prompt: Optional[str] = None
    files: Optional[List[str]] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    message_id: Optional[int] = None


class SessionResponse(BaseModel):
    session_id: str
    title: Optional[str] = None
    message_count: int
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: str


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    api_key: Optional[str] = None
    created_at: str


class SystemPromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=5000)


class SystemPromptResponse(BaseModel):
    id: str
    name: str
    content: str
    is_default: bool


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=50, ge=1, le=100)


class SearchResult(BaseModel):
    session_id: str
    message_id: int
    snippet: str
    role: str
    created_at: str


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str
    char_count: int
    status: str


# ============ Authentication Endpoints ============

@router.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
async def register_user(user: UserRegister):
    """
    Register a new user account.

    Returns user info and a unique API key for programmatic access.
    """
    db = get_database()
    try:
        result = db.create_user(user.username, user.email, user.password)

        # Get the API key for the user
        user_record = db.get_user(result.id)
        api_key = None
        if user_record:
            conn = db._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT api_key FROM users WHERE id = ?", (result.id,))
            row = cursor.fetchone()
            if row:
                api_key = row["api_key"]

        return UserResponse(
            id=result.id,
            username=result.username,
            email=result.email,
            api_key=api_key,
            created_at=result.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login", response_model=UserResponse, tags=["Authentication"])
async def login_user(credentials: UserLogin):
    """
    Authenticate a user and return their info with API key.
    """
    db = get_database()
    result = db.authenticate_user(credentials.username, credentials.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Get the API key for the user
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT api_key FROM users WHERE id = ?", (result.id,))
    row = cursor.fetchone()
    api_key = row["api_key"] if row else None

    return UserResponse(
        id=result.id,
        username=result.username,
        email=result.email,
        api_key=api_key,
        created_at=result.created_at or ""
    )


# ============ Chat Endpoints ============

def _build_document_context(db, session_id: str) -> Optional[str]:
    """
    Build document context from uploaded files for a session.

    This enables the Stateless Document-Aware AI Assistant architecture
    by injecting uploaded document content into LLM context.
    """
    try:
        files = db.get_session_files(session_id)
        if not files:
            return None

        doc_context = "=== UPLOADED DOCUMENTS ===\n\n"
        for f in files:
            doc_context += f"--- {f.filename} ---\n{f.content[:10000]}\n\n"

        return doc_context
    except Exception:
        return None


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    api_key: Optional[str] = None,
):
    """WebSocket endpoint for streaming chat with conversation memory and document awareness."""
    db = get_database()

    if session_id:
        valid, msg = InputValidator.validate_session_id(session_id)
        if not valid:
            await websocket.close(code=1008, reason="Invalid session ID")
            return
        if not db.get_session(session_id):
            db.create_session(session_id)
    else:
        session_id = str(uuid.uuid4())[:8]
        db.create_session(session_id)

    # Get user from API key if provided
    user_id = None
    if api_key:
        user = db.get_user_by_api_key(api_key)
        if user:
            user_id = user.id

    await websocket.accept()

    await websocket.send_json({
        "type": "session",
        "session_id": session_id
    })

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if data.get("type") == "message":
                content = data.get("content", "").strip()

                valid, msg = InputValidator.validate_message(content)
                if not valid:
                    await websocket.send_json({
                        "type": "error",
                        "content": msg
                    })
                    continue

                content = InputValidator.sanitize_message(content)

                await websocket.send_json({"type": "token", "content": ""})

                try:
                    context = db.get_conversation_context(session_id, max_messages=10)

                    # Get session system prompt if not provided
                    session = db.get_session(session_id)
                    effective_prompt = system_prompt or (session.system_prompt if session else None)

                    # Inject document context for Document-Aware AI Assistant
                    doc_context = _build_document_context(db, session_id)
                    if doc_context:
                        doc_instruction = "\n\nUse the above uploaded documents to answer user questions. If the user asks about content in the documents, reference them directly."
                        if effective_prompt:
                            effective_prompt = effective_prompt + doc_instruction + "\n\n" + doc_context
                        else:
                            effective_prompt = "You are a helpful AI assistant." + doc_instruction + "\n\n" + doc_context

                    agent = _get_or_create_agent(api_key)
                    response_text = ""

                    async for token in agent.chat_stream(
                        user_message=content,
                        system_prompt=effective_prompt,
                        history=context
                    ):
                        response_text += token
                        await websocket.send_json({"type": "token", "content": token})

                    db.add_message(session_id, "user", content)
                    db.add_message(session_id, "assistant", response_text)

                    await websocket.send_json({"type": "done", "content": "[DONE]"})

                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "rate limit" in error_msg.lower():
                        await websocket.send_json({
                            "type": "error",
                            "content": "Rate limit exceeded. Please wait before sending more messages."
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "content": f"Error generating response: {error_msg}"
                        })
                continue

            if data.get("type") == "history":
                messages = db.get_conversation_context(session_id, max_messages=50)
                await websocket.send_json({
                    "type": "history",
                    "messages": messages
                })
                continue

            if data.get("type") == "update_system_prompt":
                new_prompt = data.get("content", "")
                db.update_session_system_prompt(session_id, new_prompt)
                await websocket.send_json({
                    "type": "system_prompt_updated",
                    "content": new_prompt
                })
                continue

            await websocket.send_json({
                "type": "error",
                "content": f"Unknown message type: {data.get('type')}"
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Connection error: {str(e)}"
            })
        except Exception:
            pass


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_direct(
    request: ChatRequest = None,
    message: str = None,
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    api_key: Optional[str] = Header(None),
):
    """
    Direct chat endpoint with conversation memory and document awareness.

    Supports both JSON body and query parameters for flexibility.
    Automatically injects uploaded document content into LLM context.
    """
    if message is None and request is None:
        raise HTTPException(
            status_code=400,
            detail="Message is required. Send as JSON body or query parameter."
        )

    if message is None and request is not None:
        message = request.message
        if session_id is None:
            session_id = request.session_id
        if system_prompt is None:
            system_prompt = request.system_prompt

    valid, msg = InputValidator.validate_message(message)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    content = InputValidator.sanitize_message(message)

    db = get_database()
    if session_id:
        valid, msg = InputValidator.validate_session_id(session_id)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)
        if not db.get_session(session_id):
            db.create_session(session_id)
    else:
        session_id = str(uuid.uuid4())[:8]
        db.create_session(session_id)

    try:
        agent = _get_or_create_agent(api_key)

        context = db.get_conversation_context(session_id, max_messages=10)

        # Get session system prompt if not provided
        if system_prompt is None:
            session = db.get_session(session_id)
            if session and session.system_prompt:
                system_prompt = session.system_prompt

        # Inject document context for Document-Aware AI Assistant
        doc_context = _build_document_context(db, session_id)
        if doc_context:
            doc_instruction = "\n\nUse the above uploaded documents to answer user questions. If the user asks about content in the documents, reference them directly."
            if system_prompt:
                system_prompt = system_prompt + doc_instruction + "\n\n" + doc_context
            else:
                system_prompt = "You are a helpful AI assistant." + doc_instruction + "\n\n" + doc_context

        response_text = await agent.chat(content, system_prompt, history=context)

        db.add_message(session_id, "user", content)
        msg_record = db.add_message(session_id, "assistant", response_text)

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            message_id=msg_record.id
        )

    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "quota" in error_str:
            raise HTTPException(
                status_code=429,
                detail="API rate limit exceeded. Please try again later."
            )
        if "401" in error_str or "api key" in error_str:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key. Please check your configuration."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )


# ============ Multi-File Upload Endpoints ============

@router.post("/upload/documents", response_model=List[FileUploadResponse], tags=["Files"])
async def upload_multiple_documents(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = None,
):
    """
    Upload and process multiple documents simultaneously.

    Supported formats: PDF, TXT, MD, DOCX
    Max file size: 10MB per file
    Max files: 10
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed")

    db = get_database()
    if session_id:
        valid, msg = InputValidator.validate_session_id(session_id)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)
        if not db.get_session(session_id):
            db.create_session(session_id)
    else:
        session_id = str(uuid.uuid4())[:8]
        db.create_session(session_id)

    results = []
    temp_dirs = []

    try:
        for file in files:
            valid, msg = InputValidator.validate_file_type(
                file.filename,
                FileProcessor.SUPPORTED_FORMATS.keys()
            )
            if not valid:
                results.append(FileUploadResponse(
                    file_id="",
                    filename=file.filename,
                    file_type="",
                    char_count=0,
                    status=f"error: {msg}"
                ))
                continue

            content = await file.read()
            valid, msg = InputValidator.validate_file_size(len(content))
            if not valid:
                results.append(FileUploadResponse(
                    file_id="",
                    filename=file.filename,
                    file_type="",
                    char_count=0,
                    status=f"error: {msg}"
                ))
                continue

            file_id = str(uuid.uuid4())
            temp_dir = tempfile.mkdtemp()
            temp_dirs.append(temp_dir)
            temp_path = Path(temp_dir) / file.filename

            with open(temp_path, "wb") as f:
                f.write(content)

            try:
                processor = get_file_processor()
                result = processor.process_file(str(temp_path), file.filename)

                # Save to database
                db.add_file(file_id, session_id, result.filename, result.file_type, result.content)
                db.add_message(
                    session_id,
                    "system",
                    f"[Document: {result.filename} - {result.char_count} characters extracted]"
                )

                results.append(FileUploadResponse(
                    file_id=file_id,
                    filename=result.filename,
                    file_type=result.file_type,
                    char_count=result.char_count,
                    status="success" if result.success else "error"
                ))
            except Exception as e:
                results.append(FileUploadResponse(
                    file_id=file_id,
                    filename=file.filename,
                    file_type="",
                    char_count=0,
                    status=f"error: {str(e)}"
                ))

        return results

    finally:
        for temp_dir in temp_dirs:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/upload/document", response_model=FileUploadResponse, tags=["Files"])
async def upload_document(
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
):
    """Upload and extract text from a single document."""
    results = await upload_multiple_documents([file], session_id)
    return results[0]


@router.get("/files/{session_id}", tags=["Files"])
async def get_session_files(session_id: str):
    """Get all uploaded files for a session."""
    db = get_database()
    files = db.get_session_files(session_id)

    return JSONResponse({
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "file_type": f.file_type,
                "content": f.content,
                "created_at": f.created_at
            }
            for f in files
        ],
        "count": len(files)
    })


# ============ Session Management Endpoints ============

@router.get("/sessions", tags=["Sessions"])
async def list_sessions(
    limit: int = 20,
    api_key: Optional[str] = Header(None),
):
    """List recent conversation sessions."""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    db = get_database()

    # Get user from API key if provided
    user_id = None
    if api_key:
        user = db.get_user_by_api_key(api_key)
        if user:
            user_id = user.id

    sessions = db.list_sessions(limit=limit, user_id=user_id)

    return JSONResponse({
        "sessions": [
            {
                "session_id": s.id,
                "title": s.title,
                "created_at": s.created_at,
                "updated_at": s.updated_at
            }
            for s in sessions
        ],
        "count": len(sessions)
    })


@router.get("/session/{session_id}", tags=["Sessions"])
async def get_session_info(session_id: str):
    """Get information about a conversation session."""
    valid, msg = InputValidator.validate_session_id(session_id)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    db = get_database()
    session = db.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.get_messages(session_id, limit=1000)

    return JSONResponse({
        "session_id": session.id,
        "title": session.title,
        "system_prompt": session.system_prompt,
        "message_count": len(messages),
        "created_at": session.created_at,
        "updated_at": session.updated_at
    })


@router.get("/session/{session_id}/messages", tags=["Sessions"])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
):
    """Get all messages for a session."""
    valid, msg = InputValidator.validate_session_id(session_id)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    db = get_database()
    messages = db.get_messages(session_id, limit=limit)

    return JSONResponse({
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at
            }
            for m in messages
        ],
        "count": len(messages)
    })


@router.patch("/session/{session_id}", tags=["Sessions"])
async def update_session(
    session_id: str,
    title: Optional[str] = None,
    system_prompt: Optional[str] = None,
):
    """Update session title or system prompt."""
    valid, msg = InputValidator.validate_session_id(session_id)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    db = get_database()
    session = db.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if title is not None:
        db.update_session_title(session_id, title)

    if system_prompt is not None:
        db.update_session_system_prompt(session_id, system_prompt)

    return JSONResponse({"status": "success"})


@router.delete("/session/{session_id}", tags=["Sessions"])
async def delete_session(session_id: str):
    """Delete a conversation session and all its messages."""
    valid, msg = InputValidator.validate_session_id(session_id)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    db = get_database()
    deleted = db.delete_session(session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return JSONResponse({
        "status": "success",
        "message": f"Session {session_id} deleted"
    })


# ============ Search Endpoints ============

@router.post("/search", response_model=List[SearchResult], tags=["Search"])
async def search_messages(
    request: SearchRequest,
    api_key: Optional[str] = Header(None),
):
    """
    Search messages across all sessions.

    Returns snippets with highlighted matches.
    """
    db = get_database()

    # Get user from API key if provided
    user_id = None
    if api_key:
        user = db.get_user_by_api_key(api_key)
        if user:
            user_id = user.id

    results = db.search_messages(request.query, user_id, request.limit)

    return [
        SearchResult(
            session_id=r.session_id,
            message_id=r.message_id,
            snippet=r.snippet,
            role=r.role,
            created_at=r.created_at
        )
        for r in results
    ]


# ============ Export Endpoints ============

@router.get("/export/{session_id}/json", tags=["Export"])
async def export_session_json(session_id: str):
    """Export session data as JSON."""
    valid, msg = InputValidator.validate_session_id(session_id)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    db = get_database()
    data = db.export_session_json(session_id)

    return JSONResponse(data)


@router.get("/export/{session_id}/text", tags=["Export"])
async def export_session_text(session_id: str):
    """Export session data as plain text."""
    valid, msg = InputValidator.validate_session_id(session_id)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    db = get_database()
    text = db.export_session_text(session_id)

    return StreamingResponse(
        iter([text]),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=chat_export_{session_id}.txt"
        }
    )


# ============ System Prompts Endpoints ============

@router.get("/prompts", response_model=List[SystemPromptResponse], tags=["System Prompts"])
async def get_system_prompts(api_key: Optional[str] = Header(None)):
    """Get all available system prompts."""
    db = get_database()

    # Get user from API key if provided
    user_id = None
    if api_key:
        user = db.get_user_by_api_key(api_key)
        if user:
            user_id = user.id

    prompts = db.get_system_prompts(user_id)

    return [
        SystemPromptResponse(
            id=p["id"],
            name=p["name"],
            content=p["content"],
            is_default=p["is_default"]
        )
        for p in prompts
    ]


@router.post("/prompts", response_model=SystemPromptResponse, tags=["System Prompts"])
async def create_system_prompt(
    prompt: SystemPromptCreate,
    api_key: Optional[str] = Header(None),
):
    """Create a custom system prompt."""
    db = get_database()

    # Get user from API key if provided
    user_id = None
    if api_key:
        user = db.get_user_by_api_key(api_key)
        if user:
            user_id = user.id

    prompt_id = secrets.token_urlsafe(16)
    db.save_system_prompt(prompt_id, user_id, prompt.name, prompt.content)

    return SystemPromptResponse(
        id=prompt_id,
        name=prompt.name,
        content=prompt.content,
        is_default=False
    )


@router.delete("/prompts/{prompt_id}", tags=["System Prompts"])
async def delete_system_prompt(prompt_id: str):
    """Delete a custom system prompt."""
    db = get_database()
    deleted = db.delete_system_prompt(prompt_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Prompt not found or is a default prompt")

    return JSONResponse({"status": "success"})


# ============ Health and Info Endpoints ============

@router.get("/health", tags=["Info"])
async def health_check():
    """Health check endpoint."""
    db = get_database()
    sessions = db.list_sessions(limit=1)

    return {
        "status": "healthy",
        "service": "chat-agent",
        "version": "2.0.0",
        "provider": os.environ.get("AI_PROVIDER", "openai"),
        "model": os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini"),
        "total_sessions": len(db.list_sessions(limit=1000)),
        "features": {
            "conversation_memory": True,
            "multi_file_upload": True,
            "rate_limiting": True,
            "user_authentication": True,
            "message_search": True,
            "session_export": True,
            "system_prompts": True,
            "websocket_streaming": True
        }
    }


@router.get("/formats", tags=["Info"])
async def get_supported_formats():
    """Get list of supported document formats."""
    processor = get_file_processor()
    return JSONResponse({
        "formats": processor.get_supported_formats(),
        "max_file_size_mb": 10,
        "max_files_per_request": 10
    })


@router.get("/graph", tags=["Info"])
async def get_agent_graph():
    """Get Mermaid flowchart representation of the agent."""
    try:
        agent = _get_or_create_agent()
        graph = await agent.get_agent_graph()
        return JSONResponse({"flowchart": graph})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating agent graph: {str(e)}"
        )
