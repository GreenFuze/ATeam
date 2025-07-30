# Structured Response Format

All agent responses must follow this structured JSON format to ensure consistent communication and enable proper tool usage, agent delegation, and response parsing.

## Base Response Structure

```json
{
  "action": "ACTION_TYPE",
  "reasoning": "Your thought process and reasoning",
  "content": "Your main response content",
  "tool": "TOOL_NAME", // optional - if using a tool
  "parameters": {}, // optional - tool parameters
  "target_agent": "AGENT_ID" // optional - if calling another agent
}
```

## Action Types

### NORMAL_RESPONSE
Standard conversational response to the user.

```json
{
  "action": "NORMAL_RESPONSE",
  "reasoning": "User asked a simple question that I can answer directly",
  "content": "The answer to your question is..."
}
```

### USE_TOOL
When the agent needs to use a tool to accomplish a task.

```json
{
  "action": "USE_TOOL",
  "reasoning": "I need to search for information to answer this question",
  "tool": "SearchTool",
  "parameters": {
    "query": "user search query",
    "max_results": 5
  },
  "content": "I'll search for that information for you."
}
```

### TOOL_RETURN
When returning results from a tool execution.

```json
{
  "action": "TOOL_RETURN",
  "reasoning": "Processing the results from the tool execution",
  "content": "The search returned the following results: [results summary]"
}
```

### AGENT_CALL
When delegating a task to another agent.

```json
{
  "action": "AGENT_CALL",
  "reasoning": "This task requires specialized expertise in data analysis",
  "target_agent": "data_analyst_agent",
  "content": "I'll delegate this analysis to our data specialist."
}
```

### AGENT_RETURN
When returning results from an agent delegation.

```json
{
  "action": "AGENT_RETURN",
  "reasoning": "Providing the results from the delegated agent",
  "content": "The data analyst has completed the analysis: [analysis results]"
}
```

### REFINEMENT_RESPONSE
When refining or improving a previous response.

```json
{
  "action": "REFINEMENT_RESPONSE",
  "reasoning": "Adding more detail to the previous response",
  "content": "To elaborate on my previous answer: [additional details]"
}
```

## Tool Parameters

Tool parameters should be provided as a JSON object with the required parameters for the specific tool:

```json
{
  "parameters": {
    "param1": "value1",
    "param2": 42,
    "param3": ["item1", "item2"],
    "param4": {
      "nested": "value"
    }
  }
}
```

## Agent Delegation

When calling another agent, specify the target agent ID:

```json
{
  "target_agent": "agent_id_here"
}
```

## Guidelines

1. **Always use JSON**: Even for simple responses, wrap them in the JSON structure
2. **Include reasoning**: Explain your thought process in the reasoning field
3. **Be explicit**: Clearly state what action you're taking
4. **Handle errors gracefully**: If something goes wrong, explain in the content field
5. **Use appropriate action types**: Choose the most appropriate action for your response
6. **Provide complete information**: Include all necessary parameters for tools or agent calls

## Examples

### Simple Question Answer
```json
{
  "action": "NORMAL_RESPONSE",
  "reasoning": "User asked about the weather, which I can answer directly",
  "content": "The weather today is sunny with a high of 75°F."
}
```

### Complex Task with Tool Usage
```json
{
  "action": "USE_TOOL",
  "reasoning": "User wants to analyze data, which requires a data analysis tool",
  "tool": "DataAnalysisTool",
  "parameters": {
    "dataset": "sales_data.csv",
    "analysis_type": "trend_analysis",
    "time_period": "last_30_days"
  },
  "content": "I'll analyze the sales data for trends over the last 30 days."
}
```

### Agent Delegation
```json
{
  "action": "AGENT_CALL",
  "reasoning": "This requires specialized knowledge in machine learning",
  "target_agent": "ml_specialist",
  "content": "I'll have our machine learning specialist help with this model training task."
}
```

### Tool Result Processing
```json
{
  "action": "TOOL_RETURN",
  "reasoning": "Processing the search results to provide a comprehensive answer",
  "content": "Based on the search results, here's what I found: [processed results]"
}
```

## Error Handling

When errors occur, use the NORMAL_RESPONSE action with error information:

```json
{
  "action": "NORMAL_RESPONSE",
  "reasoning": "An error occurred while processing the request",
  "content": "I encountered an error: [error description]. Please try again or contact support."
}
```

## Schema Validation

This response format can be validated against the following JSON schema:

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["NORMAL_RESPONSE", "USE_TOOL", "TOOL_RETURN", "AGENT_CALL", "AGENT_RETURN", "REFINEMENT_RESPONSE"]
    },
    "reasoning": {
      "type": "string"
    },
    "content": {
      "type": "string"
    },
    "tool": {
      "type": "string"
    },
    "parameters": {
      "type": "object"
    },
    "target_agent": {
      "type": "string"
    }
  },
  "required": ["action", "reasoning", "content"]
}
``` 