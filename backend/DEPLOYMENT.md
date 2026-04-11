# Deployment Guide for Agentic Crawler

This guide covers deploying Agentic Crawler to production environments.

## 📋 Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Dependencies up to date
- [ ] Environment variables configured
- [ ] API keys secured
- [ ] Documentation updated
- [ ] Version number incremented
- [ ] CHANGELOG updated

## 🏗️ Deployment Options

### Option 1: Docker Deployment (Recommended)

#### 1. Create Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install Node.js for Firecrawl MCP
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    apt-get clean

# Copy requirements
COPY requirements.txt .
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application
COPY src/ src/
COPY main.py .

# Create necessary directories
RUN mkdir -p cache sessions tool_outputs qa_reports

# Set environment
ENV PYTHONUNBUFFERED=1

# Run application
CMD ["python", "main.py"]
```

#### 2. Build and Run

```bash
# Build image
docker build -t agentic-crawler:latest .

# Run container
docker run -it \
  -e FIRECRAWL_API_KEY=your_key \
  -e GOOGLE_API_KEY=your_key \
  -v $(pwd)/qa_reports:/app/qa_reports \
  -v $(pwd)/tool_outputs:/app/tool_outputs \
  agentic-crawler:latest
```

#### 3. Docker Compose

```yaml
version: '3.8'

services:
  agentic-crawler:
    build: .
    environment:
      - FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - DEBUG_MODE=false
    volumes:
      - ./qa_reports:/app/qa_reports
      - ./tool_outputs:/app/tool_outputs
      - ./cache:/app/cache
    restart: unless-stopped
```

### Option 2: Cloud Platform Deployment

#### AWS (EC2)

```bash
# 1. Launch EC2 instance (Ubuntu 22.04, t3.medium)

# 2. SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# 3. Install dependencies
sudo apt update
sudo apt install -y python3.12 python3-pip nodejs npm git

# 4. Clone repository
git clone https://github.com/yourusername/agentic-crawler.git
cd agentic-crawler

# 5. Set up virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 6. Install package
pip install -e .

# 7. Configure environment
cp .env.example .env
nano .env  # Add your API keys

# 8. Run with systemd (see below)
```

#### Google Cloud (Compute Engine)

Similar to AWS, but use:
```bash
gcloud compute instances create agentic-crawler \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --machine-type=n1-standard-2
```

#### Azure (VM)

```bash
az vm create \
  --resource-group myResourceGroup \
  --name agentic-crawler \
  --image Ubuntu2204 \
  --size Standard_B2s
```

### Option 3: Systemd Service (Linux)

Create `/etc/systemd/system/agentic-crawler.service`:

```ini
[Unit]
Description=Agentic Crawler QA Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/agentic-crawler
Environment="PATH=/home/ubuntu/agentic-crawler/venv/bin"
EnvironmentFile=/home/ubuntu/agentic-crawler/.env
ExecStart=/home/ubuntu/agentic-crawler/venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable agentic-crawler
sudo systemctl start agentic-crawler
sudo systemctl status agentic-crawler
```

### Option 4: Kubernetes

#### deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentic-crawler
spec:
  replicas: 2
  selector:
    matchLabels:
      app: agentic-crawler
  template:
    metadata:
      labels:
        app: agentic-crawler
    spec:
      containers:
      - name: agentic-crawler
        image: your-registry/agentic-crawler:latest
        env:
        - name: FIRECRAWL_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: firecrawl
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: google
        volumeMounts:
        - name: reports
          mountPath: /app/qa_reports
        - name: outputs
          mountPath: /app/tool_outputs
      volumes:
      - name: reports
        persistentVolumeClaim:
          claimName: reports-pvc
      - name: outputs
        persistentVolumeClaim:
          claimName: outputs-pvc
```

## 🔒 Security Best Practices

### 1. Environment Variables

Never commit `.env` files:
```bash
# .gitignore
.env
.env.*
!.env.example
```

### 2. API Key Rotation

Rotate API keys regularly:
```bash
# Update in cloud provider secrets manager
# AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id agentic-crawler/api-keys \
  --secret-string '{"firecrawl":"new_key","google":"new_key"}'
```

### 3. Rate Limiting

Implement rate limiting for API calls:
```python
# In config/settings.py
MAX_REQUESTS_PER_MINUTE = 60
ENABLE_RATE_LIMITING = True
```

### 4. Access Control

Restrict access:
```bash
# Firewall rules
sudo ufw allow from trusted_ip to any port 22
sudo ufw deny 22
```

## 📊 Monitoring & Logging

### 1. Application Logging

Configure logging:
```python
# In config/settings.py
LOG_LEVEL = "INFO"
LOG_FILE = "/var/log/agentic-crawler/app.log"
```

### 2. Health Checks

Add health check endpoint (if using API mode):
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

### 3. Metrics Collection

Use Prometheus for metrics:
```python
from prometheus_client import Counter, Histogram

requests_total = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')
```

## 🔄 CI/CD Pipeline

### GitHub Actions Example

`.github/workflows/deploy.yml`:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: pytest tests/
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and push Docker image
        run: |
          docker build -t myregistry/agentic-crawler:latest .
          docker push myregistry/agentic-crawler:latest
      - name: Deploy to server
        run: |
          ssh user@server 'cd /app && docker-compose pull && docker-compose up -d'
```

## 📈 Scaling Considerations

### Horizontal Scaling

Run multiple instances:
```bash
# Docker Compose with replicas
docker-compose up --scale agentic-crawler=3
```

### Caching Strategy

Use Redis for distributed caching:
```python
# services/cache_service.py
import redis

class RedisCacheService(CacheService):
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379)
```

### Load Balancing

Use Nginx:
```nginx
upstream agentic_crawler {
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

server {
    listen 80;
    location / {
        proxy_pass http://agentic_crawler;
    }
}
```

## 🚨 Troubleshooting

### Common Issues

1. **Out of Memory**
   - Increase cache size limits
   - Add memory limits to Docker
   - Scale horizontally

2. **API Rate Limits**
   - Implement exponential backoff
   - Use multiple API keys
   - Add request queuing

3. **Slow Performance**
   - Enable caching
   - Optimize prompt length
   - Use faster models

### Debugging Production

```bash
# View logs
docker logs -f agentic-crawler

# Check resource usage
docker stats agentic-crawler

# Access container
docker exec -it agentic-crawler bash
```

## 📞 Support

For deployment issues:
- Check documentation: [link]
- Open issue on GitHub
- Contact support: support@example.com

---

**Last Updated**: 2025-01-15  
**Version**: 1.0.0
