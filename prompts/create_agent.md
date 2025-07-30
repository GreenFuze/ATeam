# Agent Creation Instructions

When creating a new agent, follow these guidelines:

## Required Information

1. **Name**: A clear, descriptive name for the agent
2. **Description**: What this agent does and its purpose
3. **Model**: The LLM model to use (e.g., gpt-4, gpt-3.5-turbo)
4. **Prompts**: List of prompt files to use (optional)
5. **Tools**: List of tool names to assign (optional)

## Agent Types

- **Specialist Agents**: Focused on specific tasks or domains
- **General Agents**: Broad capabilities for general assistance
- **Coordinator Agents**: Manage other agents and workflows
- **Tool Agents**: Specialized in using specific tools

## Best Practices

1. **Clear Purpose**: Each agent should have a well-defined role
2. **Appropriate Tools**: Assign tools that match the agent's capabilities
3. **Effective Prompts**: Use prompts that guide the agent's behavior
4. **Balanced Configuration**: Consider temperature, token limits, and other parameters

## Example Agent Creation

```json
{
  "action": "USE_TOOL",
  "tool": "CreateAgent",
  "parameters": {
    "name": "DataAnalyst",
    "description": "Specialized agent for data analysis and visualization",
    "model": "gpt-4",
    "prompts": ["data_analysis_system.md"],
    "tools": ["PandasTool", "MatplotlibTool"]
  }
}
```

Always use the structured response format when creating agents.