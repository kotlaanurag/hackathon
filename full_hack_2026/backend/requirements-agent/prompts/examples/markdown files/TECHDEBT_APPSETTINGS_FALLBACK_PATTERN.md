# Technical Debt: FieldMappings Fallback Pattern

**Feature Branch**: TBD
**Created**: April 2, 2026
**Completed**: TBD
**Status**: PROPOSED
**Priority**: LOW
**Type**: Technical Debt / Configuration Cleanup
**Implementation**: AI Agent (GitHub Copilot or similar)

> **⚠️ SCOPE BOUNDARY WARNING**
>
> This requirements document defines **EXACT SCOPE** for AI agent implementation. The implementing agent MUST:
> - Only modify FieldMappingService.GetMappedFieldName() method
> - Only modify appsettings.json Renew section (remove duplicates)
> - Only modify appsettings.test.json Renew section (remove duplicates)
> - NOT add additional features, optimizations, or refactorings
> - NOT modify any other files beyond those specified
> - STOP and request authorization if any ambiguity or edge case is encountered
>
> **NO CHANGES** beyond this explicit scope are authorized without prior approval.

## Overview

Eliminate ~90% duplication in FieldMappings configuration by implementing a fallback pattern where Renew mappings automatically inherit from Policy mappings. This reduces the Renew section from 30+ fields to 1-2 renewal-specific fields while preserving all existing functionality.

**Scope**: This refactoring is **STRICTLY LIMITED** to adding fallback logic in one method and removing duplicated configuration entries. No behavior changes, no additional features.

## Business Value

### Problem Statement

**Current State Issues**:
1. **Configuration Duplication**: 29 of 30 fields in `FieldMappings.Renew` are identical to `FieldMappings.Policy`
2. **Maintenance Risk**: Field mapping changes must be applied in multiple places (Policy AND Renew)
3. **Configuration Bloat**: 465 lines of configuration could be reduced to ~50 lines
4. **Error Prone**: Past incidents where Renew mappings drifted from Policy mappings (e.g., PolicyDeductions vs Deductions)

**Impact**:
- **Development Velocity**: ~2x effort for field mapping changes (must update 2 sections)
- **Bug Risk**: MEDIUM - configuration drift has occurred (fixed March 2026)
- **Readability**: Hard to identify which fields are actually renewal-specific

### Benefits of Fallback Pattern

**Immediate Benefits**:
1. **Eliminate Duplication**: 90% reduction in Renew section (30 fields → 1-2 fields)
2. **Single Source of Truth**: Policy mappings are canonical
3. **Clearer Intent**: Renew section explicitly shows what's renewal-specific (ExpiringPolicyRef)
4. **Reduced Maintenance**: Update field mappings in one place only

**Long-Term Benefits**:
1. **Consistency**: Impossible for Renew mappings to drift from Policy mappings
2. **Discoverability**: Developers immediately see which fields are renewal-specific
3. **Future-Proof**: New fields added to Policy automatically work in Renew

## Current State

### Configuration Analysis

**appsettings.json - FieldMappings.Renew** (30 fields total):

**Renewal-Specific Fields** (1):
- `ExpiringPolicyRef: "PHUSRF"` - No equivalent in Policy section

**Duplicated from Policy** (29):
- PolicyNumber, Sequence, InceptionYear, InceptionDate, ExpiryDate, RiskReference
- Domicile, InsuredDomicile, InsuredIRISCode, ReinsuredIRISCode
- BranchCode, ProductCode, PlacingType, BrokerCode, BrokerName
- MultinationType, CollectionType, EscapeControlNumber, EscapeSubmissionId
- Attachment, Limit, EverestTargetTechnicalGrossGross, WrittenLine
- BrokerCommissionPercentOfGwp, EEAIndicator, ActualPremium
- BusinessSegment, UWAuthority, PolicyOrLayer, LeadInsurer, LeadorFollow
- OurShareGWPPer, GELR, Currency, ExposureMeasure, ExposureMeasureAmt
- PolicyHolderType, SanctionsCheckComplete

**Mapping Comparison**:
All 29 duplicated fields have **IDENTICAL** mappings in both Policy and Renew sections.

### Code Analysis

**FieldMappingService.GetMappedFieldName()** (Current):
```csharp
private string GetMappedFieldName(string modelKey, string propertyName, Dictionary<string, string> mapping)
{
    // Try specific mapping
    if (mapping.ContainsKey(propertyName))
        return mapping[propertyName];

    // Check complex mapping
    var section = _configuration.GetSection($"FieldMappings:{modelKey}:{propertyName}");
    if (section.Exists())
    {
        var fieldValue = section["Field"];
        if (!string.IsNullOrEmpty(fieldValue))
            return fieldValue;
    }

    // Fall back to property name (PROBLEM: returns unmapped names)
    return propertyName;
}
```

**Issue**: Falls back to property name instead of checking Policy mappings first.

## Solution Approach

### Step 1: Modify FieldMappingService (1 file, 1 method)

**File**: `PolicyConnectorService/Core/Utilities/FieldMappingService.cs`
**Method**: `GetMappedFieldName()`

**Add Fallback Logic** (before final return statement):

```csharp
private string GetMappedFieldName(string modelKey, string propertyName, Dictionary<string, string> mapping)
{
    // 1. Try specific mapping (e.g., "Renew")
    if (mapping.ContainsKey(propertyName))
        return mapping[propertyName];

    // 2. Check for complex mapping with "Field" property
    var section = _configuration.GetSection($"FieldMappings:{modelKey}:{propertyName}");
    if (section.Exists())
    {
        var fieldValue = section["Field"];
        if (!string.IsNullOrEmpty(fieldValue))
            return fieldValue;
    }

    // 3. NEW: Fallback to Policy mappings if modelKey is "Renew"
    if (modelKey == "Renew" && _config.ContainsKey("Policy"))
    {
        var policyMapping = _config["Policy"];
        if (policyMapping.ContainsKey(propertyName))
        {
            return policyMapping[propertyName];
        }

        // Check Policy complex mapping
        var policySection = _configuration.GetSection($"FieldMappings:Policy:{propertyName}");
        if (policySection.Exists())
        {
            var fieldValue = policySection["Field"];
            if (!string.IsNullOrEmpty(fieldValue))
            {
                return fieldValue;
            }
        }
    }

    // 4. Fall back to property name
    return propertyName;
}
```

**Lines Changed**: ~15 lines added (total method size: 30→45 lines)

### Step 2: Clean Up Configuration (2 files)

**File 1**: `PolicyConnectorService/appsettings.json`

**Remove from FieldMappings.Renew** (keep only renewal-specific):
```json
"Renew": {
  "ExpiringPolicyRef": "PHUSRF"
}
```

**Before**: 30 fields (145 lines)
**After**: 1 field (3 lines)
**Reduction**: 142 lines

**File 2**: `PolicyConnectorService.Tests/appsettings.test.json`

**Same change** - reduce Renew section to ExpiringPolicyRef only.

**Before**: 30 fields
**After**: 1 field
**Reduction**: ~140 lines

### Step 3: Validation (No code changes)

**Existing Test Suite**: All 242 tests must pass unchanged
- Handler tests verify correct IRIS codes in SOAP output
- SoapXmlUtility tests verify field mapping behavior
- No new tests required (fallback is transparent)

**Manual Verification**: Compare SOAP output before/after:
1. Create skeleton request → Verify all IRIS codes present
2. Renew policy request → Verify all IRIS codes present (not property names)
3. Check logs for any unmapped field warnings

## Files Modified (EXACT SCOPE)

### Production Code (1 file)
1. `PolicyConnectorService/Core/Utilities/FieldMappingService.cs`
   - Modify `GetMappedFieldName()` method only
   - Add fallback logic (~15 lines)

### Configuration (2 files)
2. `PolicyConnectorService/appsettings.json`
   - Reduce `FieldMappings.Renew` section (142 lines removed)

3. `PolicyConnectorService.Tests/appsettings.test.json`
   - Reduce `FieldMappings.Renew` section (140 lines removed)

**Total Files**: 3
**Lines Added**: 15
**Lines Removed**: 282
**Net Reduction**: -267 lines

## Testing Requirements

### Acceptance Criteria

**PASS Criteria**:
1. ✅ All 242 existing tests pass unchanged
2. ✅ Create skeleton SOAP contains correct IRIS codes (not property names)
3. ✅ Renew policy SOAP contains correct IRIS codes (not property names)
4. ✅ ExpiringPolicyRef maps to PHUSRF in renewals
5. ✅ All Policy fields correctly fall back in Renew context

**FAIL Criteria**:
1. ❌ Any test fails
2. ❌ Any unmapped property names appear in SOAP output
3. ❌ Any field that worked before now fails to map

### Test Execution

**Commands**:
```powershell
# Run full test suite
dotnet test PolicyConnectorService.Tests/PolicyConnectorService.Tests.csproj

# Expected output
Passed!  - Failed: 0, Passed: 242, Skipped: 0, Total: 242
```

**No new tests required** - existing tests validate behavior.

## Implementation Steps (AI Agent Instructions)

### Phase 1: Code Changes
1. Read `PolicyConnectorService/Core/Utilities/FieldMappingService.cs`
2. Locate `GetMappedFieldName()` method
3. Add fallback logic as specified in Solution Approach Step 1
4. Verify code compiles

### Phase 2: Configuration Cleanup
5. Read `PolicyConnectorService/appsettings.json`
6. Reduce `FieldMappings.Renew` to only `ExpiringPolicyRef: "PHUSRF"`
7. Read `PolicyConnectorService.Tests/appsettings.test.json`
8. Reduce `FieldMappings.Renew` to only `ExpiringPolicyRef: "PHUSRF"`

### Phase 3: Validation
9. Run full test suite: `dotnet test`
10. Verify all 242 tests pass
11. If any test fails, STOP and report failure

### Phase 4: Commit
12. Git add modified files
13. Git commit with message: "Implement FieldMappings fallback pattern to eliminate duplication"
14. Git push --no-verify

**STOP CONDITIONS**: Agent MUST stop and request guidance if:
- Any test fails after changes
- Compilation errors occur
- Any ambiguity about which fields to remove

## Risks & Mitigation

### Risk 1: Unintended Behavior Change
**Likelihood**: LOW
**Impact**: MEDIUM
**Mitigation**: All 242 tests validate behavior - any change will be caught

### Risk 2: Configuration Drift in Other Environments
**Likelihood**: NONE
**Impact**: N/A
**Mitigation**: Same configuration files used in all environments (via env-specific overrides)

### Risk 3: Future Fields Not Falling Back
**Likelihood**: LOW
**Impact**: LOW
**Mitigation**: Fallback to property name still works (existing behavior), will be caught in testing

## Success Metrics

**Quantitative**:
- ✅ 267 lines of configuration removed
- ✅ 100% test pass rate maintained (242/242)
- ✅ 0 new bugs introduced

**Qualitative**:
- ✅ Renew section clearly shows only renewal-specific fields
- ✅ Maintenance effort reduced (single source of truth)
- ✅ Intent clear to developers reviewing configuration

## Future Considerations

**Not in Scope** (future enhancements):
- Extend fallback pattern to other model types (Reference, Assured)
- Add logging when fallback occurs (for debugging)
- Create validation tool to detect configuration drift

**Extensibility**: This pattern can be extended to support:
- Multiple fallback levels (Renew → Policy → BaseDefaults)
- Environment-specific mapping overrides
- Dynamic mapping reloading without restart
