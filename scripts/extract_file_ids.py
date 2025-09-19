#!/usr/bin/env python3
"""
Extract File IDs Utility

This utility extracts just the file IDs from a larger JSON file response
and creates a simplified JSON file for use with the hard_delete_files.py script.

Usage:
    python scripts/extract_file_ids.py input.json output.json
    python scripts/extract_file_ids.py input.json  # outputs to input_ids.json

Examples:
    # Convert full file list response to simple ID list
    python scripts/extract_file_ids.py deleted_files_full.json deleted_file_ids.json
    
    # Extract only files with status "deleted"
    python scripts/extract_file_ids.py all_files.json deleted_only.json --status deleted
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional


def extract_file_ids(
    input_data: Dict[str, Any], 
    status_filter: Optional[str] = None
) -> List[str]:
    """
    Extract file IDs from various JSON structures
    
    Args:
        input_data: JSON data containing files
        status_filter: Only include files with this status (e.g., "deleted")
        
    Returns:
        List of file ID strings
    """
    files = []
    
    # Handle different JSON structures
    if isinstance(input_data, dict):
        if "files" in input_data:
            files = input_data["files"]
        elif "data" in input_data:
            files = input_data["data"]
        elif "id" in input_data:
            # Single file object
            files = [input_data]
        else:
            raise ValueError("Could not find file data in JSON structure")
    elif isinstance(input_data, list):
        files = input_data
    else:
        raise ValueError("Invalid JSON structure - expected dict or list")
    
    # Extract IDs with optional status filtering
    file_ids = []
    for file_data in files:
        if not isinstance(file_data, dict) or "id" not in file_data:
            continue
            
        # Apply status filter if specified
        if status_filter:
            file_status = file_data.get("status", "").lower()
            if file_status != status_filter.lower():
                continue
        
        file_ids.append(file_data["id"])
    
    return file_ids


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Extract file IDs from JSON file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all file IDs
  python scripts/extract_file_ids.py full_response.json simple_ids.json
  
  # Extract only deleted files
  python scripts/extract_file_ids.py all_files.json deleted_ids.json --status deleted
  
  # Extract and use default output name
  python scripts/extract_file_ids.py my_files.json  # creates my_files_ids.json
        """
    )
    
    parser.add_argument(
        "input_file",
        help="Input JSON file containing file data"
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        help="Output JSON file for extracted IDs (optional)"
    )
    parser.add_argument(
        "--status",
        help="Only extract files with this status (e.g., 'deleted')"
    )
    parser.add_argument(
        "--format",
        choices=["simple", "detailed"],
        default="simple",
        help="Output format: 'simple' (just IDs) or 'detailed' (with metadata)"
    )
    
    args = parser.parse_args()
    
    # Determine output filename
    if args.output_file:
        output_file = args.output_file
    else:
        input_path = Path(args.input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_ids.json")
    
    try:
        # Load input file
        print(f"📁 Loading file data from: {args.input_file}")
        with open(args.input_file, 'r') as f:
            input_data = json.load(f)
        
        # Extract file IDs
        file_ids = extract_file_ids(input_data, args.status)
        
        if not file_ids:
            print("❌ No files found matching the criteria")
            sys.exit(1)
        
        print(f"📊 Found {len(file_ids)} file IDs")
        if args.status:
            print(f"   (filtered by status: {args.status})")
        
        # Create output data
        if args.format == "simple":
            # Simple array of IDs
            output_data = file_ids
        else:
            # Detailed format with metadata
            output_data = {
                "file_ids": file_ids,
                "total": len(file_ids),
                "extracted_at": "2025-09-17T00:00:00Z",
                "status_filter": args.status,
                "source_file": args.input_file
            }
        
        # Save output file
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"✅ Extracted file IDs saved to: {output_file}")
        print(f"📋 You can now use: poetry run python scripts/hard_delete_files.py {output_file} --verify")
        
    except FileNotFoundError:
        print(f"❌ Error: Input file '{args.input_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{args.input_file}': {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()