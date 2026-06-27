"""
Generic Chat Agent - Main Application

A production-ready chatbot service with conversation memory,
WebSocket streaming, and multi-format document support.

Author: Cavin Otieno
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from generic_agent.router import router
from generic_agent.database import get_database
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    print("=" * 50)
    print("Generic Chat Agent - Starting Up (LangChain)")
    print("=" * 50)
    print(f"AI Provider: {os.environ.get('AI_PROVIDER', 'openai')}")
    print("=" * 50)

    db = get_database()
    print("Database initialized")

    yield

    print("=" * 50)
    print("Generic Chat Agent - Shutting Down")
    print("=" * 50)


app = FastAPI(
    title="Generic Chat Agent",
    description="A production-ready chatbot with LangChain AI orchestration, conversation memory, and document processing.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API information."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Generic Chat Agent API</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .card {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            h1 { color: #333; margin-bottom: 10px; }
            h2 { color: #666; font-size: 1.2em; margin-top: 20px; }
            code {
                background: #e8e8e8;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: monospace;
            }
            .endpoint {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
            }
            .method {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 0.85em;
                margin-right: 10px;
            }
            .get { background: #10b981; color: white; }
            .post { background: #3b82f6; color: white; }
            .ws { background: #8b5cf6; color: white; }
            a { color: #3b82f6; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Generic Chat Agent API (LangChain)</h1>
            <p>Production-ready chatbot with LangChain AI orchestration, conversation memory, and document processing.</p>
            <p><strong>Version:</strong> 1.0.0</p>
            <p><strong>Framework:</strong> LangChain</p>
        </div>

        <div class="card">
            <h2>API Documentation</h2>
            <p><a href="/docs">Swagger UI</a> | <a href="/redoc">ReDoc</a></p>
        </div>

        <div class="card">
            <h2>Key Endpoints</h2>

            <div class="endpoint">
                <span class="method ws">WS</span>
                <code>/generic-chat/ws</code> - WebSocket streaming chat
            </div>

            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/generic-chat/chat</code> - Direct chat API
            </div>

            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/generic-chat/upload/document</code> - Upload documents (PDF, DOCX, TXT, MD)
            </div>

            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/generic-chat/health</code> - Health check
            </div>

            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/generic-chat/sessions</code> - List conversation sessions
            </div>
        </div>

        <div class="card">
            <h2>Features</h2>
            <ul>
                <li><strong>AI Providers:</strong> OpenAI (GPT-4) and Google Gemini</li>
                <li><strong>Conversation Memory:</strong> SQLite-based persistent storage</li>
                <li><strong>Multi-Format Support:</strong> PDF, DOCX, TXT, Markdown</li>
                <li><strong>Rate Limiting:</strong> Configurable request limits</li>
                <li><strong>WebSocket Streaming:</strong> Real-time token-by-token responses</li>
            </ul>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def global_health():
    """Global health check."""
    return {
        "status": "healthy",
        "service": "generic-chat-agent-langchain",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    debug = os.environ.get("DEBUG", "false").lower() == "true"

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
