# Hard Delete Files Script

This script permanently deletes files from both the database and storage based on a JSON input file.

## ⚠️ WARNING
**This operation is IRREVERSIBLE. Files will be permanently deleted from both the database and storage.**

## Usage

### 1. Verify Files First (Recommended)
```bash
poetry run python scripts/hard_delete_files.py your_files.json --verify
```

### 2. Dry Run (See What Would Be Deleted)
```bash
poetry run python scripts/hard_delete_files.py your_files.json --dry-run
```

### 3. Actually Delete Files
```bash
poetry run python scripts/hard_delete_files.py your_files.json --confirm
```

### 4. Force Delete (Skip Interactive Confirmation)
```bash
poetry run python scripts/hard_delete_files.py your_files.json --confirm --force
```

## JSON File Format

The script accepts JSON files in several formats:

### Format 1: File List Response (Most Common)
```json
{
    "files": [
        {
            "id": "68ee3091-4f0d-47b4-8b99-7e8ccd9d074c",
            "filename": "test.txt",
            "status": "deleted"
        }
    ],
    "total": 1
}
```

### Format 2: Simple Array
```json
[
    {
        "id": "68ee3091-4f0d-47b4-8b99-7e8ccd9d074c",
        "filename": "test.txt"
    }
]
```

### Format 3: Array of IDs
```json
[
    "68ee3091-4f0d-47b4-8b99-7e8ccd9d074c",
    "ba24fa66-5e76-4115-a66e-8db7521d2559"
]
```

## Examples

### Get Deleted Files and Save to JSON
You can get deleted files from your API and save them:

```bash
# Get deleted files from your database/API response and save to a file
# (The API currently blocks status=deleted queries, so you might need to get this data differently)

# If you have a full file response, you can extract just the deleted ones:
poetry run python scripts/extract_file_ids.py all_files.json deleted_only.json --status deleted
```

### Complete Workflow

```bash
# 1. (Optional) Extract deleted files from a larger response
poetry run python scripts/extract_file_ids.py your_large_file_response.json deleted_files.json --status deleted

# 2. Verify what files exist in the database
poetry run python scripts/hard_delete_files.py deleted_files.json --verify

# 3. Do a dry run to see what would be deleted
poetry run python scripts/hard_delete_files.py deleted_files.json --dry-run

# 4. If everything looks correct, delete them
poetry run python scripts/hard_delete_files.py deleted_files.json --confirm
```

### Quick Deletion (if you're sure)
```bash
# Extract IDs and delete in one go
poetry run python scripts/extract_file_ids.py large_response.json --status deleted
poetry run python scripts/hard_delete_files.py large_response_ids.json --confirm --force
```

## Output

The script provides detailed output:

```
📁 Loading file IDs from: deleted_files.json
📊 Found 3 file IDs to process

🗑️ Permanently deleting files...
✅ Deleted from storage: attachments/2025/09/68ee3091-4f0d-47b4-8b99-7e8ccd9d074c.txt
✅ Deleted from database: test_upload.txt (68ee3091-4f0d-47b4-8b99-7e8ccd9d074c)

📊 Deletion Results:
  Total requested: 3
  Found in database: 3
  Deleted from database: 3
  Deleted from storage: 3
  Not found: 0
  Errors: 0

✅ Success rate: 100.0%
🎉 Successfully deleted 3 files permanently!
```

## Safety Features

1. **Requires explicit confirmation** - Must use `--confirm` flag
2. **Interactive confirmation** - Asks you to type "DELETE" unless `--force` is used
3. **Dry run mode** - See what would be deleted without actually deleting
4. **Verification mode** - Check which files exist before deletion
5. **Detailed logging** - Shows exactly what's being deleted
6. **Error handling** - Continues processing even if some files fail
7. **Storage and DB cleanup** - Deletes from both storage and database

## Important Notes

- Only files with valid UUIDs will be processed
- Files not found in the database will be skipped (not an error)
- Storage deletion failures are logged but don't stop database deletion
- The script uses the same storage service as the main application
- Database transactions ensure consistency

## Troubleshooting

### "File not found" errors
This is normal - files may have been deleted already or IDs might be incorrect.

### Storage deletion failures
The script will continue and delete from database even if storage deletion fails. You may need to clean up storage manually.

### Permission errors
Make sure you're running with appropriate database and storage permissions.