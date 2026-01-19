# Talk to the Book

A production-grade system for transforming uploaded books into interactive Q&A experiences with source-only answering and voice-preserving responses.

## Overview

This system enables users to upload books and interact with them through natural language questions. The core component is the **Master Ingest & Authoring Prompt** (`master_ingest_prompt.txt`), which instructs an AI model to analyze an uploaded book and generate all necessary artifacts for a production-ready "Talk to the Book" instance.

## Key Features

- **Source-Only Answering**: Answers are derived exclusively from the uploaded book content
- **Voice Preservation**: Emulates the book's unique writing style and tone
- **Structured Output**: Generates comprehensive JSON artifacts including:
  - Book metadata and profiles
  - Chunking and retrieval configurations
  - QA datasets (gold, synthetic, interpretive)
  - Chapter summaries and canonical quotes
  - Training and evaluation specifications
  - Runtime prompts and deployment recommendations

## Project Structure

```
talk_to_the_book/
├── master_ingest_prompt.txt      # Master prompt for book ingestion
├── ingest_output_schema.json      # JSON schema for validation
├── example_ingest_output.json    # Example output structure
│
├── run_ingest.py                 # Main ingest script
├── validate_ingest_output.py     # Validation utility
├── chunk_processor.py            # Text chunking utility
├── embedding_utils.py             # Embedding generation & FAISS index
├── runtime_orchestrator.py       # Runtime Q&A orchestrator
│
├── process_book.sh               # Complete workflow (Unix/Mac)
├── process_book.bat              # Complete workflow (Windows)
│
├── requirements.txt              # Python dependencies
├── config.example.json           # Configuration template
├── .gitignore                    # Git ignore rules
│
├── README.md                     # This file
├── QUICKSTART.md                 # Quick start guide
│
└── [generated directories]
    ├── ingested_books/          # Processed book JSON outputs
    ├── chunks/                   # Chunked text JSONL files
    ├── embeddings/               # Embeddings and FAISS indices
    └── datasets/                 # QA datasets (optional)
```

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

**Quick workflow:**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Process a book (automated)
./process_book.sh my_book.txt openai $OPENAI_API_KEY

# 3. Start interactive Q&A
python runtime_orchestrator.py ingested_books/{book_id}.json \
  --embeddings embeddings/{book_id}_embeddings.npz \
  --index embeddings/{book_id}_index.faiss \
  --chunks chunks/{book_id}_chunks.jsonl \
  --api-key $OPENAI_API_KEY
```

**Manual workflow:**
1. **Ingest**: `python run_ingest.py book.txt --api openai`
2. **Validate**: `python validate_ingest_output.py ingested_books/{book_id}.json`
3. **Chunk**: `python chunk_processor.py book.txt ingested_books/{book_id}.json`
4. **Embed**: `python embedding_utils.py chunks/{book_id}_chunks.jsonl ingested_books/{book_id}.json`
5. **Query**: Use `runtime_orchestrator.py` for interactive Q&A

## Output Schema

The ingest process produces a comprehensive JSON object containing:

- `book_metadata`: Title, author, language, genres, copyright status
- `book_profile`: Voice analysis, themes, key concepts, chapter index
- `chunking_plan`: Strategy for text segmentation
- `retrieval_config`: Embedding models, vector index settings, reranking
- `persona_and_voice`: Voice emulation parameters
- `qa_datasets`: Gold, synthetic, and interpretive Q/A pairs
- `chapter_summaries`: Detailed chapter breakdowns
- `canonical_quotes`: High-value quotations
- `training_spec`: Fine-tuning configuration
- `evaluation_spec`: Testing and validation plan
- `runtime_prompts`: System and user prompt templates
- `security_and_ip`: Consent, retention, copyright handling
- `dev_checklist`: Implementation tasks
- `deployment_recommendations`: Infrastructure guidance
- `monitoring_and_metrics`: Observability setup
- `deliverables`: File artifacts list
- `notes_for_human_review`: Flags for manual review

## Default Configuration

- **Chunk Size**: 600 words
- **Overlap**: 20%
- **Top-K Retrieval**: 6 chunks
- **Similarity Threshold**: 0.12 (cosine)
- **Embedding Model**: `sentence-transformers/all-mpnet-base-v2` or `text-embedding-3-large`
- **Reranking**: Top 50 → Top 6
- **Retention**: 180 days

## Requirements

- Python 3.8+
- Access to LLM API (for running the ingest prompt)
- Vector database (FAISS, Qdrant, or Weaviate)
- Embedding models (sentence-transformers or OpenAI)
