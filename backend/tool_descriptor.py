import inspect
from typing import Callable, Iterable, Any, List, Dict

def tools_to_prompt(
    tools: Iterable[Callable],
    *,
    heading: str | None = None,
    sep: str = "\n\n",
) -> str:
    """
    Convert a list/iterable of callables (plain or @tool-wrapped) into a single
    prompt-friendly string.

    Parameters
    ----------
    tools   : iterable of callables (@tool objects or plain functions)
    heading : optional first line (e.g. "Available tools:")
    sep     : separator between tool blocks (default: blank line)

    Returns
    -------
    str
        A human-readable description of all tools, ready to embed in a prompt.
    """

    def _describe(func: Callable) -> str:
        sig = inspect.signature(getattr(func, "fn", func))
        base_name = getattr(func, "name", func.__name__)
        
        # Get module name and create full tool name
        module_name = func.__module__
        if module_name.startswith('tools.'):
            # Extract just the module name without the full path
            module_short_name = module_name.split('.')[-1]
            name = f"{module_short_name}.{base_name}"
        else:
            name = base_name
            
        doc = (getattr(func, "description", "") or func.__doc__ or "").strip().split("\n")[0] \
               or "No description provided."

        # Build argument list
        arg_lines = []
        for p in sig.parameters.values():
            if p.name == "self":
                continue
            ann = p.annotation if p.annotation is not inspect._empty else "Any"
            ann_name = ann.__name__ if hasattr(ann, "__name__") else str(ann) # type: ignore
            if p.default is inspect._empty:
                arg_lines.append(f"  - {p.name} ({ann_name})")
            else:
                arg_lines.append(f"  - {p.name} ({ann_name}, default={p.default!r})")

        arg_block = "\n".join(arg_lines) or "  (no arguments)"
        return f"Tool: {name}\nDescription: {doc}\nArguments:\n{arg_block}"

    body = sep.join(_describe(f) for f in tools)
    return f"# {heading}\n{body}" if heading else body

def class_to_prompt(
    cls: type,
    *,
    heading: str | None = None,
    sep: str = "\n\n",
) -> str:
    """
    Convert a class with public methods into a prompt-friendly string.

    Parameters
    ----------
    cls     : class to describe
    heading : optional first line (e.g. "Available tools:")
    sep     : separator between method blocks (default: blank line)

    Returns
    -------
    str
        A human-readable description of the class and its methods, ready to embed in a prompt.
    """

    def _describe_method(method: Callable, class_name: str) -> str:
        sig = inspect.signature(method)
        method_name = method.__name__
        
        # Create full method name
        name = f"{class_name}.{method_name}"
        
        doc = (method.__doc__ or "").strip().split("\n")[0] or "No description provided."

        # Build argument list
        arg_lines = []
        for p in sig.parameters.values():
            if p.name == "self":
                continue
            ann = p.annotation if p.annotation is not inspect._empty else "Any"
            ann_name = ann.__name__ if hasattr(ann, "__name__") else str(ann) # type: ignore
            if p.default is inspect._empty:
                arg_lines.append(f"  - {p.name} ({ann_name})")
            else:
                arg_lines.append(f"  - {p.name} ({ann_name}, default={p.default!r})")

        arg_block = "\n".join(arg_lines) or "  (no arguments)"
        return f"Tool: {name}\nDescription: {doc}\nArguments:\n{arg_block}"

    # Get all public methods (not starting with _)
    methods = []
    for name, method in inspect.getmembers(cls):
        if (inspect.isfunction(method) and 
            not name.startswith('_') and 
            method.__module__ == cls.__module__):
            methods.append(method)

    if not methods:
        return f"# {heading}\nNo public methods found in class {cls.__name__}" if heading else f"No public methods found in class {cls.__name__}"

    body = sep.join(_describe_method(m, cls.__name__) for m in methods)
    return f"# {heading}\n{body}" if heading else body

def get_tool_prompt_for_agent(tool_names: List[str], tool_manager) -> str:
    """
    Generate a prompt-friendly description of tools for an agent.
    
    Parameters
    ----------
    tool_names : List of tool names to include
    tool_manager : ToolManager instance to get tool information
    
    Returns
    -------
    str
        A human-readable description of the tools, ready to embed in a prompt.
    """
    if not tool_names:
        return ""
    
    tools_info = []
    
    for tool_name in tool_names:
        tool = tool_manager.get_tool(tool_name)
        if not tool:
            continue

        # Derive module name from relative_path (e.g., 'agent_management.py' -> 'agent_management')
        rel_path = tool.get('relative_path') or tool.get('file_path', '')
        module_name = str(rel_path).rsplit('/', 1)[-1].rsplit('\\', 1)[-1].replace('.py', '')

        if tool['type'] == 'function':
            # Use fully qualified name expected by executor: module.function
            fq_name = f"{module_name}.{tool['name']}"
            desc_full = tool.get('description', 'No description provided.') or 'No description provided.'
            desc = (desc_full.strip().split('\n')[0]) if desc_full else 'No description provided.'
            tools_info.append(
                "\n".join([
                    f"Tool: {fq_name}",
                    f"Description: {desc}",
                    f"Arguments: {tool.get('signature', '(...)')}"
                ])
            )
        elif tool['type'] == 'class':
            # For classes, list fully qualified method names: module.Class.method
            class_name = tool['name']
            methods = tool.get('methods', [])
            if methods:
                for method in methods:
                    method_name = method['name']
                    fq_name = f"{module_name}.{class_name}.{method_name}"
                    desc_full = method.get('description', 'No description provided.') or 'No description provided.'
                    description = (desc_full.strip().split('\n')[0]) if desc_full else 'No description provided.'
                    signature = method.get('signature', '(...)')
                    tools_info.append(
                        "\n".join([
                            f"Tool: {fq_name}",
                            f"Description: {description}",
                            f"Arguments: {signature}"
                        ])
                    )
            else:
                # No public methods; still expose class name to hint capabilities
                fq_name = f"{module_name}.{class_name}"
                tools_info.append(
                    "\n".join([
                        f"Tool: {fq_name}",
                        f"Description: {(tool.get('description', 'No description provided.') or 'No description provided.').strip().split('\n')[0]}",
                        "Arguments: (class with no public methods)"
                    ])
                )
        else:
            raise ValueError(f"Unknown tool type: {tool['type']} for tool {tool_name}")
    
    if not tools_info:
        return ""
    
    header = (
        "Available tools (use the Tool name exactly when calling a tool):\n"
        "- Functions: module.function\n"
        "- Class methods: module.Class.method\n\n"
    )
    return header + "\n\n".join(tools_info)