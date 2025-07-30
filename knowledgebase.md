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

### Frontend (React/TypeScript)
- **React 18 + TypeScript**: Modern UI framework with type safety
- **Mantine v7**: UI component library with dark mode
- **TailwindCSS**: Utility-first CSS framework
- **Vite**: Build tool for production static files
- **Dark Mode**: Consistent dark theme throughout

### Development Workflow
- **Single Server**: Backend serves built frontend static files from `backend/static/`
- **Build Process**: PowerShell script (`build_and_run.ps1`) builds frontend and copies to backend
- **Production Mode**: Backend serves both API and frontend from port 8000

## Implementation Status

### ✅ Core Features
- **Multi-Agent System**: YAML-based agent configuration with full CRUD operations
- **LLM Integration**: Full integration with `llm` package and multiple providers
- **Tool System**: Dynamic Python tool loading and execution
- **Real-time Communication**: WebSocket-based chat system
- **Configuration Management**: YAML-based configuration files (agents.yaml, tools.yaml, providers.yaml, models.yaml)
- **Provider Management**: Support for OpenAI, Anthropic, Google, and local models

### ✅ UI/UX Features
- **Dark Mode**: Consistent dark theme throughout with proper contrast
- **Two-Tab Sidebar**: Agents tab (shows agent list) and Settings tab (Tools, Models, Providers, Prompts, Monitoring)
- **Agent Management**: Full CRUD operations with modal interface and delete confirmation
- **Chat Interface**: Multiline input with context window progress tracking
- **Message Display**: Type-specific icons, tooltips, and formatting options with SYSTEM message type support
- **Settings Organization**: Properly separated sections for different configuration types
- **Empty States**: Proper empty states when no data exists
- **Responsive Design**: Mobile-friendly layout with full-screen utilization

### ✅ Development & Deployment Features
- **Single Server Setup**: Backend serves built frontend static files
- **Build Automation**: PowerShell script handles all build steps with TypeScript compilation check
- **Error Handling**: Comprehensive error reporting and debugging with fail-fast philosophy
- **Monitoring**: Real-time system health and performance monitoring

## File Organization

### Backend Configuration Files
- `backend/agents.yaml` - Agent configurations
- `backend/tools.yaml` - Tool definitions (custom only)
- `backend/providers.yaml` - LLM provider definitions (no models)
- `backend/models.yaml` - Model configurations with provider references
- `backend/prompts/` - Directory containing markdown prompt files

### Backend Core Files
- `backend/main.py` - FastAPI application with all endpoints and static file serving
- `backend/agent_manager.py` - Agent lifecycle management (fixed delete path issue)
- `backend/tool_manager.py` - Tool loading and execution
- `backend/provider_manager.py` - LLM provider management
- `backend/prompt_manager.py` - Prompt file management (fail fast implementation)
- `backend/llm_interface.py` - LLM integration layer
- `backend/chat_engine.py` - Chat processing logic
- `backend/models.py` - Pydantic data models

### Frontend Structure
- `frontend/src/components/Sidebar.tsx` - Two-tab sidebar (Agents/Settings)
- `frontend/src/components/AgentsPage.tsx` - Agent list with empty state
- `frontend/src/components/SettingsPage.tsx` - Settings with conditional rendering
- `frontend/src/components/AgentChat.tsx` - Enhanced chat interface
- `frontend/src/components/AgentSettingsModal.tsx` - Agent configuration modal with delete functionality
- `frontend/src/components/MessageDisplay.tsx` - Message rendering component
- `frontend/src/components/ContextProgress.tsx` - Context window progress indicator
- `frontend/src/api/index.ts` - API client with proper response handling

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
10. **Message Display**: Advanced message rendering with formatting options
11. **Message Type System**: Complete message type handling with SYSTEM type support
12. **Dark Mode Messages**: All messages properly styled for dark theme readability
13. **Agent Deletion**: Delete functionality with confirmation dialog in settings modal

### 🔄 Current State
- **Application Running**: Server starts successfully on port 8000
- **Frontend Accessible**: Clean UI with proper navigation and dark mode
- **API Working**: All endpoints responding correctly
- **Agents Available**: 3 pre-configured agents (God, ToolBuilder, Assistant)
- **All Features Working**: Complete frontend improvements implemented
- **Message Types**: System messages properly displayed with correct icons
- **Dark Mode**: All messages readable with proper contrast and styling

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

## Key Implementation Lessons

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

### Error Handling & Fail Fast Philosophy
1. **Core Principle**: "Fail fast, not silent" - never create defaults that hide problems
2. **No Default Creation**: System never creates default files or configurations
3. **Explicit Errors**: Missing resources result in clear error messages
4. **Configuration Management**: Clear separation of concerns in YAML files
5. **Error Handling Architecture**: Comprehensive backend error details with frontend error dialogs

### Frontend UX Design
1. **Component Reusability**: Created reusable components (ContextProgress, MessageDisplay)
2. **Consistent Design**: Dark theme throughout with Mantine components
3. **Responsive Layout**: Full-screen utilization with grid system
4. **User Feedback**: Context progress, loading states, and proper error handling
5. **Accessibility**: Proper keyboard shortcuts and tooltips

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

### Common Issues and Solutions
1. **404 on Direct Routes**: Ensure catch-all route is defined after API routes
2. **Layout Issues**: Use proper flexbox CSS with `!important` declarations
3. **Static File Serving**: Copy built files to correct location (`backend/static/`)
4. **CSS Conflicts**: Override conflicting styles with higher specificity
5. **Delete Agent Path Issue**: Check for empty directory path before calling `os.makedirs()`

## Removed Features
- ❌ Local SQLite database integration
- ❌ Basic authentication system
- ❌ Development mode with Vite dev server proxying
- ❌ Separate development and production scripts

## Implementation Phases Status

### ✅ Completed Phases (1-11)
- **Phase 1-2**: Project structure, backend foundation, core features
- **Phase 3-4**: Frontend foundation and advanced features
- **Phase 5**: Integration and advanced features
- **Phase 6**: Build process and dependency management
- **Phase 7**: Development architecture and UX improvements
- **Phase 8**: LLM integration and configuration
- **Phase 9**: Advanced features and optimization
- **Phase 10**: Frontend improvements and UX enhancement
- **Phase 11**: Error handling and fail fast implementation

### 🔄 Remaining Phases (12-13)
- **Phase 12**: Testing & Quality Assurance
- **Phase 13**: Documentation & Local Deployment

## File Structure Summary

```
ATeam/
├── backend/
│   ├── main.py                 # FastAPI application with frontend serving
│   ├── agent_manager.py        # Agent management (fixed delete path issue)
│   ├── tool_manager.py         # Tool system
│   ├── prompt_manager.py       # Prompt management (fail fast implementation)
│   ├── llm_interface.py        # LLM integration
│   ├── chat_engine.py          # Chat processing
│   ├── monitoring.py           # System monitoring
│   ├── models.yaml             # Model configurations
│   ├── agents.yaml             # Agent configurations
│   ├── tools.yaml              # Tool definitions (custom only)
│   ├── providers.yaml          # Provider definitions (no models)
│   └── prompts/                # Prompt templates
├── frontend/
│   ├── src/components/         # React components
│   ├── src/api/index.ts        # API client
│   └── package.json            # Dependencies
├── build_and_run.ps1           # Single development server script
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
``` 