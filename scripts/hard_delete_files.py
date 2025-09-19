#!/usr/bin/env python3
"""
Hard Delete Files Script

This script permanently deletes files from both the database and storage
based on a JSON input file containing file records.

Usage:
    python scripts/hard_delete_files.py <json_file_path> [--dry-run] [--confirm]

Example:
    python scripts/hard_delete_files.py deleted_files.json --dry-run
    python scripts/hard_delete_files.py deleted_files.json --confirm

Warning: This operation is IRREVERSIBLE. Files will be permanently deleted.
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
from uuid import UUID

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.models.file import File
from app.services.storage.factory import get_storage_service
from app.config.settings import get_settings


class FileHardDeleter:
    """Service for permanently deleting files from database and storage"""
    
    def __init__(self):
        self.settings = get_settings()
        self.storage_service = get_storage_service()
        self.session_maker = AsyncSessionLocal
    
    async def hard_delete_files(
        self, 
        file_ids: List[str], 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Permanently delete files from database and storage
        
        Args:
            file_ids: List of file ID strings to delete
            dry_run: If True, only show what would be deleted without actually deleting
            
        Returns:
            Dictionary with deletion results
        """
        results = {
            "total_requested": len(file_ids),
            "found_in_db": 0,
            "deleted_from_db": 0,
            "deleted_from_storage": 0,
            "errors": [],
            "deleted_files": [],
            "not_found": []
        }
        
        async with self.session_maker() as db:
            for file_id_str in file_ids:
                try:
                    file_uuid = UUID(file_id_str)
                    
                    # Find the file in database
                    query = select(File).where(File.id == file_uuid)
                    result = await db.execute(query)
                    file_obj = result.scalar_one_or_none()
                    
                    if not file_obj:
                        results["not_found"].append(file_id_str)
                        continue
                    
                    results["found_in_db"] += 1
                    
                    file_info = {
                        "id": str(file_obj.id),
                        "filename": file_obj.filename,
                        "file_path": file_obj.file_path,
                        "file_size": file_obj.file_size,
                        "mime_type": file_obj.mime_type,
                        "status": file_obj.status.value if file_obj.status else "unknown",
                        "created_at": file_obj.created_at.isoformat() if file_obj.created_at else None
                    }
                    
                    if dry_run:
                        print(f"[DRY RUN] Would delete: {file_obj.filename} ({file_obj.id})")
                        results["deleted_files"].append(file_info)
                        results["deleted_from_db"] += 1
                        results["deleted_from_storage"] += 1
                        continue
                    
                    # Delete from storage first
                    storage_deleted = False
                    if file_obj.file_path:
                        try:
                            await self.storage_service.delete_content(file_obj.file_path)
                            storage_deleted = True
                            results["deleted_from_storage"] += 1
                            print(f"✅ Deleted from storage: {file_obj.file_path}")
                        except Exception as e:
                            error_msg = f"Failed to delete from storage {file_obj.file_path}: {str(e)}"
                            results["errors"].append(error_msg)
                            print(f"⚠️ {error_msg}")
                    
                    # Delete from database
                    try:
                        await db.delete(file_obj)
                        await db.commit()
                        results["deleted_from_db"] += 1
                        results["deleted_files"].append(file_info)
                        print(f"✅ Deleted from database: {file_obj.filename} ({file_obj.id})")
                    except Exception as e:
                        error_msg = f"Failed to delete from database {file_obj.id}: {str(e)}"
                        results["errors"].append(error_msg)
                        print(f"❌ {error_msg}")
                        await db.rollback()
                        continue
                
                except ValueError as e:
                    error_msg = f"Invalid UUID format: {file_id_str}"
                    results["errors"].append(error_msg)
                    print(f"❌ {error_msg}")
                except Exception as e:
                    error_msg = f"Unexpected error processing {file_id_str}: {str(e)}"
                    results["errors"].append(error_msg)
                    print(f"❌ {error_msg}")
        
        return results
    
    async def verify_files_exist(self, file_ids: List[str]) -> Dict[str, Any]:
        """
        Verify which files exist in the database
        
        Args:
            file_ids: List of file ID strings to check
            
        Returns:
            Dictionary with verification results
        """
        verification = {
            "total_requested": len(file_ids),
            "found": [],
            "not_found": [],
            "invalid_uuids": []
        }
        
        async with self.session_maker() as db:
            for file_id_str in file_ids:
                try:
                    file_uuid = UUID(file_id_str)
                    
                    # Find the file in database
                    query = select(File).where(File.id == file_uuid)
                    result = await db.execute(query)
                    file_obj = result.scalar_one_or_none()
                    
                    if file_obj:
                        verification["found"].append({
                            "id": str(file_obj.id),
                            "filename": file_obj.filename,
                            "status": file_obj.status.value if file_obj.status else "unknown",
                            "is_deleted": file_obj.is_deleted,
                            "file_size": file_obj.file_size
                        })
                    else:
                        verification["not_found"].append(file_id_str)
                        
                except ValueError:
                    verification["invalid_uuids"].append(file_id_str)
                except Exception as e:
                    print(f"Error verifying {file_id_str}: {str(e)}")
        
        return verification


def load_files_from_json(json_file_path: str) -> List[str]:
    """
    Load file IDs from JSON file
    
    Args:
        json_file_path: Path to JSON file containing file data
        
    Returns:
        List of file ID strings
    """
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, dict):
            if "files" in data:
                files = data["files"]
            elif "data" in data:
                files = data["data"]
            else:
                # Assume the dict itself contains file data
                files = [data]
        elif isinstance(data, list):
            files = data
        else:
            raise ValueError("Invalid JSON structure")
        
        # Extract file IDs
        file_ids = []
        for file_data in files:
            if isinstance(file_data, dict) and "id" in file_data:
                file_ids.append(file_data["id"])
            elif isinstance(file_data, str):
                file_ids.append(file_data)
            else:
                print(f"Warning: Skipping invalid file data: {file_data}")
        
        return file_ids
    
    except FileNotFoundError:
        print(f"❌ Error: File '{json_file_path}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{json_file_path}': {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading file: {str(e)}")
        sys.exit(1)


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Hard delete files from database and storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (show what would be deleted)
  python scripts/hard_delete_files.py deleted_files.json --dry-run
  
  # Verify files exist before deletion
  python scripts/hard_delete_files.py deleted_files.json --verify
  
  # Actually delete files (requires confirmation)
  python scripts/hard_delete_files.py deleted_files.json --confirm
  
  # Force deletion without interactive confirmation
  python scripts/hard_delete_files.py deleted_files.json --confirm --force

Warning: This operation permanently deletes files and cannot be undone!
        """
    )
    
    parser.add_argument(
        "json_file", 
        help="Path to JSON file containing file data with 'id' fields"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--verify", 
        action="store_true", 
        help="Only verify which files exist in the database"
    )
    parser.add_argument(
        "--confirm", 
        action="store_true", 
        help="Confirm that you want to permanently delete files"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Skip interactive confirmation (use with --confirm)"
    )
    
    args = parser.parse_args()
    
    # Load file IDs from JSON
    print(f"📁 Loading file IDs from: {args.json_file}")
    file_ids = load_files_from_json(args.json_file)
    print(f"📊 Found {len(file_ids)} file IDs to process")
    
    if not file_ids:
        print("❌ No file IDs found in the JSON file")
        sys.exit(1)
    
    # Initialize deleter
    deleter = FileHardDeleter()
    
    # Verification mode
    if args.verify:
        print("\n🔍 Verifying files in database...")
        verification = await deleter.verify_files_exist(file_ids)
        
        print(f"\n📊 Verification Results:")
        print(f"  Total requested: {verification['total_requested']}")
        print(f"  Found in database: {len(verification['found'])}")
        print(f"  Not found: {len(verification['not_found'])}")
        print(f"  Invalid UUIDs: {len(verification['invalid_uuids'])}")
        
        if verification['found']:
            print(f"\n✅ Files found in database:")
            for file_info in verification['found']:
                status_icon = "🗑️" if file_info['is_deleted'] else "📄"
                print(f"  {status_icon} {file_info['filename']} ({file_info['id']}) - Status: {file_info['status']}")
        
        if verification['not_found']:
            print(f"\n❌ Files not found:")
            for file_id in verification['not_found']:
                print(f"  📭 {file_id}")
        
        return
    
    # Dry run mode
    if args.dry_run:
        print("\n🔍 DRY RUN - No files will be actually deleted")
        results = await deleter.hard_delete_files(file_ids, dry_run=True)
    else:
        # Confirmation for actual deletion
        if not args.confirm:
            print("❌ Error: --confirm flag is required for actual deletion")
            print("Use --dry-run to see what would be deleted")
            sys.exit(1)
        
        if not args.force:
            print("\n⚠️  WARNING: This will PERMANENTLY DELETE files from both database and storage!")
            print(f"📊 Files to delete: {len(file_ids)}")
            response = input("\nType 'DELETE' to confirm (anything else will cancel): ")
            
            if response != "DELETE":
                print("❌ Operation cancelled")
                sys.exit(0)
        
        print("\n🗑️ Permanently deleting files...")
        results = await deleter.hard_delete_files(file_ids, dry_run=False)
    
    # Print results
    print(f"\n📊 Deletion Results:")
    print(f"  Total requested: {results['total_requested']}")
    print(f"  Found in database: {results['found_in_db']}")
    print(f"  Deleted from database: {results['deleted_from_db']}")
    print(f"  Deleted from storage: {results['deleted_from_storage']}")
    print(f"  Not found: {len(results['not_found'])}")
    print(f"  Errors: {len(results['errors'])}")
    
    if results['errors']:
        print(f"\n❌ Errors encountered:")
        for error in results['errors']:
            print(f"  • {error}")
    
    if results['not_found']:
        print(f"\n📭 Files not found in database:")
        for file_id in results['not_found']:
            print(f"  • {file_id}")
    
    success_rate = (results['deleted_from_db'] / results['total_requested'] * 100) if results['total_requested'] > 0 else 0
    print(f"\n✅ Success rate: {success_rate:.1f}%")
    
    if not args.dry_run and results['deleted_from_db'] > 0:
        print(f"\n🎉 Successfully deleted {results['deleted_from_db']} files permanently!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)