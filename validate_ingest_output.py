#!/usr/bin/env python3
"""
Validate ingest output JSON against the schema and check data quality.
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def validate_schema_structure(data: dict) -> Tuple[bool, List[str]]:
    """Validate basic schema structure."""
    errors = []
    required_keys = [
        "book_id", "book_metadata", "ingest_summary", "book_profile",
        "chunking_plan", "retrieval_config", "persona_and_voice",
        "qa_datasets", "chapter_summaries", "canonical_quotes",
        "training_spec", "evaluation_spec", "runtime_prompts",
        "security_and_ip", "dev_checklist", "deployment_recommendations",
        "monitoring_and_metrics", "deliverables", "notes_for_human_review"
    ]
    
    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required key: {key}")
    
    return len(errors) == 0, errors


def validate_book_metadata(metadata: dict) -> List[str]:
    """Validate book_metadata section."""
    errors = []
    
    required_fields = ["title", "detected_language", "file_format", "total_words", "copyright_flag"]
    for field in required_fields:
        if field not in metadata:
            errors.append(f"book_metadata missing required field: {field}")
    
    if "copyright_flag" in metadata:
        valid_flags = ["public_domain", "clearly_copyrighted", "unknown"]
        if metadata["copyright_flag"] not in valid_flags:
            errors.append(f"Invalid copyright_flag: {metadata['copyright_flag']}")
    
    return errors


def validate_qa_datasets(qa_datasets: dict) -> List[str]:
    """Validate QA datasets."""
    errors = []
    warnings = []
    
    # Check required datasets
    required_datasets = ["gold", "synthetic", "interpretive"]
    for dataset_name in required_datasets:
        if dataset_name not in qa_datasets:
            errors.append(f"Missing QA dataset: {dataset_name}")
            continue
        
        dataset = qa_datasets[dataset_name]
        if not isinstance(dataset, list):
            errors.append(f"QA dataset '{dataset_name}' must be a list")
            continue
        
        # Check minimum counts
        if dataset_name == "gold" and len(dataset) < 20:
            warnings.append(f"Gold QA dataset has only {len(dataset)} pairs (recommended: 20+)")
        
        if dataset_name == "synthetic" and len(dataset) < 200:
            warnings.append(f"Synthetic QA dataset has only {len(dataset)} pairs (recommended: 200+)")
        
        if dataset_name == "interpretive" and len(dataset) < 50:
            warnings.append(f"Interpretive QA dataset has only {len(dataset)} pairs (recommended: 50+)")
        
        # Validate QA pair structure
        for i, qa_pair in enumerate(dataset):
            if not isinstance(qa_pair, dict):
                errors.append(f"QA pair {i} in '{dataset_name}' is not an object")
                continue
            
            if "question" not in qa_pair or "answer" not in qa_pair:
                errors.append(f"QA pair {i} in '{dataset_name}' missing question or answer")
            
            if dataset_name == "synthetic":
                if "source_chunk_ids" not in qa_pair:
                    warnings.append(f"Synthetic QA pair {i} missing source_chunk_ids")
                if "confidence_source_overlap" not in qa_pair:
                    warnings.append(f"Synthetic QA pair {i} missing confidence_source_overlap")
    
    return errors, warnings


def validate_chunking_plan(plan: dict) -> List[str]:
    """Validate chunking_plan."""
    errors = []
    
    required_fields = [
        "recommended_chunk_size_words",
        "overlap_percent",
        "chunk_boundary_preference",
        "special_handling_for_quotations",
        "token_estimate_per_chunk",
        "algorithm_description"
    ]
    
    for field in required_fields:
        if field not in plan:
            errors.append(f"chunking_plan missing required field: {field}")
    
    # Validate ranges
    if "recommended_chunk_size_words" in plan:
        size = plan["recommended_chunk_size_words"]
        if not (400 <= size <= 800):
            errors.append(f"Chunk size {size} outside recommended range (400-800)")
    
    if "overlap_percent" in plan:
        overlap = plan["overlap_percent"]
        if not (15 <= overlap <= 30):
            errors.append(f"Overlap {overlap}% outside recommended range (15-30%)")
    
    return errors


def validate_runtime_prompts(prompts: dict) -> List[str]:
    """Validate runtime_prompts."""
    errors = []
    
    required_prompts = ["system_prompt", "user_prompt_template", "explainability_prompt"]
    for prompt_name in required_prompts:
        if prompt_name not in prompts:
            errors.append(f"runtime_prompts missing: {prompt_name}")
        elif not isinstance(prompts[prompt_name], str) or len(prompts[prompt_name].strip()) == 0:
            errors.append(f"runtime_prompts.{prompt_name} is empty or not a string")
    
    return errors


def validate_canonical_quotes(quotes: List[dict]) -> List[str]:
    """Validate canonical_quotes."""
    errors = []
    warnings = []
    
    if len(quotes) > 30:
        warnings.append(f"Canonical quotes exceed recommended limit (30), found {len(quotes)}")
    
    for i, quote in enumerate(quotes):
        required_fields = ["chunk_id", "quote_text", "page_loc", "paraphrase"]
        for field in required_fields:
            if field not in quote:
                errors.append(f"Quote {i} missing required field: {field}")
        
        if "quote_text" in quote:
            word_count = len(quote["quote_text"].split())
            if word_count > 25:
                warnings.append(f"Quote {i} exceeds 25-word limit ({word_count} words)")
    
    return errors, warnings


def validate_dev_checklist(checklist: List[str]) -> List[str]:
    """Validate dev_checklist."""
    errors = []
    
    if not isinstance(checklist, list):
        errors.append("dev_checklist must be a list")
        return errors
    
    if len(checklist) < 20:
        errors.append(f"dev_checklist has only {len(checklist)} items (required: 20+)")
    
    return errors


def validate_all(data: dict) -> Tuple[bool, List[str], List[str]]:
    """Run all validation checks."""
    all_errors = []
    all_warnings = []
    
    # Schema structure
    valid, errors = validate_schema_structure(data)
    if not valid:
        all_errors.extend(errors)
        return False, all_errors, all_warnings
    
    # Book metadata
    if "book_metadata" in data:
        all_errors.extend(validate_book_metadata(data["book_metadata"]))
    
    # QA datasets
    if "qa_datasets" in data:
        errors, warnings = validate_qa_datasets(data["qa_datasets"])
        all_errors.extend(errors)
        all_warnings.extend(warnings)
    
    # Chunking plan
    if "chunking_plan" in data:
        all_errors.extend(validate_chunking_plan(data["chunking_plan"]))
    
    # Runtime prompts
    if "runtime_prompts" in data:
        all_errors.extend(validate_runtime_prompts(data["runtime_prompts"]))
    
    # Canonical quotes
    if "canonical_quotes" in data:
        errors, warnings = validate_canonical_quotes(data["canonical_quotes"])
        all_errors.extend(errors)
        all_warnings.extend(warnings)
    
    # Dev checklist
    if "dev_checklist" in data:
        all_errors.extend(validate_dev_checklist(data["dev_checklist"]))
    
    return len(all_errors) == 0, all_errors, all_warnings


def main():
    parser = argparse.ArgumentParser(
        description="Validate ingest output JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "ingest_json",
        help="Path to ingest JSON file to validate"
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    
    args = parser.parse_args()
    
    # Load JSON
    try:
        with open(args.ingest_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {args.ingest_json}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate
    print(f"Validating: {args.ingest_json}")
    print("="*60)
    
    valid, errors, warnings = validate_all(data)
    
    # Print results
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for error in errors:
            print(f"  • {error}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  • {warning}")
    
    if not errors and not warnings:
        print("\n✓ Validation passed with no errors or warnings")
    elif not errors:
        print("\n✓ Validation passed (warnings only)")
    else:
        print("\n❌ Validation failed")
    
    print("="*60)
    
    # Print summary statistics
    print("\nSUMMARY STATISTICS:")
    print(f"  Book ID: {data.get('book_id', 'N/A')}")
    print(f"  Title: {data.get('book_metadata', {}).get('title', 'N/A')}")
    print(f"  Chapters: {len(data.get('chapter_summaries', []))}")
    print(f"  Gold QA: {len(data.get('qa_datasets', {}).get('gold', []))}")
    print(f"  Synthetic QA: {len(data.get('qa_datasets', {}).get('synthetic', []))}")
    print(f"  Interpretive QA: {len(data.get('qa_datasets', {}).get('interpretive', []))}")
    print(f"  Canonical Quotes: {len(data.get('canonical_quotes', []))}")
    print(f"  Dev Checklist Items: {len(data.get('dev_checklist', []))}")
    
    # Exit code
    if errors or (args.strict and warnings):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
