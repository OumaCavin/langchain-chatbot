# Generic Chat Agent - LangChain Implementation

![Featured Image](./imgs/featured.png)

<div align="center">

![Python](imgs/badges/python.svg)
![FastAPI](imgs/badges/fastapi.svg)
![LangChain](imgs/badges/langchain.svg)
![WebSocket](imgs/badges/websocket.svg)
![OpenAI](imgs/badges/openai.svg)
![SQLite](imgs/badges/sqlite.svg)
![Streaming](imgs/badges/streaming.svg)

</div>

A production-ready generic chat agent built with LangChain, featuring WebSocket streaming, conversation memory, and multi-format document support.

## Features

- **Generic Chat Agent**: AI-powered conversational interface with streaming responses
- **WebSocket Support**: Real-time token-by-token streaming for enhanced user experience
- **PDF File Upload**: Upload and extract text from PDF documents with progress tracking
- **Conversation Memory**: SQLite-based persistent storage for conversation history
- **Multi-Format Support**: Process PDF, TXT, MD, and DOCX files
- **OpenAI & Gemini Support**: Works with both OpenAI GPT and Google Gemini models
- **Clean Architecture**: Modular design with separation of concerns

## Architecture

```
langchain-chatbot/
├── generic_agent/
│   ├── __init__.py
│   ├── agent.py         # Core chat agent with LLM integration
│   ├── router.py        # FastAPI routes for REST and WebSocket
│   ├── database.py      # SQLite-based conversation storage
│   ├── config.py        # Configuration management
│   ├── security.py      # Input validation and rate limiting
│   └── file_processor.py # Document processing utilities
├── data/                # Database storage
├── main.py              # FastAPI application entry point
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variables template
```

## Installation

### Prerequisites

- Python 3.9 or higher
- pip or uv package manager

### Setup

1. **Clone the repository**

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

   Or with uvicorn:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Configuration

Edit the `.env` file to configure the application:

```env
# AI Provider (openai or gemini)
AI_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL_NAME=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TEMPERATURE=0.7

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

## API Endpoints

### WebSocket Chat

**Endpoint**: `ws://host:port/generic-chat/ws`

Connect to receive real-time streaming responses:

```javascript
const ws = new WebSocket('ws://localhost:8000/generic-chat/ws');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'message',
        content: 'Hello, how are you?'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'token') {
        console.log(data.content);
    }
};
```

### REST Chat

**Endpoint**: `POST /generic-chat/chat`

```bash
curl -X POST http://localhost:8000/generic-chat/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

### File Upload

**Endpoint**: `POST /generic-chat/upload/document`

```bash
curl -X POST http://localhost:8000/generic-chat/upload/document \
  -F "file=@document.pdf"
```

### Session Management

- `GET /generic-chat/sessions` - List all sessions
- `GET /generic-chat/session/{session_id}` - Get session info
- `DELETE /generic-chat/session/{session_id}` - Delete session

### Health Check

**Endpoint**: `GET /generic-chat/health`

## Development

### Running Tests

```bash
pytest tests/
```

### Project Structure

- `generic_agent/agent.py`: Core agent logic with LangChain integration
- `generic_agent/router.py`: API endpoints and WebSocket handling
- `generic_agent/database.py`: SQLite storage for conversations
- `generic_agent/file_processor.py`: Document text extraction

## License

MIT License

## Author

Cavin Otieno
