# Langfuse Integration

This document describes how OpenHands integrates with Langfuse for LLM observability and tracing.

## Overview

Langfuse provides LLM observability and tracing capabilities:
1. Request/response logging for LLM calls
2. Cost tracking and analytics
3. Latency monitoring
4. Prompt versioning and evaluation
5. User session tracking

## Architecture

### Integration Flow

```mermaid
flowchart TB
    subgraph OpenHands ["OpenHands"]
        Agent[Agent Runtime]
        LLM[LLM Client]
        Config[Configuration<br/>WEB_HOST env var]
    end

    subgraph LiteLLM ["LiteLLM Proxy"]
        Proxy[Proxy Server]
        Callback[Langfuse Callback]
    end

    subgraph Langfuse ["Langfuse"]
        Ingest[Ingestion API]
        Dashboard[Dashboard]
        Traces[Trace Storage]
    end

    subgraph LLMProviders ["LLM Providers"]
        Anthropic[Anthropic]
        OpenAI[OpenAI]
    end

    Agent --> LLM
    LLM --> Proxy
    Proxy --> Anthropic & OpenAI
    Proxy --> Callback
    Callback --> Ingest
    Ingest --> Traces
    Traces --> Dashboard
    Config -.->|WEB_HOST for session tracking| Callback

    style Langfuse fill:#90EE90
```

### Trace Structure

```mermaid
flowchart TB
    subgraph Trace ["Langfuse Trace"]
        Session[Session<br/>user_id + conversation_id]
        
        subgraph Spans ["Spans"]
            S1[Agent Loop Span]
            S2[LLM Call Span]
            S3[Tool Execution Span]
        end
        
        subgraph Generations ["Generations"]
            G1[LLM Generation<br/>- model<br/>- prompt<br/>- completion<br/>- tokens<br/>- cost<br/>- latency]
        end
        
        Session --> S1
        S1 --> S2 & S3
        S2 --> G1
    end

    subgraph Metadata ["Captured Metadata"]
        M1[user_id]
        M2[conversation_id]
        M3[org_id]
        M4[model_name]
        M5[WEB_HOST]
    end

    Metadata -.-> Session
```

### Data Flow

```mermaid
sequenceDiagram
    autonumber
    participant Agent as Agent Runtime
    participant LiteLLM as LiteLLM Proxy
    participant Provider as LLM Provider
    participant Langfuse as Langfuse

    Agent->>LiteLLM: Chat completion request
    Note over Agent,LiteLLM: Headers include:<br/>- user_id<br/>- conversation_id<br/>- trace metadata

    LiteLLM->>LiteLLM: Start trace span
    LiteLLM->>Provider: Forward request
    Provider-->>LiteLLM: Response

    LiteLLM->>LiteLLM: Calculate cost & tokens
    LiteLLM->>Langfuse: Send trace data (async)
    
    Note over LiteLLM,Langfuse: Trace Data:<br/>- input (prompt)<br/>- output (completion)<br/>- model<br/>- usage (tokens)<br/>- cost<br/>- latency_ms<br/>- metadata

    LiteLLM-->>Agent: Response

    Note over Langfuse: Langfuse processes<br/>and stores trace<br/>for analytics
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `WEB_HOST` | Host identifier for session tracking | Yes |
| `LANGFUSE_PUBLIC_KEY` | Langfuse project public key | Yes (in LiteLLM) |
| `LANGFUSE_SECRET_KEY` | Langfuse project secret key | Yes (in LiteLLM) |
| `LANGFUSE_HOST` | Langfuse API host | Optional |

### Critical Configuration Note

From `enterprise/integrations/utils.py`:

```python
# ---- DO NOT REMOVE ----
# WARNING: Langfuse depends on the WEB_HOST environment variable being set to track events.
HOST = WEB_HOST
# ---- DO NOT REMOVE ----
```

The `WEB_HOST` environment variable is **critical** for Langfuse to properly track and correlate events across sessions.

## Metrics Captured

### Per-Request Metrics

| Metric | Description |
|--------|-------------|
| `latency_ms` | Total request latency |
| `prompt_tokens` | Input token count |
| `completion_tokens` | Output token count |
| `total_tokens` | Total tokens used |
| `cost_usd` | Estimated cost in USD |

### Aggregated Analytics

```mermaid
flowchart LR
    subgraph Metrics ["Available Analytics"]
        M1[Cost per user]
        M2[Cost per model]
        M3[Latency percentiles]
        M4[Token usage trends]
        M5[Error rates]
        M6[Prompt performance]
    end

    subgraph Dashboards ["Dashboard Views"]
        D1[User Analytics]
        D2[Model Comparison]
        D3[Cost Analysis]
        D4[Quality Metrics]
    end

    M1 & M2 --> D3
    M3 & M5 --> D2
    M4 --> D1
    M6 --> D4
```

## Use Cases

### 1. Cost Attribution
Track LLM costs by user, organization, and conversation:

```mermaid
flowchart TD
    Cost[Total LLM Cost] --> User[Per User]
    Cost --> Org[Per Organization]
    Cost --> Conv[Per Conversation]
    Cost --> Model[Per Model]
```

### 2. Quality Monitoring
Monitor response quality and detect issues:
- High latency requests
- Token limit exceeded
- Model errors
- Unexpected completions

### 3. Debugging
Trace individual requests for debugging:
- Full prompt/completion capture
- Request timing breakdown
- Error context

## Integration with LiteLLM

Langfuse is integrated via LiteLLM's callback system:

```python
# LiteLLM configuration (in proxy)
litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]
```

This automatically sends all LLM calls to Langfuse without modifying application code.

## Related Files

- `enterprise/integrations/utils.py` - WEB_HOST configuration
- `enterprise/server/constants.py` - Environment configuration
- LiteLLM Proxy configuration (external)

## External Documentation

- [Langfuse Documentation](https://langfuse.com/docs)
- [LiteLLM + Langfuse Integration](https://docs.litellm.ai/docs/observability/langfuse_integration)
- [Langfuse Tracing](https://langfuse.com/docs/tracing)
