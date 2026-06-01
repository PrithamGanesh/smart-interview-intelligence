# Production System Deployment & Launch Guide

**Smart Interview Intelligence - Scalable Production Deployment**

---

## Overview

This guide walks through deploying the production-ready Smart Interview Intelligence system with:
- PostgreSQL for persistent storage
- Redis for caching and rate limiting
- Horizontal scalability (Kubernetes-ready)
- Enterprise-grade monitoring
- 99.95% uptime SLA

---

## Prerequisites

### Required Software
- Docker 20.10+
- Docker Compose 2.0+ (or Kubernetes 1.20+)
- PostgreSQL 13+ (or use containerized version)
- Redis 6.0+ (or use containerized version)
- Python 3.11+
- Git

### Hardware Requirements
- **Development**: 4 CPU cores, 8GB RAM
- **Staging**: 8 CPU cores, 16GB RAM
- **Production**: 16 CPU cores, 32GB RAM (recommend 3 nodes minimum)

---

## Part 1: Local Development Setup

### 1.1 Clone and Setup Environment

```bash
git clone https://github.com/your-org/smart-interview-intelligence.git
cd smart-interview-intelligence

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 1.2 Configure Environment

Create `.env` file:

```env
# Application
DEBUG=true
LOG_LEVEL=DEBUG
VERSION=1.0.0

# Database (local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/smart_interview
DB_POOL_SIZE=20

# Cache (local Redis)
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_KEY=dev-api-key-123
PAGE_SIZE_DEFAULT=20

# Rate Limiting
RATE_LIMIT_PER_SEC=1000

# ML Models
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
```

### 1.3 Start Local Services (Docker)

```bash
# Start PostgreSQL and Redis
docker-compose -f docker/docker-compose.local.yml up -d

# Verify services
docker ps
```

**Expected output:**
```
CONTAINER ID   IMAGE           PORTS           NAMES
abc123...      postgres:15     5432->5432      smart-interview-db
def456...      redis:7         6379->6379      smart-interview-cache
```

### 1.4 Initialize Database

```bash
# Create tables
python -m app.database.init_db

# Verify
psql -U postgres -d smart_interview -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
```

**Expected output:**
```
          table_name
--------------------
 resumes
 jobs
 match_results
 interview_questions
 tenants
 audit_log
(6 rows)
```

### 1.5 Run Application

```bash
# Development server with hot reload
uvicorn app.main_production:app --reload --host 0.0.0.0 --port 8000

# Or using gunicorn (production-like)
gunicorn app.main_production:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

### 1.6 Verify Setup

```bash
# Test API
curl -X GET http://localhost:8000/health
curl -X GET http://localhost:8000/ready

# Access API docs
# Browser: http://localhost:8000/docs
# Redoc: http://localhost:8000/redoc

# Test database connection
curl -X GET http://localhost:8000/metrics/health
```

---

## Part 2: Docker Containerization

### 2.1 Build Docker Image

Create `docker/docker-compose.yml`:

```yaml
version: '3.8'

services:
  # API Server
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://user:password@db:5432/smart_interview
      REDIS_URL: redis://cache:6379/0
      LOG_LEVEL: INFO
      DEBUG: "false"
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/ready"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - smart-interview

  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: smart_interview
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d smart_interview"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - smart-interview

  # Redis Cache
  cache:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - smart-interview

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - smart-interview

  # Grafana Dashboard
  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    networks:
      - smart-interview

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  smart-interview:
    driver: bridge
```

### 2.2 Build Image

```bash
docker build -f docker/Dockerfile -t smart-interview:1.0.0 .

# Verify
docker images | grep smart-interview
```

### 2.3 Run Docker Compose Stack

```bash
# Start all services
cd docker
docker-compose up -d

# View logs
docker-compose logs -f api

# Check status
docker-compose ps
```

### 2.4 Initialize Database in Container

```bash
# Run migrations inside container
docker-compose exec api python -m app.database.init_db

# Verify
docker-compose exec db psql -U user -d smart_interview -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```

---

## Part 3: Kubernetes Deployment

### 3.1 Create Kubernetes Manifests

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: smart-interview-api
  labels:
    app: smart-interview-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: smart-interview-api
  template:
    metadata:
      labels:
        app: smart-interview-api
    spec:
      containers:
      - name: api
        image: smart-interview:1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          value: redis://smart-interview-cache:6379/0
        - name: LOG_LEVEL
          value: INFO
        - name: DEBUG
          value: "false"
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2

---
apiVersion: v1
kind: Service
metadata:
  name: smart-interview-api
spec:
  selector:
    app: smart-interview-api
  type: LoadBalancer
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: db-credentials
data:
  url: postgresql+asyncpg://user:password@postgres:5432/smart_interview
```

### 3.2 Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace smart-interview

# Deploy
kubectl apply -f k8s/ -n smart-interview

# Check deployment status
kubectl get deployments -n smart-interview
kubectl get pods -n smart-interview
kubectl get svc -n smart-interview
```

### 3.3 Monitor Deployment

```bash
# View logs
kubectl logs -f deployment/smart-interview-api -n smart-interview

# Check pod status
kubectl describe pod <pod-name> -n smart-interview

# Port forward for testing
kubectl port-forward svc/smart-interview-api 8000:80 -n smart-interview

# Test
curl http://localhost:8000/health
```

---

## Part 4: Production Configuration

### 4.1 Load Balancer Setup

**NGINX Configuration** (`nginx/nginx.conf`):

```nginx
upstream api {
    least_conn;
    server api-1:8000;
    server api-2:8000;
    server api-3:8000;
}

server {
    listen 80;
    server_name api.smartinterview.com;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;

    location / {
        limit_req zone=api_limit burst=200 nodelay;
        
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Request-ID $request_id;
        
        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://api;
    }
}
```

### 4.2 SSL/TLS Configuration

```bash
# Using Let's Encrypt with certbot
certbot certonly --standalone -d api.smartinterview.com

# Update NGINX
# Add ssl_certificate and ssl_certificate_key directives
# Redirect HTTP to HTTPS
```

### 4.3 Database Backups

```bash
# Daily backup script (backup.sh)
#!/bin/bash
BACKUP_DIR="/backups/smart-interview"
DATE=$(date +%Y%m%d_%H%M%S)

pg_dump -U postgres -h postgres -d smart_interview | \
  gzip > "$BACKUP_DIR/smart_interview_$DATE.sql.gz"

# Keep only last 30 days
find "$BACKUP_DIR" -mtime +30 -delete
```

Schedule with cron:
```bash
0 2 * * * /scripts/backup.sh
```

### 4.4 Monitoring & Alerting

**Prometheus rules** (`prometheus/rules.yml`):

```yaml
groups:
- name: smart_interview
  interval: 30s
  rules:
  - alert: APIHighErrorRate
    expr: rate(api_errors_total[5m]) > 0.05
    for: 5m
    annotations:
      summary: "High error rate on API"
  
  - alert: DatabaseConnectionPoolExhausted
    expr: db_pool_utilization_percent > 90
    for: 2m
    annotations:
      summary: "Database connection pool utilization > 90%"
  
  - alert: CacheHighMemoryUsage
    expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.85
    for: 5m
    annotations:
      summary: "Redis memory usage > 85%"
```

---

## Part 5: Testing & Validation

### 5.1 API Tests

```bash
# Run integration tests
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### 5.2 Load Testing

```bash
# Using locust
locust -f tests/locustfile.py --host=http://localhost:8000 -u 1000 -r 50

# Using Apache JMeter or k6
k6 run tests/load-test.js
```

### 5.3 Performance Benchmarks

Target metrics:
- **Throughput**: 10,000 req/sec
- **Latency (p95)**: < 100ms
- **Latency (p99)**: < 500ms
- **Cache hit ratio**: > 80%
- **Database query latency**: < 50ms

---

## Part 6: Operational Procedures

### 6.1 Health Checks

```bash
# API health
curl -s http://api/health | jq .

# Database health
curl -s http://api/metrics/health | jq '.database'

# Cache health
redis-cli info stats

# System metrics
kubectl top nodes
kubectl top pods
```

### 6.2 Scaling

```bash
# Horizontal scaling (Kubernetes)
kubectl scale deployment smart-interview-api --replicas=10

# Auto-scaling
kubectl autoscale deployment smart-interview-api --min=2 --max=20 --cpu-percent=70
```

### 6.3 Rolling Updates

```bash
# Update image
kubectl set image deployment/smart-interview-api \
  api=smart-interview:1.1.0 -n smart-interview

# Monitor rollout
kubectl rollout status deployment/smart-interview-api -n smart-interview

# Rollback if needed
kubectl rollout undo deployment/smart-interview-api -n smart-interview
```

### 6.4 Debugging

```bash
# View application logs
kubectl logs -f pod/<pod-name> -n smart-interview

# Execute commands in pod
kubectl exec -it pod/<pod-name> -n smart-interview -- /bin/bash

# Inspect pod details
kubectl describe pod/<pod-name> -n smart-interview

# Database connection check
docker exec smart-interview-db psql -U user -d smart_interview -c "SELECT 1"

# Redis connection check
redis-cli -h localhost ping
```

---

## Part 7: Post-Deployment Checklist

- [ ] Database backup configured
- [ ] Monitoring and alerting active
- [ ] SSL/TLS certificates deployed
- [ ] Load balancer running
- [ ] Auto-scaling policies configured
- [ ] API responding on all endpoints
- [ ] Health checks passing
- [ ] Cache hit ratio > 80%
- [ ] Database query performance acceptable
- [ ] All integration tests passing
- [ ] Load tests completed successfully
- [ ] Documentation updated
- [ ] Team trained on operations

---

## Appendix: Useful Commands

```bash
# View application logs
docker-compose logs -f api

# Database connection
psql -U postgres -d smart_interview -h localhost

# Redis CLI
redis-cli -h localhost

# Monitor system resources
docker stats

# Database query performance
EXPLAIN ANALYZE SELECT * FROM resumes WHERE tenant_id = '...';

# Kubernetes debugging
kubectl describe nodes
kubectl get events -n smart-interview

# Container shell
docker-compose exec api /bin/bash

# View environment variables
kubectl get pod <pod-name> -o yaml | grep -A 100 "env:"
```

---

## Support & Troubleshooting

**Issue**: API not responding
- Check health: `curl http://localhost:8000/health`
- View logs: `docker-compose logs api`
- Verify database: `psql -U postgres -d smart_interview -c "SELECT 1"`

**Issue**: Slow queries
- Check query performance: `EXPLAIN ANALYZE SELECT ...`
- Verify indexes: `\d+ resumes`
- Monitor connections: `SELECT COUNT(*) FROM pg_stat_activity`

**Issue**: Cache misses
- Check Redis connection: `redis-cli ping`
- Monitor cache: `redis-cli INFO stats`
- Verify TTL: `redis-cli TTL resume:xxx`

---

## Summary

You now have:
✅ Production-ready database with PostgreSQL
✅ Distributed caching with Redis
✅ Containerized deployment ready
✅ Kubernetes manifests for scaling
✅ Monitoring and alerting configured
✅ Backup and recovery procedures
✅ Operational runbooks

**Next steps**: Deploy to production and monitor.
