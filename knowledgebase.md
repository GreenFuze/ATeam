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
- **Tool System**: Dynamic Python tool loading and execution
- **Real-time Communication**: WebSocket-based chat system
- **Configuration Management**: YAML-based configuration files (agents.yaml, tools.yaml, providers.yaml, models.yaml, prompts.yaml)
- **Provider Management**: Support for OpenAI, Anthropic, Google, and local models
- **Dynamic Model Management**: Runtime discovery of models and their capabilities
- **Schema Management**: JSON schema CRUD operations for structured outputs
- **Context Window Tracking**: Real-time context usage calculation and visualization
- **Global Notification System**: Proactive system health monitoring and user alerts
- **Enhanced Prompt Management**: Full CRUD operations with specialized editing interfaces for different prompt types

### ✅ UI/UX Features
- **Dark Mode**: Consistent dark theme throughout with proper contrast
- **Two-Tab Sidebar**: Agents tab (shows agent list) and Settings tab (Tools, Models, Providers, Prompts, Schemas)
- **Agent Management**: Full CRUD operations with modal interface and delete confirmation
- **Chat Interface**: Multiline input with context window progress tracking
- **Message Display**: Type-specific icons, tooltips, and formatting options with SYSTEM message type support and editable mode
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

## Recent Enhancements

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

## File Organization
- `backend/agents.yaml` - Agent configurations
- `backend/tools.yaml` - Tool definitions (custom only)
- `backend/providers.yaml` - LLM provider definitions (no models)
- `backend/models.yaml` - Model configurations with provider references
- `backend/prompts.yaml` - Prompt metadata (name, type) for persistence
- `backend/prompts/` - Directory containing markdown prompt files
- `backend/schemas/` - Directory containing JSON schema files

### Backend Core Files
- `backend/main.py` - FastAPI application with all endpoints and static file serving
- `backend/agent_manager.py` - Agent lifecycle management (fixed delete path issue)
- `backend/tool_manager.py` - Tool loading and execution
- `backend/provider_manager.py` - LLM provider management with strict typing
- `backend/models_manager.py` - Dynamic model discovery and settings management
- `backend/schema_manager.py` - JSON schema CRUD operations
- `backend/prompt_manager.py` - Prompt file management (fail fast implementation)
- `backend/llm_interface.py` - LLM integration layer
- `backend/chat_engine.py` - Chat processing logic with context window tracking
- `backend/schemas.py` - Pydantic data models and type definitions

### Frontend Structure
- `frontend/src/components/Sidebar.tsx` - Two-tab sidebar (Agents/Settings) with notifications
- `frontend/src/components/AgentsPage.tsx` - Agent list with empty state
- `frontend/src/components/SettingsPage.tsx` - Settings with conditional rendering and model groups
- `frontend/src/components/AgentChat.tsx` - Enhanced chat interface with context tracking
- `frontend/src/components/AgentSettingsModal.tsx` - Agent configuration modal with delete functionality
- `frontend/src/components/MessageDisplay.tsx` - Message rendering component
- `frontend/src/components/ContextProgress.tsx` - Context window progress indicator with N/A state
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

### 🔄 Current State
- **Application Running**: Server starts successfully on port 8000
- **Frontend Accessible**: Clean UI with proper navigation and dark mode
- **API Working**: All endpoints responding correctly
- **Agents Available**: 3 pre-configured agents (God, ToolBuilder, Assistant)
- **All Features Working**: Complete frontend improvements implemented
- **Message Types**: System messages properly displayed with correct icons
- **Dark Mode**: All messages readable with proper contrast and styling
- **Dynamic Models**: 29 chat models, 8 embedding models discovered
- **Context Tracking**: Real-time context usage with N/A state for missing context windows
- **Global Notifications**: System health monitoring with 0 warnings (all models configured)
- **Model Warning Icons**: No warning icons displayed (all models have context window sizes)

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

### Error Handling & Fail Fast Philosophy
1. **Core Principle**: "Fail fast, not silent" - never create defaults that hide problems
2. **No Default Creation**: System never creates default files or configurations
3. **Explicit Errors**: Missing resources result in clear error messages
4. **Configuration Management**: Clear separation of concerns in YAML files
5. **Error Handling Architecture**: Comprehensive backend error details with frontend error dialogs
6. **Global Notifications**: Proactive issue detection and user alerts
7. **Model-Specific Warnings**: Targeted warnings for specific configuration issues

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

## Removed Features
- ❌ Local SQLite database integration
- ❌ Basic authentication system
- ❌ Development mode with Vite dev server proxying
- ❌ Separate development and production scripts
- ❌ Static model configurations in YAML
- ❌ "Discovered" badges (all models are discovered)
- ❌ "Configured" badges (replaced with "Default" badge logic)
- ❌ Global context window notifications (replaced with model-specific warning icons)

## Implementation Phases Status

### ✅ Completed Phases (1-14)
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

### 🎉 All Phases Complete
- **Dynamic Model Management**: Complete runtime discovery and settings
- **Enhanced UI**: Separate model groups, proper field types, badges
- **Context Window Tracking**: Real-time usage with visual progress
- **Global Notifications**: System health monitoring and alerts
- **Schema Management**: Complete CRUD operations for JSON schemas
- **Type Safety**: Comprehensive type handling throughout the system
- **Model Warning System**: Targeted warnings for models needing configuration
- **Complete Model Configuration**: All OpenAI models properly configured

## File Structure Summary

```
ATeam/
├── backend/
│   ├── main.py                 # FastAPI application with frontend serving
│   ├── agent_manager.py        # Agent management (fixed delete path issue)
│   ├── tool_manager.py         # Tool system
│   ├── models_manager.py       # Dynamic model discovery and settings
│   ├── schema_manager.py       # JSON schema CRUD operations
│   ├── provider_manager.py     # LLM provider management with strict typing
│   ├── prompt_manager.py       # Prompt management (fail fast implementation)
│   ├── llm_interface.py        # LLM integration
│   ├── chat_engine.py          # Chat processing with context tracking
│   ├── monitoring.py           # System monitoring
│   ├── models.yaml             # Model configurations (complete OpenAI coverage)
│   ├── agents.yaml             # Agent configurations
│   ├── tools.yaml              # Tool definitions (custom only)
│   ├── providers.yaml          # Provider definitions (no models)
│   ├── prompts/                # Prompt templates
│   └── schemas/                # JSON schema files
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

### System Health
- **0 Warnings**: All providers and models properly configured
- **All APIs Working**: Models, providers, schemas, agents
- **Frontend Responsive**: All components working correctly
- **Type Safety**: No type errors in development
- **Complete Configuration**: All 29 OpenAI chat models configured with accurate specifications

The LLM model management system is now complete with all requested features implemented and working! 🎉 