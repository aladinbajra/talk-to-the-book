#!/usr/bin/env python3
"""
Run the book ingest process using the master ingest prompt.

This script loads a book file, sends it to an LLM with the master ingest prompt,
and saves the resulting JSON output.
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Optional
import uuid
from datetime import datetime


def load_book_text(book_path: str) -> str:
    """Load book text from file."""
    path = Path(book_path)
    if not path.exists():
        raise FileNotFoundError(f"Book file not found: {book_path}")
    
    # Try to detect encoding
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    
    raise ValueError(f"Could not decode file {book_path} with any supported encoding")


def load_master_prompt(prompt_path: str = "master_ingest_prompt.txt") -> str:
    """Load the master ingest prompt."""
    path = Path(prompt_path)
    if not path.exists():
        raise FileNotFoundError(f"Master prompt not found: {prompt_path}")
    return path.read_text(encoding='utf-8')


def call_llm_api(prompt: str, book_text: str, api_type: str = "openai", **kwargs) -> str:
    """
    Call LLM API with the prompt and book text.
    
    Args:
        prompt: System prompt (master ingest prompt)
        book_text: The book content to analyze
        api_type: Type of API ('openai', 'anthropic', 'local')
        **kwargs: Additional API-specific parameters
    
    Returns:
        JSON string response from the LLM
    """
    if api_type == "openai":
        try:
            import openai
            client = openai.OpenAI(api_key=kwargs.get('api_key'))
            
            response = client.chat.completions.create(
                model=kwargs.get('model', 'gpt-4-turbo-preview'),
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Process this book:\n\n{book_text}"}
                ],
                temperature=kwargs.get('temperature', 0.1),
                max_tokens=kwargs.get('max_tokens', 16000),
                response_format={"type": "json_object"} if kwargs.get('json_mode', True) else None
            )
            return response.choices[0].message.content
            
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")
    
    elif api_type == "anthropic":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=kwargs.get('api_key'))
            
            message = client.messages.create(
                model=kwargs.get('model', 'claude-3-opus-20240229'),
                max_tokens=kwargs.get('max_tokens', 16000),
                system=prompt,
                messages=[
                    {"role": "user", "content": f"Process this book:\n\n{book_text}"}
                ]
            )
            return message.content[0].text
            
        except ImportError:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")
    
    elif api_type == "local":
        # For local models using transformers/llama.cpp/etc.
        raise NotImplementedError("Local model support not yet implemented. Use 'openai' or 'anthropic'.")
    
    else:
        raise ValueError(f"Unknown API type: {api_type}")


def validate_json_output(json_str: str) -> dict:
    """Validate and parse JSON output."""
    try:
        data = json.loads(json_str)
        
        # Basic validation - check required top-level keys
        required_keys = [
            "book_id", "book_metadata", "ingest_summary", "book_profile",
            "chunking_plan", "retrieval_config", "persona_and_voice",
            "qa_datasets", "chapter_summaries", "canonical_quotes",
            "training_spec", "evaluation_spec", "runtime_prompts",
            "security_and_ip", "dev_checklist", "deployment_recommendations",
            "monitoring_and_metrics", "deliverables", "notes_for_human_review"
        ]
        
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            print(f"Warning: Missing required keys: {missing_keys}", file=sys.stderr)
        
        return data
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON output: {e}")


def save_output(data: dict, output_path: str):
    """Save validated JSON output to file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Pretty print JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved ingest output to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Run book ingest process using master ingest prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using OpenAI API
  python run_ingest.py book.txt --api openai --api-key $OPENAI_API_KEY
  
  # Using Anthropic API
  python run_ingest.py book.txt --api anthropic --api-key $ANTHROPIC_API_KEY --model claude-3-opus-20240229
  
  # Custom output path
  python run_ingest.py book.txt --output ingested_books/mybook.json
        """
    )
    
    parser.add_argument(
        "book_file",
        help="Path to the book text file to ingest"
    )
    
    parser.add_argument(
        "--prompt",
        default="master_ingest_prompt.txt",
        help="Path to master ingest prompt file (default: master_ingest_prompt.txt)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output JSON file path (default: ingested_books/{book_id}.json)"
    )
    
    parser.add_argument(
        "--api",
        choices=["openai", "anthropic", "local"],
        default="openai",
        help="LLM API to use (default: openai)"
    )
    
    parser.add_argument(
        "--api-key",
        help="API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY env var)"
    )
    
    parser.add_argument(
        "--model",
        help="Model name (default: gpt-4-turbo-preview for OpenAI, claude-3-opus-20240229 for Anthropic)"
    )
    
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Temperature for generation (default: 0.1)"
    )
    
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=16000,
        help="Maximum tokens in response (default: 16000)"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing JSON file (skip API call)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.validate_only:
            # Just validate existing output
            output_path = args.output or args.book_file.replace('.txt', '.json')
            with open(output_path, 'r', encoding='utf-8') as f:
                data = validate_json_output(f.read())
            print(f"✓ Validation passed for {output_path}")
            return
        
        # Load book text
        print(f"Loading book from: {args.book_file}")
        book_text = load_book_text(args.book_file)
        print(f"✓ Loaded {len(book_text):,} characters")
        
        # Load master prompt
        print(f"Loading master prompt from: {args.prompt}")
        master_prompt = load_master_prompt(args.prompt)
        print(f"✓ Loaded prompt ({len(master_prompt):,} characters)")
        
        # Get API key
        api_key = args.api_key
        if not api_key:
            if args.api == "openai":
                import os
                api_key = os.getenv("OPENAI_API_KEY")
            elif args.api == "anthropic":
                import os
                api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ValueError(f"API key required. Provide --api-key or set {args.api.upper()}_API_KEY env var")
        
        # Call LLM API
        print(f"\nCalling {args.api} API...")
        print("(This may take several minutes for large books)")
        
        response = call_llm_api(
            master_prompt,
            book_text,
            api_type=args.api,
            api_key=api_key,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens
        )
        
        print("✓ Received response from API")
        
        # Validate and parse JSON
        print("Validating JSON output...")
        data = validate_json_output(response)
        print("✓ JSON validation passed")
        
        # Generate output path if not provided
        output_path = args.output
        if not output_path:
            book_id = data.get("book_id", str(uuid.uuid4()))
            output_dir = Path("ingested_books")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{book_id}.json"
        
        # Save output
        save_output(data, output_path)
        
        # Print summary
        print("\n" + "="*60)
        print("INGEST SUMMARY")
        print("="*60)
        print(f"Book ID: {data.get('book_id', 'N/A')}")
        print(f"Title: {data.get('book_metadata', {}).get('title', 'N/A')}")
        print(f"Total Words: {data.get('book_metadata', {}).get('total_words', 'N/A'):,}")
        print(f"Chapters: {len(data.get('chapter_summaries', []))}")
        print(f"Gold QA Pairs: {len(data.get('qa_datasets', {}).get('gold', []))}")
        print(f"Synthetic QA Pairs: {len(data.get('qa_datasets', {}).get('synthetic', []))}")
        print(f"Interpretive QA Pairs: {len(data.get('qa_datasets', {}).get('interpretive', []))}")
        print("="*60)
        
        if data.get('notes_for_human_review'):
            print(f"\n⚠ Notes for Review: {data['notes_for_human_review']}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
