# New Output Directory Structure

## What Files Actually Contain:

### Batches
**NOT one document per batch!** Batches are groups of documents processed together to optimize API calls:
- `batch_01_11docs.json` - Contains extraction from 11 documents (e.g., 7 Excel files + 4 PDFs)
- `batch_02_1docs.json` - Contains extraction from 1 large document
- Each batch is sized to stay under token limits (~30,000 tokens)

### Merges
**NOT individual document merges!** These are cumulative data after processing multiple batches:
- `cumulative_after_01_batches.json` - Data from batch 1 only
- `cumulative_after_02_batches.json` - Combined data from batches 1 + 2
- `cumulative_after_03_batches.json` - Combined data from batches 1 + 2 + 3
- Uses deep merging to preserve all extracted information

## New Structure:
```
outputs/extracted_data/
├── Brigham_Dallas_202508_1430/        # Dataset name + timestamp (minute precision)
│   ├── batch_01_11docs.json           # Batch 1: processed 11 documents together
│   ├── batch_02_1docs.json            # Batch 2: processed 1 large document
│   ├── batch_03_1docs.json            # Batch 3: processed 1 document
│   ├── merged_data.json               # Final merged data from ALL batches
│   ├── complete_result.json           # Complete result with metadata
│   └── merges/                        # Progressive merge states
│       ├── cumulative_after_01_batches.json  # Data after batch 1
│       ├── cumulative_after_02_batches.json  # Data after batches 1+2
│       └── cumulative_after_03_batches.json  # Data after batches 1+2+3
├── Dave_Burlington_202508_1430/       # Second dataset with same timestamp
│   └── [same structure]
└── summary_202508_1430.json           # Overall summary for all datasets
```

## Benefits:
1. **Clearer naming**: Dataset name comes first, making it easy to identify
2. **Minute precision**: Timestamp only to the minute (YYYYMM_HHMM) since we clean regularly
3. **Simplified filenames**: Removed redundant words like "extraction", "incremental", etc.
4. **Flatter structure**: No nested "run_" directories, dataset folders are at top level
5. **Easy cleanup**: Can easily delete old runs by timestamp or dataset name

## Example filenames:
- `Brigham_Dallas_202508_1430/` - Brigham Dallas dataset processed at 2:30 PM on Aug 14, 2025
- `batch_01.json` - First batch of documents
- `merged_data.json` - All batches merged together
- `summary_202508_1430.json` - Overall summary for all datasets in this run