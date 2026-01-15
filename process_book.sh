#!/bin/bash
# Complete workflow script for processing a book through the Talk to the Book system

set -e  # Exit on error

BOOK_FILE="$1"
API_TYPE="${2:-openai}"
API_KEY="${3:-$OPENAI_API_KEY}"

if [ -z "$BOOK_FILE" ]; then
    echo "Usage: $0 <book_file.txt> [api_type] [api_key]"
    echo "Example: $0 my_book.txt openai \$OPENAI_API_KEY"
    exit 1
fi

if [ ! -f "$BOOK_FILE" ]; then
    echo "Error: Book file not found: $BOOK_FILE"
    exit 1
fi

if [ -z "$API_KEY" ]; then
    echo "Error: API key required. Set OPENAI_API_KEY or pass as third argument."
    exit 1
fi

echo "=========================================="
echo "Processing book: $BOOK_FILE"
echo "=========================================="

# Step 1: Ingest
echo ""
echo "Step 1: Running ingest process..."
python run_ingest.py "$BOOK_FILE" --api "$API_TYPE" --api-key "$API_KEY"

# Extract book_id from output (simplified - in practice, parse JSON)
INGEST_FILE=$(ls -t ingested_books/*.json | head -1)
BOOK_ID=$(python -c "import json, sys; print(json.load(open('$INGEST_FILE'))['book_id'])")

echo "✓ Ingest complete. Book ID: $BOOK_ID"

# Step 2: Validate
echo ""
echo "Step 2: Validating ingest output..."
python validate_ingest_output.py "$INGEST_FILE" || {
    echo "Warning: Validation found issues. Continuing anyway..."
}

# Step 3: Chunk
echo ""
echo "Step 3: Processing chunks..."
python chunk_processor.py "$BOOK_FILE" "$INGEST_FILE"

CHUNKS_FILE="chunks/${BOOK_ID}_chunks.jsonl"

# Step 4: Generate embeddings
echo ""
echo "Step 4: Generating embeddings and FAISS index..."
python embedding_utils.py "$CHUNKS_FILE" "$INGEST_FILE"

echo ""
echo "=========================================="
echo "Processing complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review ingest output: $INGEST_FILE"
echo "2. Start interactive Q&A:"
echo "   python runtime_orchestrator.py $INGEST_FILE \\"
echo "     --embeddings embeddings/${BOOK_ID}_embeddings.npz \\"
echo "     --index embeddings/${BOOK_ID}_index.faiss \\"
echo "     --chunks $CHUNKS_FILE \\"
echo "     --api-key \$OPENAI_API_KEY"
echo ""
