# ATeam API Documentation

## Overview

The ATeam API provides a comprehensive interface for managing multi-agent systems, tools, prompts, and real-time communication. All endpoints return JSON responses and use standard HTTP status codes.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Currently, the API does not require authentication for local development.

## Response Format

API responses vary by endpoint. Most endpoints return the data directly without a wrapper format.

## Health & Monitoring

### Get System Health

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1704067200.0,
  "version": "1.0.0"
}
```

### Get Detailed System Health

```http
GET /api/monitoring/health
```

**Response:**
```json
{
  "system": {
    "cpu_usage": 25.5,
    "memory_usage": 45.2,
    "disk_usage": 60.1,
    "network_status": "healthy"
  },
  "llm": {
    "status": "healthy",
    "available_models": ["gpt-4", "claude-3-sonnet"],
    "last_check": "2024-01-01T00:00:00Z"
  }
}
```

### Get Performance Metrics

```http
GET /api/monitoring/metrics
```

**Response:**
```json
{
  "api_calls": {
    "total": 150,
    "successful": 145,
    "failed": 5,
    "average_response_time": 0.25
  },
  "chat_messages": {
    "total": 89,
    "average_length": 45
  }
}
```

### Get Specific Metric Statistics

```http
GET /api/monitoring/metrics/{metric_name}?minutes=60
```

**Parameters:**
- `metric_name`: Name of the metric to get statistics for
- `minutes` (optional): Number of minutes to look back (default: 60)

**Response:**
```json
{
  "count": 150,
  "min": 0.1,
  "max": 2.5,
  "avg": 0.25,
  "latest": 0.3
}
```

### Get Error Summary

```http
GET /api/monitoring/errors?hours=24
```

**Parameters:**
- `hours` (optional): Number of hours to look back (default: 24)

**Response:**
```json
{
  "total_errors": 5,
  "error_types": {
    "validation_error": 2,
    "llm_error": 3
  },
  "recent_errors": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "type": "llm_error",
      "message": "API key invalid",
      "details": {}
    }
  ]
}
```

## Agent Management

### List All Agents

```http
GET /api/agents
```

**Response:**
```json
[
  {
    "id": "assistant",
    "name": "General Assistant",
    "description": "A helpful AI assistant",
    "model": "gpt-4",
    "prompts": ["system_prompt.md"],
    "tools": [],
    "schema_file": null,
    "grammar_file": null,
    "temperature": 0.7,
    "max_tokens": null,
    "enable_summarization": true,
    "enable_scratchpad": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get Specific Agent

```http
GET /api/agents/{agent_id}
```

**Response:**
```json
{
  "id": "assistant",
  "name": "General Assistant",
  "description": "A helpful AI assistant",
  "model": "gpt-4",
  "prompts": ["system_prompt.md"],
  "tools": [],
  "schema_file": null,
  "grammar_file": null,
  "temperature": 0.7,
  "max_tokens": null,
  "enable_summarization": true,
  "enable_scratchpad": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Create Agent

```http
POST /api/agents
```

**Request Body:**
```json
{
  "name": "New Agent",
  "description": "A new AI agent",
  "model": "gpt-4",
  "prompts": ["system_prompt.md"],
  "tools": ["calculator"],
  "schema_file": null,
  "grammar_file": null,
  "temperature": 0.7,
  "max_tokens": null,
  "enable_summarization": true,
  "enable_scratchpad": true
}
```

**Response:**
```json
{
  "agent_id": "new_agent_123",
  "status": "created"
}
```

### Update Agent

```http
PUT /api/agents/{agent_id}
```

**Request Body:**
```json
{
  "name": "Updated Agent",
  "description": "Updated description",
  "model": "claude-3-sonnet",
  "prompts": ["system_prompt.md", "specialist_prompt.md"],
  "tools": ["calculator", "web_search"],
  "temperature": 0.8,
  "enable_summarization": true,
  "enable_scratchpad": true
}
```

**Response:**
```json
{
  "status": "updated"
}
```

### Delete Agent

```http
DELETE /api/agents/{agent_id}
```

**Response:**
```json
{
  "status": "deleted"
}
```

## Tool Management

### List All Tools

```http
GET /api/tools
```

**Response:**
```json
[
  {
    "name": "calculator",
    "description": "Perform mathematical calculations",
    "parameters": {
      "expression": {
        "type": "string",
        "required": true,
        "description": "Mathematical expression to evaluate"
      }
    },
    "is_provider_tool": false,
    "provider": null,
    "file_path": "tools/calculator.py"
  }
]
```

### Get Specific Tool

```http
GET /api/tools/{tool_name}
```

**Response:**
```json
{
  "name": "calculator",
  "description": "Perform mathematical calculations",
  "parameters": {
    "expression": {
      "type": "string",
      "required": true,
      "description": "Mathematical expression to evaluate"
    }
  },
  "is_provider_tool": false,
  "provider": null,
  "file_path": "tools/calculator.py"
}
```

### Create Tool

```http
POST /api/tools
```

**Request Body:**
```json
{
  "name": "new_tool",
  "description": "A new tool",
  "code": "def execute(expression):\n    return eval(expression)",
  "parameters": {
    "expression": {
      "type": "string",
      "required": true,
      "description": "Input parameter"
    }
  }
}
```

**Response:**
```json
{
  "tool_name": "new_tool",
  "status": "created"
}
```

## Prompt Management

### List All Prompts

```http
GET /api/prompts
```

**Response:**
```json
[
  {
    "name": "system_prompt.md",
    "content": "# System Prompt\n\nYou are a helpful AI assistant...",
    "type": "system",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get Specific Prompt

```http
GET /api/prompts/{prompt_name}
```

**Response:**
```json
{
  "name": "system_prompt.md",
  "content": "# System Prompt\n\nYou are a helpful AI assistant...",
  "type": "system",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Create Prompt

```http
POST /api/prompts
```

**Request Body:**
```json
{
  "name": "new_prompt.md",
  "content": "# New Prompt\n\nThis is a new prompt...",
  "type": "system"
}
```

**Response:**
```json
{
  "prompt_name": "new_prompt.md",
  "status": "created"
}
```

### Update Prompt

```http
PUT /api/prompts/{prompt_name}
```

**Request Body:**
```json
{
  "content": "# Updated Prompt\n\nThis is an updated prompt..."
}
```

**Response:**
```json
{
  "status": "updated"
}
```

## Chat & Communication

### Send Message to Agent

```http
POST /api/chat/{agent_id}
```

**Request Body:**
```json
{
  "content": "Hello, how can you help me today?"
}
```

**Response:**
```json
{
  "message": {
    "id": "msg_123",
    "agent_id": "assistant",
    "content": "Hello! I'm here to help you with various tasks...",
    "message_type": "NORMAL_RESPONSE",
    "timestamp": "2024-01-01T00:00:00Z",
    "metadata": {}
  },
  "session_id": "session_123",
  "agent_response": {
    "content": "Hello! I'm here to help you with various tasks...",
    "message_type": "NORMAL_RESPONSE",
    "metadata": {}
  }
}
```

### WebSocket Chat

Connect to the WebSocket endpoint for real-time chat:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/assistant');

ws.onopen = function() {
  console.log('Connected to chat');
};

ws.onmessage = function(event) {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

// Send a message
ws.send(JSON.stringify({
  content: "Hello, how are you?"
}));
```

**Message Format:**
```json
{
  "content": "Message content"
}
```

## Models

### List Available Models

```http
GET /api/models
```

**Response:**
```json
[
  {
    "name": "gpt-4",
    "provider": "openai",
    "supports_schema": true,
    "supports_grammar": true,
    "max_tokens": 8192,
    "description": "OpenAI's most capable model"
  },
  {
    "name": "claude-3-sonnet",
    "provider": "anthropic",
    "supports_schema": true,
    "supports_grammar": false,
    "max_tokens": 4096,
    "description": "Anthropic's Claude 3 Sonnet model"
  }
]
```

## Validation

### Validate Agent Configuration

```http
POST /api/validate-agent?agent_id={agent_id}
```

**Response:**
```json
{
  "valid": true
}
```

## Error Handling

The API uses standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

Error responses include:

```json
{
  "detail": "Error message"
}
```

## Rate Limiting

Currently, no rate limiting is implemented for local development.

## WebSocket Events

### Connection Events

- `open` - Connection established
- `close` - Connection closed
- `error` - Connection error

### Message Events

- `message` - Received message from agent
- `error` - Error message

## Examples

### Python Client Example

```python
import requests
import json

# Base URL
base_url = "http://localhost:8000/api"

# Create an agent
agent_data = {
    "name": "Python Test Agent",
    "description": "Agent created via Python client",
    "model": "gpt-4",
    "prompts": ["system_prompt.md"],
    "tools": [],
    "temperature": 0.7,
    "enable_summarization": True,
    "enable_scratchpad": True
}

response = requests.post(f"{base_url}/agents", json=agent_data)
agent_id = response.json()["agent_id"]

# Send a message
message_data = {"content": "Hello from Python!"}
response = requests.post(f"{base_url}/chat/{agent_id}", json=message_data)
print(response.json()["agent_response"]["content"])
```

### JavaScript Client Example

```javascript
// Get all agents
fetch('/api/agents')
  .then(response => response.json())
  .then(agents => {
    console.log('Agents:', agents);
  });

// Create an agent
const agentData = {
  name: "JS Test Agent",
  description: "Agent created via JavaScript",
  model: "gpt-4",
  prompts: ["system_prompt.md"],
  tools: [],
  temperature: 0.7,
  enable_summarization: true,
  enable_scratchpad: true
};

fetch('/api/agents', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(agentData)
})
.then(response => response.json())
.then(data => {
  console.log('Created agent:', data.agent_id);
});
```