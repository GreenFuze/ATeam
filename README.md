# ATeam - Multi-Agent System

A full-stack web application for managing and interacting with AI agents using the `llm` Python package. Built with FastAPI backend and React frontend.

## Features

- **Multi-Agent Architecture**: Configurable agents with YAML configuration
- **LLM Integration**: Support for multiple providers via the `llm` package
- **Dynamic Tool System**: Python tools loaded at runtime
- **Real-time Chat**: WebSocket-based communication
- **Dark Mode UI**: Modern interface with Mantine components
- **System Monitoring**: Real-time health checks and performance metrics
- **Streaming Responses**: Real-time LLM response streaming
- **Local Development**: Single server setup for easy development

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- PowerShell (Windows)

### Installation & Running

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ATeam
   ```

2. **Run the application**
   ```powershell
   .\build.ps1
   ```

3. **Access the application**
   - Open your browser to `http://localhost:8000`
   - The application will automatically install dependencies and start the server

## Architecture

### Backend (FastAPI)

- **`main.py`**: Application entry point with API routes and frontend serving
- **`agent_manager.py`**: Agent configuration and management
- **`tool_manager.py`**: Dynamic tool loading and execution
- **`prompt_manager.py`**: Prompt template management
- **`llm_interface.py`**: LLM integration with the `llm` package
- **`chat_engine.py`**: Chat processing and message handling
- **`monitoring.py`**: System health and performance monitoring
- **`streaming.py`**: Real-time response streaming

### Frontend (React + TypeScript)

- **`App.tsx`**: Main application component with routing
- **`Sidebar.tsx`**: Navigation and agent selection
- **`AgentChat.tsx`**: Real-time chat interface
- **`AgentsPage.tsx`**: Agent management interface
- **`MonitoringDashboard.tsx`**: System monitoring dashboard

### Configuration Files

- **`models.yaml`**: LLM model configurations
- **`agents.yaml`**: Agent definitions
- **`tools/`**: Python tool files
- **`prompts/`**: Markdown prompt templates

## API Endpoints

### Health & Monitoring
- `GET /api/health` - Basic health check
- `GET /api/monitoring/health` - System health information
- `GET /api/monitoring/metrics` - Performance metrics
- `GET /api/monitoring/errors` - Error summary

### Agent Management
- `GET /api/agents` - List all agents
- `GET /api/agents/{agent_id}` - Get specific agent
- `POST /api/agents` - Create new agent
- `PUT /api/agents/{agent_id}` - Update agent
- `DELETE /api/agents/{agent_id}` - Delete agent

### Tool Management
- `GET /api/tools` - List all tools
- `GET /api/tools/{tool_name}` - Get specific tool
- `POST /api/tools` - Create new tool

### Prompt Management
- `GET /api/prompts` - List all prompts
- `GET /api/prompts/{prompt_name}` - Get specific prompt
- `POST /api/prompts` - Create new prompt
- `PUT /api/prompts/{prompt_name}` - Update prompt

### Chat & Communication
- `POST /api/chat/{agent_id}` - Send message to agent
- `WebSocket /ws/chat/{agent_id}` - Real-time chat

### Models
- `GET /api/models` - List available LLM models

## Development

### Running Tests

**Backend Tests:**
```bash
cd backend
python -m pytest test_api.py -v
```

**Frontend Tests:**
```bash
cd frontend
npm test
```

### Project Structure

```
ATeam/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── agent_manager.py        # Agent management
│   ├── tool_manager.py         # Tool system
│   ├── prompt_manager.py       # Prompt management
│   ├── llm_interface.py        # LLM integration
│   ├── chat_engine.py          # Chat processing
│   ├── monitoring.py           # System monitoring
│   ├── streaming.py            # Streaming responses
│   ├── test_api.py             # API tests
│   ├── models.yaml             # Model configurations
│   ├── agents.yaml             # Agent configurations
│   ├── tools/                  # Python tools
│   └── prompts/                # Prompt templates
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── App.tsx             # Main app
│   │   └── index.css           # Global styles
│   ├── package.json            # Dependencies
│   └── jest.config.js          # Test configuration
├── build.ps1                   # Development server script
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Configuration

### LLM Models (`backend/models.yaml`)

Configure available LLM models and their capabilities:

```yaml
models:
  gpt-4:
    name: "GPT-4"
    provider: "openai"
    supports_schema: true
    supports_grammar: true
    max_tokens: 8192
    description: "OpenAI's most capable model"

defaults:
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 4096

providers:
  openai:
    api_key_env: "OPENAI_API_KEY"
    base_url: "https://api.openai.com/v1"
```

### Agents (`backend/agents.yaml`)

Define your agents:

```yaml
agents:
  assistant:
    name: "General Assistant"
    description: "A helpful AI assistant"
    model: "gpt-4"
    tools: []
    prompts: ["system_prompt.md"]
    
  specialist:
    name: "Specialist Agent"
    description: "Specialized in specific tasks"
    model: "claude-3-sonnet"
    tools: ["calculator", "web_search"]
    prompts: ["specialist_prompt.md"]
```

## Environment Variables

Set these environment variables for LLM providers:

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Google
export GOOGLE_API_KEY="your-google-api-key"
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   - The application uses port 8000 by default
   - Check if another service is using the port
   - Kill the process or change the port in `main.py`

2. **Missing dependencies**
   - Run `.\build.ps1` to install all dependencies
   - Check Python and Node.js versions

3. **LLM API errors**
   - Verify your API keys are set correctly
   - Check the `llm` package installation
   - Review the `models.yaml` configuration

4. **Frontend not loading**
   - Ensure the backend is running on port 8000
   - Check browser console for errors
   - Verify TypeScript compilation

### Logs

- Backend logs are displayed in the terminal
- Frontend errors appear in browser console
- System monitoring is available at `/monitoring`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Open an issue on GitHub
