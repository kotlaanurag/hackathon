# Technical Debt: Remove Redundant Failed Status Retry Logic

**Feature Branch**: TBD
**Created**: March 30, 2026
**Completed**: TBD
**Status**: PROPOSED
**Priority**: MEDIUM
**Type**: Performance / Technical Debt
**Implementation**: AI Agent (GitHub Copilot or similar)

> **⚠️ SCOPE BOUNDARY WARNING**
>
> This requirements document defines **EXACT SCOPE** for AI agent implementation. The implementing agent MUST:
> - Only modify the 2 files explicitly listed in this document
> - Only make changes described in the Solution Approach section
> - NOT add additional features, optimizations, or refactorings
> - NOT modify any other files beyond those specified
> - STOP and request authorization if any ambiguity or edge case is encountered
>
> **NO CHANGES** beyond this explicit scope are authorized without prior approval.

## Overview

Remove the redundant retry logic that checks IRIS job status multiple times when the job has already reached a **permanent Failed state** with business rule validation errors. This eliminates unnecessary network calls, reduces request latency by 1-1.5 seconds per failed operation, and improves overall system efficiency.

**Scope**: This refactoring is **STRICTLY LIMITED** to modifying the status polling retry logic in CommonHelper. No additional features, no behavior changes beyond removing redundant retries for permanent failures.

## Business Value

### Problem Statement

**Current State Issues**:
1. **Redundant Network Calls**: When IRIS returns `Status=Failed` with business rule errors, the service retries GetStatus 2 more times (total 3 checks on same failed job)
2. **Unnecessary Latency**: Each retry adds ~500ms + network overhead = **1-1.5 seconds wasted per failed request**
3. **IRIS Server Load**: Generates 3× unnecessary GetStatus API calls on IRIS for operations that will never succeed
4. **Poor User Experience**: Users wait longer to receive error messages that are already available
5. **Logic Flaw**: Retry assumes IRIS might "fix itself", but business rule errors (missing references, invalid field formats) are **permanent and immutable**

**Evidence from Production Logs** (DEV Environment - March 30, 2026):

**Example 1 - JobID 168941** (Missing Reference):
```
13:28:00: Status=Failed, Error="The Reference (407637012500) doesn't exist"
13:28:01: [Retry 1/2] Status=Failed, Error="The Reference (407637012500) doesn't exist" (IDENTICAL)
13:28:02: [Retry 2/2] Status=Failed, Error="The Reference (407637012500) doesn't exist" (IDENTICAL)
Total wasted time: ~1.2 seconds, 2 unnecessary API calls
```

**Example 2 - JobID 197018** (Invalid Field Format):
```
13:22:50: Status=Failed, Error="Escape Ref is 9 length field example(1234567-1)"
13:22:51: [Retry 1/2] Status=Failed, Error="Escape Ref is 9 length field example(1234567-1)" (IDENTICAL)
13:22:52: [Retry 2/2] Status=Failed, Error="Escape Ref is 9 length field example(1234567-1)" (IDENTICAL)
Total wasted time: ~1.0 seconds, 2 unnecessary API calls
```

**Example 3 - JobID 197017** (Multiple Validation Errors):
```
13:22:01: Status=Failed, Errors="Escape Ref is 9 length field...; Folio number is 10 length field..."
13:22:02: [Retry 1/2] Status=Failed, Errors="Escape Ref is 9 length field...; Folio number is 10 length field..." (IDENTICAL)
13:22:03: [Retry 2/2] Status=Failed, Errors="Escape Ref is 9 length field...; Folio number is 10 length field..." (IDENTICAL)
Total wasted time: ~1.4 seconds, 2 unnecessary API calls
```

**Impact Metrics** (based on log analysis):
- **Operations Affected**: Policy Creation, Policy Renewal (all handlers using CommonHelper.PollStatusAsync)
- **Frequency**: Every failed operation with validation errors
- **Performance Impact**: +1-1.5 seconds per failed request
- **Network Impact**: 3× GetStatus calls instead of 1× for permanent failures
- **IRIS Load**: Estimated 2,000-5,000 unnecessary API calls per day (assuming 1,000-2,500 validation failures)

### Root Cause

**File**: `PolicyConnectorService/Core/Utilities/CommonHelper.cs`
**Method**: `PollStatusAsync()`
**Lines**: ~145-155 (approximate, based on described behavior)

**Current Logic**:
```csharp
// Retry 2 times when errors occur on final status to allow IRIS to settle
if (statusResult.Status == "Failed" && finalStatusRetries < config.FinalStatusRetries)
{
    _logger.LogInformation("JobID \"{JobId}\" returned errors while status Failed appears final; retry {Retry}/{Max} to allow IRIS to settle.",
        jobId, finalStatusRetries + 1, config.FinalStatusRetries);
    await Task.Delay(config.FinalStatusDelayMs, cancellationToken);
    finalStatusRetries++;
    continue;  // Goes back to polling loop, calls GetStatus again
}
```

**Configuration** (`appsettings.json`):
```json
{
  "Polling": {
    "FinalStatusRetries": 2,
    "FinalStatusDelayMs": 500
  }
}
```

**Why This Is Wrong**:
1. **IRIS Job State Is Immutable**: Once JobID reaches `Status=Failed` with ErrorXml, it will NEVER change
2. **Business Rule Errors Are Permanent**: Validation failures (missing refs, invalid formats) cannot "settle" or "fix themselves"
3. **No Transient Error Detection**: Logic retries ALL failures, not just transient/network errors
4. **False Assumption**: Original developer assumed IRIS might be "eventually consistent" - this is not true for validation errors

**When Retry MIGHT Be Valid**:
- IRIS timeout/network errors (but these typically don't return Status=Failed, they throw exceptions)
- Internal IRIS processing errors (very rare, and would likely require manual intervention)
- Race conditions in IRIS (not observed in production logs)

**When Retry IS NEVER Valid** (99% of Failed states):
- Missing IRIS codes/references
- Invalid field formats (length, pattern violations)
- Business rule violations (duplicate policies, invalid dates)
- Schema validation failures

### Benefits of Removal

**Immediate Benefits**:
1. **Reduce Response Time**: Failed requests return 1-1.5 seconds faster
2. **Reduce IRIS Load**: 66% reduction in GetStatus calls for failed operations (3 calls → 1 call)
3. **Clearer Logs**: No confusing "retry 1/2, retry 2/2" messages when failure is permanent
4. **Better Error Messages**: Users get errors immediately without artificial delays

**Long-Term Benefits**:
1. **Maintainability**: Simpler polling logic, fewer edge cases
2. **Cost Savings**: Reduced network traffic and IRIS API consumption
3. **Scalability**: Better performance under high load (fewer redundant calls)
4. **Debuggability**: Logs are cleaner, failures are immediately obvious

**Risk Assessment**: **LOW**
- No behavior change for successful operations
- No behavior change for InProgress/NotStarted polling
- Only removes redundant checks that provide no value
- Errors still returned to user (just faster)

## Current State

### Affected Files

**Primary File**:
1. **`PolicyConnectorService/Core/Utilities/CommonHelper.cs`** - Contains PollStatusAsync method with retry logic

**Configuration File**:
2. **`PolicyConnectorService/appsettings.json`** - Contains Polling.FinalStatusRetries and Polling.FinalStatusDelayMs

**Test Files** (will need updates):
3. **`PolicyConnectorService.Tests/Core/Utilities/CommonHelperTests.cs`** - Tests for PollStatusAsync behavior

### Current Implementation

**CommonHelper.cs - PollStatusAsync Method**:
```csharp
public static async Task<StatusResult> PollStatusAsync(
    int jobId,
    string irisHost,
    Func<int, string, CancellationToken, Task<string>> getStatusFunc,
    ILogger logger,
    CancellationToken cancellationToken = default)
{
    var config = GetPollingConfig();
    var attempts = 0;
    var finalStatusRetries = 0;

    while (attempts < config.MaxAttempts)
    {
        attempts++;
        var response = await getStatusFunc(jobId, irisHost, cancellationToken);
        var statusResult = ParseStatusResponse(response);

        if (statusResult.Status == "NotStarted")
        {
            logger.LogInformation("JobID \"{JobId}\" currently NotStarted; continuing to poll.", jobId);
            await Task.Delay(config.DelayMs, cancellationToken);
            continue;
        }

        if (statusResult.Status == "InProgress")
        {
            logger.LogInformation("JobID \"{JobId}\" currently InProgress; continuing to poll.", jobId);
            await Task.Delay(config.DelayMs, cancellationToken);
            continue;
        }

        if (statusResult.Status == "Completed")
        {
            // Success - return immediately
            return statusResult;
        }

        // ❌ PROBLEM: Retry logic for Failed status
        if (statusResult.Status == "Failed" && finalStatusRetries < config.FinalStatusRetries)
        {
            logger.LogInformation("JobID \"{JobId}\" returned errors while status Failed appears final; retry {Retry}/{Max} to allow IRIS to settle.",
                jobId, finalStatusRetries + 1, config.FinalStatusRetries);
            await Task.Delay(config.FinalStatusDelayMs, cancellationToken);
            finalStatusRetries++;
            continue;  // ❌ This loops back and calls GetStatus AGAIN
        }

        // After retries exhausted or other status
        return statusResult;
    }

    // Timeout
    throw new TimeoutException($"Status polling for JobID {jobId} exceeded {config.MaxAttempts} attempts");
}
```

**Configuration**:
```json
{
  "Polling": {
    "MaxAttempts": 50,
    "DelayMs": 2000,
    "FinalStatusRetries": 2,      // ❌ Remove this
    "FinalStatusDelayMs": 500      // ❌ Remove this
  }
}
```

### Usage Locations

**PollStatusAsync is called from**:
1. `CreateSkeletonQueryHandler.Handle()` - After ProcessMessage for policy creation
2. `RenewPolicyQueryHandler.Handle()` - After ProcessMessage for policy renewal
3. *(Potentially other handlers using CommonHelper)*

**Test Coverage**:
- `CommonHelperTests.cs` has tests for polling behavior
- Tests likely verify retry logic (will need updates)

## Solution Approach

### Implementation Steps

#### Step 1: Remove Retry Logic from CommonHelper.cs

**File**: `PolicyConnectorService/Core/Utilities/CommonHelper.cs`

**Changes**:
1. Remove `finalStatusRetries` variable initialization
2. Remove the entire `if (statusResult.Status == "Failed" && finalStatusRetries < config.FinalStatusRetries)` block
3. Keep direct return of statusResult when Status="Failed"

**Before**:
```csharp
var attempts = 0;
var finalStatusRetries = 0;

while (attempts < config.MaxAttempts)
{
    // ... NotStarted and InProgress handling ...

    if (statusResult.Status == "Completed")
    {
        return statusResult;
    }

    // ❌ Remove this entire block
    if (statusResult.Status == "Failed" && finalStatusRetries < config.FinalStatusRetries)
    {
        logger.LogInformation("JobID \"{JobId}\" returned errors while status Failed appears final; retry {Retry}/{Max} to allow IRIS to settle.",
            jobId, finalStatusRetries + 1, config.FinalStatusRetries);
        await Task.Delay(config.FinalStatusDelayMs, cancellationToken);
        finalStatusRetries++;
        continue;
    }

    // After retries exhausted or other status
    return statusResult;
}
```

**After**:
```csharp
var attempts = 0;

while (attempts < config.MaxAttempts)
{
    // ... NotStarted and InProgress handling ...

    if (statusResult.Status == "Completed")
    {
        return statusResult;
    }

    if (statusResult.Status == "Failed")
    {
        // Failed status is final - return immediately
        return statusResult;
    }

    // Unknown status - return for handling upstream
    return statusResult;
}
```

**Result**:
- Failed status returns immediately on first detection
- No artificial delays or redundant GetStatus calls
- Cleaner, simpler logic

#### Step 2: Remove Configuration Properties

**File**: `PolicyConnectorService/appsettings.json` (and all environment variants)

**Changes**:
1. Remove `FinalStatusRetries` property from `Polling` section
2. Remove `FinalStatusDelayMs` property from `Polling` section

**Before**:
```json
{
  "Polling": {
    "MaxAttempts": 50,
    "DelayMs": 2000,
    "FinalStatusRetries": 2,
    "FinalStatusDelayMs": 500
  }
}
```

**After**:
```json
{
  "Polling": {
    "MaxAttempts": 50,
    "DelayMs": 2000
  }
}
```

**Files to Update**:
- `appsettings.json`
- `appsettings.Development.json`
- `appsettings.Production.json`
- `appsettings.QA.json`
- `appsettings.Staging.json`
- *(Any other appsettings variants)*

**Note**: If PollingConfig class/record exists, also remove those properties from the type definition.

#### Step 3: Update Tests

**File**: `PolicyConnectorService.Tests/Core/Utilities/CommonHelperTests.cs`

**Changes**:
1. Remove or update tests that verify retry behavior for Failed status
2. Add new test: `PollStatusAsync_FailedStatus_ReturnsImmediately`
3. Update test assertions to expect immediate return on Failed

**Example New Test**:
```csharp
[Fact]
public async Task PollStatusAsync_FailedStatus_ReturnsImmediately()
{
    // Arrange
    var jobId = 12345;
    var irisHost = "Ireland";
    var mockLogger = new Mock<ILogger>();
    var callCount = 0;

    Func<int, string, CancellationToken, Task<string>> getStatusFunc = (id, host, ct) =>
    {
        callCount++;
        return Task.FromResult(@"<GetStatusResponse>
            <Status>Failed</Status>
            <ErrorXml><Errors><Error ID=""1""><Message>Test error</Message></Error></Errors></ErrorXml>
        </GetStatusResponse>");
    };

    // Act
    var result = await CommonHelper.PollStatusAsync(jobId, irisHost, getStatusFunc, mockLogger.Object);

    // Assert
    Assert.Equal("Failed", result.Status);
    Assert.True(result.HasErrors);
    Assert.Equal(1, callCount); // ✅ Called exactly ONCE, not 3 times
}
```

**Tests to Remove/Update**:
- Any tests verifying "retry 1/2" or "retry 2/2" log messages
- Any tests expecting multiple GetStatus calls for Failed status
- Any tests asserting delay behavior for Failed status

### Validation & Testing

**Unit Tests**:
1. Verify Failed status returns immediately (1 GetStatus call)
2. Verify Completed status still works correctly
3. Verify InProgress/NotStarted polling still works with delays
4. Verify timeout behavior unchanged

**Integration Tests**:
1. Test with real IRIS integration (DEV environment)
2. Verify failed policy creation returns error immediately
3. Verify failed policy renewal returns error immediately
4. Measure response time improvement (~1-1.5 seconds faster)

**Manual Testing**:
1. Submit invalid policy creation request (missing IRIS code)
2. Verify error returned in ~3 seconds instead of ~4.5 seconds
3. Check logs - should NOT see "retry 1/2" or "retry 2/2" messages
4. Verify IRIS GetStatus API called only once per failure

### Acceptance Criteria

**MUST HAVE**:
1. ✅ Failed status returns immediately without retries
2. ✅ No "retry 1/2" or "retry 2/2" log messages for Failed status
3. ✅ GetStatus called exactly ONCE for permanent failures
4. ✅ Response time for failed operations reduced by ~1-1.5 seconds
5. ✅ All existing unit tests pass (after updates)
6. ✅ Successful operations (Completed status) behavior unchanged
7. ✅ Polling behavior for InProgress/NotStarted unchanged

**MUST NOT HAVE**:
1. ❌ No behavior changes for Completed status
2. ❌ No behavior changes for InProgress/NotStarted polling
3. ❌ No changes to timeout behavior (MaxAttempts still enforced)
4. ❌ No changes to delay configuration for normal polling (DelayMs)

**NICE TO HAVE** (Optional):
- Log message when Failed status detected: `"JobID {JobId} failed with {ErrorCount} errors - returning immediately"`
- Metrics/telemetry to track GetStatus call reduction

## Risk Assessment

**Risk Level**: **LOW**

**Potential Issues**:
1. **Transient IRIS Errors**: If IRIS occasionally returns Failed for transient issues, those won't be retried
   - **Mitigation**: Production logs show NO evidence of transient Failed states
   - **Fallback**: Users can retry request manually if needed

2. **Breaking Change**: Removes configuration properties
   - **Mitigation**: Properties are never used elsewhere in codebase
   - **Impact**: None - configurations are loaded at startup, no runtime references

3. **Test Failures**: Existing tests expect retry behavior
   - **Mitigation**: Update tests as part of this change
   - **Validation**: All tests must pass before merge

**Testing Strategy**:
1. Run all unit tests (update failing tests)
2. Deploy to DEV environment
3. Trigger validation failures (invalid fields, missing references)
4. Verify errors return immediately
5. Monitor logs for any unexpected behavior
6. Run integration tests for successful operations

## Implementation Checklist

**Pre-Implementation**:
- [ ] Create feature branch: `feature/remove-failed-status-retry-logic`
- [ ] Review current CommonHelper.cs implementation
- [ ] Review current test coverage in CommonHelperTests.cs

**Code Changes**:
- [ ] Remove retry logic from `CommonHelper.PollStatusAsync()`
- [ ] Remove `FinalStatusRetries` from all appsettings.json files
- [ ] Remove `FinalStatusDelayMs` from all appsettings.json files
- [ ] Remove properties from PollingConfig class (if exists)
- [ ] Update `CommonHelperTests.cs` (remove/update retry tests)
- [ ] Add new test: `PollStatusAsync_FailedStatus_ReturnsImmediately`

**Testing**:
- [ ] All unit tests pass
- [ ] Manual test in DEV: Failed policy creation
- [ ] Manual test in DEV: Failed policy renewal
- [ ] Verify log messages (no "retry 1/2" messages)
- [ ] Measure response time improvement
- [ ] Verify IRIS GetStatus call count (1 per failure, not 3)

**Documentation**:
- [ ] Update `docs/RUNBOOK.md` if retry behavior mentioned
- [ ] Update `CHANGELOG.md` with change description
- [ ] Update `docs/TESTING.md` if relevant

**Deployment**:
- [ ] Code review by at least 1 team member
- [ ] Merge to Dev branch
- [ ] Deploy to DEV environment
- [ ] Monitor DEV for 24-48 hours
- [ ] Deploy to QA environment
- [ ] Deploy to STAGE environment
- [ ] Deploy to PROD environment

## Related Issues & References

**Related Technical Debt Items**:
- Previous issue: Missing pre-flight validation for expiring policy references (to be documented separately)
- Strategy Pattern refactoring (TECHDEBT_IRIS_HOST_STRATEGY_PATTERN.md) - complementary, independent effort

**Reference Documentation**:
- [docs/RUNBOOK.md](../RUNBOOK.md) - Operational guidance for troubleshooting
- [docs/TESTING.md](../TESTING.md) - Testing standards and coverage requirements
- Confluence Wiki: https://everest.atlassian.net/wiki/spaces/GAD/pages/1559724097

**Production Evidence**:
- DEV environment logs: `logs/table-data (11).csv` (March 30, 2026)
- JobID examples: 168941, 197017, 197018
- All show identical Failed responses across 3 status checks

## AI Agent Implementation Notes

**FOR AI AGENT EXECUTING THIS WORK**:

### Critical Requirements
1. **ONLY modify the 2 files listed in Step 1 and Step 2** (CommonHelper.cs and appsettings variants)
2. **DO NOT** add any additional features or optimizations
3. **DO NOT** modify handler files (CreateSkeletonQueryHandler, RenewPolicyQueryHandler)
4. **DO NOT** add new logging, metrics, or telemetry beyond what exists
5. **STOP and ask** if you encounter any ambiguity or unexpected code structure

### Exact Scope
- Remove `finalStatusRetries` variable and associated logic from PollStatusAsync
- Make Failed status return immediately (no retry loop)
- Remove FinalStatusRetries and FinalStatusDelayMs from all appsettings files
- Update CommonHelperTests.cs to match new behavior

### Success Verification
1. Grep search: No occurrences of "retry 1/2" or "retry 2/2" in CommonHelper.cs
2. Grep search: No occurrences of "FinalStatusRetries" in appsettings.json files
3. Run: `dotnet test PolicyConnectorService.Tests/Core/Utilities/CommonHelperTests.cs` - all tests pass
4. Check: Failed status returns immediately without delays

### When to Stop
- If CommonHelper.cs structure differs significantly from described implementation
- If PollingConfig class doesn't exist or has unexpected properties
- If tests fail after updates and reason is unclear
- If any file beyond CommonHelper.cs and appsettings.json needs modification

**Estimated Effort**: 1-2 hours (simple removal of existing code)
**Complexity**: LOW (removing code is simpler than adding code)
**Test Impact**: MEDIUM (need to update ~5-10 tests)

---

**Document Version**: 1.0
**Last Updated**: March 30, 2026
**Author**: AI Agent + Development Team
