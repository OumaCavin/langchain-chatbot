"""
FastAPI Router Module for Generic Chat Agent

Provides WebSocket streaming, REST chat, and document upload endpoints.
Features: conversation memory, multi-format support, rate limiting.

Author: Cavin Otieno
"""

import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    Body,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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

router = APIRouter(prefix="/generic-chat", tags=["Generic Chat Agent"])

_agents: dict[str, GenericChatAgent] = {}


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = Field(None, max_length=100)
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    session_id: str
    message_id: Optional[int] = None


class SessionResponse(BaseModel):
    """Session info response."""
    session_id: str
    message_count: int
    created_at: str
    updated_at: str


def _get_or_create_agent() -> GenericChatAgent:
    """Get or create the default agent."""
    if "default" not in _agents:
        provider = os.environ.get("AI_PROVIDER", "openai")
        api_key = os.environ.get("OPENAI_API_KEY")
        model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini")
        base_url = os.environ.get("OPENAI_BASE_URL")
        temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))

        _agents["default"] = create_generic_chat_agent(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            temperature=temperature,
            streaming=True,
        )
    return _agents["default"]


@router.websocket("/ws")
async def websocket_chat(
    websocket: WebSocket,
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
):
    """WebSocket endpoint for streaming chat with conversation memory."""
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

                    agent = _get_or_create_agent()
                    response_text = ""

                    async for token in agent.chat_stream(
                        user_message=content,
                        system_prompt=system_prompt,
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


@router.post("/chat", response_model=ChatResponse)
async def chat_direct(
    request: ChatRequest = None,
    message: str = None,
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
):
    """
    Direct chat endpoint with conversation memory.

    Supports both JSON body and query parameters for flexibility.
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
        agent = _get_or_create_agent()

        context = db.get_conversation_context(session_id, max_messages=10)

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


@router.post("/upload/document")
async def upload_document(
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
):
    """
    Upload and extract text from a document.

    Supported formats: PDF, TXT, MD, DOCX
    Max file size: 10MB
    """
    valid, msg = InputValidator.validate_file_type(
        file.filename,
        FileProcessor.SUPPORTED_FORMATS.keys()
    )
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    content = await file.read()
    valid, msg = InputValidator.validate_file_size(len(content))
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

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

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir) / file.filename

        with open(temp_path, "wb") as f:
            f.write(content)

        processor = get_file_processor()
        result = processor.process_file(str(temp_path), file.filename)

        db.add_message(
            session_id,
            "system",
            f"[Document: {result.filename} - {result.char_count} characters extracted]"
        )

        return JSONResponse({
            "filename": result.filename,
            "file_type": result.file_type,
            "extracted_text": result.content,
            "char_count": result.char_count,
            "session_id": session_id,
            "status": "success" if result.success else "error",
            "error": result.error
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )
    finally:
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/upload/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
):
    """Legacy PDF upload endpoint (redirects to document upload)."""
    return await upload_document(file, session_id)


@router.get("/session/{session_id}", response_model=SessionResponse)
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

    return SessionResponse(
        session_id=session.id,
        message_count=len(messages),
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.delete("/session/{session_id}")
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


@router.get("/sessions")
async def list_sessions(limit: int = 20):
    """List recent conversation sessions."""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    db = get_database()
    sessions = db.list_sessions(limit=limit)

    return JSONResponse({
        "sessions": sessions,
        "count": len(sessions)
    })


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    db = get_database()
    sessions = db.list_sessions(limit=1)

    return {
        "status": "healthy",
        "service": "chat-agent",
        "provider": os.environ.get("AI_PROVIDER", "openai"),
        "model": os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini"),
        "version": "1.0.0",
        "total_sessions": len(db.list_sessions(limit=1000)),
        "features": {
            "conversation_memory": True,
            "multi_format_upload": True,
            "rate_limiting": True,
        }
    }


@router.get("/graph")
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


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported document formats."""
    processor = get_file_processor()
    return JSONResponse({
        "formats": processor.get_supported_formats(),
        "max_file_size_mb": 10
    })
