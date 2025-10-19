# Version-Based Locking for Shared Caches

## Overview

This document describes the optimistic locking implementation for the 3 shared cache attributes (LocationCache, StationCache, ZoneCache) in the Clima Cast Alexa skill.

## Problem Statement

The Clima Cast skill uses a single DynamoDB item (partition key: `SHARED_CACHE`) to store cache data that is shared across all users. When multiple Lambda invocations run concurrently, there was a risk of race conditions where one invocation's writes could overwrite another's, leading to lost updates.

## Solution

Implemented optimistic locking using a version number field in the SHARED_CACHE DynamoDB item. This approach:
- Prevents lost updates from concurrent writes
- Automatically retries on version conflicts
- Merges changes from multiple concurrent invocations
- Requires no manual locking or distributed locks

## Implementation

### Version Number Tracking

The SHARED_CACHE item now includes a `version` field:
```json
{
  "id": "SHARED_CACHE",
  "version": 42,
  "attributes": {
    "LocationCache": {...},
    "StationCache": {...},
    "ZoneCache": {...}
  }
}
```

### Conditional Writes

When writing to shared caches, the code now:
1. Reads the current version number
2. Increments it locally
3. Uses a DynamoDB conditional expression to ensure the version hasn't changed
4. On conflict, retries with exponential backoff

### Code Changes

#### cache_put() Method

```python
# Read current version
response = table.get_item(Key={"id": "SHARED_CACHE"})
current_version = response["Item"].get("version", 0)

# Update cache data
# ... (update cache dict) ...

# Write with version check
new_version = current_version + 1
table.put_item(
    Item={
        "id": "SHARED_CACHE",
        "attributes": attrs,
        "version": new_version
    },
    ConditionExpression="version = :current_version",
    ExpressionAttributeValues={
        ":current_version": current_version
    }
)
```

#### Retry Logic

On `ConditionalCheckFailedException`:
- Automatically retries up to 5 times
- Uses exponential backoff: 0.2s, 0.4s, 0.8s, 1.6s, 3.2s
- Re-reads current state on each retry
- Merges local changes with latest data

#### cache_get() Method

Also updated to use version numbers when removing expired items from shared caches.

## Benefits

### Data Consistency
- **No Lost Updates**: Version conflicts are detected and resolved automatically
- **Atomic Operations**: Uses DynamoDB's built-in conditional write support
- **Eventual Consistency**: All concurrent updates eventually succeed

### Performance
- **Minimal Overhead**: Only one additional field in DynamoDB item
- **Fast Path**: Most writes succeed on first attempt (no conflicts)
- **Efficient Retries**: Exponential backoff reduces contention

### Simplicity
- **No Distributed Locks**: No need for separate locking service
- **No Deadlocks**: Optimistic approach avoids lock-based deadlocks
- **Transparent**: Works with existing cache_put/cache_get API

## Scenarios

### Scenario 1: No Concurrent Writes (Common Case)

```
Lambda A:
  1. Read version=10
  2. Update cache
  3. Write with version=11 (condition: version=10)
  ✓ Success on first attempt
```

### Scenario 2: Concurrent Writes (Rare Case)

```
Lambda A:                           Lambda B:
  1. Read version=10                  1. Read version=10
  2. Update cache (add Boulder)       2. Update cache (add Seattle)
  3. Write version=11                 3. Write version=11
     ✓ Success                           ✗ ConditionalCheckFailed
                                       4. Retry: Read version=11
                                       5. Merge Seattle with Boulder
                                       6. Write version=12
                                          ✓ Success

Result: Both Boulder and Seattle are in cache (no lost updates)
```

## Testing

### Automated Tests

**test_version_locking.py** includes:
- Test for successful write with version increment
- Test for conditional expression with existing versions
- Test for retry logic on concurrent conflicts
- Test for cache_get with version field

### Manual Verification

**test_manual_verification.py** demonstrates:
- Concurrent write scenario
- Automatic conflict detection and retry
- Data preservation across retries

Run tests:
```bash
python3 test_cache_refactoring.py    # Original tests
python3 test_version_locking.py      # Version locking tests
python3 test_manual_verification.py  # Interactive demo
```

## Security

- CodeQL analysis: **0 vulnerabilities found**
- Uses DynamoDB's built-in security features
- No exposure of version numbers to end users
- Exception handling prevents information leakage

## Backward Compatibility

The implementation is fully backward compatible:
- Existing SHARED_CACHE items without version field work (treated as version=0)
- User-specific caches unchanged (no version tracking needed)
- All existing tests pass without modification

## Performance Characteristics

### Best Case (No Conflicts)
- Latency: 1 DynamoDB read + 1 DynamoDB write
- Same as before version locking

### Worst Case (Max Retries)
- Latency: 6 DynamoDB reads + 6 DynamoDB writes
- Total backoff: ~6.2 seconds
- Very rare (requires 5 consecutive conflicts)

### Expected Case
- Most writes succeed on first attempt
- Conflicts rare (requires exact timing overlap)
- Typical retry count: 0-1

## Monitoring

Watch for these CloudWatch logs:
- `"Version conflict on shared cache write, retry X/5"` - Indicates concurrent writes (normal)
- `"Failed to write shared cache after 5 retries"` - Indicates high contention (investigate)

## Future Enhancements

Potential improvements:
1. Add jitter to exponential backoff to reduce thundering herd
2. Adjust max_retries based on historical conflict rate
3. Add CloudWatch metrics for version conflict frequency
4. Consider per-cache version numbers for finer-grained locking

## References

- [DynamoDB Conditional Writes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.ConditionalUpdate)
- [Optimistic Locking Pattern](https://en.wikipedia.org/wiki/Optimistic_concurrency_control)
- [Exponential Backoff](https://en.wikipedia.org/wiki/Exponential_backoff)
