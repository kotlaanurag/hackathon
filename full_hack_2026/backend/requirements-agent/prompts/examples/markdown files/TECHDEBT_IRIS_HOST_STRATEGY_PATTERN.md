# Technical Debt: IRIS Host Strategy Pattern Refactoring

**Feature Branch**: TBD
**Created**: March 30, 2026
**Completed**: TBD
**Status**: PROPOSED
**Priority**: MEDIUM
**Type**: Technical Debt / Architecture Improvement
**Implementation**: AI Agent (GitHub Copilot or similar)

> **⚠️ SCOPE BOUNDARY WARNING**
>
> This requirements document defines **EXACT SCOPE** for AI agent implementation. The implementing agent MUST:
> - Only create/modify the 7 files explicitly listed in this document
> - Only make changes described in the Solution Approach section
> - NOT add additional features, optimizations, or refactorings
> - NOT modify any other files beyond those specified
> - STOP and request authorization if any ambiguity or edge case is encountered
>
> **NO CHANGES** beyond this explicit scope are authorized without prior approval.

## Overview

Refactor duplicated IRISHost-specific logic from handler classes into a Strategy Pattern implementation. This eliminates ~241 lines of code duplication between CreateSkeletonQueryHandler and RenewPolicyQueryHandler, improves testability, and establishes a maintainable architecture for host-specific behavioral variants.

**Scope**: This refactoring is **STRICTLY LIMITED** to extracting existing IRISHost logic into Strategy Pattern classes. No additional features, no behavior changes, no optimizations beyond what is explicitly documented in this requirements file.

## Business Value

### Problem Statement

**Current State Issues**:
1. **Code Duplication**: ~241 lines of identical host-detection and assured-handling logic duplicated across 2 handlers
2. **Low Testability**: Private static methods cannot be unit tested in isolation
3. **Maintenance Risk**: Changes to host logic must be applied in multiple places (2+ locations)
4. **Poor Extensibility**: Adding a new IRIS host (e.g., "Asia Pacific") requires editing multiple handler files
5. **Handler Bloat**: CreateSkeletonQueryHandler is 605 lines, RenewPolicyQueryHandler is 386 lines - handlers mix orchestration with business rules

**Impact**:
- **Development Velocity**: ~2x effort for any host-logic changes (must update 2 files)
- **Bug Risk**: HIGH - logic drift between handlers has occurred (fixed in past PRs)
- **Test Coverage**: Cannot directly test private methods, reducing coverage confidence
- **Onboarding**: New developers must understand scattered logic across multiple files

### Benefits of Strategy Pattern

**Immediate Benefits**:
1. **Eliminate Duplication**: Single source of truth for all host-specific logic
2. **Improve Testability**: Strategy classes are public, easily unit tested in isolation
3. **Reduce Handler Size**: CreateSkeletonQueryHandler: 605→450 lines (-25%), RenewPolicyQueryHandler: 386→300 lines (-22%)
4. **Enable Future Growth**: Adding new hosts requires only creating a new strategy class

**Long-Term Benefits**:
1. **Maintainability**: All Syndicate behavior in one file, easy to understand and modify
2. **Quality**: Direct unit tests for strategies reduce regression risk
3. **Compliance**: Easier to audit host-specific compliance rules (e.g., GDPR, data residency)
4. **Documentation**: Strategy classes serve as living documentation of host differences

## Current State

### Duplicated Code Analysis

**Duplicated Methods** (identical across CreateSkeletonQueryHandler and RenewPolicyQueryHandler):

1. **`IsSyndicateHost(string? host)`** - 3 lines
   - Determines if host is "Syndicate" (case-insensitive)
   - Used: 10+ times per handler

2. **`ApplyCompanyTypeRules(Model reqObj, bool isSyndicateHost)`** - ~28-36 lines
   - Sets CompanyType based on host and assured/reinsured data
   - **Syndicate**: Always `"C"` (Cedent)
   - **Non-Syndicate**: `"C"` if reinsured present, `"A"` if only insured

3. **`HasValidAssuredDetails(Model request, IrisLookupTarget target, bool isSyndicateHost)`** - ~22-26 lines
   - Validates if sufficient data exists for assured creation/lookup
   - **Syndicate Insured**: Requires Name OR Domicile (relaxed)
   - **Non-Syndicate Insured**: Requires Name AND Domicile AND DUNS (strict)
   - **All Reinsured**: Requires Name AND Domicile AND DUNS

4. **`BuildIrisLookupPayload(Model request, ...)`** - ~21-22 lines
   - Constructs IRIS lookup request payload
   - **Syndicate**: Uses CompanyType="C", omits CompaniesHouse
   - **Non-Syndicate**: Uses CompanyType="A" for insured, includes CompaniesHouse

**Additional Methods** (CreateSkeletonQueryHandler only):
5. **`BuildIrisLookupContexts()`** - 17 lines
6. **`ApplyLookupResult()`** - 10 lines
7. **`BuildAssuredEntry()`** - 20 lines

**Supporting Types**:
- `IrisLookupTarget` enum (duplicated)
- `IrisLookupContext` struct (CreateSkeleton only)
- `AssuredLookupOutcome` struct (CreateSkeleton only)

**Total Duplication**: ~155 lines in CreateSkeletonQueryHandler + ~86 lines in RenewPolicyQueryHandler = **241 lines**

### IRISHost Behavioral Variants

**Current IRIS Hosts**:
- **Ireland** (Primary) - Standard behavior
- **UK** - Standard behavior
- **Syndicate** - Special behavior (relaxed validation, different CompanyType rules)
- **Asia** - Standard behavior (future/potential)

**Syndicate-Specific Differences**:
1. **CompanyType**: Always `"C"`, regardless of data
2. **Insured Validation**: Only requires Name OR Domicile (no DUNS)
3. **Lookup Payload**: Omits `CompaniesHouse` field
4. **Lookup CompanyType**: Always `"C"` in payload
5. **InsuredName Field**: Not skipped from SOAP XML (other hosts skip it)
6. **Insured-Only Path**: Special fast-path when only insured details present

**Reference**: See [CreateSkeletonQueryHandler.cs](../../PolicyConnectorService/Handlers/Queries/CreateSkeletonQueryHandler.cs#L370-L605) and [RenewPolicyQueryHandler.cs](../../PolicyConnectorService/Handlers/Queries/RenewPolicyQueryHandler.cs#L217-L386) for current implementation.

## Solution Approach - Strategy Pattern

### Architecture Overview

**Pattern**: Strategy Pattern (Gang of Four behavioral pattern)
**Location**: `PolicyConnectorService/Services/HostStrategies/`
**Reasoning**: IRIS host type is a behavioral variant that affects multiple aspects of policy processing

### Component Design

#### 1. Strategy Interface

**File**: `Services/HostStrategies/IIRISHostStrategy.cs`

```csharp
public interface IIRISHostStrategy
{
    /// <summary>
    /// The IRIS host name this strategy handles (e.g., "Syndicate", "Ireland").
    /// </summary>
    string HostName { get; }

    /// <summary>
    /// Determines if this strategy handles the given host (case-insensitive).
    /// </summary>
    bool HandlesHost(string? host);

    /// <summary>
    /// Applies CompanyType rules based on host and assured/reinsured data.
    /// </summary>
    void ApplyCompanyTypeRules(PolicyDataModel model);

    /// <summary>
    /// Validates if sufficient assured details exist for IRIS lookup/creation.
    /// </summary>
    bool HasValidAssuredDetails(PolicyDataModel model, IrisLookupTarget target);

    /// <summary>
    /// Builds IRIS lookup payload for assured creation/lookup.
    /// </summary>
    string BuildAssuredLookupPayload(PolicyDataModel model, string? duns, IrisLookupTarget target);

    /// <summary>
    /// Determines if InsuredName should be included in SOAP payload.
    /// </summary>
    bool ShouldIncludeInsuredNameInSoap(PolicyDataModel model);

    /// <summary>
    /// Determines if this is a Syndicate insured-only scenario requiring special handling.
    /// </summary>
    bool IsSyndicateInsuredOnlyPath(PolicyDataModel model);
}

public enum IrisLookupTarget
{
    Insured,
    Reinsured
}
```

**Design Notes**:
- Interface defines all host-specific behavioral variation points
- Methods accept `PolicyDataModel` base class (shared by SkeletonModel and RenewModel)
- Stateless interface - strategies are singleton-scoped
- Clear XML doc comments for each method

#### 2. Syndicate Host Strategy

**File**: `Services/HostStrategies/SyndicateHostStrategy.cs`

```csharp
public class SyndicateHostStrategy : IIRISHostStrategy
{
    public string HostName => "Syndicate";

    public bool HandlesHost(string? host) =>
        !string.IsNullOrWhiteSpace(host) &&
        host.Equals("Syndicate", StringComparison.OrdinalIgnoreCase);

    public void ApplyCompanyTypeRules(PolicyDataModel model)
    {
        if (model == null) return;

        // Syndicate ALWAYS uses CompanyType "C" (Cedent/Reinsured)
        model.CompanyType = "C";
    }

    public bool HasValidAssuredDetails(PolicyDataModel model, IrisLookupTarget target)
    {
        if (model == null) return false;

        if (target == IrisLookupTarget.Reinsured)
        {
            // Reinsured: Same strict rules as standard hosts
            return (!string.IsNullOrWhiteSpace(model.ReinsuredName)
                && !string.IsNullOrWhiteSpace(model.ReinsuredDomicile)
                && !string.IsNullOrWhiteSpace(model.ReinsuredDUNS))
                || !string.IsNullOrEmpty(model.ReinsuredIRISCode);
        }

        // Insured: RELAXED rules - only Name OR Domicile required (no DUNS)
        return !string.IsNullOrWhiteSpace(model.InsuredName)
               || !string.IsNullOrWhiteSpace(model.InsuredDomicile);
    }

    public string BuildAssuredLookupPayload(PolicyDataModel model, string? duns, IrisLookupTarget target)
    {
        var payload = new Dictionary<string, string?>();

        if (target == IrisLookupTarget.Insured)
        {
            payload["CODUNS"] = duns;
            payload["CODOMC"] = model.InsuredDomicile;
            payload["CONAME"] = model.InsuredName;
            payload["COSERE"] = model.InsuredSendReference;
            // Syndicate: OMIT CompaniesHouse
        }
        else
        {
            payload["CODUNS"] = duns;
            payload["CODOMC"] = model.ReinsuredDomicile;
            payload["CONAME"] = model.ReinsuredName;
            payload["COSERE"] = model.ReinsuredSendReference;
        }

        return JsonConvert.SerializeObject(payload);
    }

    public bool ShouldIncludeInsuredNameInSoap(PolicyDataModel model) =>
        !string.IsNullOrWhiteSpace(model.InsuredName);

    public bool IsSyndicateInsuredOnlyPath(PolicyDataModel model)
    {
        // Special fast-path: Syndicate with insured-only details
        return HasValidAssuredDetails(model, IrisLookupTarget.Insured)
            && !HasValidAssuredDetails(model, IrisLookupTarget.Reinsured);
    }
}
```

**Implementation Notes**:
- All Syndicate-specific rules encapsulated in one class (~200 lines)
- Clear comments documenting why Syndicate is different
- Easy to understand "what makes Syndicate special?"
- No dependencies on other services (pure logic)

#### 3. Standard Host Strategy

**File**: `Services/HostStrategies/StandardHostStrategy.cs`

```csharp
public class StandardHostStrategy : IIRISHostStrategy
{
    private readonly string _hostName;

    public StandardHostStrategy(string hostName = "Standard")
    {
        _hostName = hostName;
    }

    public string HostName => _hostName;

    public bool HandlesHost(string? host)
    {
        // Handles Ireland, UK, Asia, and any non-Syndicate host
        if (string.IsNullOrWhiteSpace(host)) return false;
        return !host.Equals("Syndicate", StringComparison.OrdinalIgnoreCase);
    }

    public void ApplyCompanyTypeRules(PolicyDataModel model)
    {
        if (model == null) return;

        var insuredDataProvided = !string.IsNullOrWhiteSpace(model.InsuredDUNS)
            || !string.IsNullOrWhiteSpace(model.InsuredDomicile)
            || !string.IsNullOrWhiteSpace(model.InsuredName)
            || !string.IsNullOrWhiteSpace(model.InsuredIRISCode);

        var reinsuredDataProvided = !string.IsNullOrWhiteSpace(model.ReinsuredDUNS)
            || !string.IsNullOrWhiteSpace(model.ReinsuredDomicile)
            || !string.IsNullOrWhiteSpace(model.ReinsuredName)
            || !string.IsNullOrWhiteSpace(model.ReinsuredIRISCode);

        if (reinsuredDataProvided)
        {
            model.CompanyType = "C"; // Cedent
        }
        else if (insuredDataProvided)
        {
            model.CompanyType = "A"; // Assured
        }
        // Else remains null
    }

    public bool HasValidAssuredDetails(PolicyDataModel model, IrisLookupTarget target)
    {
        if (model == null) return false;

        if (target == IrisLookupTarget.Reinsured)
        {
            return (!string.IsNullOrWhiteSpace(model.ReinsuredName)
                && !string.IsNullOrWhiteSpace(model.ReinsuredDomicile)
                && !string.IsNullOrWhiteSpace(model.ReinsuredDUNS))
                || !string.IsNullOrEmpty(model.ReinsuredIRISCode);
        }

        // Insured: STRICT rules - Name AND Domicile AND DUNS required
        return (!string.IsNullOrWhiteSpace(model.InsuredName)
            && !string.IsNullOrWhiteSpace(model.InsuredDomicile)
            && !string.IsNullOrWhiteSpace(model.InsuredDUNS))
            || !string.IsNullOrEmpty(model.InsuredIRISCode);
    }

    public string BuildAssuredLookupPayload(PolicyDataModel model, string? duns, IrisLookupTarget target)
    {
        var companyTypeForLookup = target == IrisLookupTarget.Reinsured ? "C" : "A";

        var payload = new Dictionary<string, string?>();

        if (target == IrisLookupTarget.Insured)
        {
            payload["CODUNS"] = duns;
            payload["CODOMC"] = model.InsuredDomicile;
            payload["CONAME"] = model.InsuredName;
            payload["COSERE"] = model.InsuredSendReference;
            payload["COMHNO"] = model.CompaniesHouse; // Standard: INCLUDE CompaniesHouse
        }
        else
        {
            payload["CODUNS"] = duns;
            payload["CODOMC"] = model.ReinsuredDomicile;
            payload["CONAME"] = model.ReinsuredName;
            payload["COSERE"] = model.ReinsuredSendReference;
        }

        return JsonConvert.SerializeObject(payload);
    }

    public bool ShouldIncludeInsuredNameInSoap(PolicyDataModel model) => false;

    public bool IsSyndicateInsuredOnlyPath(PolicyDataModel model) => false;
}
```

**Implementation Notes**:
- Handles Ireland, UK, Asia, and any future non-Syndicate hosts
- Default/standard IRIS behavior
- Can be subclassed for host-specific customizations if needed in future

#### 4. Strategy Factory

**File**: `Services/HostStrategies/HostStrategyFactory.cs`

```csharp
public interface IHostStrategyFactory
{
    IIRISHostStrategy GetStrategy(string? host);
}

public class HostStrategyFactory : IHostStrategyFactory
{
    private readonly IEnumerable<IIRISHostStrategy> _strategies;
    private readonly ILogger<HostStrategyFactory> _logger;

    public HostStrategyFactory(
        IEnumerable<IIRISHostStrategy> strategies,
        ILogger<HostStrategyFactory> logger)
    {
        _strategies = strategies ?? throw new ArgumentNullException(nameof(strategies));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    public IIRISHostStrategy GetStrategy(string? host)
    {
        var strategy = _strategies.FirstOrDefault(s => s.HandlesHost(host));

        if (strategy == null)
        {
            _logger.LogWarning(
                "No specific strategy found for host '{Host}', using StandardHostStrategy",
                host ?? "null");
            return new StandardHostStrategy();
        }

        _logger.LogDebug("Selected {StrategyName} for host '{Host}'",
            strategy.GetType().Name, host);
        return strategy;
    }
}
```

**Implementation Notes**:
- Factory resolves strategy from DI container collection
- Falls back to StandardHostStrategy if no match found
- Logs strategy selection for observability

### Handler Refactoring

**CreateSkeletonQueryHandler Changes** (~155 lines removed):

**Before** (605 lines):
```csharp
var isSyndicateHost = IsSyndicateHost(host);
ApplyCompanyTypeRules(reqObj, isSyndicateHost);
if (HasValidAssuredDetails(reqObj, target, isSyndicateHost)) { ... }
var payload = BuildIrisLookupPayload(reqObj, duns, target, isSyndicateHost);

// + 8 private static methods (150+ lines)
```

**After** (450 lines):
```csharp
var strategy = _hostStrategyFactory.GetStrategy(host);
strategy.ApplyCompanyTypeRules(reqObj);
if (strategy.HasValidAssuredDetails(reqObj, target)) { ... }
var payload = strategy.BuildAssuredLookupPayload(reqObj, duns, target);

// No private methods - all in strategies
```

**RenewPolicyQueryHandler Changes** (~86 lines removed):

**Before** (386 lines):
```csharp
var isSyndicateHost = IsSyndicateHost(host);
ApplyCompanyTypeRules(reqObj, isSyndicateHost);
// + 4 private static methods (~80 lines)
```

**After** (300 lines):
```csharp
var strategy = _hostStrategyFactory.GetStrategy(host);
strategy.ApplyCompanyTypeRules(reqObj);
// No private methods
```

### Dependency Injection Registration

**File**: `PolicyConnectorService/Program.cs`

```csharp
// Register strategies
builder.Services.AddSingleton<IIRISHostStrategy, SyndicateHostStrategy>();
builder.Services.AddSingleton<IIRISHostStrategy, StandardHostStrategy>();

// Register factory
builder.Services.AddSingleton<IHostStrategyFactory, HostStrategyFactory>();
```

**Design Notes**:
- Strategies are **singleton** - stateless, thread-safe, reusable
- Factory is **singleton** - no per-request overhead
- DI automatically injects `IEnumerable<IIRISHostStrategy>` into factory

## Testing Strategy

### Existing Handler Tests

**Status**: ✅ **NO CHANGES REQUIRED**

**Why**:
- Handler tests call `_handler.Handle(query, token)` - external behavior unchanged
- Mock setup unchanged (`_mockSoapService`, etc.)
- Strategies are internal dependencies
- All existing tests pass without modification

**Example** (unchanged):
```csharp
[Fact]
public async Task Handle_SyndicateHost_UsesReinsuredDuns()
{
    var query = new CreateSkeletonQuery
    {
        Policy = new SkeletonModel { IRISHost = "Syndicate", ... }
    };

    var result = await _handler.Handle(query, CancellationToken.None);

    Assert.True(result.IsSuccess);
    // Test still passes - behavior identical
}
```

### New Strategy Tests

**Files to Create**:

1. **`Services.Tests/HostStrategies/SyndicateHostStrategyTests.cs`** (~150 lines)
   - `HandlesHost_SyndicateInput_ReturnsTrue()`
   - `ApplyCompanyTypeRules_AlwaysSetsTypeC()`
   - `HasValidAssuredDetails_Insured_OnlyRequiresNameOrDomicile()`
   - `HasValidAssuredDetails_Reinsured_RequiresNameDomicileDuns()`
   - `BuildAssuredLookupPayload_OmitsCompaniesHouse()`
   - `ShouldIncludeInsuredNameInSoap_WithName_ReturnsTrue()`
   - `IsSyndicateInsuredOnlyPath_InsuredOnlyDetails_ReturnsTrue()`
   - ~15-20 test methods covering all edge cases

2. **`Services.Tests/HostStrategies/StandardHostStrategyTests.cs`** (~150 lines)
   - `HandlesHost_IrelandInput_ReturnsTrue()`
   - `HandlesHost_SyndicateInput_ReturnsFalse()`
   - `ApplyCompanyTypeRules_ReinsuredData_SetsTypeC()`
   - `ApplyCompanyTypeRules_InsuredOnly_SetsTypeA()`
   - `HasValidAssuredDetails_Insured_RequiresNameDomicileDuns()`
   - `BuildAssuredLookupPayload_IncludesCompaniesHouse()`
   - `ShouldIncludeInsuredNameInSoap_ReturnsFalse()`
   - ~15-20 test methods covering all edge cases

3. **`Services.Tests/HostStrategies/HostStrategyFactoryTests.cs`** (~50 lines)
   - `GetStrategy_SyndicateHost_ReturnsSyndicateStrategy()`
   - `GetStrategy_IrelandHost_ReturnsStandardStrategy()`
   - `GetStrategy_NullHost_ReturnsStandardStrategy()`
   - `GetStrategy_UnknownHost_ReturnsStandardStrategy_LogsWarning()`
   - ~5-8 test methods

**Total New Tests**: ~350 lines across 3 files

**Benefits of Strategy Tests**:
- Test private logic that was previously untestable
- Faster execution (no handler/MediatR setup overhead)
- Better edge case coverage
- Clear documentation of strategy behavior
- Easier to debug failures

## Acceptance Criteria

> **CRITICAL**: All criteria below must be met. If ANY criterion cannot be satisfied within the defined scope, STOP implementation and request human authorization.

### Scope Compliance (AI Agent Implementation)

- [ ] **ONLY** 4 files created: IIRISHostStrategy.cs, SyndicateHostStrategy.cs, StandardHostStrategy.cs, HostStrategyFactory.cs
- [ ] **ONLY** 3 files modified: Program.cs, CreateSkeletonQueryHandler.cs, RenewPolicyQueryHandler.cs
- [ ] **NO** changes to: appsettings.json, models, controllers, middleware, configuration, SOAP utilities, or any other files
- [ ] **NO** additional features beyond Strategy Pattern extraction
- [ ] **NO** optimizations or refactorings beyond moving existing logic to strategies
- [ ] **NO** changes to existing method signatures (except removed private methods)
- [ ] Logic copied **verbatim** from handlers to strategies (byte-for-byte identical behavior)
- [ ] If uncertain about any implementation detail, implementation STOPPED and human consulted

### Functional Requirements

- [ ] `IIRISHostStrategy` interface defined with all host-specific methods
- [ ] `SyndicateHostStrategy` implements all Syndicate-specific behavior
- [ ] `StandardHostStrategy` implements default behavior for Ireland/UK/Asia
- [ ] `HostStrategyFactory` correctly resolves strategy by host name
- [ ] CreateSkeletonQueryHandler uses strategy (no private host methods)
- [ ] RenewPolicyQueryHandler uses strategy (no private host methods)
- [ ] All existing handler tests pass without modification
- [ ] End-to-end behavior identical to pre-refactoring state
- [ ] No breaking changes to API contracts or responses

### Non-Functional Requirements

- [ ] Test coverage ≥ 95% line coverage maintained (current: 98.9%)
- [ ] ~350 lines of new strategy unit tests added
- [ ] Build succeeds with 0 errors (pre-existing warnings acceptable)
- [ ] CreateSkeletonQueryHandler reduced from 605 → ~450 lines (-25%)
- [ ] RenewPolicyQueryHandler reduced from 386 → ~300 lines (-22%)
- [ ] No performance degradation - response times within acceptable limits
- [ ] Strategies are singleton-scoped (no per-request overhead)

### Code Quality Requirements

- [ ] Strategies follow existing `Services/` patterns (e.g., ResilienceSoapService)
- [ ] XML doc comments on all public strategy methods
- [ ] Clear comments explaining Syndicate differences
- [ ] Consistent naming conventions (`{ServiceName}Strategy.cs`)
- [ ] No duplicate code between strategies
- [ ] All strategy methods are pure functions (stateless, deterministic)

### Documentation Requirements

- [ ] Update [copilot-instructions.md](../../.github/copilot-instructions.md) with strategy pattern guidance
- [ ] Add inline code comments documenting strategy selection logic
- [ ] Create this requirements document
- [ ] Update CHANGELOG.md with refactoring details
- [ ] Document strategy extensibility for future hosts

### Testing Requirements

- [ ] All existing handler tests pass (CreateSkeletonQueryHandler, RenewPolicyQueryHandler)
- [ ] New SyndicateHostStrategyTests created with 95%+ coverage
- [ ] New StandardHostStrategyTests created with 95%+ coverage
- [ ] New HostStrategyFactoryTests created with 95%+ coverage
- [ ] Tests verify Syndicate vs Standard behavior differences
- [ ] Tests verify CompanyType rules for all scenarios
- [ ] Tests verify assured validation logic for all scenarios
- [ ] Integration tests verify end-to-end behavior unchanged

## Migration Impact

### Developer Impact

**Existing Code**:
- ✅ **No changes** to controller endpoints
- ✅ **No changes** to models (SkeletonModel, RenewModel)
- ✅ **No changes** to API contracts
- ✅ **No changes** to SOAP integration
- ✅ **No changes** to configuration (appsettings.json)

**New Development**:
- ✅ **Easier** to add new hosts (just add new strategy class)
- ✅ **Easier** to modify host logic (single location)
- ✅ **Easier** to test host logic (unit test strategies)

### API Consumer Impact

**Impact**: ✅ **NONE** - Zero breaking changes

- API endpoints unchanged
- Request/response schemas unchanged
- Authentication unchanged
- Error responses unchanged
- Performance characteristics unchanged

### Operational Impact

**Deployment**:
- ✅ Standard deployment - no special steps required
- ✅ No database migrations
- ✅ No configuration changes
- ✅ No secret updates
- ✅ Backward compatible - can rollback if issues

**Observability**:
- ✅ Strategy selection logged at Debug level
- ✅ Existing logs unchanged
- ✅ Dynatrace queries unchanged

## Implementation Plan

> **🤖 AI AGENT IMPLEMENTATION NOTES**
>
> This section defines the **ONLY** changes authorized for implementation. An AI agent implementing this requirement MUST:
> 1. Follow this plan exactly - do not add "improvements" or "while we're here" changes
> 2. Copy existing logic verbatim - do not optimize, refactor, or "improve" the logic during migration
> 3. Stop immediately if encountering code that differs from what's described in "Current State" section
> 4. Request human authorization for ANY deviation from this plan
> 5. Create ONLY the 7 files listed below (4 new, 3 modified)
> 6. Do not modify appsettings.json, models, controllers, or any other files
>
> **Files to Create** (4):
> - `Services/HostStrategies/IIRISHostStrategy.cs`
> - `Services/HostStrategies/SyndicateHostStrategy.cs`
> - `Services/HostStrategies/StandardHostStrategy.cs`
> - `Services/HostStrategies/HostStrategyFactory.cs`
>
> **Files to Modify** (3):
> - `PolicyConnectorService/Program.cs` (DI registration only)
> - `PolicyConnectorService/Handlers/Queries/CreateSkeletonQueryHandler.cs` (remove ~155 lines, inject factory)
> - `PolicyConnectorService/Handlers/Queries/RenewPolicyQueryHandler.cs` (remove ~86 lines, inject factory)
>
> **Total Scope**: +490 lines, -241 lines, net +249 lines

### Phase 1: Create Strategies (~4 hours)

1. Create `Services/HostStrategies/` directory
2. Implement `IIRISHostStrategy.cs` interface
3. Implement `SyndicateHostStrategy.cs` (~200 lines)
4. Implement `StandardHostStrategy.cs` (~200 lines)
5. Implement `HostStrategyFactory.cs` (~40 lines)
6. Register strategies in `Program.cs`

### Phase 2: Refactor CreateSkeletonQueryHandler (~2 hours)

1. Add factory injection to constructor
2. Replace `IsSyndicateHost()` calls with `strategy.HandlesHost()`
3. Replace `ApplyCompanyTypeRules()` calls with `strategy.ApplyCompanyTypeRules()`
4. Replace `HasValidAssuredDetails()` calls with `strategy.HasValidAssuredDetails()`
5. Replace `BuildIrisLookupPayload()` calls with `strategy.BuildAssuredLookupPayload()`
6. Remove private static methods (IsSyndicateHost, ApplyCompanyTypeRules, etc.)
7. Remove supporting types (IrisLookupTarget enum - move to strategy namespace)
8. Run existing tests to verify no regressions

### Phase 3: Refactor RenewPolicyQueryHandler (~1 hour)

1. Add factory injection to constructor
2. Replace method calls with strategy methods (same as Phase 2)
3. Remove private static methods
4. Run existing tests to verify no regressions

### Phase 4: Add Strategy Tests (~4 hours)

1. Create `SyndicateHostStrategyTests.cs` (~150 lines, 15-20 tests)
2. Create `StandardHostStrategyTests.cs` (~150 lines, 15-20 tests)
3. Create `HostStrategyFactoryTests.cs` (~50 lines, 5-8 tests)
4. Run full test suite to verify 95%+ coverage maintained

### Phase 5: Documentation (~1 hour)

1. Update [copilot-instructions.md](../../.github/copilot-instructions.md)
2. Add inline code comments
3. Update CHANGELOG.md
4. Create this requirements document

**Total Effort**: ~12 hours (1.5 days)

### Phase 6: Scope Verification (~30 minutes)

1. Verify **ONLY** 7 files changed (4 created, 3 modified)
2. Run `git diff --stat` to confirm line count changes (~+249 net)
3. Verify **NO** changes to appsettings.json, models, controllers
4. Confirm all existing tests pass without modification
5. Confirm 95%+ test coverage maintained
6. Document any deviations from this requirements document (should be ZERO)

**Stopping Criteria for AI Agents**:
- If more than 7 files need changes → STOP, request authorization
- If existing logic doesn't match "Current State" section → STOP, request authorization
- If tests fail after refactoring → STOP, request authorization
- If coverage drops below 95% → STOP, request authorization
- If ANY uncertainty about implementation → STOP, request authorization

## Risks and Mitigation

### Risk 1: Behavioral Drift During Refactoring

**Risk**: Logic differences introduced between old and new implementation
**Likelihood**: MEDIUM
**Impact**: HIGH (incorrect IRIS processing, data corruption)

**Mitigation**:
- ✅ Copy existing logic verbatim into strategies (no optimization during move)
- ✅ Run full test suite after each handler refactoring
- ✅ Add integration tests comparing before/after behavior
- ✅ Code review with focus on logic preservation

### Risk 2: Test Coverage Drop

**Risk**: New code not adequately tested
**Likelihood**: LOW
**Impact**: MEDIUM (reduced confidence in changes)

**Mitigation**:
- ✅ Require 95%+ coverage on all new strategy classes
- ✅ Run coverage report before and after refactoring
- ✅ Add explicit tests for Syndicate vs Standard differences

### Risk 3: Performance Regression

**Risk**: Strategy factory introduces per-request overhead
**Likelihood**: LOW
**Impact**: LOW (strategies are singleton, factory is singleton)

**Mitigation**:
- ✅ Strategies are stateless singletons (no allocation overhead)
- ✅ Factory caches strategy instances
- ✅ Monitor response times in DEV after deployment

### Risk 4: Team Unfamiliarity with Pattern

**Risk**: Developers unfamiliar with Strategy Pattern
**Likelihood**: MEDIUM
**Impact**: LOW (pattern is well-documented)

**Mitigation**:
- ✅ Clear documentation in copilot-instructions.md
- ✅ Code comments explaining pattern
- ✅ Team walkthrough/demo before merge
- ✅ Strategy Pattern is standard GoF pattern (well-known)

## Future Extensibility

### Adding a New IRIS Host

**Scenario**: Add "Asia Pacific" host with custom behavior

**Steps**:
1. Create `AsiaPacificHostStrategy.cs` implementing `IIRISHostStrategy`
2. Register in `Program.cs`: `builder.Services.AddSingleton<IIRISHostStrategy, AsiaPacificHostStrategy>()`
3. Add tests: `AsiaPacificHostStrategyTests.cs`

**Effort**: ~2-3 hours (vs ~8 hours editing 2 handlers today)

### Strategy Extensions (Future Possibilities)

If IRISHost affects more than assured logic:

1. **Field Mapping Overrides**:
   ```csharp
   Dictionary<string, string> GetFieldMappingOverrides();
   ```

2. **Custom Validation**:
   ```csharp
   ValidationResult ValidateRequest(PolicyDataModel model);
   ```

3. **SOAP Structure**:
   ```csharp
   string GetSOAPEnvelopeTemplate();
   ```

4. **Response Parsing**:
   ```csharp
   GetStatusResult ParseResponse(string soapResponse);
   ```

**Extensibility**: Strategy interface can grow without breaking existing handlers

## Success Metrics

### Code Quality Metrics

- **Code Duplication**: 241 lines → 0 lines (**100% reduction**)
- **Handler Size**: CreateSkeleton 605→450 lines (**-25%**), Renew 386→300 lines (**-22%**)
- **Test Coverage**: Maintain ≥95% line coverage (current 98.9%)
- **Cyclomatic Complexity**: Reduced in handlers (less branching logic)

### Development Velocity Metrics

- **Time to Add Host**: 8 hours → 2-3 hours (**60% reduction**)
- **Time to Modify Host Logic**: 2x effort → 1x effort (**50% reduction**)
- **Unit Test Execution**: New strategy tests execute faster than handler tests

### Quality Metrics

- **Bug Risk**: HIGH → MEDIUM (single source of truth)
- **Regression Risk**: MEDIUM → LOW (directly testable strategies)
- **Code Review Time**: Reduced (easier to understand isolated strategies)

## Technical Standards

**See**: [copilot-instructions.md](../../.github/copilot-instructions.md) for:
- CQRS/MediatR patterns
- Dependency Injection standards
- Testing requirements
- Code organization rules
- Naming conventions
- Documentation standards

## References

- **Gang of Four**: Strategy Pattern (Behavioral Design Pattern)
- **Martin Fowler**: Refactoring - Replace Conditional with Polymorphism
- **Current Implementation**: [CreateSkeletonQueryHandler.cs](../../PolicyConnectorService/Handlers/Queries/CreateSkeletonQueryHandler.cs), [RenewPolicyQueryHandler.cs](../../PolicyConnectorService/Handlers/Queries/RenewPolicyQueryHandler.cs)
- **Architecture Guidance**: [copilot-instructions.md](../../.github/copilot-instructions.md)

---

**Last Updated**: March 30, 2026
**Maintained By**: EverView Development Team
