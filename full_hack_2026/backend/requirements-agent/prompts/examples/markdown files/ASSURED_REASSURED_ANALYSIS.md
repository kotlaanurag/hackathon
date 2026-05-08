# Assured / Reassured Creation Logic — Analysis & Recommendations

**Date**: April 17, 2026
**Author**: Code Analysis (AI-assisted)
**Status**: Review Required

---

## 1. Overview

This document analyses how PolicyConnectorService resolves and creates Insured (Assured) and Reinsured (Reassured) entities when sending requests to the IRIS backend. It compares the implemented logic against the documented business rules and identifies gaps.

---

## 2. Documented Business Rules (Reference)

### Exceptions / Assumptions

1. Insured and Reinsured are the same except:
   - In **Syndicate for Insured** — only a company name is sent

### Resolution Process

| Priority | Condition | Action |
|----------|-----------|--------|
| 1 | IRIS Code is sent | Use IRIS code directly. No lookups. Fail if not mapped. |
| 2 | No IRIS Code, DUNS Number sent | Lookup by DUNS. Found → use IRIS code. Not found → create new insured. |
| 3 | No IRIS Code or DUNS, SEND Reference sent | Lookup by SEND Ref. Found → use IRIS code. Not found → create new insured. |
| 4 | None of the above present | PCS validation error |

---

## 3. Implemented Logic Summary

### 3.1 CreateSkeletonQueryHandler (Primary Flow)

The skeleton handler implements the most complete version of assured resolution:

**Step 1 — Pre-processing**
- InsuredName truncated to 40 characters if longer
- Syndicate host detection determines CompanyType rules (`"C"` for Syndicate/Reinsured, `"A"` for Insured)

**Step 2 — IRIS Code Resolution Decision**
- If **both** InsuredIRISCode and ReinsuredIRISCode are provided → trim and use directly (no lookups)
- If **one** is provided → use the provided one; run lookup for the missing one if valid details exist
- If **neither** is provided → enter full lookup/creation flow

**Step 3 — Lookup Flow (AssuredCreationService)**
- **Phase 1 — DUNS Lookup**: If DUNS is present, calls `SEND_GetAssuredByRef` to find the IRIS code (`CSCSCD` field)
- **Phase 2 — Assured Creation**: If DUNS lookup fails and valid details exist, creates a new assured entity via `CreateAssured` SOAP message, then re-lookups by DUNS to retrieve the new IRIS code

**Step 4 — Syndicate Exception**
- When the host is Syndicate and only insured details are present, the lookup is skipped entirely. Only `InsuredName` is passed through to the skeleton SOAP payload (no IRIS code, no DUNS, no domicile).

### 3.2 CreateRenewalQueryHandler (Simplified Flow)

The renewal handler uses a **simpler** approach:
- Only triggers lookup if **both** IRIS codes are missing
- Performs DUNS lookup only (via `ResilienceSoapService.GetIRISCodeAsync`)
- **Does NOT create new assured entities** — if lookup fails, no fallback

---

## 4. Gap Analysis: Documented Rules vs Implementation

### 4.1 MATCHES (Confirmed Correct)

| Rule | Status | Evidence |
|------|--------|----------|
| Rule 1: IRIS Code provided → use directly | MATCH | Both handlers trim and use provided IRIS codes without lookups |
| Rule 2: DUNS lookup when no IRIS Code | MATCH | `AssuredCreationService.LookupDunsForTargets()` queries `SEND_GetAssuredByRef` using DUNS |
| Rule 2: Create new insured if DUNS not found | PARTIAL MATCH | Skeleton handler creates; Renewal handler does NOT (see Gap 1) |
| Syndicate exception: only company name sent | MATCH | `InsuredName` re-added to SOAP payload; all other insured fields skipped |
| Insured/Reinsured treated the same (except Syndicate) | MATCH | Same resolution logic applied to both targets |

### 4.2 GAPS AND MISMATCHES

#### GAP 1 — SEND Reference Lookup Not Implemented as Standalone Step (HIGH)

**Documented Rule 3**: If no IRIS Code or DUNS, but SEND Reference is present → lookup using SEND Ref → if not found, create new insured.

**Actual Implementation**: SEND Reference is included in the DUNS lookup payload as an additional parameter, but there is **no standalone SEND Reference lookup** when DUNS is absent. The lookup payload is structured as:
```
[duns, companiesHouse, sendReference, companyType]
```

If DUNS is missing, the code skips the lookup entirely and proceeds directly to assured creation. The SEND Reference is never used independently as a lookup key.

**Impact**: Entities that could be found by SEND Reference alone will instead trigger unnecessary new assured creation, potentially creating duplicates in IRIS.

**Recommendation**: Implement a separate lookup path that queries `SEND_GetAssuredByRef` using SEND Reference when DUNS is absent but SEND Reference is present.

---

#### GAP 2 — No Upfront "At Least One Identifier" Validation (HIGH)

**Documented Rule 4**: If none of IRIS Code, DUNS, or SEND Reference are present → PCS validation error.

**Actual Implementation**: There is no explicit upfront validation that at least one identifier is present. The code relies on `HasValidAssuredDetails()` which checks for Name + Domicile + DUNS (all three together for non-Syndicate), but does not enforce "at least one of IRIS Code / DUNS / SEND Ref".

If all identifiers are missing but Name + Domicile are provided:
- The code enters assured creation with null DUNS
- Creates the entity in IRIS
- Post-creation DUNS re-lookup is skipped (guarded by a null check on DUNS)
- No IRIS code is resolved → likely downstream failure

**Impact**: Requests with insufficient identifiers are not rejected early, leading to unnecessary IRIS calls and confusing error states.

**Recommendation**: Add explicit validation at the handler level:
```
if (string.IsNullOrWhiteSpace(irisCode)
    && string.IsNullOrWhiteSpace(duns)
    && string.IsNullOrWhiteSpace(sendReference))
{
    return Result.Failure("At least one identifier (IRIS Code, DUNS, or SEND Reference) is required");
}
```

---

#### GAP 3 — Renewal Handler Does Not Create New Assureds (MEDIUM)

**Documented Process**: Rules 2 and 3 state "Not Found → Create new insured" — no distinction between skeleton and renewal.

**Actual Implementation**: `CreateRenewalQueryHandler` only performs DUNS lookups. If the lookup fails, there is no fallback to create a new assured entity. Several tests in the renewal handler test file are commented out with TODO notes about "assured creation not triggering."

**Impact**: Renewal requests for policies where the assured is not yet in IRIS will fail, requiring manual intervention or a skeleton creation first.

**Recommendation**: Either implement assured creation in the renewal flow (matching skeleton behaviour) or explicitly document this as a known limitation with a clear error message.

---

#### GAP 4 — Renewal vs Skeleton SOAP Payload Format Mismatch (MEDIUM)

**Skeleton handler** (`AssuredCreationService.BuildLookupPayload`): Sends a JSON array:
```json
[duns, companiesHouse, sendReference, companyType]
```

**Renewal handler** (`RenewPolicyQueryHandler`): Sends a JSON dictionary:
```json
{"CODUNS": duns, "CODOMC": domicile, "CONAME": name, "COSERE": sendRef}
```

These produce entirely different SOAP XML structures. If the IRIS backend expects a consistent format, one of these may not work correctly.

**Recommendation**: Verify with the IRIS team which format is correct and align both handlers.

---

#### GAP 5 — Post-Creation IRIS Code Retrieval Depends on DUNS (LOW)

After creating a new assured, the code re-lookups by DUNS to retrieve the newly created IRIS code. If the assured was created without a DUNS (e.g., only Name + Domicile), the re-lookup is skipped, and no IRIS code is returned.

**Impact**: Assured entities created without DUNS will not have their IRIS codes resolved automatically.

**Recommendation**: Consider using the IRIS job completion response to extract the new IRIS code directly, rather than relying on a secondary DUNS lookup.

---

## 5. Validation Rules Summary

| Target | Host | Required for Valid Details |
|--------|------|--------------------------|
| Reinsured | Any | (Name + Domicile + DUNS) OR IRISCode |
| Insured | Syndicate | Name OR Domicile (relaxed) |
| Insured | Non-Syndicate | (Name + Domicile + DUNS) OR IRISCode |

**Note**: SEND Reference is not part of the "valid details" check — it is only used opportunistically during DUNS lookups.

---

## 6. SEND Reference Handling Detail

The SEND Reference field is mapped to `SandPRating` in the assured creation payload:
```json
"Assured": {
    "SandPRating": "SandPRating"  // ← stores SEND Reference
}
```

This field-repurposing (SEND Reference stored in `SandPRating`) is a non-obvious mapping that could confuse maintainers. It should be clearly documented in the field mapping documentation.

---

## 7. Recommendations Summary

| # | Priority | Recommendation |
|---|----------|----------------|
| 1 | HIGH | Implement standalone SEND Reference lookup when DUNS is absent (Rule 3) |
| 2 | HIGH | Add upfront validation requiring at least one identifier (Rule 4) |
| 3 | MEDIUM | Align renewal handler with skeleton handler for assured creation |
| 4 | MEDIUM | Verify and align SOAP payload formats between skeleton and renewal handlers |
| 5 | LOW | Improve post-creation IRIS code retrieval to not depend solely on DUNS |
| 6 | LOW | Document the SEND Reference → SandPRating field mapping explicitly |

---

## 8. Flow Diagram (Current Implementation)

```
Request Arrives
│
├── InsuredName > 40 chars? → Truncate
├── Determine isSyndicateHost
├── Apply CompanyType Rules (A or C)
│
├── BOTH IRIS codes provided?
│     └── YES → Trim, skip all lookups ✓ (Rule 1)
│
├── EITHER IRIS code provided?
│     └── YES → Trim provided one; lookup missing one if valid details exist
│
└── NEITHER provided?
      ├── Syndicate + insured-only? → Skip lookup, pass InsuredName only ✓ (Exception)
      └── Otherwise → AssuredCreationService:
            ├── Phase 1: DUNS lookup via SEND_GetAssuredByRef ✓ (Rule 2)
            │     ├── Found → Use IRIS code ✓
            │     └── Not Found → Phase 2
            │
            ├── Phase 2: Create assured via CreateAssured SOAP ✓ (Rule 2)
            │     └── Re-lookup by DUNS for new IRIS code
            │
            └── ✗ MISSING: Standalone SEND Reference lookup (Rule 3)
                  No fallback to SEND Ref when DUNS is absent
```

---

## 9. Proposed Code Changes

### Change 1: SEND Reference Standalone Lookup (GAP 1 — HIGH)

**File**: [PolicyConnectorService/Handlers/Queries/CreateSkeletonQueryHandler.cs](PolicyConnectorService/Handlers/Queries/CreateSkeletonQueryHandler.cs)

**Problem**: In `BuildIrisLookupPayload` (line ~517), SEND Reference is only populated when DUNS is present due to the guard condition `!string.IsNullOrWhiteSpace(request.InsuredDUNS)`. When DUNS is absent, SEND Reference is never sent to IRIS for lookup.

**Current code** (lines 517–528):
```csharp
string? sendReference = null;

if (target == IrisLookupTarget.Insured && !string.IsNullOrWhiteSpace(request.InsuredDUNS))
{
    sendReference = string.IsNullOrWhiteSpace(request.InsuredSendReference)
        ? sendReference
        : request.InsuredSendReference;
}
else if (target == IrisLookupTarget.Reinsured && !string.IsNullOrWhiteSpace(request.ReinsuredDUNS))
{
    sendReference = string.IsNullOrWhiteSpace(request.ReinsuredSendReference)
        ? sendReference
        : request.ReinsuredSendReference;
}
```

**Proposed change** — remove the DUNS guard so SEND Reference is always populated:
```csharp
string? sendReference = null;

if (target == IrisLookupTarget.Insured)
{
    sendReference = string.IsNullOrWhiteSpace(request.InsuredSendReference)
        ? sendReference
        : request.InsuredSendReference;
}
else if (target == IrisLookupTarget.Reinsured)
{
    sendReference = string.IsNullOrWhiteSpace(request.ReinsuredSendReference)
        ? sendReference
        : request.ReinsuredSendReference;
}
```

Additionally, the DUNS lookup loop (lines 286–303) currently skips lookups when DUNS is absent. It should also attempt lookup when SEND Reference is present:

**Current code** (lines 288–292):
```csharp
if (string.IsNullOrWhiteSpace(lookup.Duns))
{
    pendingLookups.Add(lookup);
    continue;
}
```

**Proposed change** — allow lookup when SEND Reference exists even without DUNS:
```csharp
var hasSendRef = lookup.Target == IrisLookupTarget.Insured
    ? !string.IsNullOrWhiteSpace(request.InsuredSendReference)
    : !string.IsNullOrWhiteSpace(request.ReinsuredSendReference);

if (string.IsNullOrWhiteSpace(lookup.Duns) && !hasSendRef)
{
    pendingLookups.Add(lookup);
    continue;
}
```

**Tests needed**: `CreateSkeletonQueryHandlerTests.cs`
- `Handle_NoDuns_WithSendReference_PerformsLookup`
- `Handle_NoDuns_WithSendReference_Found_UsesIrisCode`
- `Handle_NoDuns_WithSendReference_NotFound_CreatesAssured`

---

### Change 2: Upfront Identifier Validation (GAP 2 — HIGH)

**File**: [PolicyConnectorService/Handlers/Queries/CreateSkeletonQueryHandler.cs](PolicyConnectorService/Handlers/Queries/CreateSkeletonQueryHandler.cs)

**Add after line 74** (after `SkeletonModel reqObj = request.Policy;`):
```csharp
// Validate at least one identifier is present for insured
if (string.IsNullOrWhiteSpace(reqObj.InsuredIRISCode)
    && string.IsNullOrWhiteSpace(reqObj.InsuredDUNS)
    && string.IsNullOrWhiteSpace(reqObj.InsuredSendReference)
    && string.IsNullOrWhiteSpace(reqObj.InsuredName))
{
    _logger.LogWarning("{Handler} failed: No insured identifier provided (IRIS Code, DUNS, SEND Reference, or Name).",
        nameof(CreateSkeletonQueryHandler));
    return Result.Failure<SkeletonResult?>("At least one insured identifier (IRIS Code, DUNS Number, or SEND Reference) is required.", 400);
}
```

**File**: [PolicyConnectorService/Handlers/Queries/RenewPolicyQueryHandler.cs](PolicyConnectorService/Handlers/Queries/RenewPolicyQueryHandler.cs)

**Add after line 70** (after `RenewModel reqObj = request.RenewPolicy;`):
```csharp
// Validate at least one identifier is present for insured
if (string.IsNullOrWhiteSpace(reqObj.InsuredIRISCode)
    && string.IsNullOrWhiteSpace(reqObj.InsuredDUNS)
    && string.IsNullOrWhiteSpace(reqObj.InsuredSendReference)
    && string.IsNullOrWhiteSpace(reqObj.InsuredName))
{
    _logger.LogWarning("{Handler} failed: No insured identifier provided (IRIS Code, DUNS, SEND Reference, or Name).",
        nameof(RenewPolicyQueryHandler));
    return Result.Failure<GetStatusResult?>("At least one insured identifier (IRIS Code, DUNS Number, or SEND Reference) is required.", 400);
}
```

**Tests needed**: Both handler test files
- `Handle_NoIdentifiersProvided_Returns400`
- `Handle_OnlyInsuredName_Proceeds`
- `Handle_OnlyDuns_Proceeds`
- `Handle_OnlySendReference_Proceeds`

---

### Change 3: Renewal Handler Assured Creation Fallback (GAP 3 — MEDIUM)

**File**: [PolicyConnectorService/Handlers/Queries/RenewPolicyQueryHandler.cs](PolicyConnectorService/Handlers/Queries/RenewPolicyQueryHandler.cs)

The `CreateAssuredAsync` method (line ~275) only does a DUNS lookup via `GetIRISCodeAsync`. If the lookup returns null, it should fall back to creating a new assured (matching the skeleton handler behaviour).

**Current code** (lines 302–310):
```csharp
string? insuredCode = null;
string? reinsuredCode = null;

if (!string.IsNullOrWhiteSpace(insuredPayload))
{
    insuredCode = await GetIRISCodeAsync(insuredPayload, host);
}

if (!string.IsNullOrWhiteSpace(reinsuredPayload))
{
    reinsuredCode = await GetIRISCodeAsync(reinsuredPayload, host);
}

return (insuredCode, reinsuredCode);
```

**Proposed change** — add assured creation when lookup fails:
```csharp
string? insuredCode = null;
string? reinsuredCode = null;

if (!string.IsNullOrWhiteSpace(insuredPayload))
{
    insuredCode = await GetIRISCodeAsync(insuredPayload, host);
}

if (!string.IsNullOrWhiteSpace(reinsuredPayload))
{
    reinsuredCode = await GetIRISCodeAsync(reinsuredPayload, host);
}

// Fallback: Create assured in IRIS if lookup failed
if (string.IsNullOrWhiteSpace(insuredCode) && HasValidAssuredDetails(request, IrisLookupTarget.Insured, isSyndicateHost))
{
    insuredCode = await CreateAndLookupAssuredAsync(request, host, IrisLookupTarget.Insured, isSyndicateHost);
}

if (string.IsNullOrWhiteSpace(reinsuredCode) && HasValidAssuredDetails(request, IrisLookupTarget.Reinsured, isSyndicateHost))
{
    reinsuredCode = await CreateAndLookupAssuredAsync(request, host, IrisLookupTarget.Reinsured, isSyndicateHost);
}

return (insuredCode, reinsuredCode);
```

**New private method** to add in the same file:
```csharp
private async Task<string?> CreateAndLookupAssuredAsync(
    RenewModel request, string? host, IrisLookupTarget target, bool isSyndicateHost)
{
    try
    {
        bool isReinsured = target == IrisLookupTarget.Reinsured;
        var assuredEntry = new AssuredModel
        {
            InsuredName = isReinsured ? request.ReinsuredName : request.InsuredName,
            Domicile = isReinsured ? request.ReinsuredDomicile : request.InsuredDomicile,
            DUNS = isReinsured ? request.ReinsuredDUNS : request.InsuredDUNS,
            CompanyStatus = "A",
            InsuredReinsured = isReinsured ? "C" : "A",
            SandPRating = isReinsured ? request.ReinsuredSendReference : request.InsuredSendReference,
            CompaniesHouse = request.CompaniesHouse
        };

        var soapReq = _fieldMappingService.MapFields("Assured", assuredEntry, null);
        var assuredPayload = JsonConvert.SerializeObject(soapReq);
        var assuredSoapXml = SoapXmlUtility.ConvertJsonToSoapXml(assuredPayload, _assuredName, _assuredNameType);
        var jobId = await _soapService.ProcessMessageAsync(assuredSoapXml, host);

        // Poll for completion
        var (statusResult, _) = await CommonHelper.PollStatusAsync(jobId, host, _soapService, _logger);

        if (statusResult?.Status == IRISRequestStatuses.Completed)
        {
            // Re-lookup by DUNS to get the new IRIS code
            var duns = isReinsured ? request.ReinsuredDUNS : request.InsuredDUNS;
            if (!string.IsNullOrWhiteSpace(duns))
            {
                var lookupPayload = BuildIrisLookupPayload(request, duns, target, isSyndicateHost);
                return await GetIRISCodeAsync(lookupPayload, host);
            }
        }

        return null;
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "{Handler} Failed to create assured for {Target}.",
            nameof(RenewPolicyQueryHandler), target);
        return null;
    }
}
```

**Note**: This requires adding DI dependencies for `_fieldMappingService`, `_assuredName`, and `_assuredNameType` config values to `RenewPolicyQueryHandler`, matching what `CreateSkeletonQueryHandler` already has. Also requires the `AssuredModel` and `SoapXmlUtility` imports.

**Tests needed**: `RenewPolicyQueryHandlerTests.cs`
- `Handle_DunsLookupFails_CreatesAssuredAndRetries`
- `Handle_AssuredCreationFails_ReturnsNull`

---

### Change 4: Align Renewal Lookup Payload Format (GAP 4 — MEDIUM)

**File**: [PolicyConnectorService/Handlers/Queries/RenewPolicyQueryHandler.cs](PolicyConnectorService/Handlers/Queries/RenewPolicyQueryHandler.cs)

The `BuildIrisLookupPayload` method (line ~324) uses a dictionary format, but `GetIRISCodeAsync` calls the **lookup** SOAP action which expects the array format (same as the skeleton handler).

**Current code** (lines 324–355):
```csharp
private static string BuildIrisLookupPayload(RenewModel request, string? duns, IrisLookupTarget target, bool isSyndicateHost)
{
    var payload = new Dictionary<string, string?>();

    if (target == IrisLookupTarget.Insured)
    {
        payload["CODUNS"] = duns;
        payload["CODOMC"] = request.InsuredDomicile;
        payload["CONAME"] = request.InsuredName;
        payload["COSERE"] = request.InsuredSendReference;
        if (!isSyndicateHost)
        {
            payload["COMHNO"] = request.CompaniesHouse;
        }
    }
    else // Reinsured
    {
        payload["CODUNS"] = duns;
        payload["CODOMC"] = request.ReinsuredDomicile;
        payload["CONAME"] = request.ReinsuredName;
        payload["COSERE"] = request.ReinsuredSendReference;
    }

    return JsonConvert.SerializeObject(payload);
}
```

**Proposed change** — align with skeleton handler's array format:
```csharp
private static string BuildIrisLookupPayload(RenewModel request, string? duns, IrisLookupTarget target, bool isSyndicateHost)
{
    var companyTypeForLookup = isSyndicateHost
        ? "C"
        : target == IrisLookupTarget.Reinsured
            ? "C"
            : "A";

    string? sendReference = null;

    if (target == IrisLookupTarget.Insured)
    {
        sendReference = string.IsNullOrWhiteSpace(request.InsuredSendReference)
            ? null
            : request.InsuredSendReference;
    }
    else if (target == IrisLookupTarget.Reinsured)
    {
        sendReference = string.IsNullOrWhiteSpace(request.ReinsuredSendReference)
            ? null
            : request.ReinsuredSendReference;
    }

    var irisRequest = new[] { duns, request.CompaniesHouse, sendReference, companyTypeForLookup };
    return JsonConvert.SerializeObject(irisRequest);
}
```

**Tests needed**: `RenewPolicyQueryHandlerTests.cs`
- `BuildIrisLookupPayload_ProducesArrayFormat`
- `BuildIrisLookupPayload_IncludesSendReference`

---

## 10. Implementation Order

Changes should be implemented in this order to minimise risk:

| Step | Change | Risk | Effort |
|------|--------|------|--------|
| 1 | **Change 4**: Fix renewal payload format | LOW — aligns with proven skeleton format | Small |
| 2 | **Change 2**: Add identifier validation | LOW — early rejection, no logic change | Small |
| 3 | **Change 1**: SEND Ref standalone lookup | MEDIUM — new lookup path | Medium |
| 4 | **Change 3**: Renewal assured creation | MEDIUM — new creation path, needs DI changes | Medium-Large |

**Estimated total effort**: 2–3 days including tests and QA validation.

---

*This analysis should be reviewed by the development team and validated against IRIS backend documentation before any changes are implemented.*
