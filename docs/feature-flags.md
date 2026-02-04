# Feature Flags in OpenHands

This document outlines the feature flag infrastructure in OpenHands, including recommended libraries, implementation patterns, and PR integration guidelines.

## Table of Contents

1. [Current Infrastructure](#current-infrastructure)
2. [Recommended Feature Flag Libraries](#recommended-feature-flag-libraries)
3. [Implementation Guide](#implementation-guide)
4. [PR Integration](#pr-integration)
5. [Best Practices](#best-practices)

---

## Current Infrastructure

OpenHands already has a basic feature flag system in place:

### Frontend (TypeScript/React)

**Location:** `frontend/src/utils/feature-flags.ts`

```typescript
// Current implementation uses localStorage
export function loadFeatureFlag(flagName: string, defaultValue: boolean = false): boolean {
  try {
    const stringValue = localStorage.getItem(`FEATURE_${flagName}`) || defaultValue.toString();
    return !!JSON.parse(stringValue);
  } catch (e) {
    return defaultValue;
  }
}

// Example flags
export const BILLING_SETTINGS = () => loadFeatureFlag("BILLING_SETTINGS");
export const HIDE_LLM_SETTINGS = () => loadFeatureFlag("HIDE_LLM_SETTINGS");
export const USE_PLANNING_AGENT = () => loadFeatureFlag("USE_PLANNING_AGENT");
```

### Backend (Python/FastAPI)

**Location:** `openhands/app_server/web_client/web_client_models.py`

```python
class WebClientFeatureFlags(BaseModel):
    enable_billing: bool = False
    hide_llm_settings: bool = False
    enable_jira: bool = False
    enable_jira_dc: bool = False
    enable_linear: bool = False
```

### Analytics Integration

OpenHands uses **PostHog** for analytics, which also provides feature flag capabilities:
- Client key configured in server config
- React SDK available via `posthog-js/react`
- Python SDK available via `posthog` package

---

## Recommended Feature Flag Libraries

### Primary Recommendation: PostHog (Already Integrated)

Since PostHog is already integrated for analytics, we recommend expanding its use for feature flags.

**Pros:**
- ✅ Already integrated in the codebase
- ✅ Single platform for analytics and feature flags
- ✅ Supports A/B testing and experiments
- ✅ Both Python and React SDKs available
- ✅ Local evaluation support for performance
- ✅ Percentage rollouts and user targeting

**Cons:**
- ⚠️ Requires PostHog account for remote flags
- ⚠️ May add latency for server-side evaluation

**Implementation:**

```python
# Python Backend
import posthog

# Initialize
posthog.project_api_key = 'your_api_key'

# Check flag
is_enabled = posthog.feature_enabled('new-feature', user_id)

# Get variant (for multivariate flags)
variant = posthog.get_feature_flag('experiment-flag', user_id)
```

```typescript
// React Frontend
import { useFeatureFlag } from 'posthog-js/react';

function MyComponent() {
  const showNewFeature = useFeatureFlag('new-feature');

  if (showNewFeature) {
    return <NewFeatureComponent />;
  }
  return <OldComponent />;
}
```

### Alternative Options

#### 1. Unleash (Self-Hosted)

Best for teams wanting full control over their feature flag infrastructure.

**Pros:**
- ✅ Open-source and self-hosted
- ✅ Strong community support
- ✅ SDKs for Python and JavaScript
- ✅ GitOps-friendly

**Cons:**
- ⚠️ Requires infrastructure setup
- ⚠️ Additional operational overhead

```bash
# Installation
pip install UnleashClient  # Python
npm install unleash-client  # JavaScript
```

#### 2. Flagsmith (Hybrid)

Best for teams wanting flexibility between self-hosted and managed.

**Pros:**
- ✅ Django-based (familiar to Python developers)
- ✅ Both self-hosted and cloud options
- ✅ Feature segments and A/B testing

**Cons:**
- ⚠️ Less mature than PostHog/Unleash

```bash
# Installation
pip install flagsmith  # Python
npm install flagsmith  # JavaScript
```

#### 3. OpenFeature (Standard)

Best for teams wanting vendor-agnostic feature flags.

**Pros:**
- ✅ Vendor-neutral standard
- ✅ Easy to switch providers
- ✅ Growing ecosystem

**Cons:**
- ⚠️ Requires additional provider setup
- ⚠️ Less feature-rich than dedicated solutions

```bash
# Installation
pip install openfeature-sdk  # Python
npm install @openfeature/web-sdk  # JavaScript
```

### Comparison Table

| Feature | PostHog | Unleash | Flagsmith | OpenFeature |
|---------|---------|---------|-----------|-------------|
| Already Integrated | ✅ | ❌ | ❌ | ❌ |
| Self-Hosted Option | ✅ | ✅ | ✅ | ✅ |
| A/B Testing | ✅ | ✅ | ✅ | Provider-dependent |
| Analytics | ✅ | ❌ | ❌ | ❌ |
| Python SDK | ✅ | ✅ | ✅ | ✅ |
| React SDK | ✅ | ✅ | ✅ | ✅ |
| Local Evaluation | ✅ | ✅ | ✅ | Provider-dependent |
| Percentage Rollouts | ✅ | ✅ | ✅ | Provider-dependent |

---

## Implementation Guide

### Extending the Existing System

#### 1. Enhanced Feature Flag Service (Python)

Create a unified feature flag service that supports both local and remote flags:

```python
# openhands/core/feature_flags.py
from enum import Enum
from typing import Any
from pydantic import BaseModel
import posthog
from openhands.core.logger import openhands_logger as logger


class FeatureFlagSource(Enum):
    LOCAL = "local"
    POSTHOG = "posthog"
    CONFIG = "config"


class FeatureFlag(BaseModel):
    name: str
    default_value: bool = False
    source: FeatureFlagSource = FeatureFlagSource.LOCAL
    description: str = ""


class FeatureFlagService:
    """Unified feature flag service supporting multiple sources."""

    def __init__(self, posthog_api_key: str | None = None):
        self._local_flags: dict[str, bool] = {}
        self._posthog_enabled = posthog_api_key is not None

        if self._posthog_enabled:
            posthog.project_api_key = posthog_api_key

    def is_enabled(
        self,
        flag_name: str,
        user_id: str | None = None,
        default: bool = False,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """Check if a feature flag is enabled."""

        # Check local overrides first
        if flag_name in self._local_flags:
            return self._local_flags[flag_name]

        # Check PostHog if available
        if self._posthog_enabled and user_id:
            try:
                return posthog.feature_enabled(
                    flag_name,
                    user_id,
                    person_properties=properties,
                )
            except Exception as e:
                logger.warning(f"PostHog feature flag check failed: {e}")

        return default

    def get_variant(
        self,
        flag_name: str,
        user_id: str,
        properties: dict[str, Any] | None = None,
    ) -> str | None:
        """Get the variant of a multivariate feature flag."""

        if not self._posthog_enabled:
            return None

        try:
            return posthog.get_feature_flag(
                flag_name,
                user_id,
                person_properties=properties,
            )
        except Exception as e:
            logger.warning(f"PostHog variant check failed: {e}")
            return None

    def set_local_flag(self, flag_name: str, value: bool) -> None:
        """Set a local flag override (useful for testing)."""
        self._local_flags[flag_name] = value

    def clear_local_flags(self) -> None:
        """Clear all local flag overrides."""
        self._local_flags.clear()


# Global instance
_feature_flag_service: FeatureFlagService | None = None


def get_feature_flag_service() -> FeatureFlagService:
    """Get the global feature flag service instance."""
    global _feature_flag_service

    if _feature_flag_service is None:
        from openhands.server.config.server_config import ServerConfig
        config = ServerConfig.model_validate({})
        _feature_flag_service = FeatureFlagService(
            posthog_api_key=config.posthog_client_key
        )

    return _feature_flag_service


def is_feature_enabled(
    flag_name: str,
    user_id: str | None = None,
    default: bool = False,
) -> bool:
    """Convenience function to check if a feature is enabled."""
    return get_feature_flag_service().is_enabled(flag_name, user_id, default)
```

#### 2. Enhanced Feature Flag Hook (React)

```typescript
// frontend/src/hooks/use-feature-flag.ts
import { usePostHog } from 'posthog-js/react';
import { useCallback, useMemo } from 'react';

interface FeatureFlagOptions {
  defaultValue?: boolean;
  sendEvent?: boolean;
}

/**
 * Hook to check feature flag status with fallback support.
 *
 * Priority:
 * 1. Local storage override (for development/testing)
 * 2. PostHog remote flag
 * 3. Default value
 */
export function useFeatureFlag(
  flagName: string,
  options: FeatureFlagOptions = {}
): boolean {
  const { defaultValue = false, sendEvent = true } = options;
  const posthog = usePostHog();

  const localStorageKey = `FEATURE_${flagName}`;

  const value = useMemo(() => {
    // Check local storage override first
    try {
      const localValue = localStorage.getItem(localStorageKey);
      if (localValue !== null) {
        return JSON.parse(localValue);
      }
    } catch {
      // Ignore localStorage errors
    }

    // Check PostHog
    if (posthog) {
      const phValue = posthog.isFeatureEnabled(flagName);
      if (phValue !== undefined) {
        return phValue;
      }
    }

    return defaultValue;
  }, [flagName, localStorageKey, posthog, defaultValue]);

  return value;
}

/**
 * Hook to get feature flag variant for A/B tests.
 */
export function useFeatureFlagVariant(flagName: string): string | undefined {
  const posthog = usePostHog();

  return useMemo(() => {
    if (!posthog) return undefined;

    const variant = posthog.getFeatureFlag(flagName);
    return typeof variant === 'string' ? variant : undefined;
  }, [flagName, posthog]);
}

/**
 * Hook for feature flag with payload data.
 */
export function useFeatureFlagPayload<T = unknown>(
  flagName: string
): T | undefined {
  const posthog = usePostHog();

  return useMemo(() => {
    if (!posthog) return undefined;

    return posthog.getFeatureFlagPayload(flagName) as T | undefined;
  }, [flagName, posthog]);
}
```

#### 3. Feature Flag Registry

Create a centralized registry for all feature flags:

```python
# openhands/core/feature_flag_registry.py
from dataclasses import dataclass
from enum import Enum


class FlagCategory(Enum):
    UI = "ui"
    BACKEND = "backend"
    EXPERIMENT = "experiment"
    INTEGRATION = "integration"


@dataclass
class FlagDefinition:
    name: str
    description: str
    category: FlagCategory
    default_value: bool = False
    owner: str = ""
    created_date: str = ""
    cleanup_date: str | None = None  # When this flag should be removed


# Central registry of all feature flags
FEATURE_FLAGS: dict[str, FlagDefinition] = {
    # UI Flags
    "BILLING_SETTINGS": FlagDefinition(
        name="BILLING_SETTINGS",
        description="Enable billing settings in the UI",
        category=FlagCategory.UI,
        default_value=False,
        owner="team-billing",
    ),
    "HIDE_LLM_SETTINGS": FlagDefinition(
        name="HIDE_LLM_SETTINGS",
        description="Hide LLM configuration settings from users",
        category=FlagCategory.UI,
        default_value=False,
    ),
    "USE_PLANNING_AGENT": FlagDefinition(
        name="USE_PLANNING_AGENT",
        description="Enable the planning agent feature",
        category=FlagCategory.EXPERIMENT,
        default_value=False,
        owner="team-agents",
    ),
    "VSCODE_IN_NEW_TAB": FlagDefinition(
        name="VSCODE_IN_NEW_TAB",
        description="Open VSCode in a new tab instead of embedded",
        category=FlagCategory.UI,
        default_value=False,
    ),
    "TRAJECTORY_REPLAY": FlagDefinition(
        name="TRAJECTORY_REPLAY",
        description="Enable trajectory replay feature",
        category=FlagCategory.EXPERIMENT,
        default_value=False,
    ),
    # Integration Flags
    "ENABLE_JIRA": FlagDefinition(
        name="ENABLE_JIRA",
        description="Enable Jira integration",
        category=FlagCategory.INTEGRATION,
        default_value=False,
    ),
    "ENABLE_LINEAR": FlagDefinition(
        name="ENABLE_LINEAR",
        description="Enable Linear integration",
        category=FlagCategory.INTEGRATION,
        default_value=False,
    ),
}


def get_flag_definition(flag_name: str) -> FlagDefinition | None:
    """Get the definition for a feature flag."""
    return FEATURE_FLAGS.get(flag_name)


def get_flags_by_category(category: FlagCategory) -> list[FlagDefinition]:
    """Get all flags in a specific category."""
    return [f for f in FEATURE_FLAGS.values() if f.category == category]


def get_flags_needing_cleanup() -> list[FlagDefinition]:
    """Get flags that have passed their cleanup date."""
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    return [
        f for f in FEATURE_FLAGS.values()
        if f.cleanup_date and f.cleanup_date <= today
    ]
```

---

## PR Integration

### Automatic Detection

A GitHub Action workflow (`.github/workflows/feature-flag-detection.yml`) automatically:

1. **Scans PR changes** for feature flag patterns
2. **Adds labels** (`feature-flag`) to PRs containing flags
3. **Posts a comment** with a checklist for feature flag documentation

### Detected Patterns

The workflow looks for these patterns:

**Python:**
- `feature_enabled(`
- `get_feature_flag(`
- `FeatureFlag`
- `feature_flags`
- `WebClientFeatureFlags`
- `@feature_flag`
- `FEATURE_`

**TypeScript/JavaScript:**
- `loadFeatureFlag(`
- `useFeatureFlag`
- `featureFlags`
- `FEATURE_`
- `posthog.isFeatureEnabled`
- `posthog.getFeatureFlag`

### PR Template

The PR template (`.github/pull_request_template.md`) includes a feature flag section:

```markdown
## Feature Flags

**Flag Name:** ENABLE_NEW_FEATURE

**Flag Type:**
- [x] New feature flag

**Rollout Plan:**
- [x] Internal testing only
- [ ] Percentage rollout (specify %): ___

**Testing:**
- [x] Tested with flag enabled
- [x] Tested with flag disabled

**Cleanup Plan:** Remove after successful rollout (Q2 2025)
```

---

## Best Practices

### 1. Naming Conventions

```
# Format: FEATURE_AREA_DESCRIPTION
FEATURE_UI_NEW_DASHBOARD
FEATURE_AGENT_PLANNING_MODE
FEATURE_INTEGRATION_SLACK_V2
```

### 2. Flag Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Create    │────▶│   Rollout   │────▶│  Validate   │────▶│   Remove    │
│    Flag     │     │  (Gradual)  │     │  (Monitor)  │     │   (Clean)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. **Create:** Define flag with clear description and owner
2. **Rollout:** Start with 0% → internal → % rollout → 100%
3. **Validate:** Monitor metrics, gather feedback
4. **Remove:** Clean up code after successful rollout

### 3. Testing Guidelines

```python
# Test both states
def test_feature_with_flag_enabled():
    flag_service.set_local_flag("NEW_FEATURE", True)
    result = my_function()
    assert result == expected_new_behavior

def test_feature_with_flag_disabled():
    flag_service.set_local_flag("NEW_FEATURE", False)
    result = my_function()
    assert result == expected_old_behavior
```

### 4. Documentation Requirements

Every feature flag should have:
- [ ] Clear description in the registry
- [ ] Owner/team assigned
- [ ] Cleanup date specified
- [ ] Both code paths tested
- [ ] Monitoring/metrics in place

### 5. Cleanup Reminders

Set up automated reminders for flag cleanup:

```yaml
# In your project management tool or CI
- Flag: FEATURE_NEW_DASHBOARD
  Created: 2025-01-01
  Cleanup Target: 2025-03-01
  Owner: @team-frontend
```

---

## Quick Start

### Adding a New Feature Flag

1. **Define the flag** in the registry:

```python
# openhands/core/feature_flag_registry.py
FEATURE_FLAGS["MY_NEW_FEATURE"] = FlagDefinition(
    name="MY_NEW_FEATURE",
    description="What this flag controls",
    category=FlagCategory.UI,
    owner="your-team",
    cleanup_date="2025-06-01",
)
```

2. **Use in Python:**

```python
from openhands.core.feature_flags import is_feature_enabled

if is_feature_enabled("MY_NEW_FEATURE", user_id=user.id):
    # New behavior
else:
    # Old behavior
```

3. **Use in React:**

```typescript
import { useFeatureFlag } from '#/hooks/use-feature-flag';

function MyComponent() {
  const isEnabled = useFeatureFlag('MY_NEW_FEATURE');

  if (isEnabled) {
    return <NewFeature />;
  }
  return <OldFeature />;
}
```

4. **Create PR** with the feature flag section filled out

5. **Monitor** the rollout via PostHog analytics

6. **Cleanup** after successful rollout
