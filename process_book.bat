@echo off
REM Complete workflow script for processing a book through the Talk to the Book system

setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Usage: %0 ^<book_file.txt^> [api_type] [api_key]
    echo Example: %0 my_book.txt openai
    exit /b 1
)

set BOOK_FILE=%~1
set API_TYPE=%~2
if "!API_TYPE!"=="" set API_TYPE=openai
set API_KEY=%~3
if "!API_KEY!"=="" set API_KEY=%OPENAI_API_KEY%

if not exist "%BOOK_FILE%" (
    echo Error: Book file not found: %BOOK_FILE%
    exit /b 1
)

if "!API_KEY!"=="" (
    echo Error: API key required. Set OPENAI_API_KEY environment variable or pass as third argument.
    exit /b 1
)

echo ==========================================
echo Processing book: %BOOK_FILE%
echo ==========================================

REM Step 1: Ingest
echo.
echo Step 1: Running ingest process...
python run_ingest.py "%BOOK_FILE%" --api %API_TYPE% --api-key %API_KEY%
if errorlevel 1 (
    echo Error: Ingest failed
    exit /b 1
)

REM Extract book_id (simplified - find most recent JSON file)
for /f "delims=" %%i in ('dir /b /o-d ingested_books\*.json 2^>nul') do (
    set INGEST_FILE=ingested_books\%%i
    goto :found
)
:found

echo Step 2: Validating ingest output...
python validate_ingest_output.py "!INGEST_FILE!"

echo.
echo Step 3: Processing chunks...
python chunk_processor.py "%BOOK_FILE%" "!INGEST_FILE!"

REM Extract book_id from JSON (requires Python)
for /f "delims=" %%i in ('python -c "import json; print(json.load(open('!INGEST_FILE!'))['book_id'])"') do set BOOK_ID=%%i

set CHUNKS_FILE=chunks\!BOOK_ID!_chunks.jsonl

echo.
echo Step 4: Generating embeddings and FAISS index...
python embedding_utils.py "!CHUNKS_FILE!" "!INGEST_FILE!"

echo.
echo ==========================================
echo Processing complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Review ingest output: !INGEST_FILE!
echo 2. Start interactive Q^&A:
echo    python runtime_orchestrator.py !INGEST_FILE! --embeddings embeddings\!BOOK_ID!_embeddings.npz --index embeddings\!BOOK_ID!_index.faiss --chunks !CHUNKS_FILE! --api-key %API_KEY%
echo.
