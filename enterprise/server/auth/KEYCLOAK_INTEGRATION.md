# Keycloak Integration

This document describes how OpenHands integrates with Keycloak for identity and access management.

## Overview

Keycloak serves as our identity provider (IdP) and handles:
1. User authentication via OAuth 2.0 / OpenID Connect
2. Social login federation (GitHub, GitLab, Bitbucket)
3. Token management (access tokens, refresh tokens, offline tokens)
4. User account management
5. Session management

## Architecture

### Authentication Flow

```mermaid
sequenceDiagram
    autonumber
    participant Browser
    participant Frontend
    participant Backend as Backend (auth.py)
    participant Keycloak
    participant GitHub as GitHub/GitLab/Bitbucket

    Note over Browser,GitHub: OAuth 2.0 Authorization Code Flow with PKCE

    %% Initial Login Request
    Browser->>Frontend: User clicks "Login with GitHub"
    Frontend->>Backend: GET /oauth/github/login
    Backend->>Backend: Generate state parameter
    Backend-->>Browser: Redirect to Keycloak authorize endpoint
    
    Note over Backend,Keycloak: Redirect URL includes:<br/>- client_id<br/>- redirect_uri<br/>- response_type=code<br/>- scope=openid profile email<br/>- state (CSRF protection)<br/>- kc_idp_hint=github

    %% Keycloak -> GitHub Federation
    Browser->>Keycloak: Follow redirect
    Keycloak->>Keycloak: Check kc_idp_hint
    Keycloak-->>Browser: Redirect to GitHub OAuth
    Browser->>GitHub: Authorization request
    GitHub-->>Browser: Show consent screen
    Browser->>GitHub: User approves
    GitHub-->>Browser: Redirect with auth code
    Browser->>Keycloak: Auth code from GitHub
    
    %% Keycloak Token Exchange
    Keycloak->>GitHub: Exchange code for tokens
    GitHub-->>Keycloak: Access token + user info
    Keycloak->>Keycloak: Create/update user
    Keycloak->>Keycloak: Generate Keycloak tokens
    Keycloak-->>Browser: Redirect to callback with code

    %% Backend Token Exchange
    Browser->>Backend: GET /oauth/keycloak/callback?code=xxx
    Backend->>Keycloak: POST /token (exchange code)
    
    Note over Backend,Keycloak: Token Request:<br/>- grant_type=authorization_code<br/>- code<br/>- client_id<br/>- client_secret<br/>- redirect_uri

    Keycloak-->>Backend: Token Response
    
    Note over Backend,Keycloak: Token Response:<br/>- access_token (JWT)<br/>- refresh_token<br/>- id_token<br/>- expires_in<br/>- token_type=Bearer

    %% User Info & Session
    Backend->>Keycloak: GET /userinfo
    Keycloak-->>Backend: User claims
    
    Note over Backend: User Info Contains:<br/>- sub (Keycloak user ID)<br/>- preferred_username<br/>- email<br/>- name<br/>- idp (github/gitlab/bitbucket)

    Backend->>Backend: Create/update user in DB
    Backend->>Backend: reCAPTCHA verification
    Backend->>Backend: Domain blocklist check
    Backend->>Backend: Sign JWT cookie
    Backend-->>Browser: Set keycloak_auth cookie + redirect
```

### Token Management

```mermaid
flowchart TB
    subgraph TokenTypes ["Token Types"]
        AT[Access Token<br/>Short-lived: 5 min<br/>Used for API calls]
        RT[Refresh Token<br/>Medium-lived: 30 min<br/>Used to get new access tokens]
        OT[Offline Token<br/>Long-lived: 30 days<br/>Used for background jobs]
    end

    subgraph TokenFlow ["Token Refresh Flow"]
        A[API Request] --> B{Access Token<br/>Valid?}
        B -->|Yes| C[Process Request]
        B -->|No| D{Refresh Token<br/>Valid?}
        D -->|Yes| E[Get New Access Token]
        E --> C
        D -->|No| F{Offline Token<br/>Valid?}
        F -->|Yes| G[Get New Refresh Token]
        G --> E
        F -->|No| H[Redirect to Login]
    end

    subgraph Storage ["Token Storage"]
        Cookie[keycloak_auth Cookie<br/>Signed JWT containing:<br/>- access_token<br/>- refresh_token<br/>- accepted_tos]
        DB[(Database<br/>Offline tokens for<br/>background integrations)]
    end

    AT --> Cookie
    RT --> Cookie
    OT --> DB

    style AT fill:#90EE90
    style RT fill:#FFE4B5
    style OT fill:#87CEEB
```

### User Identity Linking

```mermaid
flowchart LR
    subgraph Providers ["Identity Providers"]
        GH[GitHub]
        GL[GitLab]
        BB[Bitbucket]
    end

    subgraph Keycloak ["Keycloak"]
        KC_User[Keycloak User<br/>sub: uuid<br/>email: user@example.com]
        
        subgraph FederatedIdentities ["Federated Identities"]
            FI_GH[GitHub Identity<br/>provider_id: github<br/>user_id: 12345]
            FI_GL[GitLab Identity<br/>provider_id: gitlab<br/>user_id: 67890]
        end
        
        KC_User --- FI_GH
        KC_User --- FI_GL
    end

    subgraph OpenHands ["OpenHands"]
        OH_User[User Record<br/>id: keycloak_sub<br/>current_org_id: uuid]
        Org[Organization<br/>id: uuid<br/>name: My Org]
        
        OH_User --> Org
    end

    GH --> FI_GH
    GL --> FI_GL
    BB -.->|Not linked| Keycloak
    KC_User --> OH_User
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `KEYCLOAK_SERVER_URL` | Internal Keycloak URL | `http://keycloak:8080` |
| `KEYCLOAK_SERVER_URL_EXT` | External Keycloak URL | `https://auth.all-hands.dev` |
| `KEYCLOAK_REALM_NAME` | Realm name | `openhands` |
| `KEYCLOAK_CLIENT_ID` | OAuth client ID | `openhands-web` |
| `KEYCLOAK_CLIENT_SECRET` | OAuth client secret | `***` |
| `KEYCLOAK_PROVIDER_NAME` | Default IdP hint | `github` |
| `KEYCLOAK_ADMIN_PASSWORD` | Admin API password | `***` |

### Keycloak Realm Configuration

The realm should be configured with:
- Identity Providers: GitHub, GitLab, Bitbucket
- Client: Web application with authorization code flow
- Token settings: Access token (5 min), Refresh token (30 min), Offline session (30 days)

## Token Manager

The `TokenManager` class (`token_manager.py`) provides:

```python
class TokenManager:
    async def get_keycloak_tokens(code, redirect_uri) -> tuple[str, str]
    async def refresh_tokens(refresh_token) -> tuple[str, str]
    async def get_user_info(access_token) -> dict
    async def get_user_info_from_user_id(user_id) -> dict
    async def disable_keycloak_user(user_id, email) -> None
    async def delete_keycloak_user(user_id) -> bool
```

## Session Expiration

```mermaid
flowchart TD
    subgraph SessionExpiry ["Session Expiration Scenarios"]
        A[User Session] --> B{Token Check}
        B -->|Access Token Expired| C[Try Refresh]
        C -->|Refresh Success| D[Continue Session]
        C -->|Refresh Failed| E{Offline Token?}
        E -->|Yes| F[Background Refresh]
        F -->|Success| D
        F -->|Failed| G[Session Expired]
        E -->|No| G
        G --> H[Redirect to Login]
    end

    subgraph Integrations ["Integration Impact"]
        I[GitHub Webhooks]
        J[GitLab Webhooks]
        K[Slack Bot]
        
        G -.->|Session expired message| I
        G -.->|Session expired message| J
        G -.->|Session expired message| K
    end
```

When a session expires, integrations show:
> "Your session has expired. Please login again at OpenHands Cloud and try again."

## Security Considerations

### Token Security
- Access tokens are short-lived (5 min) to minimize exposure
- Refresh tokens are stored in HTTP-only, secure cookies
- Tokens are signed with a server-side secret

### CSRF Protection
- State parameter in OAuth flow prevents CSRF attacks
- SameSite cookie attribute set appropriately per environment

### Session Hijacking Prevention
- Cookies are HTTP-only (no JavaScript access)
- Secure flag set in production
- Domain-scoped cookies

## Related Files

- `enterprise/server/auth/keycloak_manager.py` - Keycloak client singletons
- `enterprise/server/auth/token_manager.py` - Token operations
- `enterprise/server/auth/saas_user_auth.py` - User authentication logic
- `enterprise/server/routes/auth.py` - OAuth endpoints
- `enterprise/server/middleware.py` - Request authentication

## External Documentation

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OpenID Connect Spec](https://openid.net/connect/)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
