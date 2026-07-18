# Deployment Guide

**Author:** Cavin Otieno
**Version:** 2.0.0
**Last Updated:** 2024-07-19

This guide covers deploying the LangChain Chatbot to various platforms. The LangChain chatbot is a production-ready Stateless Document-Aware AI Assistant built with LangChain, featuring WebSocket streaming, conversation memory, user authentication, search, export, and multi-format document support.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Platforms](#cloud-platforms)
   - [Railway](#railway)
   - [Render](#render)
   - [Fly.io](#flyio)
   - [AWS](#aws)
   - [Google Cloud](#google-cloud)
4. [Reverse Proxy Setup](#reverse-proxy-setup)
5. [SSL/HTTPS Setup](#sslhttps-setup)
6. [Production Checklist](#production-checklist)

---

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/OumaCavin/langchain-chatbot.git
cd langchain-chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Run the server
python main.py
```

### Development with Auto-reload

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Docker Deployment

### Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data uploads

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  chatbot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AI_PROVIDER=${AI_PROVIDER:-openai}
      - OPENAI_MODEL_NAME=${OPENAI_MODEL_NAME:-gpt-4o-mini}
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
    restart: unless-stopped
```

### Build and Run

```bash
# Build image
docker build -t langchain-chatbot .

# Run container
docker run -d \
  --name chatbot \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key_here \
  langchain-chatbot

# Or use docker-compose
docker-compose up -d
```

---

## Cloud Platforms

### Railway

Railway offers the easiest deployment for Python applications.

#### Steps:

1. **Create Railway Account**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

2. **Deploy from GitHub**
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway auto-detects Python

3. **Configure Environment**
   - Add environment variables in Railway dashboard:
     - `OPENAI_API_KEY`
     - `AI_PROVIDER`
     - `OPENAI_MODEL_NAME`

4. **Set Start Command**
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

#### Railway `railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Render

#### Steps:

1. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Connect GitHub repository

2. **Create Web Service**
   - Click "New" → "Web Service"
   - Connect your repository
   - Configure:
     - **Root Directory:** (leave empty)
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port 10000`

3. **Add Environment Variables**
   - In dashboard, add:
     - `OPENAI_API_KEY`
     - `AI_PROVIDER`
     - `OPENAI_MODEL_NAME`

#### Render `render.yaml`:

```yaml
services:
  - type: web
    name: langchain-chatbot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port 10000
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: AI_PROVIDER
        value: openai
      - key: OPENAI_MODEL_NAME
        value: gpt-4o-mini
```

### Fly.io

#### Steps:

1. **Install Fly CLI**
   ```bash
   brew install flyctl  # macOS
   # or
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login and Initialize**
   ```bash
   fly auth login
   fly launch
   ```

3. **Configure**
   - Set app name
   - Choose region closest to users

4. **Deploy**
   ```bash
   # Set secrets
   fly secrets set OPENAI_API_KEY=your_key_here

   # Deploy
   fly deploy
   ```

#### Fly `fly.toml`:

```toml
app = "langchain-chatbot"
primary_region = "iad"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
```

### AWS

#### Option 1: Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 langchain-chatbot

# Create environment
eb create production-env

# Set environment variables
eb setenv OPENAI_API_KEY=your_key_here

# Deploy updates
eb deploy
```

#### Option 2: ECS/Fargate

1. Push image to ECR:
   ```bash
   aws ecr create-repository --repository-name langchain-chatbot
   docker tag langchain-chatbot:latest your-account.dkr.ecr.us-east-1.amazonaws.com/langchain-chatbot:latest
   docker push your-account.dkr.ecr.us-east-1.amazonaws.com/langchain-chatbot:latest
   ```

2. Create Task Definition and Service in ECS Console

#### Option 3: Lambda + API Gateway

For serverless, consider:
- Using [Mangum](https://github.com/jordaneremia/mangum) for FastAPI Lambda adapter
- Note: WebSocket support requires API Gateway WebSocket API

### Google Cloud

#### Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/langchain-chatbot

# Deploy
gcloud run deploy langchain-chatbot \
  --image gcr.io/PROJECT_ID/langchain-chatbot \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "OPENAI_API_KEY=your_key_here"
```

#### App Engine

Create `app.yaml`:

```yaml
runtime: python311

instance_class: F2

env_variables:
  OPENAI_API_KEY: "your_key_here"
  AI_PROVIDER: "openai"
  OPENAI_MODEL_NAME: "gpt-4o-mini"

handlers:
  - url: /.*
    script: auto
    secure: always
```

Deploy:
```bash
gcloud app deploy
```

---

## Reverse Proxy Setup

### Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
```

### Caddy

```caddy
yourdomain.com {
    reverse_proxy localhost:8000

    # Enable WebSocket
    @websocket {
        header Connection *Upgrade*
        header Upgrade websocket
    }
    reverse_proxy @websocket localhost:8000
}
```

---

## SSL/HTTPS Setup

### Let's Encrypt (Certbot)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renew
sudo certbot renew --dry-run
```

### Cloudflare (Recommended)

1. Add domain to Cloudflare
2. Set SSL/TLS mode to "Full" or "Flexible"
3. Update DNS to point to your server
4. No additional SSL config needed on server

---

## Production Checklist

### Security

- [ ] Use HTTPS only
- [ ] Set strong `SECRET_KEY` for JWT
- [ ] Enable rate limiting
- [ ] Set up CORS properly
- [ ] Use environment variables for secrets
- [ ] Enable input validation
- [ ] Set up logging and monitoring

### Performance

- [ ] Enable response caching
- [ ] Set appropriate timeouts
- [ ] Configure connection pooling
- [ ] Enable database indexing
- [ ] Set up CDN for static files
- [ ] Monitor memory usage

### Reliability

- [ ] Set up health checks
- [ ] Configure auto-restart
- [ ] Set up log rotation
- [ ] Implement circuit breakers
- [ ] Enable dead letter queues
- [ ] Set up alerting

### Environment Variables

Required for production:

```env
# AI Configuration
OPENAI_API_KEY=sk-prod-key-here
AI_PROVIDER=openai
OPENAI_MODEL_NAME=gpt-4o-mini
OPENAI_TEMPERATURE=0.7

# Security
SECRET_KEY=your-super-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com

# Database
DB_PATH=/app/data/chatbot.db

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
```

### Health Check Endpoint

Verify deployment:

```bash
curl https://yourdomain.com/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## Monitoring

### Application Logs

```python
# In main.py
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

### Prometheus Metrics

Add `prometheus-fastapi-instrumentator`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

### Uptime Monitoring

- Use services like UptimeRobot, Pingdom, or Grafana
- Monitor `/api/v1/health` endpoint
- Set up alerts for downtime

---

## Scaling

### Horizontal Scaling

For multiple instances:

1. **Use a load balancer**
2. **Enable sticky sessions for WebSocket**
3. **Use Redis for session storage**

```python
# In database.py
from redis import Redis

redis_client = Redis(host='redis-host', port=6379)
```

### Vertical Scaling

Increase resources:
- CPU: 2+ cores recommended
- Memory: 1GB+ minimum
- Disk: SSD for database

---

## Backup & Recovery

### Database Backup

```bash
# Create backup
sqlite3 data/chatbot.db ".backup data/backup_$(date +%Y%m%d).db"

# Restore
sqlite3 data/chatbot.db ".restore data/backup_20240101.db"
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * cp /path/to/data/chatbot.db /path/to/backup/
```

---

## Troubleshooting

This section covers common issues and their solutions when deploying and running the LangChain Chatbot.

### Common Issues and Solutions

#### Issue: Chatbot Not Responding Properly

**Symptom:** The chatbot returns empty responses or does not generate proper AI responses.

**Root Cause:** The LLM may not be properly initialized or the message context is not being passed correctly to the LangChain chain.

**Solution:** Verify that the LangChain chain is properly configured:

1. Check that OPENAI_API_KEY is set correctly in your .env file
2. Ensure the chat history is being passed to the chain
3. Verify that the ChatOpenAI model is properly initialized

**Debug Steps:**

```bash
# Enable debug mode to see detailed logs
DEBUG=true LOG_LEVEL=DEBUG uvicorn main:app --reload

# Test direct LLM call
python -c "
from langchain_openai import ChatOpenAI
import os
llm = ChatOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
print(llm.invoke('Hello'))
"
```

**Code Verification:** Check that the LangChain chain is properly configured in agent.py:

```python
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=api_key
)

# Create chain with prompt
prompt = ChatPromptTemplate.from_messages([...])
chain = LLMChain(llm=llm, prompt=prompt)
```

#### Issue: Module 'langchain' Not Found

**Symptom:** ImportError when running the application.

**Solution:**

```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify langchain installation
pip show langchain-openai
```

#### Issue: WebSocket Connection Failed

**Symptom:** Cannot connect to WebSocket endpoint or connection drops immediately.

**Solution:**

1. Check that the server is running:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

2. Verify firewall settings:
   ```bash
   sudo ufw allow 8000
   ```

3. For Nginx reverse proxy, ensure WebSocket support is enabled:
   ```nginx
   location / {
       proxy_pass http://127.0.0.1:8000;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
   }
   ```

#### Issue: OpenAI API Errors

**Symptom:** API errors such as "Invalid API Key" or "Rate limit exceeded".

**Solution:**

1. Verify your API key starts with "sk-":
   ```bash
   grep OPENAI_API_KEY .env
   ```

2. Check that the model name is correct:
   ```env
   OPENAI_MODEL_NAME=gpt-4o-mini
   ```

3. Check rate limits and implement backoff:
   ```python
   from tenacity import retry, wait_exponential

   @retry(wait=wait_exponential(multiplier=1, min=2, max=10))
   async def call_llm_with_retry(messages):
       return await llm.ainvoke(messages)
   ```

4. Ensure you have API credits:
   - Log into OpenAI dashboard
   - Check your usage and billing

#### Issue: File Upload Fails

**Symptom:** PDF or document uploads return errors.

**Solution:**

1. Check directory permissions:
   ```bash
   ls -la data/
   chmod 755 data/
   ```

2. Verify file size is within limits (default: 10MB)

3. Check file format is supported (PDF, TXT, MD, DOCX)

4. Verify file processor is working:
   ```python
   from generic_agent.file_processor import FileProcessor
   processor = FileProcessor()
   content = processor.extract_text("document.pdf")
   ```

#### Issue: CORS Policy Errors

**Symptom:** Browser blocks requests with CORS error.

**Solution:** Configure allowed origins in main.py:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Issue: Database Locked

**Symptom:** SQLite database errors during concurrent access.

**Solution:**

1. Use WAL mode for better concurrency:
   ```python
   conn.execute("PRAGMA journal_mode=WAL")
   ```

2. Set an appropriate busy timeout:
   ```python
   conn.execute("PRAGMA busy_timeout=5000")
   ```

3. For production, consider using PostgreSQL

#### Issue: Streaming Not Working

**Symptom:** Responses are not streamed token-by-token.

**Solution:**

1. Verify streaming is enabled in LangChain:
   ```python
   llm = ChatOpenAI(
       model="gpt-4o-mini",
       streaming=True,
       callbacks=[StreamingStdOutCallbackHandler()]
   )
   ```

2. Check WebSocket is properly configured for streaming

3. Ensure async generator is used for streaming responses

### Logging and Debugging

**Enable Debug Mode:**

```bash
DEBUG=true LOG_LEVEL=DEBUG uvicorn main:app --reload
```

**Check Application Logs:**

```bash
# If running with systemd
sudo journalctl -u langchain-chatbot -f

# If running with Docker
docker logs -f langchain-chatbot
```

**Test API Endpoints:**

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Test chat
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"message": "Hello", "session_id": "test-001"}'
```

### Performance Optimization

**Connection Pooling:**

```python
from langchain_openai import ChatOpenAI

# Reuse LLM instance
llm = ChatOpenAI(
    model="gpt-4o-mini",
    max_retries=3,
    timeout=60
)
```

**Caching Responses:**

```python
from langchain.cache import InMemoryCache
import langchain

langchain.llm_cache = InMemoryCache()
```

---

## Support

For deployment help:
- GitHub Issues: [Create Issue](https://github.com/OumaCavin/langchain-chatbot/issues)
- Documentation: [docs/](docs/)
- Email: cavin.otieno012@gmail.com

## License

MIT License - Developed by Cavin Otieno
