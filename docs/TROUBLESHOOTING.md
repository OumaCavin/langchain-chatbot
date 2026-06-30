# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the LangChain Chatbot.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Authentication Problems](#authentication-problems)
3. [File Upload Issues](#file-upload-issues)
4. [Streaming Problems](#streaming-problems)
5. [Database Errors](#database-errors)
6. [Performance Issues](#performance-issues)
7. [Common Error Messages](#common-error-messages)

---

## Connection Issues

### WebSocket Connection Fails

**Symptoms:**
- Connection status shows "Disconnected" or "Error"
- Messages not sending or receiving

**Solutions:**

1. **Check API Key**
   ```bash
   # Verify your API key is set correctly
   echo $OPENAI_API_KEY
   ```

2. **Check Server Status**
   ```bash
   # Verify server is running
   curl http://localhost:8000/api/v1/health
   ```

3. **Check CORS Settings**
   Ensure your frontend origin is in the allowed CORS list in `main.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],  # Add your frontend URL
       ...
   )
   ```

4. **Network Issues**
   - Check firewall settings
   - Verify port 8000 is not blocked
   - Try using a different network

### Cannot Connect to Backend

**Symptoms:**
- Frontend shows connection error
- 502 Bad Gateway error

**Solutions:**

1. **Restart the Backend**
   ```bash
   # Kill existing process
   pkill -f "uvicorn main:app"

   # Start fresh
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Check Port Availability**
   ```bash
   # On Linux/Mac
   lsof -i :8000

   # On Windows
   netstat -ano | findstr :8000
   ```

---

## Authentication Problems

### Login/Register Fails

**Symptoms:**
- "Invalid credentials" error
- 401 Unauthorized response

**Solutions:**

1. **Check Password Requirements**
   - Minimum 8 characters
   - Passwords are case-sensitive

2. **Verify User Exists**
   ```bash
   # Try registering first
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "password123"}'
   ```

3. **Check JWT Token Expiry**
   - Tokens expire after 30 days
   - Re-login to get a fresh token

### API Key Not Working

**Symptoms:**
- "Invalid API key" error
- Requests always return 401

**Solutions:**

1. **Verify API Key Format**
   - OpenAI keys start with `sk-`
   - Google keys are longer alphanumeric strings

2. **Check Environment Variable**
   ```bash
   # Set in .env file
   OPENAI_API_KEY=sk-your-actual-key-here

   # Or export directly
   export OPENAI_API_KEY=sk-your-actual-key-here
   ```

3. **Test API Key Directly**
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer YOUR_API_KEY"
   ```

---

## File Upload Issues

### File Upload Fails

**Symptoms:**
- Upload progress stuck at 0%
- "File type not supported" error

**Solutions:**

1. **Check Supported Formats**
   - PDF (.pdf)
   - Text (.txt)
   - Markdown (.md)
   - Word (.docx)

2. **Check File Size**
   - Maximum file size: 10MB per file
   - Maximum 5 files per upload

3. **Verify File Permissions**
   ```bash
   # Ensure uploads directory exists and is writable
   mkdir -p uploads
   chmod 755 uploads
   ```

4. **Check File Encoding**
   - For text files, ensure UTF-8 encoding
   - Avoid binary files or corrupted documents

### PDF Text Extraction Fails

**Symptoms:**
- Upload succeeds but content is empty
- Garbled or missing text

**Solutions:**

1. **Use OCR for Scanned PDFs**
   - Install tesseract OCR
   - Use text-based PDFs when possible

2. **Check PDF Version**
   - Some older PDFs may have compatibility issues
   - Try converting to PDF/A format

---

## Streaming Problems

### Streaming Stops Midway

**Symptoms:**
- Response cuts off unexpectedly
- Partial response received

**Solutions:**

1. **Check Network Stability**
   - Use a stable internet connection
   - Avoid long-running requests on mobile data

2. **Increase Timeout**
   ```python
   # In main.py
   app = FastAPI(timeout=300)  # 5 minutes
   ```

3. **Check Model Quotas**
   - OpenAI: Check rate limits in dashboard
   - Google: Check quota usage in Google Cloud

### Tokens Not Displaying

**Symptoms:**
- Response received but UI doesn't update
- No streaming visible

**Solutions:**

1. **Check Frontend Network**
   - Verify SSE (Server-Sent Events) support
   - Check browser console for errors

2. **Verify Response Format**
   ```javascript
   // Ensure proper SSE parsing
   const reader = response.body.getReader();
   ```

---

## Database Errors

### Database Lock Error

**Symptoms:**
- "Database is locked" error
- Write operations fail

**Solutions:**

1. **Check for Active Connections**
   ```bash
   # Kill any hanging Python processes
   pkill -9 -f "python.*main.py"
   ```

2. **Enable WAL Mode**
   ```python
   # In database.py
   cursor.execute("PRAGMA journal_mode=WAL")
   ```

3. **Increase Timeout**
   ```python
   # Add timeout to connection
   conn = sqlite3.connect(DB_PATH, timeout=30)
   ```

### Migration Errors

**Symptoms:**
- "No such table" error
- Schema mismatch

**Solutions:**

1. **Initialize Database**
   ```bash
   # Delete existing database
   rm -f data/chatbot.db

   # Restart server to auto-create
   python main.py
   ```

2. **Backup Before Reset**
   ```bash
   cp data/chatbot.db data/chatbot.db.backup
   ```

---

## Performance Issues

### Slow Response Times

**Symptoms:**
- Long delays before first token
- Overall sluggish performance

**Solutions:**

1. **Optimize Model Settings**
   ```env
   # In .env - Use faster model for testing
   OPENAI_MODEL_NAME=gpt-4o-mini
   ```

2. **Enable Response Caching**
   - Identical queries return cached responses
   - Reduces API costs

3. **Monitor Resource Usage**
   ```bash
   # Check CPU and memory
   top -p $(pgrep -f "uvicorn")

   # Check disk I/O
   iostat -x 1
   ```

### High Memory Usage

**Symptoms:**
- Server memory keeps growing
- Eventually crashes

**Solutions:**

1. **Set Conversation Limits**
   ```python
   MAX_MESSAGES_PER_SESSION = 100
   MAX_TOKENS_PER_SESSION = 8000
   ```

2. **Clear Old Sessions**
   ```bash
   # Add to cron job
   0 2 * * * find data/ -name "*.db" -mtime +30 -delete
   ```

---

## Common Error Messages

### "LLM initialization failed"

**Cause:** API key invalid or missing

**Solution:**
1. Verify API key in `.env` file
2. Test API key directly with provider
3. Check if API key has remaining quota

### "Rate limit exceeded"

**Cause:** Too many requests

**Solution:**
1. Wait and retry after cooldown
2. Implement exponential backoff
3. Upgrade to higher tier plan

### "Invalid session ID"

**Cause:** Session doesn't exist or was deleted

**Solution:**
1. Create new session
2. List available sessions first:
   ```bash
   curl http://localhost:8000/api/v1/sessions
   ```

### "Unsupported file type"

**Cause:** File format not in allowlist

**Solution:**
1. Convert file to supported format
2. Add new extension to `ALLOWED_EXTENSIONS` in `file_processor.py`

### "CORS policy blocked"

**Cause:** Frontend origin not allowed

**Solution:**
```python
# In main.py, add your domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Getting Help

If you continue to experience issues:

1. **Check Logs**
   ```bash
   # Enable debug logging
   LOG_LEVEL=DEBUG python main.py
   ```

2. **Open an Issue**
   - GitHub Issues: https://github.com/OumaCavin/langchain-chatbot/issues

3. **Enable Debug Mode**
   ```bash
   # Set in .env
   DEBUG=true
   ```

---

## Health Check Commands

Verify your setup with these commands:

```bash
# 1. Check server is running
curl http://localhost:8000/api/v1/health

# 2. Check database
sqlite3 data/chatbot.db "SELECT COUNT(*) FROM sessions;"

# 3. Check file permissions
ls -la data/ uploads/

# 4. Check Python packages
pip list | grep -E "fastapi|langchain|openai"
```
