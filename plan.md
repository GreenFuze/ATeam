# WebSocket Architecture Refactoring Plan

## Overview
Refactor the current ChatEngine-based architecture to use dual WebSocket approach with FrontendAPI (backend → frontend) and BackendAPI (frontend → backend), eliminating ChatEngine and improving separation of concerns.

## Current Architecture Issues
- ChatEngine acts as unnecessary middleman
- Single WebSocket with mixed responsibilities
- Session management complexity
- Poor separation of concerns

## New Architecture

### Core Components
1. **FrontendAPI**: Backend → Frontend communication
2. **BackendAPI**: Frontend → Backend endpoints
3. **AgentManager**: Agent instance management with session mapping
4. **Agent**: Self-contained conversation management
5. **Objects Registry**: Global object management (renamed from manager_registry)

### WebSocket URLs
- FrontendAPI: `/ws/frontend-api` (backend → frontend)
- BackendAPI: `/ws/backend-api` (frontend → backend)

## Implementation Plan

### Phase 1: Rename and Restructure
- [x] Rename `manager_registry.py` to `objects_registry.py`
- [x] Update all imports across the codebase
- [x] Add FrontendAPI to objects_registry as global instance

### Phase 2: Create FrontendAPI
- [x] Create `frontend_api.py` with FrontendAPI class
- [x] Implement WebSocket connection management
- [x] Add methods for sending to frontend:
  - [x] `send_system_message(agent_id: str, content: str)`
  - [x] `send_agent_response(agent_id: str, response: LLMResponse)`
  - [x] `send_seed_messages(agent_id: str, messages: List[Message])`
  - [x] `send_error(agent_id: str, error: str)`
  - [x] `send_context_update(agent_id: str, context_data: ContextUsageData)`
  - [x] `send_notification(notification_type: str, message: str)`
- [x] Add to objects_registry as global instance

### Phase 3: Create BackendAPI
- [x] Create `backend_api.py` with BackendAPI class
- [x] Implement WebSocket endpoint `/ws/backend-api`
- [x] Add message handling methods:
  - [x] `handle_chat_message(agent_id: str, session_id: str, message: str)` (async)
  - [x] `handle_agent_refresh(agent_id: str, session_id: str)` (async)
  - [x] `handle_session_management(session_id: str, action: str)` (sync)
- [x] Implement session_id → agent_instance mapping via AgentManager

### Phase 4: Update AgentManager
- [x] Add session management methods:
  - [x] `create_agent_session(agent_id: str) -> str` (returns session_id)
  - [x] `get_agent_by_session(session_id: str) -> Agent`
  - [x] `session_id` format: `[agent_name]_XXX` (XXX = random number)
- [x] Remove ChatEngine dependency
- [x] Update agent instance creation to include FrontendAPI dependency

### Phase 5: Update Agent Class
- [x] Remove ChatEngine dependencies
- [x] Add FrontendAPI dependency injection
- [x] Update `get_response()` to use FrontendAPI for sending responses
- [x] Ensure conversation history is managed in memory (no file I/O yet)
- [x] Update conversation context building to use existing methods

### Phase 6: Frontend Implementation
- [x] Create dual WebSocket connection manager
- [x] Implement auto-reconnection with exponential backoff
- [x] Create "Connection closed - retrying" dialog with retry count
- [x] Update AgentChat component to use new WebSocket architecture
- [x] Implement message routing between FrontendAPI and BackendAPI

### Phase 7: Chat Window Flow Implementation
- [x] Frontend: Show "Loading agent" when chat window opens
- [x] Backend: Create new agent instance via AgentManager
- [x] Backend: Generate session_id and return to frontend
- [x] Backend: Send system message and seed messages via FrontendAPI
- [x] Frontend: Display system message and seeds before user can type

### Phase 8: Remove ChatEngine
- [x] Remove `chat_engine.py` file
- [x] Update all imports and references
- [x] Remove ChatEngine from objects_registry
- [x] Update main.py to use new architecture

### Phase 9: Update Main.py
- [x] Remove ChatEngine endpoints
- [x] Add BackendAPI WebSocket endpoint
- [x] Add FrontendAPI WebSocket endpoint
- [x] Update error handling to use FrontendAPI

### Phase 10: Testing and Validation
- [x] Test agent creation and session management
- [x] Test dual WebSocket connections
- [x] Test auto-reconnection functionality
- [x] Test error handling (sync vs async)
- [x] Test system message and seed message display
- [x] Validate conversation flow end-to-end

## Key Implementation Details

### Session ID Generation
```python
def create_agent_session(self, agent_id: str) -> str:
    agent_config = self.get_agent_config(agent_id)
    session_id = f"{agent_config.name}_{random.randint(100, 999)}"
    # Create agent instance and store mapping
    return session_id
```

### Agent Instance Management
```python
def get_agent_by_session(self, session_id: str) -> Agent:
    if session_id not in self.session_to_agent:
        raise ValueError(f"Session '{session_id}' not found")
    return self.session_to_agent[session_id]
```

### FrontendAPI Global Instance
```python
# objects_registry.py
frontend_api = FrontendAPI()

def frontend_api() -> FrontendAPI:
    return frontend_api
```

### BackendAPI Message Handling
```python
async def handle_chat_message(self, agent_id: str, session_id: str, message: str):
    try:
        agent = agent_manager().get_agent_by_session(session_id)
        response = await agent.get_response(message)
        # Response sent via FrontendAPI in agent.get_response()
    except Exception as e:
        frontend_api().send_error(agent_id, str(e))
```

## Success Criteria
- [x] ChatEngine completely removed
- [x] Dual WebSocket architecture working
- [x] Agent instances manage their own conversations
- [x] Session management via AgentManager
- [x] Auto-reconnection working on frontend
- [x] System messages and seeds displayed correctly
- [x] Error handling working for both sync and async calls
- [x] No regression in existing functionality

## Files to Create/Modify
### New Files
- `backend/frontend_api.py`
- `backend/backend_api.py`
- `frontend/src/services/FrontendAPIService.ts`
- `frontend/src/services/BackendAPIService.ts`
- `frontend/src/services/ConnectionManager.ts`
- `frontend/src/components/ConnectionDialog.tsx`

### Modified Files
- `backend/manager_registry.py` → `backend/objects_registry.py`
- `backend/agent_manager.py`
- `backend/agent.py`
- `backend/main.py`
- `frontend/src/components/AgentChat.tsx`
- All files importing from manager_registry

### Removed Files
- `backend/chat_engine.py` 