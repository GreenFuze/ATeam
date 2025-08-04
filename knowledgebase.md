# ATeam Multi-Agent System - Knowledge Base

## Project Overview
ATeam is a full-stack web agent system using Python FastAPI backend and React frontend, featuring a pluggable multi-agent architecture with LLM integration using the `llm` Python package.

## Architecture Summary

### Backend (Python/FastAPI)
- **FastAPI**: Modern async web framework serving both API and frontend static files
- **LLM Integration**: Using `llm` package for multi-provider support (OpenAI, Anthropic, Google, Local)
- **Multi-Agent System**: Pluggable agent architecture with YAML-based configuration
- **Tool System**: Dynamic Python tool loading and execution
- **WebSocket Support**: Real-time chat communication
- **Single Server Setup**: Backend serves built frontend static files from `backend/static/`
- **Strict Typing**: Pydantic models ensure type safety across the codebase
- **Dynamic Model Management**: ModelsManager for runtime model discovery and settings
- **Schema Management**: SchemaManager for JSON schema CRUD operations
- **Context Window Tracking**: Real-time context usage calculation and display
- **Global Notification System**: System health monitoring with proactive issue detection

### Frontend (React/TypeScript)
- **React 18 + TypeScript**: Modern UI framework with type safety
- **Mantine v7**: UI component library with dark mode
- **TailwindCSS**: Utility-first CSS framework
- **Vite**: Build tool for production static files
- **Dark Mode**: Consistent dark theme throughout
- **Enhanced Model Settings**: Dynamic forms with proper field types
- **Global Notifications**: System health monitoring and alerts
- **Context Progress**: Visual context window usage tracking
- **Model Warning Icons**: Visual indicators for models needing configuration

### Development Workflow
- **Single Server**: Backend serves built frontend static files from `backend/static/`
- **Build Process**: PowerShell script (`build_and_run.ps1`) builds frontend and copies to backend
- **Production Mode**: Backend serves both API and frontend from port 8000
- **Type Safety**: Pydantic validation ensures data integrity between frontend and backend

## Implementation Status

### ✅ Core Features
- **Multi-Agent System**: YAML-based agent configuration with full CRUD operations
- **LLM Integration**: Full integration with `llm` package and multiple providers
- **Tool System**: Custom tool descriptor and executor with dynamic Python tool loading and execution
- **Real-time Communication**: WebSocket-based chat system with centralized connection management
- **Configuration Management**: YAML-based configuration files (agents.yaml, providers.yaml, models.yaml, prompts.yaml)
- **Provider Management**: Support for OpenAI, Anthropic, Google, and local models
- **Dynamic Model Management**: Runtime discovery of models and their capabilities
- **Schema Management**: JSON schema CRUD operations for structured outputs
- **Context Window Tracking**: Real-time context usage calculation and visualization
- **Global Notification System**: Real-time WebSocket-based error/warning notifications with detailed dialogs
- **Enhanced Prompt Management**: Full CRUD operations with specialized editing interfaces for different prompt types
- **Comprehensive Error Handling**: Fail-fast error handling with proper exception propagation and detailed error messages
- **Custom Conversation Management**: Custom message history management without LLM package conversation object bias
- **Structured LLM Responses**: Pydantic-based structured response system with type safety and validation

### ✅ UI/UX Features
- **Dark Mode**: Consistent dark theme throughout with proper contrast
- **Two-Tab Sidebar**: Agents tab (shows agent list) and Settings tab (Tools, Models, Providers, Prompts, Schemas)
- **Agent Management**: Full CRUD operations with modal interface and delete confirmation
- **Chat Interface**: Multiline input with context window progress tracking
- **Enhanced Message Display**: Multiple view modes (Markdown, Plain Text, Raw JSON), action-based icons, reasoning toggle, and proper tooltips
- **Settings Organization**: Properly separated sections for different configuration types
- **Empty States**: Proper empty states when no data exists
- **Responsive Design**: Mobile-friendly layout with full-screen utilization
- **Enhanced Model Settings**: Dynamic forms with proper field types and validation
- **Global Notifications**: System health monitoring with color-coded alerts
- **Model Groups**: Separate sections for chat models and embedding models
- **Model Warning Icons**: Orange warning icons for models without context window sizes
- **Enhanced Prompt Management**: Large modal dialogs with specialized editing interfaces for system and seed prompts

### ✅ Development & Deployment Features
- **Single Server Setup**: Backend serves built frontend static files
- **Build Automation**: PowerShell script handles all build steps with TypeScript compilation check
- **Error Handling**: Comprehensive error reporting and debugging with fail-fast philosophy
- **Monitoring**: Real-time system health and performance monitoring
- **Provider Discovery**: Automatic discovery of LLM providers and model counts from `llm` package
- **Strict Typing**: Pydantic models for all data structures with compile-time validation
- **Dynamic Schema Extraction**: Runtime extraction of model inference settings without loading models
- **Fail-Fast Architecture**: System immediately stops on errors instead of continuing in invalid state

## Recent Enhancements

### ✅ Major System Refactoring - WebSocket Communication & Custom Conversation Management (Latest Update)
The ATeam system has undergone a comprehensive refactoring to implement WebSocket-based real-time communication, custom conversation management, and proper tool integration without relying on the `llm` package's conversation object.

#### Key Architectural Changes
- **WebSocket Flow**: All non-user messages sent via WebSocket from backend to frontend
- **Custom Conversation Management**: Replaced `llm` conversation object with custom `List[Message]` for conversation history
- **Structured LLM Responses**: All responses follow structured JSON format with Pydantic validation
- **Custom Tool Integration**: Uses custom tool descriptor and executor instead of `llm` package tool system
- **Type Safety**: Complete type safety with Pydantic models throughout the system
- **Enhanced Message Display**: Advanced message display system with multiple view modes and action-based icons

#### Technical Implementation
- **New Files Created**:
  - `backend/tool_descriptor.py` - Tool description generation for LLM prompts
  - `backend/tool_executor.py` - Dynamic tool execution with type conversion
  - `backend/websocket_manager.py` - Centralized WebSocket connection management

- **Major Files Refactored**:
  - `backend/schemas.py` - Added structured response classes (ChatResponse, ToolCallResponse, etc.)
  - `backend/agent.py` - Complete refactoring for custom conversation management
  - `backend/chat_engine.py` - WebSocket integration and cleanup
  - `backend/tool_manager.py` - New tool system integration
  - `backend/main.py` - WebSocket endpoint updates
  - `frontend/src/types/index.ts` - Updated message types
  - `frontend/src/components/AgentChat.tsx` - New WebSocket flow
  - `frontend/src/components/MessageDisplay.tsx` - Enhanced message display with multiple view modes

#### Message Flow Architecture
1. **User sends message** → Frontend adds to local state
2. **Frontend sends via WebSocket** → Backend receives
3. **Backend processes with agent** → Agent builds conversation context
4. **Agent gets LLM response** → Parses into structured format
5. **Agent handles action** → Executes tools, delegates, or responds
6. **Backend sends via WebSocket** → Frontend receives and displays

#### Structured Response System
- **Base Class**: `StructuredResponse` with common fields (action, reasoning)
- **Response Types**: `ChatResponse`, `ToolCallResponse`, `ToolReturnResponse`, `AgentDelegateResponse`, `AgentCallResponse`, `AgentReturnResponse`, `RefinementResponse`
- **Validation**: Pydantic models ensure type safety and proper validation
- **Error Handling**: Detailed exceptions for invalid JSON or schema violations

#### Tool System Refactoring
- **Custom Tool Descriptor**: `tools_to_prompt()` and `class_to_prompt()` functions
- **Dynamic Tool Executor**: `run_tool()` with dynamic module loading and type conversion
- **No LLM Package Bias**: Tools work without `llm` package's tool bias
- **Support for Functions and Classes**: Both standalone functions and class methods supported

#### WebSocket Communication
- **Centralized Management**: `WebSocketManager` class for connection tracking
- **Agent-Specific Connections**: Track connections by agent ID
- **Message Types**: `system_message`, `seed_message`, `agent_response`, `connection_established`, `error`
- **Real-time Updates**: All agent actions sent via WebSocket to frontend

#### Conversation Management
- **Custom Message History**: `self.messages: List[Message]` instead of `llm` conversation object
- **Manual Context Building**: `_build_conversation_context()` constructs full conversation for LLM
- **System Prompts**: Included in every request dynamically
- **Seed Messages**: Loaded separately and included in conversation context

#### Code Cleanup
- **Removed Unused Code**: All `llm.conversation` usage eliminated
- **Removed Unused Methods**: `_execute_tool()`, `_process_tool_result()`, `_delegate_to_agent()`, `_implements_llm_toolbox()`
- **Clean Imports**: Removed unused imports and dependencies
- **Updated Schema Fields**: Removed `NORMAL_RESPONSE`, added new message types

#### Success Criteria Met
1. ✅ **WebSocket Flow**: All non-user messages delivered via WebSocket
2. ✅ **Tool Integration**: Tools work without `llm` package bias
3. ✅ **Response Structure**: All responses follow structured format
4. ✅ **Error Handling**: Proper error propagation and display
5. ✅ **Type Safety**: Complete type safety throughout the system
6. ✅ **Performance**: No degradation in response times
7. ✅ **Reliability**: Stable WebSocket connections and message delivery
8. ✅ **Code Cleanliness**: No unused code, clean imports, no dead paths
9. ✅ **Enhanced Message Display**: Multiple view modes (Markdown, Plain Text, Raw JSON) with action-based icons
10. ✅ **User Experience**: Improved message visualization with reasoning toggle and action icons

#### Impact
- **🚀 Real-time Communication**: WebSocket-based real-time updates
- **🔧 Custom Tool System**: No LLM package bias, full control over tool execution
- **📊 Structured Responses**: Consistent JSON format with proper validation
- **🛡️ Type Safety**: Complete type safety with Pydantic models
- **🧹 Clean Architecture**: No unused code, proper separation of concerns
- **⚡ Performance**: Efficient conversation management without LLM package limitations
- **🎨 Enhanced UI**: Advanced message display with multiple view modes and action-based icons
- **👥 Better UX**: Improved message visualization with reasoning toggle and proper tooltips

### ✅ Comprehensive Error Handling Implementation
The application implements a robust **FAIL-FAST** error handling philosophy throughout all components, ensuring the system never continues running in an invalid state:

#### Key Features
- **FAIL-FAST PRINCIPLE**: All errors are immediately raised as exceptions instead of being logged and ignored
- **PROPER ERROR PROPAGATION**: Errors bubble up to API endpoints with appropriate HTTP status codes
- **DETAILED ERROR MESSAGES**: Specific, actionable error messages with context information
- **WEB SOCKET ERROR HANDLING**: Real-time error responses with detailed suggestions
- **NO SILENT FAILURES**: System immediately stops when invalid state is detected

#### Technical Implementation
- **Agent Class (`backend/agent.py`)**:
  - **`_load_prompts()`**: Raises `ValueError` for missing prompts with detailed context
  - **`_load_tools()`**: Raises `ValueError` for missing tools or tool manager
  - **`_initialize_conversation()`**: Raises `ValueError` for missing models
  - **`add_message()`**: Raises `RuntimeError` for uninitialized conversation
  - **`get_response()`**: Raises `RuntimeError` for uninitialized conversation

- **Manager Classes**:
  - **`AgentManager`**: Removed try-catch blocks, now raises exceptions naturally
  - **`ToolManager`**: Raises `RuntimeError` for tool discovery errors
  - **`SchemaManager`**: Raises `RuntimeError` for schema loading and file errors
  - **`PromptManager`**: Already properly raises `FileNotFoundError` for missing prompts
  - **`ModelsManager`**: Raises `RuntimeError` for model loading and discovery errors
  - **`ProviderManager`**: Raises `ValueError` for invalid providers, `RuntimeError` for file errors

- **API Endpoints (`backend/main.py`)**:
  - **REST API**: Proper exception handling with specific HTTP status codes
    - `ValueError` → HTTP 400 (Bad Request)
    - `RuntimeError` → HTTP 500 (Internal Server Error)
    - Other exceptions → HTTP 500 (Internal Server Error)
  - **WebSocket API**: Detailed error responses with suggestions for fixing issues

#### Error Types and Handling
- **`ValueError`**: For validation errors (missing prompts, tools, models, invalid configurations)
- **`RuntimeError`**: For runtime errors (conversation initialization failures, file system errors)
- **`FileNotFoundError`**: For missing prompt files (from prompt manager)
- **`UnknownModelError`**: For missing models (from llm package)

#### API Response Examples
```json
// REST API Error Response
{
  "detail": "Prompt 'assistant_system.md' not found for agent 'TestAgent'"
}

// WebSocket Error Response  
{
  "type": "error",
  "error": "Validation Error",
  "details": {
    "agent_id": "test-agent",
    "exception_type": "ValueError", 
    "exception_message": "Tool 'calculator' not found for agent 'TestAgent'",
    "suggestion": "Check agent configuration (prompts, tools, model)"
  }
}
```

#### Critical Security Improvements
**Before (DANGEROUS)**:
- System logged errors but continued running in invalid state
- Could process messages with missing prompts/tools/models
- Silent failures with no user visibility
- Generic error messages without context

**After (SAFE)**:
- System immediately stops when errors occur
- No processing with missing or invalid resources
- Clear, actionable error messages for users
- Proper HTTP status codes for API consumers
- Detailed error information for debugging

#### Impact
- **🚨 CRITICAL SECURITY**: Application never continues running in invalid state
- **🔍 BETTER DEBUGGING**: Specific error messages with full context
- **👥 USER EXPERIENCE**: Clear, actionable error responses
- **🛡️ RELIABILITY**: Fail-fast approach prevents cascading failures
- **📊 MONITORING**: Proper error tracking and reporting

### ✅ Global Notification System Implementation
The notification system has been completely implemented with real-time WebSocket delivery and comprehensive error/warning management:

#### Key Features
- **Real-time WebSocket Notifications**: Three dedicated WebSocket endpoints for errors, warnings, and info notifications
- **Rich Frontend Display**: Mantine-based notification system with clickable dialogs for detailed information
- **Comprehensive Error Coverage**: All backend print statements replaced with structured notifications
- **Context-Rich Logging**: Each notification includes relevant context for debugging
- **Automatic Reconnection**: Frontend automatically reconnects with exponential backoff
- **Professional UI**: Clean notification display with proper styling and user interaction

#### Technical Implementation
- **Backend Changes**:
  - Created `notification_manager.py` with WebSocket-based notification broadcasting
  - Created `notification_utils.py` with utility functions for easy integration
  - Added WebSocket endpoints: `/ws/notifications/errors`, `/ws/notifications/warnings`, `/ws/notifications/info`
  - Replaced ALL print statements in backend files with structured logging:
    - `agent.py` - Agent initialization and conversation errors
    - `models_manager.py` - Configuration and discovery errors
    - `agent_manager.py` - Agent loading and creation errors
    - `main.py` - API endpoint and WebSocket errors
    - `provider_manager.py` - Provider configuration errors
    - `prompt_manager.py` - Prompt loading and metadata errors
    - `tool_manager.py` - Tool discovery errors
    - `schema_manager.py` - Schema file errors
  - Enhanced error handling with detailed context information

- **Frontend Changes**:
  - Created `NotificationService.ts` with WebSocket connection management
  - Implemented rich notification display with Mantine components
  - Added clickable notifications with detailed error dialogs
  - Automatic reconnection with exponential backoff strategy
  - Proper cleanup on page unload
  - Fallback to console logging if WebSocket unavailable

#### Notification Types
- **Errors**: Agent failures, tool loading errors, conversation errors, API failures, configuration issues
- **Warnings**: Missing tool manager, tool not found, prompt not found, configuration files missing
- **Info**: System status updates, successful operations, directory creation

#### User Experience
- **Immediate Visibility**: Errors and warnings appear instantly as popup notifications
- **Detailed Information**: Click notifications to see full stack traces and context
- **No Missed Issues**: All backend issues are immediately visible in the frontend
- **Professional UI**: Clean, modern notification system with proper styling
- **Context-Rich**: Each notification includes relevant context for debugging

#### Impact
- **Dramatically Improved Debugging**: No more hidden errors in console output
- **Real-time Issue Detection**: Immediate visibility of all backend problems
- **Professional Error Handling**: Structured error reporting with detailed information
- **Better User Experience**: Clear, actionable notifications instead of silent failures

### Enhanced Tool Management with Signature Display (July 2025)
The tool management system has been significantly enhanced with dynamic discovery and comprehensive signature display capabilities:

#### Key Features
- **Dynamic Tool Discovery**: Automatic discovery of Python functions and classes from the tools directory
- **Signature Extraction**: Complete function and method signatures with parameter types and return types
- **YAML Configuration Removal**: Eliminated `tools.yaml` in favor of dynamic file system discovery
- **Comprehensive UI Display**: Signatures shown in all tool views (Settings, ToolsPage, ToolViewer)
- **Method Expansion**: Expandable class methods with individual signatures and descriptions
- **Docstring Integration**: Automatic detection and display of function/method documentation
- **Warning System**: Visual indicators for missing docstrings with helpful tooltips
- **Type Safety**: Complete type safety with enhanced TypeScript interfaces
- **Simplified Interface**: Clean UI without refresh buttons - users can use browser refresh to see new tools
- **Dual-Capability Model Support**: Models supporting both chat and embedding capabilities now appear in both sections with original model names

#### Technical Implementation
- **Backend Changes**:
  - Enhanced `ToolManager` with `_get_function_signature()` method using Python's `inspect.signature()`
  - Dynamic discovery of public functions (not starting with `_`) and `llm.Toolbox` classes
  - Signature extraction with automatic `self` parameter cleanup for methods
  - Error handling with graceful fallback to `(...)` for signature extraction failures
  - Removed all CRUD operations (create, update, delete) as tools are now read-only
  - New API endpoint `/api/tools/directory/path` to expose tools directory location

- **Frontend Changes**:
  - Enhanced `ToolConfig` and `ToolMethod` interfaces with optional `signature` field
  - Updated `SettingsPage.tsx` with signature display for functions and expandable method signatures
  - Enhanced `ToolViewer.tsx` with dedicated signature sections for functions and methods
  - Updated `ToolsPage.tsx` with signature display in tool cards and expanded method views
  - Monospace font styling for signatures with proper visual hierarchy
  - Removed "View" buttons and CRUD operations from tool interfaces
  - Removed refresh buttons from both SettingsPage and ToolsPage - users can use browser refresh instead

#### Tool Discovery Process
- **Function Discovery**: Scans all `.py` files (excluding `__init__.py`) for public functions
- **Class Discovery**: Identifies classes implementing `llm.Toolbox` interface
- **Method Extraction**: Extracts all public methods from discovered classes
- **Signature Analysis**: Uses `inspect.signature()` to extract complete function/method signatures
- **Metadata Collection**: Gathers docstrings, file paths, and relative paths for display

#### Signature Examples
- **Function `add`**: `add(x: int, y: int) -> int`
- **Memory Class Methods**:
  - `append(key: str, value: str)`
  - `get(key: str)`
  - `keys()` (no parameters)
  - `set(key: str, value: str)`

#### User Experience Improvements
- **Visual Hierarchy**: Signatures displayed in monospace font with dimmed styling
- **Expandable Methods**: Chevron buttons to expand/collapse class method details
- **Warning Indicators**: Orange warning triangles for missing docstrings
- **Consistent Display**: Signatures shown across all tool viewing interfaces
- **Directory Path Display**: Tools directory path shown below the "Available Tools" title
- **Method Counts**: Clear indication of how many methods each class contains
- **Simplified Interface**: Clean UI without refresh buttons - users can use browser refresh (F5) to see new tools

### Enhanced Prompt Management (July 2025)
The prompt management system has been significantly enhanced with comprehensive editing capabilities and improved user experience:

#### Key Features
- **Full CRUD Operations**: Create, read, update, and delete prompts with persistent metadata
- **YAML-based Metadata**: Prompt metadata (name, type) stored in `prompts.yaml` for version control
- **Specialized Editing Interfaces**: Different editing experiences for system vs seed prompts
- **Large Modal Dialogs**: Percentage-based sizing (80% width, 95% max height) that adapts to content without horizontal scrolling
- **Enhanced MessageDisplay**: Reusable component that supports both view and edit modes with dynamic textarea sizing
- **Seed Prompt Editor**: Chat-like interface for creating simulated conversations with multiple roles
- **Type Safety**: Complete type safety with Pydantic models and TypeScript interfaces
- **Dynamic Content Sizing**: Textarea automatically resizes based on content (8-50 rows) with autosize functionality
- **Enhanced Menu Options**: Context-aware display options with edit/view mode switching

#### Technical Implementation
- **Backend Changes**:
  - New `prompts.yaml` file for metadata persistence
  - Enhanced `PromptManager` with YAML integration and metadata management
  - New API endpoints for seed prompt structured data (`/api/prompts/{name}/seed`)
  - Removed "agent" prompt type (reclassified as "system")
  - Added `UpdatePromptRequest`, `SeedMessage`, `SeedPromptData` schemas
  - JSON-based storage for seed prompts with markdown fallback for backward compatibility

- **Frontend Changes**:
  - Enhanced `MessageDisplay` component with editable mode and dynamic textarea sizing
  - New `SeedPromptEditor` component for chat-like editing with role selection
  - Larger `PromptEditor` modal (95% max height) with delete functionality
  - Updated API client with new endpoints for structured seed data
  - Changed "View" buttons to "Edit" buttons throughout the interface
  - Enhanced menu options with conditional display based on edit state

#### Prompt Types and Editing Experience
- **System Prompts**: 
  - Editable content with text/markdown toggle (default: text view for editing)
  - Large textarea (8-50 rows) with autosize functionality
  - Enhanced menu options: "Edit Content" when viewing, "View Content" when editing
  - Markdown/Plain Text options only available when not in edit mode
- **Seed Prompts**: 
  - Chat-like interface for creating simulated conversations
  - JSON-based storage format for LLM compatibility
  - Support for multiple roles (user, assistant, system) in any order
  - Backward compatibility with existing markdown-formatted seed prompts

#### User Experience Improvements
- **Dynamic Sizing**: Textarea starts at 8 rows minimum and can expand up to 50 rows based on content
- **Autosize Functionality**: Textarea automatically adjusts height to fit content
- **Better Typography**: Improved font size (14px) and line height (1.5) for readability
- **Context-Aware Menus**: Display options change based on current edit state
- **Large Modal Support**: Modal can use up to 95% of screen height for extensive content
- **Content Persistence**: Content properly loads and persists when switching between prompts

### ✅ Draggable System Prompts in Agent Settings (August 2025)
The agent settings dialog has been enhanced with a new draggable system prompts interface:

#### Key Features
- **Dropdown Selection**: Users can select system prompts from a dropdown list of available prompts
- **Add/Remove Functionality**: Easy addition and removal of prompts with visual feedback
- **Drag-and-Drop Reordering**: Prompts can be reordered by dragging and dropping
- **Order Preservation**: The order of prompts is saved in agents.yaml and maintained during agent execution
- **Visual Feedback**: Clear visual indicators for drag handles and remove buttons
- **Empty State**: Helpful message when no prompts are selected

#### Technical Implementation
- **Frontend Changes**:
  - Replaced checkbox-based system with dropdown + draggable list
  - Added `@dnd-kit/core`, `@dnd-kit/sortable`, and `@dnd-kit/utilities` for drag-and-drop functionality
  - Created `SortablePromptItem` component with drag handle and remove button
  - Implemented `DndContext` with proper sensors and collision detection
  - Added state management for selected prompt to add and drag operations
  - Enhanced UI with `ActionIcon` components for better user interaction
  - Added `IconGripVertical` and `IconX` icons for intuitive user interaction
  - Implemented `arrayMove` utility for smooth reordering operations

- **User Experience**:
  - Dropdown only shows prompts not already selected
  - Drag handle (grip icon) for intuitive reordering
  - Remove button (X icon) for easy prompt removal
  - Card-based layout for better visual separation
  - Responsive design that works on different screen sizes
  - Increased max height (300px) for better visibility of prompt list
  - Clear visual feedback with cursor changes and hover states

#### Order Management
- **Backend Integration**: Order is preserved in agents.yaml and used during agent execution
- **Real-time Updates**: Changes are immediately reflected in the UI
- **Validation**: Prevents duplicate prompts and handles edge cases
- **Persistence**: Order is maintained across agent sessions and restarts

#### Build and Deployment
- **Dependency Management**: All required `@dnd-kit` packages properly installed and configured
- **TypeScript Integration**: Full type safety with proper import statements
- **Production Build**: Frontend compiles successfully with all drag-and-drop functionality
- **Static File Serving**: Built frontend properly served from backend static directory

## File Organization
- `backend/agents.yaml` - Agent configurations
- `backend/providers.yaml` - LLM provider definitions (no models)
- `backend/models.yaml` - Model configurations with provider references
- `backend/prompts.yaml` - Prompt metadata (name, type) for persistence
- `backend/prompts/` - Directory containing markdown prompt files
- `backend/schemas/` - Directory containing JSON schema files
- `backend/tools/` - Directory containing Python tool files (dynamically discovered)

### Backend Core Files
- `backend/main.py` - FastAPI application with all endpoints and static file serving
- `backend/manager_registry.py` - Global manager registry with centralized initialization and aliases
- `backend/agent_manager.py` - Agent lifecycle management (fixed delete path issue)
- `backend/tool_manager.py` - Dynamic tool discovery and signature extraction
- `backend/provider_manager.py` - LLM provider management with strict typing
- `backend/models_manager.py` - Dynamic model discovery and settings management
- `backend/schema_manager.py` - JSON schema CRUD operations
- `backend/prompt_manager.py` - Prompt file management (fail fast implementation)
- `backend/chat_engine.py` - Chat processing logic with context window tracking
- `backend/schemas.py` - Pydantic data models and type definitions

### Frontend Structure
- `frontend/src/components/Sidebar.tsx` - Two-tab sidebar (Agents/Settings) with notifications
- `frontend/src/components/AgentsPage.tsx` - Agent list with empty state
- `frontend/src/components/SettingsPage.tsx` - Settings with conditional rendering, model groups, and tool signature display
- `frontend/src/components/AgentChat.tsx` - Enhanced chat interface with context tracking
- `frontend/src/components/AgentSettingsModal.tsx` - Agent configuration modal with draggable system prompts and delete functionality
- `frontend/src/components/MessageDisplay.tsx` - Message rendering component
- `frontend/src/components/ContextProgress.tsx` - Context window progress indicator with N/A state
- `frontend/src/components/ToolViewer.tsx` - Tool detail modal with signature display
- `frontend/src/pages/ToolsPage.tsx` - Dedicated tools page with expandable method signatures
- `frontend/src/api/index.ts` - API client with proper response handling
- `frontend/src/services/NotificationService.ts` - WebSocket-based notification service with Mantine components

## Current Implementation Status

### ✅ Completed Features
1. **Single Server Setup**: Backend serves built frontend static files
2. **YAML Configuration**: All configurations in dedicated YAML files
3. **Provider Management**: Complete provider and model management system
4. **UI Refinements**: Clean sidebar navigation, empty states, dark mode
5. **API Response Handling**: Proper response format handling in frontend
6. **Build Process**: Automated build and run script
7. **Agent Management**: Full CRUD operations with modal interface
8. **Chat Interface**: Enhanced with multiline input and context tracking
9. **Settings Organization**: Properly separated configuration sections
10. **Enhanced Message Display**: Multiple view modes (Markdown, Plain Text, Raw JSON), action-based icons, reasoning toggle, and proper tooltips
11. **Message Type System**: Complete message type handling with SYSTEM type support
12. **Dark Mode Messages**: All messages properly styled for dark theme readability
13. **Agent Deletion**: Delete functionality with confirmation dialog in settings modal
14. **Provider Discovery**: Automatic discovery of LLM providers with chat/embedding model counts
15. **Provider Edit UI**: Edit provider settings (API key requirements, environment variables, base URLs) through modal interface
16. **Provider Configuration Warnings**: Warning icons for discovered providers that need configuration
17. **Strict Provider Typing**: Pydantic models for provider data with compile-time validation
18. **Clear File Organization**: Renamed models.py to schemas.py for better context clarity
19. **Dynamic Model Management**: ModelsManager for runtime model discovery and settings
20. **Enhanced Model Settings**: Dynamic forms with proper field types and validation
21. **Context Window Integration**: Real-time context usage calculation and visualization
22. **Global Notification System**: System health monitoring with color-coded alerts
23. **Schema Management**: Complete CRUD operations for JSON schemas
24. **Model Groups**: Separate sections for chat models and embedding models
25. **Enhanced Badge System**: Comprehensive capability badges for models
26. **Type-Safe Data Handling**: Proper type conversion and validation throughout
27. **Model Warning Icons**: Visual indicators for models without context window sizes
28. **Streamlined Notifications**: Removed context window notifications from global system, replaced with model-specific warnings
29. **Dynamic Tool Discovery**: Automatic discovery of Python functions and classes from tools directory
30. **Tool Signature Display**: Complete function and method signatures with parameter types and return types
31. **Method Expansion**: Expandable class methods with individual signatures and descriptions
32. **Docstring Integration**: Automatic detection and display of function/method documentation
33. **Tool Warning System**: Visual indicators for missing docstrings with helpful tooltips
34. **Simplified Tool Interface**: Removed refresh buttons - users can use browser refresh to see new tools
35. **Dual-Capability Model Support**: Models supporting both chat and embedding now appear in both sections with the same ID but different flags
36. **Draggable System Prompts**: Agent settings now feature drag-and-drop reordering of system prompts with dropdown selection
37. **Frontend Build System**: Complete TypeScript compilation and production build with all dependencies properly configured
38. **Strict Schema Implementation**: Replaced all dictionary usage with Pydantic schemas for type safety and maintainability
39. **Context Progress Tooltip**: Enhanced tooltip showing "[tokens used]/[context window]" on hover
40. **File Logging Removal**: Removed file logging, keeping only console output for cleaner system
41. **Agent Class with LLM Integration**: New Agent class using llm package for conversations with tools
42. **Conversation Persistence**: Save/load conversations in agent_history directory as JSON files
43. **Lazy Loading Agent Instances**: AgentManager uses lazy loading for efficient memory usage
44. **LLMInterface Removal**: Eliminated redundant abstraction layer, direct Agent integration
45. **JSON Serialization Fix**: Proper response handling with `response.text()` method for llm package
46. **Manager Isolation Enforcement**: Strict enforcement of configuration file access through managers only
47. **System Prompts Integration**: Agent loads system prompts and seed prompts during conversation initialization
48. **Agent History API**: Dedicated endpoint for frontend to load conversation history from agent
49. **Frontend Message Source**: Frontend only reads messages from agent history, not from other sources
50. **Tool Manager Isolation**: Agent uses ToolManager for tool loading, maintains proper isolation
51. **Context Progress Bug Fix**: Eliminated incorrect frontend context calculations on initial load
52. **WebSocket Error Handling**: Proper handling of WebSocket disconnections to prevent ASGI errors
53. **Comprehensive Error Handling**: Fail-fast error handling with proper exception propagation throughout all components
54. **Agent Error Handling**: Agent class raises exceptions for missing prompts, tools, models, and conversation failures
55. **Manager Error Handling**: All manager classes properly raise exceptions instead of logging and continuing
56. **API Error Handling**: REST and WebSocket endpoints with proper HTTP status codes and detailed error responses
57. **Security Improvements**: System never continues running in invalid state, preventing silent failures
58. **Global Manager Registry**: Centralized manager management with aliases and no local copies
59. **Manager Aliases**: Direct function access (`agent_manager()`, `tool_manager()`, etc.) for current instances
60. **Centralized Initialization**: Single `initialize_managers()` function for all manager creation
61. **Simplified Dependencies**: No need to pass manager instances around components
62. **Cleaner Constructors**: Components don't require manager parameters
63. **No Stale References**: Always get current manager instance via function call
64. **Enhanced Message Display**: Multiple view modes (Markdown, Plain Text, Raw JSON) with action-based icons and reasoning toggle
65. **Action-Based Icons**: Secondary icons for LLM messages showing action type (CHAT_RESPONSE, USE_TOOL, etc.)
66. **Raw Message View**: Complete JSON structure display for debugging and analysis
67. **Reasoning Toggle**: User-controlled visibility of reasoning boxes in message metadata
68. **Proper Tooltips**: User messages show "User response" tooltip, LLM messages show action-specific tooltips

### 🔄 Current State
- **Application Running**: Server starts successfully on port 8000
- **Frontend Accessible**: Clean UI with proper navigation and dark mode
- **API Working**: All endpoints responding correctly
- **Agents Available**: 3 pre-configured agents (God, ToolBuilder, Assistant)
- **All Features Working**: Complete frontend improvements implemented
- **Enhanced Message Display**: Multiple view modes (Markdown, Plain Text, Raw JSON) with action-based icons and reasoning toggle
- **Dark Mode**: All messages readable with proper contrast and styling
- **Dynamic Models**: 29 chat models, 8 embedding models discovered
- **Context Tracking**: Real-time context usage with N/A state for missing context windows
- **Global Notifications**: System health monitoring with 0 warnings (all models configured)
- **Model Warning Icons**: No warning icons displayed (all models have context window sizes)
- **Dynamic Tools**: 2 tools discovered (add function, Memory class with 4 methods)
- **Tool Signatures**: Complete function and method signatures displayed with parameter types
- **Method Expansion**: Expandable class methods with individual signatures and descriptions
- **Simplified Interface**: Clean UI without refresh buttons - browser refresh works for tool updates
- **Dual-Capability Models**: `llama3.1:8b` now appears in both chat and embedding sections with the same ID but different flags
- **Draggable System Prompts**: Agent settings feature drag-and-drop reordering with dropdown selection for system prompts
- **Frontend Build**: Complete TypeScript compilation successful with all dependencies installed and configured
- **Strict Schemas**: All data structures use Pydantic models with type safety and validation
- **Context Progress Tooltips**: Detailed token information displayed on hover over progress rings
- **Console Logging**: Clean logging system without file output
- **Agent Class**: New Agent class with llm package integration and conversation persistence
- **Lazy Loading**: Efficient agent instance management with on-demand creation
- **Architecture Simplification**: Removed redundant LLMInterface layer, direct Agent integration
- **JSON Serialization Fixed**: Proper response handling with `response.text()` method
- **Manager Isolation**: Strict enforcement of configuration file access through managers only
- **Zeus Agent Working**: Agent responding correctly with proper text content instead of object references
- **Context Progress Bug Fix**: Eliminated incorrect frontend context calculations on initial load
- **System Prompts Integration**: Agent loads system prompts and seed prompts during conversation initialization
- **Agent History API**: Dedicated endpoint for frontend to load conversation history from agent
- **Frontend Message Source**: Frontend only reads messages from agent history, not from other sources
- **Tool Manager Isolation**: Agent uses ToolManager for tool loading, maintains proper isolation
- **WebSocket Error Handling**: Proper handling of WebSocket disconnections to prevent ASGI errors
- **System Prompts Fix**: Fixed system prompts integration by including them directly in messages sent to `chain()` method
- **LLM Package Integration**: Proper understanding of how `llm` package conversation object works with system prompts
- **Global Manager Registry**: Centralized manager management with aliases and no local copies
- **Manager Aliases**: Direct function access for current manager instances throughout the application
- **Centralized Initialization**: Single `initialize_managers()` function handles all manager creation
- **Simplified Dependencies**: No need to pass manager instances around components
- **Cleaner Constructors**: Components don't require manager parameters
- **No Stale References**: Always get current manager instance via function call
- **WebSocket Communication**: Real-time message delivery with proper error handling and connection management
- **Custom Conversation Management**: Manual message history management without LLM package conversation object bias
- **Structured LLM Responses**: Pydantic-based structured response system with type safety and validation
- **Custom Tool System**: Dynamic tool discovery, description generation, and execution without LLM package bias
- **Fail-Fast Architecture**: System immediately stops on errors instead of continuing in invalid state
- **Message Display Enhancements**: Advanced message visualization with multiple view modes and action-based icons

### 📋 Next Steps
- Test all new features with real agent interactions
- Implement monitoring dashboard
- Add comprehensive testing
- Create user documentation

## Recent Bug Fixes (Latest Update)

### ✅ Delete Agent Path Issue Fixed
- **Root Cause**: `os.makedirs('')` failed on Windows when `config_path` was relative
- **Issue**: `os.path.dirname("agents.yaml")` returns `''`, causing `[WinError 3] The system cannot find the path specified: ''`
- **Solution**: Added check `if dir_path:` before calling `os.makedirs()`
- **Impact**: Agent deletion now works correctly for both relative and absolute paths

### ✅ Strict Provider Typing Implementation
- **Root Cause**: Using dictionaries for provider data led to potential runtime errors and poor IDE support
- **Issue**: No type safety, difficult debugging, no autocomplete for provider fields
- **Solution**: Created `ProviderInfo` and `ProviderInfoView` Pydantic classes with strict typing
- **Impact**: Compile-time validation, better IDE support, clearer data flow, reduced bugs

### ✅ File Naming Clarity Improvement
- **Root Cause**: `models.py` conflicted with LLM "models" terminology, causing confusion
- **Issue**: Ambiguous file name in LLM application context
- **Solution**: Renamed to `schemas.py` to clearly indicate data structure definitions
- **Impact**: Better code organization, clearer context, improved maintainability
- **Cleanup**: Successfully removed old `models.py` file after confirming all imports updated

### ✅ Models Manager Implementation
- **Root Cause**: Need for dynamic model discovery and settings management
- **Issue**: Static models.yaml with hardcoded configurations, no runtime discovery
- **Solution**: Created `ModelsManager` with dynamic discovery from `llm` package
- **Implementation**:
  - **Dynamic Discovery**: `discover_models_from_llm()` finds all available models without loading them
  - **Schema Extraction**: `get_provider_model_schema()` extracts inference settings from provider Options classes
  - **Provider Support**: OpenAI (9 inference settings), Ollama (12 inference settings), embedding models
  - **Hybrid Storage**: User preferences in YAML, runtime schema from llm package
  - **API Endpoints**: GET/PUT/DELETE for models, settings schema endpoint
  - **Dynamic Forms**: Frontend renders inference settings fields based on provider schema with default values
  - **UI Improvements**: "Default" badge only for models using provider defaults, no "Configured" badge
- **Current Limitation**: Model-level settings schema (context window, model parameters) not yet implemented
- **Impact**: Dynamic model management, provider-agnostic inference settings, no model loading required
- **Status**: ✅ COMPLETE - Backend and frontend working, inference settings implemented
- **Next Step**: Implement separate model-level settings schema for instance configuration

### ✅ Enhanced Model Badge System
- **Root Cause**: Need for comprehensive model capability display
- **Issue**: Limited badge information, no distinction between model types
- **Solution**: Implemented comprehensive badge system with dynamic attribute detection
- **Implementation**:
  - **Chat Model Badges**: Vision, Attachments, Schema, Tools, Stream
  - **Embedding Model Badges**: Dimensions, Truncate, Binary, Text, Batch
  - **Dynamic Detection**: Uses `getattr()` to check for model capabilities at runtime
  - **Color Coding**: Different colors for different capability types
  - **Provider Agnostic**: Works with any provider that exposes these attributes
- **Impact**: Better model visibility, easier capability comparison, improved UX
- **Status**: ✅ COMPLETE - All badges working and tested

### ✅ Dual-Capability Model Support
- **Root Cause**: Models that support both chat and embedding capabilities were only showing in one section
- **Issue**: `llama3.1:8b` appeared only as embedding model despite supporting both chat and embedding
- **Solution**: Modified model discovery to allow the same model ID to appear in both sections with different flags
- **Implementation**:
  - **Dual-Capability Detection**: Added `is_chat_model` and `is_embedding_model` flags during discovery
  - **Same Model ID**: Models with both capabilities appear twice with the same ID but different `embedding_model` flags
  - **Independent Configuration**: Each capability can be configured separately (e.g., different context window sizes)
- **No Artificial IDs**: Uses original model ID from `llm` (e.g., `llama3.1:8b`) instead of creating artificial IDs
- **Capability-Specific Settings**: Each entry gets appropriate inference settings schema
- **Frontend Separation**: Chat section shows models with `embedding_model: false`, embedding section shows `embedding_model: true`
- **Impact**: Users can now configure dual-capability models independently for different use cases without artificial IDs
- **Status**: ✅ COMPLETE - Dual-capability models now appear in both sections with original model names

### ✅ Global Manager Registry Implementation (Latest Update)
- **Root Cause**: Need for centralized manager management and elimination of local manager copies
- **Issue**: Manager instances were being passed around and stored locally, creating potential stale references and complex dependency management
- **Solution**: Implemented global manager registry with centralized initialization and direct alias access
- **Implementation**:
  - **Global Manager Registry**: Created `manager_registry.py` with centralized manager initialization
  - **Manager Aliases**: Direct function aliases (`agent_manager()`, `tool_manager()`, etc.) for immediate access
  - **No Local Copies**: All components use manager aliases directly at point of use, never storing local references
  - **Centralized Initialization**: Single `initialize_managers()` function handles all manager creation
  - **Dependency Order**: Proper initialization order (tool_manager → agent_manager → others)
  - **Error Handling**: Clear error messages if managers not initialized
  - **Type Safety**: Proper type annotations with None handling for uninitialized state
- **Architecture Benefits**:
  - **Centralized Management**: All manager lifecycle managed in one place
  - **No Stale References**: Always get current manager instance via function call
  - **Simplified Dependencies**: No need to pass manager instances around
  - **Cleaner Constructors**: Components don't need manager parameters
  - **Better Separation**: Components focus on core functionality, not manager management
  - **Easier Testing**: Single initialization point for all managers
- **Technical Details**:
  - **Manager Registry**: `manager_registry.py` provides `initialize_managers()` and getter functions
  - **Direct Aliases**: `agent_manager()`, `tool_manager()`, `prompt_manager()`, etc. always return current instances
  - **No Local Storage**: Components call aliases directly, never assign to local variables
  - **Lazy Access**: Managers accessed only when needed, not stored in component state
  - **Type Safety**: Proper type annotations with `ManagerType | None` for uninitialized state
  - **Error Propagation**: Clear error messages if managers accessed before initialization
- **Impact**: Much cleaner architecture, centralized manager management, no stale references
- **Status**: ✅ COMPLETE - All backend files updated to use global manager registry

### ✅ LLMInterface Removal and Architecture Simplification
- **Root Cause**: Redundant abstraction layer causing JSON serialization issues and architectural violations
- **Issue**: `LLMInterface` was duplicating functionality already in `Agent` class and violating manager isolation
- **Solution**: Completely removed `LLMInterface` and simplified architecture
- **Implementation**:
  - **Eliminated LLMInterface**: Removed redundant abstraction layer entirely
  - **Direct Agent Integration**: ChatEngine now works directly with Agent instances via `agent_manager.get_agent_instance()`
  - **Fixed JSON Serialization**: Updated Agent class to use `response.text()` method instead of `str(response)`
  - **Manager Isolation Enforcement**: Removed direct YAML access from non-manager files
  - **Path Configuration Fix**: Updated ModelsManager to use correct relative path (`"models.yaml"` instead of `"backend/models.yaml"`)
  - **Monitoring Update**: Fixed health check to use `llm` package directly instead of LLMInterface
  - **Tool Manager Dependency Injection**: Pass ToolManager to AgentManager to maintain proper isolation
  - **System Prompts Integration**: Load system prompts and seed prompts during conversation initialization
  - **Agent History API**: Provide dedicated endpoint for frontend to load conversation history
  - **Frontend Message Source**: Frontend only reads messages from agent history, not from other sources
- **Architecture Benefits**:
  - **Cleaner Separation**: Agent handles LLM integration, ChatEngine handles session orchestration
  - **No Redundancy**: Single source of truth for LLM interactions
  - **Proper Isolation**: Only managers access their respective configuration files
  - **Better Error Handling**: Proper JSON serialization prevents runtime errors
  - **Clear Responsibilities**: Agent = LLM worker, ChatEngine = session manager
- **Technical Details**:
  - **Response Handling**: `llm.models.ChainResponse` objects require `.text()` method call, not `str()` conversion
  - **Manager Isolation**: Only `ModelsManager` accesses `models.yaml`, only `ProviderManager` accesses `providers.yaml`, etc.
  - **Session Management**: ChatEngine maintains session state while Agent handles individual conversations
  - **Prompt Type Handling**: Agent checks prompt type (system vs seed) before processing
  - **Tool Loading**: Agent uses ToolManager for tool loading, maintains isolation
- **Impact**: Eliminated JSON serialization errors, cleaner architecture, proper separation of concerns
- **Status**: ✅ COMPLETE - Zeus agent responding correctly with proper text content

### ✅ Model Settings Dialog Improvements
- **Root Cause**: Need for better model configuration interface
- **Issue**: Confusing settings layout, missing context window configuration
- **Solution**: Redesigned settings dialog with clear separation of concerns
- **Implementation**:
  - **Context Window Size**: Required number input for token tracking
  - **Read-only Fields**: Name and description displayed as labels
  - **Inference Settings**: Dynamic form based on provider schema
  - **Stream Option**: Conditional display based on model.can_stream
  - **Model Options**: All available options from model.Options class
- **Impact**: Clearer configuration, better user experience, proper validation
- **Status**: ✅ COMPLETE - All improvements implemented and tested

### ✅ Schema Manager Implementation
- **Root Cause**: Need for JSON schema management for structured outputs
- **Issue**: No way to manage schemas for model outputs
- **Solution**: Created complete schema management system
- **Implementation**:
  - **Backend**: `SchemaManager` class with full CRUD operations
  - **File Storage**: JSON schema files in `backend/schemas/` directory
  - **API Endpoints**: Complete REST API for schema management
  - **Frontend**: Dedicated "Schemas" tab with full UI
  - **Validation**: JSON schema format validation
  - **File Extension**: `.schema.json` for clear identification
- **Impact**: Structured output support, better model configuration, extensible system
- **Status**: ✅ COMPLETE - Backend tested, frontend implemented

### ✅ Global Notification System
- **Root Cause**: Need for system health monitoring and user alerts
- **Issue**: No way to notify users about configuration issues or system problems
- **Solution**: Implemented comprehensive notification system with health checks
- **Implementation**:
  - **Health Checks**: `checkSystemHealth()` function detects configuration issues
  - **Unconfigured Providers**: Detects providers missing API keys or base URLs
  - **Missing Context Windows**: Identifies chat models without context window size
  - **Visual Indicators**: Color-coded notification icons (green=healthy, red=issues)
  - **Notification Modal**: Detailed view of all issues with refresh capability
  - **Real-time Updates**: Notifications update when configuration changes
- **Impact**: Better user experience, proactive issue detection, improved system reliability
- **Status**: ✅ COMPLETE - All features working and tested

### ✅ Context Window Integration
- **Root Cause**: Need for real-time context usage tracking
- **Issue**: No way to monitor conversation length and prevent context overflow
- **Solution**: Implemented context window tracking with visual progress indicator
- **Implementation**:
  - **Context Calculation**: `_calculate_context_usage()` in chat engine
  - **Model Integration**: Uses model's `context_window_size` from ModelsManager
  - **Token Estimation**: Rough token calculation (4 chars per token)
  - **Visual Progress**: ContextProgress component with color-coded rings
  - **N/A State**: Gray progress ring with "N/A" text when context window not set
  - **Real-time Updates**: Context usage updates with each message
- **Impact**: Better conversation management, overflow prevention, user awareness
- **Status**: ✅ COMPLETE - All features working and tested

### ✅ Enhanced Type Safety
- **Root Cause**: Need for proper type handling in model settings
- **Issue**: Form fields not correctly converting string inputs to proper types
- **Solution**: Enhanced schema extraction with Python type information
- **Implementation**:
  - **Backend Enhancement**: `get_all_option_fields()` extracts Python type annotations
  - **Schema Enhancement**: `_enhance_schema_with_types()` adds `python_type` to JSON schema
  - **Frontend Integration**: `renderSchemaFields()` uses `python_type` for correct input components
  - **Type Conversion**: Explicit conversion (parseInt, parseFloat, boolean) in onChange handlers
  - **Field Types**: NumberInput for int/float, Switch for bool, TextInput for string
- **Impact**: Proper data types in YAML, correct form validation, better user experience
- **Status**: ✅ COMPLETE - All type handling working correctly

### ✅ Strict Schema Implementation (Latest Update)
- **Root Cause**: Using dictionaries directly is error-prone and hard to maintain
- **Issue**: No type safety, difficult debugging, no autocomplete for data structures
- **Solution**: Replaced all dictionary usage with strict Pydantic schemas
- **Implementation**:
  - **New Schemas**: Added `ContextUsageData`, `ConversationResponseData`, `AgentInfo`, `ConversationData`, `ToolExecutionResult`
  - **ChatEngine Updates**: `process_message()` now returns `ConversationResponseData` instead of `Dict[str, Any]`
  - **Context Usage**: `_calculate_context_usage()` returns `ContextUsageData` with validation rules
  - **Agent Class**: `get_agent_info()` returns `AgentInfo`, `save_conversation()` uses `ConversationData`
  - **API Layer**: Main.py properly serializes Pydantic objects using `.model_dump()`
  - **Validation Rules**: Percentage fields (0-100), token counts (≥0), context windows (≥0)
- **Benefits**:
  - **Type Safety**: Compile-time validation prevents runtime errors
  - **IDE Support**: Full autocomplete and type checking
  - **Maintainability**: Self-documenting code with clear field definitions
  - **Error Prevention**: Invalid data caught at object creation time
  - **Performance**: Optimized serialization with built-in JSON support
- **Status**: ✅ COMPLETE - All dictionary usage replaced with strict schemas

### ✅ Context Progress Tooltip Enhancement (Latest Update)
- **Root Cause**: Need for detailed token information in context progress display
- **Issue**: Context progress only showed percentage, not actual token counts
- **Solution**: Enhanced ContextProgress component with detailed tooltip
- **Implementation**:
  - **Tooltip Display**: Shows "[tokens used]/[context window]" when hovering over progress ring
  - **Token Information**: Backend returns `tokens_used` and `context_window` along with percentage
  - **Enhanced UI**: ContextProgress component accepts `tokensUsed` and `contextWindow` props
  - **Type Safety**: Updated TypeScript interfaces to include new token fields
  - **Fallback Display**: Shows percentage when token information not available
- **User Experience**: Users can now see exact token usage and context window size on hover
- **Status**: ✅ COMPLETE - Tooltip shows detailed token information

### ✅ Context Progress Bug Fix (Latest Update)
- **Root Cause**: Frontend calculating incorrect context usage on initial load
- **Issue**: Context progress showed 8% initially, then jumped to 1% after first message
- **Root Cause Analysis**: 
  - Frontend was using hardcoded default context window size (4000 tokens)
  - Rough token estimation (content.length / 4) was inaccurate
  - Frontend calculation conflicted with backend's accurate calculations
- **Solution**: Removed frontend context calculation on initial load
- **Implementation**:
  - **Removed Frontend Calculation**: `loadAgentHistory()` no longer calculates context usage
  - **Backend Accuracy**: Context usage only updated when backend provides accurate information
  - **Enhanced Backend**: Added model context window size to agent info endpoint
  - **Proper Fallback**: Use reasonable default (8192 tokens) when model info not available
- **Technical Details**:
  - **Model Context Window**: Backend attempts to include `context_window_size` from model configuration
  - **Accurate Calculation**: Backend has access to actual model configuration and can calculate usage more precisely
  - **Real-time Updates**: Context usage updated with accurate information after each message
- **Impact**: Eliminated confusing context usage jumps, accurate progress tracking
- **Status**: ✅ COMPLETE - Context progress now shows accurate percentages from backend calculations

### ✅ System Prompts Integration Fix (Latest Update)
- **Root Cause**: `llm` package conversation object doesn't maintain system prompts via `prompt()` method
- **Issue**: System prompts were being loaded but not affecting agent responses
- **Root Cause Analysis**: 
  - `conv.prompt()` method doesn't add responses to conversation
  - System prompts need to be included directly in messages sent to `chain()` method
  - `llm` package conversation object works differently than expected
- **Solution**: Include system prompts directly in messages sent to `chain()` method
- **Implementation**:
  - **Prompt Collection**: `_add_system_prompts()` now collects system prompts and seed messages
  - **Message Building**: `_build_message_with_prompts()` constructs full messages with system prompts
  - **Direct Integration**: System prompts included in every message sent to `chain()` method
  - **Proper Formatting**: System prompts formatted as "System: {content}" in messages
- **Technical Details**:
  - **Prompt Storage**: System prompts stored in `self._system_prompts` and `self._seed_messages`
  - **Message Construction**: Full message includes system prompts, seed messages, and user message
  - **Format**: "System: {prompt1}\n\nSystem: {prompt2}\n\nUser: {message}"
  - **Path Fix**: Updated prompt manager path to `"backend/prompts"` for correct file loading
- **Impact**: System prompts now properly affect agent responses, Zeus agent responds as God agent
- **Status**: ✅ COMPLETE - System prompts working correctly, agent responses include proper identity and capabilities

### ✅ File Logging Removal (Latest Update)
- **Root Cause**: File logging creates unnecessary log files that clutter the system
- **Issue**: `ateam.log` file being created and maintained unnecessarily
- **Solution**: Removed file logging handler, keeping only console output
- **Implementation**:
  - **Logging Configuration**: Removed `logging.FileHandler('ateam.log')` from monitoring.py
  - **Console Only**: Logging now outputs only to console via `logging.StreamHandler()`
  - **Health Check Fix**: Fixed LLM health check to use correct method name
- **Benefits**: Cleaner system, no log file management needed, console output sufficient for development
- **Status**: ✅ COMPLETE - File logging removed, console logging maintained

### ✅ Model Groups and UI Separation
- **Root Cause**: Need for better visual organization of models
- **Issue**: Chat models and embedding models mixed together
- **Solution**: Implemented separate model groups with distinct sections
- **Implementation**:
  - **Model Separation**: "Models" section for chat models, "Embedding Models" for embedding models
  - **Group-specific Badges**: Different badge sets for each model type
  - **Conditional Fields**: Context window size hidden for embedding models
  - **Empty States**: Separate empty state messages for each group
  - **Visual Distinction**: Clear visual separation between model types
- **Impact**: Better organization, clearer model types, improved user experience
- **Status**: ✅ COMPLETE - All UI improvements implemented

### ✅ Model Warning Icons Implementation
- **Root Cause**: Need for targeted warnings for models without context window sizes
- **Issue**: Global notifications were cluttered with context window warnings
- **Solution**: Replaced global notifications with model-specific warning icons
- **Implementation**:
  - **Warning Icons**: Orange `IconAlertTriangle` displayed next to models without context window sizes
  - **Tooltip Information**: "Context window size not set - affects context usage tracking"
  - **Conditional Display**: Only shown for chat models (not embedding models) with `context_window_size: null`
  - **Global Notification Cleanup**: Removed context window notifications from sidebar notification system
  - **Targeted Approach**: Warnings appear directly on the models that need attention
- **Impact**: Cleaner notification system, targeted user guidance, better UX
- **Status**: ✅ COMPLETE - All warning icons implemented and tested

### ✅ Complete OpenAI Model Configuration
- **Root Cause**: Need for comprehensive model configuration with accurate context window sizes
- **Issue**: Many OpenAI models lacked proper context window size configuration
- **Solution**: Updated models.yaml with all OpenAI models and their correct specifications
- **Implementation**:
  - **Context Window Sizes**: Accurate token limits from OpenAI documentation
    - GPT-4o family: 128,000 tokens
    - GPT-4.1 family: 1,047,576 tokens (1M)
    - GPT-4 Turbo: 128,000 tokens
    - GPT-4: 8,192 tokens
    - GPT-4-32k: 32,768 tokens
    - GPT-3.5 Turbo: 16,385 tokens
    - O1 family: 200,000 tokens
  - **Max Tokens**: Proper output token limits for each model
    - Modern models: 16,384 tokens
    - GPT-4.1 family: 32,768 tokens
    - O1 family: 100,000 tokens
    - Legacy models: 4,096 tokens
  - **Streaming Support**: Correct streaming flags based on model capabilities
  - **Model Coverage**: All 29 discovered OpenAI chat models now configured
- **Impact**: Complete model configuration, accurate context tracking, proper inference settings
- **Status**: ✅ COMPLETE - All models configured with accurate specifications

### ✅ Enhanced Prompt Editing Interface
- **Root Cause**: Need for better editing experience for large prompt content with dynamic sizing
- **Issue**: Small textarea (4-12 rows) insufficient for large content, missing edit options in menu
- **Solution**: Implemented dynamic textarea sizing with enhanced menu options and larger modal
- **Implementation**:
  - **Dynamic Textarea**: Increased from 4-12 rows to 8-50 rows with autosize functionality
  - **Enhanced Menu Options**: Context-aware display with "Edit Content" and "View Content" options
  - **Modal Sizing**: Increased max height from 80vh to 95vh for better content visibility
  - **Typography Improvements**: Better font size (14px) and line height (1.5) for readability
  - **Content Persistence**: Fixed content loading issues when switching between prompts
  - **Conditional Display**: Markdown/Plain Text options only shown when not in edit mode
- **Technical Challenges**:
  - **Content Synchronization**: Used `useEffect` to sync `editContent` with `message.content` changes
  - **Menu State Management**: Conditional rendering based on `isEditing` state
  - **Autosize Integration**: Proper Mantine Textarea autosize prop configuration
  - **Modal Height Optimization**: Balance between usability and screen real estate
- **Impact**: Much better editing experience for large prompt content, intuitive interface
- **Status**: ✅ COMPLETE - All editing improvements implemented and tested

## Key Implementation Lessons

### Major Refactoring Learnings (Latest Update)
1. **WebSocket Architecture**: Centralized WebSocket management with agent-specific connections provides better scalability and error handling
2. **Custom Conversation Management**: Replacing `llm` conversation object with custom message lists gives full control over conversation flow and context building
3. **Structured Response System**: Pydantic models for LLM responses ensure type safety and consistent error handling across all response types
4. **Tool System Decoupling**: Custom tool descriptor and executor eliminate LLM package bias and provide better control over tool execution
5. **Fail-Fast Philosophy**: Immediate exception raising instead of logging and continuing prevents silent failures and improves debugging
6. **Code Cleanup Strategy**: Systematic removal of unused code, methods, and imports ensures clean architecture and prevents technical debt
7. **Type Safety First**: Pydantic models throughout the system provide compile-time validation and better IDE support
8. **Real-time Communication**: WebSocket-based message flow provides immediate feedback and better user experience
9. **Separation of Concerns**: Clear boundaries between conversation management, tool execution, and message handling
10. **Comprehensive Testing**: Validation tests ensure all refactoring changes work correctly and no functionality is broken
11. **Enhanced Message Display**: Multiple view modes and action-based icons provide better debugging and user experience
12. **User Experience Design**: Proper tooltips, reasoning toggles, and raw message views improve developer and user experience

### Development Workflow
1. **Single Server Approach**: Much simpler than running separate servers with proxying
2. **Direct File Serving**: Faster development without static file building
3. **Unified Script**: One script handles everything - easier for users
4. **TypeScript Compilation Check**: Ensures code quality without building

### Architecture Decisions
1. **FastAPI for Everything**: Backend serves both API and frontend files
2. **YAML Configuration**: Human-readable and version-controlled
3. **Modular Design**: Each component is independent and testable
4. **Fail Fast Philosophy**: Never create defaults that hide problems
5. **Dynamic Discovery**: Runtime model and provider discovery without loading models
6. **Hybrid Storage**: User preferences in YAML, runtime data from discovery
7. **Strict Typing**: Pydantic models ensure type safety throughout
8. **Targeted Warnings**: Model-specific warnings instead of global notification clutter
9. **Manager Isolation**: Only managers access their respective configuration files and directories
10. **Direct LLM Integration**: Agent class uses llm package directly, no redundant abstraction layers
11. **Clear Separation of Concerns**: Agent handles LLM interactions, ChatEngine handles session orchestration
12. **Global Manager Registry**: Centralized manager management with aliases and no local copies
13. **Manager Aliases**: Direct function access for current manager instances
14. **Centralized Initialization**: Single initialization point for all managers
15. **No Local Manager Storage**: Components use manager aliases directly, never store local references
16. **System Prompts Integration**: Load system prompts and seed prompts during conversation initialization
17. **Agent History API**: Provide dedicated endpoint for frontend to load conversation history
18. **Frontend Message Source**: Frontend should only read messages from agent history, not from other sources

### Error Handling & Fail Fast Philosophy
1. **Core Principle**: "Fail fast, not silent" - never create defaults that hide problems
2. **No Default Creation**: System never creates default files or configurations
3. **Explicit Errors**: Missing resources result in clear error messages
4. **Configuration Management**: Clear separation of concerns in YAML files
5. **Error Handling Architecture**: Comprehensive backend error details with frontend error dialogs
6. **Global Notifications**: Proactive issue detection and user alerts
7. **Model-Specific Warnings**: Targeted warnings for specific configuration issues
8. **Exception Propagation**: All errors are raised as exceptions instead of being logged and ignored
9. **Proper HTTP Status Codes**: REST API returns appropriate status codes (400 for validation, 500 for runtime errors)
10. **WebSocket Error Responses**: Real-time error responses with detailed suggestions for fixing issues
11. **No Silent Failures**: System immediately stops when invalid state is detected
12. **Detailed Error Context**: All error messages include relevant context for debugging

### Frontend UX Design
1. **Component Reusability**: Created reusable components (ContextProgress, MessageDisplay)
2. **Consistent Design**: Dark theme throughout with Mantine components
3. **Responsive Layout**: Full-screen utilization with grid system
4. **User Feedback**: Context progress, loading states, and proper error handling
5. **Accessibility**: Proper keyboard shortcuts and tooltips
6. **Dynamic Forms**: Type-aware form fields based on schema information
7. **Visual Organization**: Separate sections for different model types
8. **Warning Indicators**: Visual cues for models needing configuration attention

### Message Type System & Dark Mode Implementation
1. **Message Type Architecture**: Backend and frontend enums stay synchronized
2. **System Message Type**: Added `MessageType.SYSTEM` to distinguish system prompts
3. **Dark Mode Message Styling**: User messages (`blue-9`), agent messages (`dark-6`), white text for readability
4. **Unknown Type Handling**: Graceful degradation with question mark icon and debugging support

### Single Server Development Approach
1. **Simplified Architecture**: Single backend server serves both API and frontend
2. **Frontend Serving Strategy**: Build frontend to static files, copy to `backend/static/`, serve with SPA routing
3. **Layout and CSS Fixes**: Proper flexbox layout with `!important` declarations for CSS specificity
4. **Routing Fixes**: API routes first, then catch-all frontend route for SPA routing
5. **Key Benefits**: Simpler setup, no port conflicts, easier deployment, consistent environment

### Dynamic Model Management Architecture
1. **Runtime Discovery**: `discover_models_from_llm()` finds all models without loading them
2. **Schema Extraction**: `get_provider_model_schema()` extracts inference settings from Options classes
3. **Type Enhancement**: `_enhance_schema_with_types()` adds Python type information to JSON schema
4. **Hybrid Storage**: User preferences in YAML, runtime capabilities from discovery
5. **Provider Agnostic**: Works with any provider that exposes Options classes
6. **No Model Loading**: Avoids memory issues and slow startup times

### Dual-Capability Model Architecture
1. **Same Model ID Approach**: Allow the same model ID to appear twice in the API response with different `embedding_model` flags
2. **Frontend Separation**: Chat section filters for `embedding_model: false`, embedding section filters for `embedding_model: true`
3. **No Artificial IDs**: Use original model names from `llm` instead of creating artificial IDs like `_chat` or `_embedding`
4. **Independent Configuration**: Each capability can be configured separately with different settings
5. **Clean Implementation**: Much simpler than complex ID extraction and artificial naming schemes

### Context Window Management
1. **Real-time Calculation**: `_calculate_context_usage()` computes usage percentage
2. **Model Integration**: Uses model's `context_window_size` from ModelsManager
3. **Token Estimation**: Rough calculation (4 chars per token) for real-time updates
4. **Visual Feedback**: ContextProgress component with color-coded progress rings
5. **N/A Handling**: Graceful display when context window not configured
6. **Overflow Prevention**: Helps users avoid hitting context limits

### Global Notification System
1. **Health Checks**: `checkSystemHealth()` detects configuration issues
2. **Proactive Detection**: Identifies unconfigured providers and missing context windows
3. **Visual Indicators**: Color-coded notification icons with count badges
4. **Detailed Modal**: Comprehensive view of all issues with refresh capability
5. **Real-time Updates**: Notifications update when configuration changes
6. **User Guidance**: Clear information about what needs to be configured
7. **Streamlined Approach**: Focus on critical system issues, not individual model warnings

### Model Warning System
1. **Targeted Warnings**: Model-specific warning icons instead of global notifications
2. **Visual Indicators**: Orange warning triangles with explanatory tooltips
3. **Conditional Display**: Only shown for chat models without context window sizes
4. **User Guidance**: Clear explanation of what needs to be configured
5. **Clean Interface**: Reduces notification clutter while maintaining user awareness

### Prompt Management and Editing Interface Design
1. **Dynamic Content Sizing**: Implement autosize textareas that adapt to content length (8-50 rows)
2. **Context-Aware Menus**: Display options should change based on current edit state
3. **Content Persistence**: Use `useEffect` to synchronize component state with prop changes
4. **Modal Height Optimization**: Balance between usability (95% max height) and screen real estate
5. **Typography Considerations**: Proper font size (14px) and line height (1.5) for readability
6. **Backward Compatibility**: Support both new JSON format and old markdown format for seed prompts
7. **Type Safety**: Use Pydantic models for structured data (SeedMessage, SeedPromptData)
8. **Component Reusability**: Enhance existing components (MessageDisplay) for new use cases
9. **User Experience**: Default to edit mode for system prompts, provide clear edit/view transitions
10. **Data Format Consistency**: Store seed prompts as JSON for LLM compatibility while supporting markdown fallback

### Common Issues and Solutions
1. **404 on Direct Routes**: Ensure catch-all route is defined after API routes
2. **Layout Issues**: Use proper flexbox CSS with `!important` declarations
3. **Static File Serving**: Copy built files to correct location (`backend/static/`)
4. **CSS Conflicts**: Override conflicting styles with higher specificity
5. **Delete Agent Path Issue**: Check for empty directory path before calling `os.makedirs()`
6. **Provider Discovery**: Use `llm.get_models()` and `llm.get_embedding_models()` for automatic provider detection
7. **Provider Merging**: Use consistent provider keys (lowercase) to avoid duplicates when merging configured and discovered providers
8. **Provider Configuration Warnings**: Show warning icons for discovered providers missing configuration (no api_key_env_var or base_url)
9. **Provider Edit UX**: Disable API key env var field when API key not required, auto-clear field when toggled off
10. **Provider Save Fix**: Check for empty directory path before calling `os.makedirs()` in provider manager
11. **Provider Auto-Creation**: Update provider endpoint should handle both existing and new discovered providers
12. **YAML Configuration Separation**: Keep runtime data (model counts, configured flags) separate from configuration data in YAML files
13. **Strict Type Safety**: Use Pydantic models instead of dictionaries to ensure type safety and prevent bugs
14. **Clear File Naming**: Use descriptive file names that don't conflict with domain terminology (e.g., schemas.py instead of models.py in LLM context)
15. **Provider Warning Icons**: Use explicit `configured` flag to determine if provider needs configuration warning
16. **Provider Discovery Simplification**: All providers are discovered via llm package, no need for "discovered" badges
17. **Provider Warning Icons**: Warning icons show for discovered providers that aren't configured (not in YAML)
18. **YAML Configuration Cleanup**: Runtime fields (configured, chat_models, embedding_models) are determined at runtime, not stored in YAML
19. **Strict Provider Typing**: ProviderInfo and ProviderInfoView classes ensure type safety across the codebase
20. **Clear File Naming**: Renamed models.py to schemas.py to avoid confusion with LLM models
21. **Import Management**: When renaming files, systematically update all import statements across the codebase
22. **Type-Driven Development**: Design data structures with Pydantic models first, then implement business logic
23. **Dynamic Schema Extraction**: Extract inference settings from model Options classes without loading models
24. **Type Enhancement**: Add Python type information to JSON schema for proper frontend rendering
25. **Context Window Integration**: Use model's context_window_size for real-time usage calculation
26. **N/A State Handling**: Display "N/A" when context window not configured instead of 0%
27. **Model Group Separation**: Separate chat models and embedding models for better organization
28. **Badge System**: Dynamic capability badges based on model attributes
29. **Streaming Toggle**: Proper boolean handling for streaming option in model settings
30. **Field Type Conversion**: Explicit type conversion in form onChange handlers
31. **Model Warning Icons**: Use targeted warning icons instead of global notifications for model-specific issues
32. **Notification Streamlining**: Focus global notifications on system-level issues, not individual model configurations
33. **Complete Model Configuration**: Ensure all discovered models have proper context window sizes and inference settings
34. **Content Synchronization**: Use `useEffect` to sync component state with prop changes to prevent empty content in editors
35. **Menu State Management**: Implement conditional rendering for display options based on edit state
36. **Textarea Autosize**: Use Mantine's `autosize` prop with proper `minRows` and `maxRows` for dynamic sizing
37. **Modal Height Optimization**: Set `maxHeight: '95vh'` for large content while maintaining usability
38. **Typography Optimization**: Use `fontSize: '14px'` and `lineHeight: '1.5'` for better readability in textareas
39. **Seed Prompt Format**: Store as JSON for LLM compatibility with markdown fallback for backward compatibility
40. **Component Enhancement**: Extend existing components (MessageDisplay) with new props for reusability
41. **Edit Mode Defaults**: Set `defaultEditMode={true}` for system prompts to provide immediate editing capability
42. **Context-Aware UI**: Hide display mode options when in edit mode to reduce interface clutter
43. **JSON Serialization with LLM**: Use `response.text()` method for `llm.models.ChainResponse` objects, not `str(response)`
44. **Manager Isolation**: Only managers should access their respective YAML files and directories
45. **Redundant Abstraction Removal**: Eliminate unnecessary abstraction layers that duplicate functionality
46. **Direct LLM Integration**: Use llm package directly in Agent class, avoid intermediate abstraction layers
47. **Path Configuration**: Use correct relative paths when working directory is already set to backend directory
48. **WebSocket Error Handling**: Proper error handling for WebSocket disconnections and connection issues
49. **Context Progress Accuracy**: Frontend should not calculate context usage on initial load - rely on backend accuracy
50. **Model Context Window Integration**: Include model's context window size in agent info for accurate frontend calculations
51. **Frontend-Backend Calculation Conflicts**: Avoid duplicate calculations that can lead to inconsistent UI state
52. **Token Estimation Limitations**: Frontend token estimation (content.length / 4) is too rough for accurate context tracking
53. **WebSocket Disconnect Handling**: Proper handling of WebSocket disconnections (1001, 1012 codes) to prevent ASGI errors
54. **ASGI Message Errors**: Avoid sending messages after WebSocket connection is closed to prevent "Unexpected ASGI message" errors
55. **LLM Package System Prompts**: System prompts must be included directly in messages sent to `chain()` method, not added via `prompt()` method
56. **Prompt Manager Paths**: Use correct relative paths when initializing PromptManager from different working directories
57. **Message Construction**: Build complete messages with system prompts, seed messages, and user input for proper LLM integration
58. **Global Notification System**: Real-time WebSocket-based error/warning notifications with detailed dialogs and context information
59. **Structured Error Logging**: All backend print statements replaced with context-rich notification logging
60. **Notification Manager**: WebSocket-based notification broadcasting with automatic reconnection
61. **Notification Utils**: Utility functions for easy integration of structured logging throughout the codebase
62. **Frontend Notification Service**: Mantine-based notification display with clickable error dialogs
63. **Comprehensive Error Coverage**: All backend files now use structured notifications instead of print statements
64. **Fail-Fast Error Handling**: Always raise exceptions instead of logging and continuing in invalid state
65. **Agent Error Handling**: Agent class raises exceptions for missing prompts, tools, models, and conversation failures
66. **Manager Error Handling**: All manager classes properly raise exceptions instead of logging and continuing
67. **API Error Handling**: REST and WebSocket endpoints with proper HTTP status codes and detailed error responses
68. **Exception Propagation**: Errors bubble up to API endpoints with appropriate HTTP status codes
69. **Detailed Error Context**: All error messages include relevant context for debugging
70. **No Silent Failures**: System immediately stops when invalid state is detected

## Removed Features
- ❌ Local SQLite database integration
- ❌ Basic authentication system
- ❌ Development mode with Vite dev server proxying
- ❌ Separate development and production scripts
- ❌ Static model configurations in YAML
- ❌ "Discovered" badges (all models are discovered)
- ❌ "Configured" badges (replaced with "Default" badge logic)
- ❌ Global context window notifications (replaced with model-specific warning icons)
- ❌ `tools.yaml` configuration file (replaced with dynamic file system discovery)
- ❌ Tool CRUD operations (create, update, delete) - tools are now read-only
- ❌ "View" buttons for tools (replaced with inline signature display)
- ❌ Refresh buttons for tools (users can use browser refresh instead)
- ❌ Checkbox-based system prompts in agent settings (replaced with draggable dropdown system)
- ❌ `LLMInterface` abstraction layer (replaced with direct Agent class integration)
- ❌ Local manager copies (replaced with global manager registry and aliases)
- ❌ Manager dependency injection (replaced with direct alias access)
- ❌ Manager parameters in constructors (replaced with direct alias calls)

## Implementation Phases Status

### ✅ Completed Phases (1-15)
- **Phase 1-2**: Project structure, backend foundation, core features
- **Phase 3-4**: Frontend foundation and advanced features
- **Phase 5**: Integration and advanced features
- **Phase 6**: Build process and dependency management
- **Phase 7**: Development architecture and UX improvements
- **Phase 8**: LLM integration and configuration
- **Phase 9**: Advanced features and optimization
- **Phase 10**: Frontend improvements and UX enhancement
- **Phase 11**: Error handling and fail fast implementation
- **Phase 12**: Dynamic model management and enhanced settings
- **Phase 13**: Global notifications and context window integration
- **Phase 14**: Model warning icons and complete OpenAI model configuration
- **Phase 15**: Enhanced tool management with dynamic discovery and signature display

### 🎉 All Phases Complete
- **Dynamic Model Management**: Complete runtime discovery and settings
- **Enhanced UI**: Separate model groups, proper field types, badges
- **Context Window Tracking**: Real-time usage with visual progress
- **Global Notifications**: System health monitoring and alerts
- **Schema Management**: Complete CRUD operations for JSON schemas
- **Type Safety**: Comprehensive type handling throughout the system
- **Model Warning System**: Targeted warnings for models needing configuration
- **Complete Model Configuration**: All OpenAI models properly configured
- **Dynamic Tool Discovery**: Automatic discovery of Python functions and classes
- **Tool Signature Display**: Complete function and method signatures with parameter types
- **Method Expansion**: Expandable class methods with individual signatures and descriptions
- **Simplified Tool Interface**: Clean UI without refresh buttons - browser refresh for updates
- **Docstring Integration**: Automatic detection and display of function/method documentation

## File Structure Summary

```
ATeam/
├── backend/
│   ├── main.py                 # FastAPI application with frontend serving
│   ├── manager_registry.py     # Global manager registry with centralized initialization
│   ├── agent_manager.py        # Agent management (fixed delete path issue)
│   ├── tool_manager.py         # Dynamic tool discovery and signature extraction
│   ├── models_manager.py       # Dynamic model discovery and settings
│   ├── schema_manager.py       # JSON schema CRUD operations
│   ├── provider_manager.py     # LLM provider management with strict typing
│   ├── prompt_manager.py       # Prompt management (fail fast implementation)
│   ├── notification_manager.py # WebSocket-based notification broadcasting
│   ├── notification_utils.py   # Utility functions for structured logging
│   ├── chat_engine.py          # Chat processing with context tracking
│   ├── monitoring.py           # System monitoring
│   ├── models.yaml             # Model configurations (complete OpenAI coverage)
│   ├── agents.yaml             # Agent configurations
│   ├── providers.yaml          # Provider definitions (no models)
│   ├── prompts/                # Prompt templates
│   ├── schemas/                # JSON schema files
│   └── tools/                  # Python tool files (dynamically discovered)
├── frontend/
│   ├── src/components/         # React components
│   ├── src/api/index.ts        # API client
│   └── package.json            # Dependencies
├── build_and_run.ps1           # Single development server script
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
``` 

## Strict Typing Architecture

### Provider Data Flow
1. **YAML Configuration**: `ProviderInfo` objects loaded from `providers.yaml`
2. **Runtime Discovery**: `discover_providers_from_llm()` returns dictionary data
3. **Merging**: `get_all_providers_with_discovery()` creates `ProviderInfoView` objects
4. **API Response**: `ProviderInfoView` objects serialized to JSON for frontend
5. **Frontend**: TypeScript interfaces match backend Pydantic models

### Model Data Flow
1. **YAML Configuration**: `ModelInfo` objects loaded from `models.yaml`
2. **Runtime Discovery**: `discover_models_from_llm()` returns dictionary data
3. **Schema Extraction**: `get_provider_model_schema()` extracts inference settings
4. **Merging**: `get_all_models_with_discovery()` creates `ModelInfoView` objects
5. **API Response**: `ModelInfoView` objects serialized to JSON for frontend
6. **Frontend**: Dynamic forms based on `available_settings` schema

### Type Safety Benefits
- **Compile-time Validation**: Pydantic validates data on object creation
- **IDE Support**: Full autocomplete and type checking
- **Error Prevention**: Runtime errors caught at creation time
- **Clear Data Flow**: Explicit separation between configuration and runtime data
- **Maintainability**: Changes to data structures caught early

### Key Classes
- **ProviderInfo**: Configuration data stored in YAML (name, display_name, description, api_key_required, api_key_env_var, base_url)
- **ProviderInfoView**: Complete provider data including runtime fields (configured, chat_models, embedding_models)
- **ModelInfo**: Configuration data stored in YAML (id, name, provider, description, context_window_size, model_settings, default_inference)
- **ModelInfoView**: Complete model data including runtime fields (configured, supports_schema, can_stream, available_settings, embedding_model, badges)

### Data Separation
- **Configuration Data**: Stored in YAML files (static)
- **Runtime Data**: Determined at runtime (model counts, configured flags, capabilities)
- **Schema Data**: Extracted from provider Options classes (inference settings)
- **Clean Persistence**: Only configuration data saved to YAML, runtime data computed fresh

## Current System State

### Models and Providers
- **29 Chat Models**: Discovered from llm package with dynamic capabilities
- **8 Embedding Models**: Separate group with embedding-specific badges
- **29 Configured Models**: All chat models have context window sizes set
- **0 Unconfigured Providers**: All providers properly configured (no notifications)

### Features Working
- ✅ Dynamic model discovery without loading models
- ✅ Enhanced model settings with proper field types
- ✅ Context window progress tracking with N/A state
- ✅ Global notification system with health checks
- ✅ Schema management with full CRUD operations
- ✅ Separate model groups for better organization
- ✅ Comprehensive badge system for model capabilities
- ✅ Type-safe data handling throughout the system
- ✅ Real-time context usage calculation
- ✅ Streaming toggle functionality
- ✅ Proper type conversion in forms
- ✅ Model warning icons for configuration issues
- ✅ Complete OpenAI model configuration
- ✅ Enhanced prompt management with full CRUD operations
- ✅ Dynamic textarea sizing (8-50 rows) with autosize functionality
- ✅ Context-aware menu options for prompt editing
- ✅ Large modal dialogs (95% max height) for extensive content
- ✅ Specialized editing interfaces for system and seed prompts
- ✅ JSON-based seed prompt storage with markdown fallback
- ✅ Content persistence and synchronization across prompt switches
- ✅ Dynamic tool discovery from Python files
- ✅ Complete function and method signature extraction
- ✅ Tool signature display across all interfaces
- ✅ Expandable class methods with individual signatures
- ✅ Docstring integration with warning indicators
- ✅ Method expansion with chevron controls
- ✅ Monospace font styling for signatures
- ✅ Drag-and-drop system prompts with proper dependency management
- ✅ Complete TypeScript compilation and production build
- ✅ Strict Pydantic schemas replacing all dictionary usage
- ✅ Context progress tooltips with detailed token information
- ✅ Console-only logging without file output
- ✅ Agent class with llm package integration
- ✅ Conversation persistence in agent_history directory
- ✅ Lazy loading agent instances for memory efficiency
- ✅ WebSocket-based real-time communication with centralized connection management
- ✅ Custom conversation management without LLM package conversation object bias
- ✅ Structured LLM responses with Pydantic validation and type safety
- ✅ Custom tool descriptor and executor system
- ✅ Comprehensive code cleanup with no unused dependencies
- ✅ Fail-fast error handling throughout all components

### System Health
- **0 Warnings**: All providers and models properly configured
- **All APIs Working**: Models, providers, schemas, agents, tools
- **Frontend Responsive**: All components working correctly
- **Type Safety**: No type errors in development with strict Pydantic schemas
- **Complete Configuration**: All 29 OpenAI chat models configured with accurate specifications
- **Dynamic Tools**: 2 tools discovered and displaying signatures correctly
- **Clean Logging**: Console-only logging without file clutter
- **Agent Integration**: New Agent class with llm package integration working correctly
- **Conversation Persistence**: Agent history system ready for conversation storage
- **Memory Efficient**: Lazy loading agent instances for optimal resource usage
- **Notification System**: Real-time error/warning notifications with detailed dialogs
- **Structured Logging**: All backend errors and warnings properly logged with context
- **Global Notification System**: Real-time WebSocket-based error/warning notifications with detailed dialogs
- **Structured Error Logging**: All backend print statements replaced with context-rich notification logging
- **Professional Error Handling**: Comprehensive error reporting with detailed context information
- **Fail-Fast Architecture**: System immediately stops on errors instead of continuing in invalid state
- **Exception Propagation**: All errors properly raised and handled with appropriate HTTP status codes
- **No Silent Failures**: Application never continues running with missing or invalid resources

The LLM model management system is now complete with all requested features implemented and working! The comprehensive error handling system ensures the application never continues running in an invalid state, while the notification system provides real-time error/warning visibility. The global manager registry pattern provides centralized manager management with no local copies, ensuring all components always access current manager instances. The fail-fast architecture dramatically improves the debugging experience for users and developers alike - no more hidden errors in console output, everything is immediately visible and actionable! 🎉 