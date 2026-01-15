# Talk to the Book - Production Web System

A production-ready web application for transforming uploaded books into interactive, voice-preserving, source-only Q&A experiences.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (or Anthropic)
- 4GB+ RAM

### Run Locally

```bash
# 1. Clone repository
git clone <repo-url>
cd talk_to_the_book

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Start services
docker-compose up -d

# 4. Access
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## 📋 Features

- ✅ **Multi-format Support**: PDF, TXT, ePub
- ✅ **Deterministic Chunking**: Reproducible chunk IDs
- ✅ **Vector Search**: FAISS-based semantic retrieval
- ✅ **Source-Only Answers**: No hallucinations
- ✅ **Voice Preservation**: Emulates book's writing style
- ✅ **Interactive Chat UI**: Modern React frontend
- ✅ **Monitoring**: Prometheus metrics
- ✅ **Production Ready**: Docker, logging, error handling

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │  Next.js + React + Tailwind
│  (Port 3000)│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Backend   │  FastAPI + Python
│  (Port 8000)│
└──────┬──────┘
       │
       ├──► SQLite/Postgres (Metadata)
       ├──► FAISS (Vector Index)
       └──► Local/S3 (File Storage)
```

## 📁 Project Structure

```
talk_to_the_book/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # REST endpoints
│   │   ├── core/        # Config, metrics, logging
│   │   ├── db/          # Database models
│   │   └── services/    # Business logic
│   ├── tests/           # Test suite
│   └── Dockerfile
│
├── frontend/             # Next.js frontend
│   ├── components/      # React components
│   ├── pages/           # Next.js pages
│   └── Dockerfile
│
├── docker-compose.yml    # Local development
├── master_ingest_prompt.txt
└── docs/                # Documentation
```

## 🔌 API Endpoints

See [API_EXAMPLES.md](API_EXAMPLES.md) for detailed examples.

- `POST /api/v1/upload` - Upload book
- `POST /api/v1/ingest/start` - Start processing
- `GET /api/v1/ingest/status` - Check status
- `POST /api/v1/query` - Ask questions
- `GET /api/v1/books` - List books
- `POST /api/v1/feedback` - Submit feedback
- `GET /metrics` - Prometheus metrics

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

## 📊 Monitoring

Metrics available at `/metrics`:
- Query latency (p50, p95, p99)
- Query count
- Unknown response rate
- Average confidence
- Feedback rates

## 🔒 Security

- File encryption at rest (configurable)
- User consent requirement
- Secure file storage
- CORS configuration
- Input validation

## 📚 Documentation

- [API Examples](API_EXAMPLES.md) - API usage examples
- [Deployment Guide](DEPLOYMENT.md) - Production deployment
- [Implementation Report](IMPLEMENTATION_REPORT.md) - Technical details
- [Quick Start](QUICKSTART.md) - Getting started guide

## 🛠️ Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 📝 License

[Specify your license]

## 🤝 Contributing

[Contributing guidelines]

## 📞 Support

[Support information]

---

**Status**: ✅ Production Ready
**Version**: 1.0.0
