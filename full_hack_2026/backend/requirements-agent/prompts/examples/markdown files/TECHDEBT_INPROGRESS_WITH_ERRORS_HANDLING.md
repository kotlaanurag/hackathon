# Technical Debt: Detect and Handle InProgress Status with Errors

**Feature Branch**: TBD
**Created**: March 30, 2026
**Status**: PROPOSED
**Priority**: HIGH
**Type**: Bug Fix / Resilience Improvement
**Estimated Effort**: 1-2 hours

> **⚠️ SCOPE BOUNDARY**
>
> **ONLY modify CommonHelper.cs PollStatusAsync method** to detect ErrorXml when Status=InProgress.
> **NO other changes** beyond this specific error detection logic.

## Problem Statement

**IRIS Bug/Quirk**: When IRIS encounters certain permanent errors (e.g., "file already in use"), it incorrectly returns:
- `Status=InProgress`
- `ErrorXml` populated with error details

**Current Service Behavior**:
- Service sees `Status=InProgress` and continues polling
- Ignores the `ErrorXml` field completely
- Polls until MaxAttempts (50 attempts × 2s = 100 seconds)
- Eventually times out with generic "exceeded max attempts" error
- User waits 100 seconds to receive an error that was known after 1 second

**Production Evidence** (DEV logs, March 30, 2026):

**JobID 196934** - GenerateReference (Ireland):
```
10:23:31 - GenerateReference SOAP Fault: "Could not use ''; file already in use." RequestID=196934
10:23:31 - Status=InProgress, ErrorXml="Could not use ''; file already in use."
10:23:33 - Status=InProgress, ErrorXml="Could not use ''; file already in use." (poll 1)
10:23:35 - Status=InProgress, ErrorXml="Could not use ''; file already in use." (poll 2)
10:23:38 - Status=InProgress, ErrorXml="Could not use ''; file already in use." (poll 3)
... continues for 50+ polls ...
```

**Impact**:
- User Experience: +100 seconds wasted waiting for error that's immediately available
- IRIS Load: 50× unnecessary GetStatus API calls per stuck job
- Misleading Logs: "currently InProgress" message implies job is progressing (it's not)

## Solution

**Add error detection during InProgress status checks**:

```csharp
if (statusResult.Status == "InProgress")
{
    // ✅ NEW: Check if errors present while InProgress (IRIS bug - should be Failed)
    if (statusResult.HasErrors)
    {
        logger.LogWarning("JobID \"{JobId}\" is InProgress but has {ErrorCount} errors - treating as Failed to avoid indefinite polling.",
            jobId, statusResult.ErrorJson?.Split("Error ID").Length - 1 ?? 0);
        return statusResult;  // Return immediately with errors
    }

    // Normal InProgress - continue polling
    logger.LogInformation("JobID \"{JobId}\" currently InProgress; continuing to poll.", jobId);
    await Task.Delay(config.DelayMs, cancellationToken);
    continue;
}
```

**Result**:
- InProgress with errors returns immediately (1 poll instead of 50+)
- User gets error message in ~2 seconds instead of ~100 seconds
- Logs clearly indicate the abnormal state: "InProgress but has errors"
- Still allows normal InProgress polling when no errors present

## Implementation

**File**: `PolicyConnectorService/Core/Utilities/CommonHelper.cs`

**Method**: `PollStatusAsync()`

**Change Location**: Inside the while loop, in the InProgress status check block

**Before**:
```csharp
if (statusResult.Status == "InProgress")
{
    logger.LogInformation("JobID \"{JobId}\" currently InProgress; continuing to poll.", jobId);
    await Task.Delay(config.DelayMs, cancellationToken);
    continue;
}
```

**After**:
```csharp
if (statusResult.Status == "InProgress")
{
    // Check for errors during InProgress (IRIS bug - should be Failed)
    if (statusResult.HasErrors)
    {
        logger.LogWarning("JobID \"{JobId}\" is InProgress but has {ErrorCount} errors - treating as Failed to avoid indefinite polling.",
            jobId, statusResult.ErrorJson?.Split("Error ID").Length - 1 ?? 0);
        return statusResult;
    }

    logger.LogInformation("JobID \"{JobId}\" currently InProgress; continuing to poll.", jobId);
    await Task.Delay(config.DelayMs, cancellationToken);
    continue;
}
```

**Assumptions**:
- `StatusResult` class has `HasErrors` property (likely checks if `ErrorJson` or `ErrorXml` is non-null/non-empty)
- If `HasErrors` doesn't exist, use: `!string.IsNullOrEmpty(statusResult.ErrorJson)` or similar

## Testing

**Unit Tests** (CommonHelperTests.cs):
```csharp
[Fact]
public async Task PollStatusAsync_InProgressWithErrors_ReturnsImmediately()
{
    // Arrange
    var jobId = 196934;
    var callCount = 0;

    Func<int, string, CancellationToken, Task<string>> getStatusFunc = (id, host, ct) =>
    {
        callCount++;
        return Task.FromResult(@"<GetStatusResponse>
            <Status>InProgress</Status>
            <ErrorXml><Errors><Error ID=""1""><Message>File already in use</Message></Error></Errors></ErrorXml>
        </GetStatusResponse>");
    };

    // Act
    var result = await CommonHelper.PollStatusAsync(jobId, "Ireland", getStatusFunc, mockLogger.Object);

    // Assert
    Assert.Equal("InProgress", result.Status);
    Assert.True(result.HasErrors);
    Assert.Equal(1, callCount); // ✅ Called exactly ONCE, not 50 times
}
```

**Manual Test** (DEV environment):
1. Trigger GenerateReference call that causes "file already in use" error
2. Verify error returns in ~2 seconds (not ~100 seconds)
3. Verify logs show: "InProgress but has X errors - treating as Failed"
4. Verify GetStatus called only once (check Dynatrace/logs)

## Acceptance Criteria

**MUST HAVE**:
- ✅ InProgress with ErrorXml returns immediately (1 poll, not 50+)
- ✅ Response time for stuck jobs reduced from ~100s to ~2s
- ✅ Warning log message when InProgress has errors
- ✅ Normal InProgress polling (no errors) unchanged

**MUST NOT**:
- ❌ Break normal InProgress polling for jobs that eventually complete
- ❌ Change behavior for NotStarted, Completed, or Failed status
- ❌ Modify any files other than CommonHelper.cs and CommonHelperTests.cs

## Risk Assessment

**Risk Level**: **LOW-MEDIUM**

**Potential Issues**:
1. **False Positives**: What if IRIS legitimately returns InProgress + transient errors that later clear?
   - **Mitigation**: Production logs show no evidence of this pattern
   - **Observed Reality**: InProgress with errors = permanently stuck job
   - **Fallback**: User can retry request if needed

2. **Breaking Change**: Behavior change for InProgress status
   - **Mitigation**: Only affects abnormal IRIS responses (bug cases)
   - **Impact**: Improves user experience for stuck jobs

**Testing Strategy**:
1. Deploy to DEV
2. Monitor for any InProgress jobs that legitimately have transient errors
3. If found, refine logic to detect permanent vs transient errors
4. Proceed to QA/STAGE/PROD if no issues

## Related Issues

**Related Technical Debt**:
- [TECHDEBT_REMOVE_FAILED_STATUS_RETRY_LOGIC.md](TECHDEBT_REMOVE_FAILED_STATUS_RETRY_LOGIC.md) - Complementary fix for Failed status
- Pre-flight validation for expiring policy references (to be documented)

**Root Cause**: IRIS backend bug - returns incorrect status code for certain error conditions

**Production Evidence**:
- DEV logs: `logs/table-data (11).csv` (March 30, 2026)
- JobID 196934, JobID 196933
- Error: "Could not use ''; file already in use"

## AI Agent Implementation Notes

**Critical Requirements**:
1. **ONLY modify CommonHelper.cs** - add error check to InProgress block
2. **Update CommonHelperTests.cs** - add test for InProgress with errors
3. **NO other changes** - no new features, no refactoring
4. **STOP and ask** if StatusResult doesn't have HasErrors property

**Success Verification**:
1. Code compiles without errors
2. All existing tests pass
3. New test: `PollStatusAsync_InProgressWithErrors_ReturnsImmediately` passes
4. Manual test: Generate reference that triggers "file in use" error returns immediately

**When to Stop**:
- If StatusResult structure is significantly different than expected
- If tests fail after changes and reason is unclear
- If more than 2 files need modification

---

**Document Version**: 1.0
**Last Updated**: March 30, 2026
**Author**: AI Agent + Development Team
