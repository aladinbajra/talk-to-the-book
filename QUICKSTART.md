# Quick Start Guide

This guide will walk you through ingesting your first book and setting up a "Talk to the Book" instance.

## Prerequisites

1. **Python 3.8+** installed
2. **API Keys**:
   - OpenAI API key (for ingest and runtime) OR
   - Anthropic API key (for ingest)
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Step 1: Prepare Your Book

Save your book as a plain text file (`.txt`). The system will process it automatically.

Example: `my_book.txt`

## Step 2: Run the Ingest Process

Use the `run_ingest.py` script to process your book:

```bash
# Using OpenAI
python run_ingest.py my_book.txt --api openai --api-key YOUR_OPENAI_API_KEY

# Using Anthropic
python run_ingest.py my_book.txt --api anthropic --api-key YOUR_ANTHROPIC_API_KEY
```

This will:
- Analyze the book structure, voice, and content
- Generate QA datasets
- Create chunking and retrieval configurations
- Output a complete JSON specification

The output will be saved to `ingested_books/{book_id}.json`

## Step 3: Validate the Output

Validate the generated JSON:

```bash
python validate_ingest_output.py ingested_books/{book_id}.json
```

## Step 4: Process Chunks

Generate chunks from your book text:

```bash
python chunk_processor.py my_book.txt ingested_books/{book_id}.json
```

This creates `chunks/{book_id}_chunks.jsonl`

## Step 5: Generate Embeddings

Create embeddings and FAISS index:

```bash
python embedding_utils.py chunks/{book_id}_chunks.jsonl ingested_books/{book_id}.json
```

This creates:
- `embeddings/{book_id}_embeddings.npz`
- `embeddings/{book_id}_index.faiss`

## Step 6: Run the Runtime System

Start the interactive Q&A system:

```bash
python runtime_orchestrator.py \
  ingested_books/{book_id}.json \
  --embeddings embeddings/{book_id}_embeddings.npz \
  --index embeddings/{book_id}_index.faiss \
  --chunks chunks/{book_id}_chunks.jsonl \
  --api-key YOUR_OPENAI_API_KEY
```

Or query directly:

```bash
python runtime_orchestrator.py \
  ingested_books/{book_id}.json \
  --embeddings embeddings/{book_id}_embeddings.npz \
  --index embeddings/{book_id}_index.faiss \
  --chunks chunks/{book_id}_chunks.jsonl \
  --query "What is the main theme of this book?" \
  --api-key YOUR_OPENAI_API_KEY
```

## Complete Example Workflow

```bash
# 1. Ingest
python run_ingest.py my_book.txt --api openai --api-key $OPENAI_API_KEY

# 2. Validate
python validate_ingest_output.py ingested_books/example_book_001.json

# 3. Chunk
python chunk_processor.py my_book.txt ingested_books/example_book_001.json

# 4. Embed
python embedding_utils.py chunks/example_book_001_chunks.jsonl ingested_books/example_book_001.json

# 5. Query
python runtime_orchestrator.py \
  ingested_books/example_book_001.json \
  --embeddings embeddings/example_book_001_embeddings.npz \
  --index embeddings/example_book_001_index.faiss \
  --chunks chunks/example_book_001_chunks.jsonl \
  --query "What are the key concepts?" \
  --api-key $OPENAI_API_KEY
```

## Troubleshooting

### API Key Issues
- Set environment variable: `export OPENAI_API_KEY=your_key`
- Or pass `--api-key` flag to scripts

### Memory Issues
- For large books, reduce `batch_size` in embedding generation
- Use CPU-based FAISS (`faiss-cpu`) instead of GPU version

### Validation Errors
- Check that all required fields are present
- Review `notes_for_human_review` in ingest output
- Some warnings are acceptable; errors must be fixed

## Next Steps

- Review the generated `book_profile` to understand voice emulation
- Check `qa_datasets` for evaluation examples
- Customize `runtime_prompts` if needed
- Set up monitoring using `monitoring_and_metrics` recommendations

## Production Deployment

See `deployment_recommendations` in your ingest output for:
- Infrastructure recommendations
- Autoscaling configuration
- Cost optimization strategies
- Monitoring setup
