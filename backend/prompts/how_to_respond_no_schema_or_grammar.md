# How to Respond Without Schema or Grammar

When your model doesn't support structured schemas or grammars, follow these guidelines:

## Response Structure

Always structure your responses as JSON with these fields:

```json
{
  "action": "ACTION_TYPE",
  "reasoning": "Your thought process and reasoning",
  "content": "Your main response content",
  "tool": "TOOL_NAME", // if using a tool
  "parameters": {}, // if using a tool
  "target_agent": "AGENT_ID" // if calling another agent
}
```

## Action Types

- `NORMAL_RESPONSE`: Standard conversational response
- `USE_TOOL`: When you need to use a tool
- `TOOL_RETURN`: When returning tool results
- `AGENT_CALL`: When calling another agent
- `AGENT_RETURN`: When returning from an agent call
- `REFINEMENT_RESPONSE`: When refining a previous response

## Guidelines

1. **Always use JSON**: Even for simple responses, wrap them in the JSON structure
2. **Include reasoning**: Explain your thought process in the reasoning field
3. **Be explicit**: Clearly state what action you're taking
4. **Handle errors gracefully**: If something goes wrong, explain in the content field

## Examples

**Normal Response:**
```json
{
  "action": "NORMAL_RESPONSE",
  "reasoning": "User asked a simple question that I can answer directly",
  "content": "The answer to your question is..."
}
```

**Tool Usage:**
```json
{
  "action": "USE_TOOL",
  "reasoning": "I need to use a tool to get this information",
  "tool": "SearchTool",
  "parameters": {"query": "user query"},
  "content": "I'll search for that information for you."
}
```

**Agent Call:**
```json
{
  "action": "AGENT_CALL",
  "reasoning": "This task requires specialized expertise",
  "target_agent": "specialist_agent_id",
  "content": "I'll delegate this to a specialist agent."
}
```

Remember: Always respond in this structured format when schemas or grammars are not available.