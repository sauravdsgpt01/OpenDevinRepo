# V0 to V1 Migration Checklist

## Current State

- V0 vs V1 is determined by `conversation_version` field on Conversation object
- Both versions currently coexist with "unified" hooks routing between them
- V1 uses runtime URLs + session API keys; V0 uses legacy cookie-based auth

---

## V0 Files to Remove

### Hooks
- [ ] `src/hooks/use-v0-handle-ws-events.ts`
- [ ] `src/hooks/use-v0-handle-runtime-active.ts`
- [ ] `src/hooks/mutation/use-upload-files.ts` (V0 version, no prefix)

### API Services
- [ ] `src/api/conversation-service/conversation-service.api.ts` (V0, no prefix)
- [ ] `src/api/git-service/git-service.api.ts` (V0, no prefix)

### Types
- [ ] `src/types/core/` (entire V0 types directory)
  - `src/types/core/index.ts`
  - `src/types/core/base.ts`
  - `src/types/core/actions.ts`
  - `src/types/core/observations.ts`
  - `src/types/core/guards.ts`
  - `src/types/core/variances.ts`

### Contexts / Providers
- [ ] `src/context/ws-client-provider.tsx` (V0 WebSocket provider)
- [ ] `src/context/conversation-subscriptions-provider.tsx` (V0 subscription logic)

### Components
- [ ] `src/wrapper/v0-event-handler.tsx`
- [ ] `src/components/shared/buttons/confirmation-buttons.tsx` (V0, no prefix)
- [ ] `src/components/features/chat/messages.tsx` (V0, imported as `V0Messages`)
- [ ] `src/components/features/chat/event-message.tsx` (V0 event renderer)
- [ ] `src/components/features/chat/event-message-components/` (entire V0 directory)
  - `error-event-message.tsx`
  - `finish-event-message.tsx`
  - `generic-event-message-wrapper.tsx`
  - `likert-scale-wrapper.tsx`
  - `mcp-event-message.tsx`
  - `microagent-status-wrapper.tsx`
  - `observation-pair-event-message.tsx`
  - `reject-event-message.tsx`
  - `task-tracking-event-message.tsx`
  - `user-assistant-event-message.tsx`

### Utilities
- [ ] `src/api/conversation.utils.ts` (handles both, simplify after V0 removal)
- [ ] `src/utils/git-status-mapper.ts` (V1→V0 mapping, remove after V0 gone)

### Tests
- [ ] `__tests__/components/features/chat/messages.test.tsx` (V0 Messages test)
- [ ] `__tests__/components/event-message.test.tsx` (V0 EventMessage test)

---

## V1 Files to Rename (after V0 removal)

### Hooks
- [ ] `src/hooks/mutation/use-v1-pause-conversation.ts` → `use-pause-conversation.ts`
- [ ] `src/hooks/mutation/use-v1-resume-conversation.ts` → `use-resume-conversation.ts`
- [ ] `src/hooks/mutation/use-v1-upload-files.ts` → `use-upload-files.ts`

### API Services
- [ ] `src/api/conversation-service/v1-conversation-service.api.ts` → `conversation-service.api.ts`
- [ ] `src/api/conversation-service/v1-conversation-service.types.ts` → `conversation-service.types.ts`
- [ ] `src/api/git-service/v1-git-service.api.ts` → `git-service.api.ts`

### Stores
- [ ] `src/stores/v1-conversation-state-store.ts` → `conversation-state-store.ts`

### Components
- [ ] `src/components/shared/buttons/v1-confirmation-buttons.tsx` → `confirmation-buttons.tsx`
- [ ] `src/components/v1/chat/` → `src/components/chat/` (or merge into features/chat)

### Types
- [ ] `src/types/v1/` → `src/types/core/` (or just `src/types/`)

### Tests
- [ ] `__tests__/api/v1-git-service.test.ts` → `git-service.test.ts`
- [ ] `__tests__/components/v1/chat/` → `__tests__/components/chat/`

---

## Unified Wrappers to Remove (after V0 removal)

These exist only to route between V0 and V1 implementations:

### Hooks
- [ ] `src/hooks/mutation/use-unified-upload-files.ts`
- [ ] `src/hooks/mutation/use-unified-start-conversation.ts`
- [ ] `src/hooks/mutation/use-unified-stop-conversation.ts`
- [ ] `src/hooks/query/use-unified-git-diff.ts`
- [ ] `src/hooks/query/use-unified-get-git-changes.ts`
- [ ] `src/hooks/query/use-unified-vscode-url.ts`
- [ ] `src/hooks/query/use-unified-active-host.ts`
- [ ] `src/hooks/use-unified-websocket-status.ts`

### Providers
- [ ] `src/contexts/websocket-provider-wrapper.tsx` (replace with direct V1 provider)

### Utilities
- [ ] `src/hooks/mutation/conversation-mutation-utils.ts` (simplify, remove V0 branches)

---

## Safe Removal Order

1. Confirm no V0 conversations remain in production
2. Add `@deprecated` JSDoc to all V0 files (visibility without breaking)
3. Remove V0 hooks and wrappers
4. Remove V0 API services
5. Remove V0 types (`src/types/core/`)
6. Simplify unified hooks → direct V1 calls
7. Remove unified wrappers entirely
8. Rename V1 files to default names
9. Remove `conversation_version` checks throughout codebase

---

## Pre-Removal Testing

- [ ] All V1 equivalents have test coverage matching or exceeding V0
- [ ] E2E tests pass with V1-only code paths
- [ ] No runtime errors when V0 code paths are unreachable
- [ ] Verify git status display works without `git-status-mapper.ts`

---

## Files Marked @deprecated

- [x] `OpenHandsParsedEvent` type in `src/types/core/index.ts`
- [x] `V0_WebSocketStatus` type in `src/context/ws-client-provider.tsx`
- [x] `src/hooks/use-v0-handle-ws-events.ts` (file-level)
- [x] `src/hooks/use-v0-handle-runtime-active.ts` (file-level)
- [x] `src/hooks/mutation/use-upload-files.ts` (file-level)
- [x] `src/api/conversation-service/conversation-service.api.ts` (V0-specific methods: `uploadFiles`, `startConversation`, `stopConversation`, `getVSCodeUrl`, `getWebHosts`)
- [x] `src/api/git-service/git-service.api.ts` (V0-specific methods: `getGitChanges`, `getGitChangeDiff`)
- [x] `src/context/ws-client-provider.tsx` (file-level)
- [x] `src/wrapper/v0-event-handler.tsx` (file-level)
- [x] `src/components/shared/buttons/confirmation-buttons.tsx` (file-level)
- [x] `src/types/core/base.ts` (file-level)
- [x] `src/types/core/actions.ts` (file-level)
- [x] `src/types/core/observations.ts` (file-level)
- [x] `src/types/core/guards.ts` (file-level)
- [x] `src/types/core/variances.ts` (file-level)
- [x] `src/components/features/chat/messages.tsx` (file-level)
- [x] `src/components/features/chat/event-message.tsx` (file-level)
- [x] `src/components/features/chat/event-message-components/error-event-message.tsx` (file-level)
- [x] `src/components/features/chat/event-message-components/finish-event-message.tsx` (file-level)
- [x] `src/components/features/chat/event-message-components/generic-event-message-wrapper.tsx` (file-level)
- [x] `src/components/features/chat/event-message-components/likert-scale-wrapper.tsx` (file-level)
- [x] `src/components/features/chat/event-message-components/mcp-event-message.tsx` (file-level)
- [x] `src/components/features/chat/event-message-components/microagent-status-wrapper.tsx` (file-level)
- [x] `src/components/features/chat/event-message-components/observation-pair-event-message.tsx` (file-level)
- [x] `src/components/features/chat/event-message-components/reject-event-message.tsx` (file-level)
- [x] `src/components/features/chat/event-message-components/task-tracking-event-message.tsx` (file-level)
- [x] `src/components/features/chat/event-message-components/user-assistant-event-message.tsx` (file-level)
- [x] `__tests__/components/features/chat/messages.test.tsx` (file-level)
- [x] `__tests__/components/event-message.test.tsx` (file-level)

---

## Notes

- `isV0Event()` type guard lives in `src/types/v1/type-guards.ts` (can be deleted with V0)
- `git-status-mapper.ts` converts V1 git statuses to V0 format for UI compatibility
- Some shared components (e.g., in `features/chat/`) have V0/V1 conditional branches that need cleanup
