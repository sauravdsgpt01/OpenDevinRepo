# LiteLLM Integration

This document describes how OpenHands integrates with LiteLLM for LLM API management, billing, and rate limiting.

## Overview

LiteLLM serves as our LLM proxy layer and handles:
1. Unified API for multiple LLM providers (OpenAI, Anthropic, etc.)
2. User/team budget management
3. API key generation and validation
4. Usage tracking and billing
5. Rate limiting

## Architecture

### High-Level Architecture

```mermaid
flowchart TB
    subgraph Users ["Users"]
        U1[User A]
        U2[User B]
    end

    subgraph OpenHands ["OpenHands Backend"]
        Auth[Auth Service]
        Agent[Agent Runtime]
        Billing[Billing Service]
        LLM_Manager[LiteLlmManager]
    end

    subgraph LiteLLM ["LiteLLM Proxy"]
        Proxy[LiteLLM Proxy Server]
        TeamMgmt[Team Management]
        KeyMgmt[Key Management]
        BudgetTrack[Budget Tracking]
        UsageTrack[Usage Tracking]
    end

    subgraph LLMProviders ["LLM Providers"]
        Anthropic[Anthropic<br/>Claude]
        OpenAI[OpenAI<br/>GPT-4]
        Other[Other Providers]
    end

    U1 & U2 --> Auth
    Auth --> LLM_Manager
    LLM_Manager --> TeamMgmt & KeyMgmt
    Agent --> Proxy
    Proxy --> Anthropic & OpenAI & Other
    Proxy --> BudgetTrack & UsageTrack
    Billing --> BudgetTrack

    style Proxy fill:#90EE90
    style BudgetTrack fill:#FFE4B5
```

### User Onboarding Flow

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Backend as OpenHands Backend
    participant LLM_Manager as LiteLlmManager
    participant LiteLLM as LiteLLM Proxy

    Note over User,LiteLLM: New User Registration

    User->>Backend: Complete OAuth login
    Backend->>Backend: Create user in database
    Backend->>LLM_Manager: create_entries(org_id, user_id, settings)
    
    %% Create Team (Org)
    LLM_Manager->>LiteLLM: POST /team/new
    Note over LLM_Manager,LiteLLM: Request:<br/>- team_id: org_id<br/>- team_alias: org_id<br/>- max_budget: $10 (default)
    LiteLLM-->>LLM_Manager: Team created
    
    %% Create User
    LLM_Manager->>LiteLLM: POST /user/new
    Note over LLM_Manager,LiteLLM: Request:<br/>- user_id: keycloak_user_id<br/>- user_email: email<br/>- max_budget: unlimited
    LiteLLM-->>LLM_Manager: User created
    
    %% Add User to Team
    LLM_Manager->>LiteLLM: POST /team/member_add
    Note over LLM_Manager,LiteLLM: Request:<br/>- team_id: org_id<br/>- member: {user_id, max_budget}
    LiteLLM-->>LLM_Manager: Member added
    
    %% Generate API Key
    LLM_Manager->>LiteLLM: POST /key/generate
    Note over LLM_Manager,LiteLLM: Request:<br/>- user_id: keycloak_user_id<br/>- team_id: org_id<br/>- key_alias: "OpenHands Cloud - user X - org Y"
    LiteLLM-->>LLM_Manager: API Key (sk-xxx)
    
    LLM_Manager-->>Backend: Settings with API key
    Backend->>Backend: Store settings
    Backend-->>User: Login complete
```

### LLM Request Flow

```mermaid
sequenceDiagram
    autonumber
    participant Agent as Agent Runtime
    participant LiteLLM as LiteLLM Proxy
    participant Budget as Budget Checker
    participant Provider as LLM Provider

    Agent->>LiteLLM: POST /chat/completions
    Note over Agent,LiteLLM: Headers:<br/>- x-goog-api-key: sk-xxx<br/><br/>Body:<br/>- model: litellm_proxy/claude-sonnet-4<br/>- messages: [...]

    LiteLLM->>LiteLLM: Validate API key
    LiteLLM->>Budget: Check team budget
    
    alt Budget Exceeded
        Budget-->>LiteLLM: Over budget
        LiteLLM-->>Agent: 429 Budget Exceeded
    else Budget OK
        Budget-->>LiteLLM: OK
        LiteLLM->>LiteLLM: Transform request
        Note over LiteLLM: - Strip litellm_proxy/ prefix<br/>- Add provider API key<br/>- Apply rate limits
        
        LiteLLM->>Provider: Forward request
        Provider-->>LiteLLM: Response + usage
        
        LiteLLM->>Budget: Update spend
        Note over LiteLLM,Budget: Track:<br/>- prompt_tokens<br/>- completion_tokens<br/>- cost
        
        LiteLLM-->>Agent: Response
    end
```

### Budget Management

```mermaid
flowchart TB
    subgraph TeamBudget ["Team (Organization) Budget"]
        TB[Team Budget<br/>max_budget: $10<br/>spend: $3.50]
    end

    subgraph UserBudget ["User Budget (within Team)"]
        UB[User Budget<br/>max_budget: unlimited<br/>spend: $3.50]
    end

    subgraph KeyBudget ["API Key Budget"]
        KB1[OpenHands Cloud Key<br/>max_budget: null<br/>spend: $2.00]
        KB2[BYOR Key<br/>max_budget: null<br/>spend: $1.50]
    end

    TeamBudget --> UserBudget
    UserBudget --> KB1 & KB2

    subgraph BudgetCheck ["Budget Check Order"]
        C1[1. Check Key Budget] --> C2[2. Check User Budget]
        C2 --> C3[3. Check Team Budget]
        C3 --> C4{Any Exceeded?}
        C4 -->|Yes| C5[Reject Request]
        C4 -->|No| C6[Allow Request]
    end

    style TB fill:#FFE4B5
    style C5 fill:#FFB6C1
    style C6 fill:#90EE90
```

### Key Types

```mermaid
flowchart LR
    subgraph KeyTypes ["API Key Types"]
        direction TB
        
        subgraph OpenHandsKey ["OpenHands Cloud Key"]
            OK_Desc[Created automatically<br/>on user registration]
            OK_Use[Uses OpenHands credits]
            OK_Alias["Alias: OpenHands Cloud -<br/>user {id} - org {id}"]
        end
        
        subgraph BYORKey ["BYOR Key"]
            BYOR_Desc[User provides own key]
            BYOR_Use[Uses user's own credits<br/>with their provider]
            BYOR_Alias["Alias: BYOR Key -<br/>user {id}, org {id}"]
        end
    end

    subgraph Model ["Model Routing"]
        M1[litellm_proxy/claude-sonnet-4]
        M2[litellm_proxy/gpt-4o]
        
        M1 --> |OpenHands Key| Anthropic
        M2 --> |OpenHands Key| OpenAI
        
        M1 --> |BYOR Key| UserAnthropic[User's Anthropic]
        M2 --> |BYOR Key| UserOpenAI[User's OpenAI]
    end

    OpenHandsKey --> Model
    BYORKey --> Model

    style OK_Use fill:#90EE90
    style BYOR_Use fill:#87CEEB
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LITE_LLM_API_URL` | LiteLLM proxy URL | `https://llm-proxy.app.all-hands.dev` |
| `LITE_LLM_API_KEY` | Admin API key | `sk-xxx` |
| `LITE_LLM_TEAM_ID` | Default team ID | (optional) |
| `DEFAULT_INITIAL_BUDGET` | Starting budget for new users | `10` |
| `LITELLM_DEFAULT_MODEL` | Default model | `litellm_proxy/claude-sonnet-4-20250514` |

### Model Version Mapping

| Settings Version | Default Model |
|-----------------|---------------|
| 1 | `claude-3-5-sonnet-20241022` |
| 2 | `claude-3-7-sonnet-20250219` |
| 3 | `claude-sonnet-4-20250514` |
| 4 | `claude-sonnet-4-20250514` |
| 5 | `claude-opus-4-5-20251101` |

## LiteLlmManager API

The `LiteLlmManager` class provides:

### Team Operations
```python
await LiteLlmManager.create_team(keycloak_user_id, org_id, max_budget)
await LiteLlmManager.get_team(org_id)
await LiteLlmManager.update_team(org_id, max_budget)
await LiteLlmManager.delete_team(org_id)
```

### User Operations
```python
await LiteLlmManager.create_user(email, keycloak_user_id)
await LiteLlmManager.get_user(keycloak_user_id)
await LiteLlmManager.update_user(keycloak_user_id, max_budget)
await LiteLlmManager.delete_user(keycloak_user_id)
```

### Team Membership
```python
await LiteLlmManager.add_user_to_team(keycloak_user_id, org_id, max_budget)
await LiteLlmManager.remove_user_from_team(keycloak_user_id, org_id)
await LiteLlmManager.update_user_in_team(keycloak_user_id, org_id, max_budget)
```

### Key Operations
```python
await LiteLlmManager.generate_key(keycloak_user_id, org_id, key_alias, max_budget)
await LiteLlmManager.get_key_info(key)
await LiteLlmManager.verify_existing_key(key, keycloak_user_id, org_id)
await LiteLlmManager.delete_key(key_id, key_alias)
```

## Error Handling

```mermaid
flowchart TD
    subgraph Errors ["Common Error Scenarios"]
        E1[Budget Exceeded<br/>HTTP 429]
        E2[Invalid Key<br/>HTTP 401]
        E3[Rate Limited<br/>HTTP 429]
        E4[Provider Error<br/>HTTP 5xx]
    end

    subgraph Handling ["Error Handling"]
        E1 --> H1[Show upgrade prompt]
        E2 --> H2[Re-authenticate user]
        E3 --> H3[Retry with backoff]
        E4 --> H4[Fail open or retry]
    end

    style E1 fill:#FFB6C1
    style E2 fill:#FFB6C1
    style E3 fill:#FFE4B5
    style E4 fill:#FFE4B5
```

## Related Files

- `enterprise/storage/lite_llm_manager.py` - LiteLLM API client
- `enterprise/server/constants.py` - Configuration and model mappings
- `enterprise/server/routes/billing.py` - Budget management endpoints
- `enterprise/server/routes/api_keys.py` - Key management endpoints
- `openhands/llm/llm.py` - LLM client (uses LiteLLM under the hood)

## External Documentation

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [LiteLLM Proxy](https://docs.litellm.ai/docs/simple_proxy)
- [Budget Management](https://docs.litellm.ai/docs/proxy/users)
