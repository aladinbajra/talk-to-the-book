# Deployment Guide

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (or Anthropic)
- 4GB+ RAM recommended

### Local Deployment

1. **Clone and setup**
   ```bash
   git clone <repo>
   cd talk_to_the_book
   ```

2. **Configure environment**
   ```bash
   # Create .env file
   echo "OPENAI_API_KEY=your_key_here" > .env
   echo "DEBUG=true" >> .env
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **Access**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Metrics: http://localhost:8000/metrics

## Production Deployment

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your_key
DATABASE_URL=postgresql://user:pass@host/db
STORAGE_TYPE=s3  # or 'local'
S3_BUCKET=your-bucket
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
ENCRYPTION_KEY=your-32-byte-key

# Optional
DEFAULT_LLM_MODEL=gpt-4-turbo-preview
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
RERANK_ENABLED=true
```

### Docker Compose Production

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      # ... other vars
    volumes:
      - ./storage:/app/storage
    restart: always

  frontend:
    build: ./frontend
    environment:
      - NEXT_PUBLIC_API_URL=${API_URL}
    restart: always

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=talk_to_the_book
    volumes:
      - postgres_data:/var/lib/postgresql/data

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
```

### Kubernetes (Optional)

See `k8s/` directory for manifests (to be created).

## Monitoring

### Prometheus Metrics

Available at `/metrics` endpoint:
- `query_count_total`
- `query_latency_seconds`
- `unknown_responses_total`
- `average_confidence`
- `feedback_positive_rate`

### Alerts

Configure in Prometheus:
- `query_latency_p95 > 3s`
- `unknown_rate > 0.35`
- `error_rate > 2%`

## Scaling

### Horizontal Scaling

- Backend: Stateless, can scale horizontally
- Use load balancer (nginx/HAProxy)
- Shared database and storage

### Vertical Scaling

- Increase embedding batch size
- Use GPU for embeddings/generation
- Increase database connections

## Backup

### Database

```bash
# Postgres
pg_dump talk_to_the_book > backup.sql
```

### Storage

- S3: Enable versioning
- Local: Regular backups of `storage/` directory

## Security Checklist

- [ ] Change default encryption key
- [ ] Use HTTPS (TLS)
- [ ] Configure CORS properly
- [ ] Enable authentication
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Monitor logs for anomalies
