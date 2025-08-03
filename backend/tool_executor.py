import os
import importlib.util
import inspect
from typing import Any, Dict
from schemas import ToolReturnResponse

def _convert_value_to_type(value: Any, target_type) -> Any:
    """Convert value to the target type."""
    if target_type == bool:
        # Handle boolean conversion
        if isinstance(value, str):
            if value.lower() in ('true', '1', 'yes', 'on'):
                return True
            elif value.lower() in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"Cannot convert '{value}' to boolean")
        else:
            return bool(value)
    elif target_type == int:
        return int(value)
    elif target_type == float:
        return float(value)
    elif target_type == str:
        return str(value)
    else:
        # For other types, return as is (could be extended for more types)
        return value

def run_tool(name: str, args: Dict[str, Any]) -> ToolReturnResponse:
    """
    Execute a tool by name with arguments.
    
    Parameters
    ----------
    name : str
        Tool name in format 'module.function' or 'class.method'
    args : Dict[str, Any]
        Arguments to pass to the tool
        
    Returns
    -------
    ToolReturnResponse
        Result of tool execution
    """
    # Parse tool name to get module and function/class
    if '.' not in name:
        raise ValueError(f"Invalid tool name format: {name}. Expected format: 'module.function' or 'class.method'")
    
    parts = name.split('.', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid tool name format: {name}. Expected format: 'module.function' or 'class.method'")
    
    module_name, function_or_method_name = parts
    
    # Load the tool module
    tools_dir = os.path.join(os.path.dirname(__file__), "tools")
    module_file = os.path.join(tools_dir, f"{module_name}.py")
    
    if not os.path.exists(module_file):
        return ToolReturnResponse(
            action="TOOL_RETURN",
            tool=name,
            result=f'Tool module not found: {module_file}',
            success="False"
        )
    
    try:
        # Import the module dynamically
        spec = importlib.util.spec_from_file_location(f"tools.{module_name}", module_file)
        if spec is None or spec.loader is None:
            return ToolReturnResponse(
                action="TOOL_RETURN",
                tool=name,
                result=f'Could not load spec for {module_name}',
                success="False"
            )
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check if it's a function or a class method
        if hasattr(module, function_or_method_name):
            # It's a function
            tool_func = getattr(module, function_or_method_name)
            if not inspect.isfunction(tool_func):
                return ToolReturnResponse(
                    action="TOOL_RETURN",
                    tool=name,
                    result=f'{function_or_method_name} is not a function in module {module_name}',
                    success="False"
                )
        else:
            # Check if it's a class method (format: class.method)
            if '.' in function_or_method_name:
                class_name, method_name = function_or_method_name.split('.', 1)
                if not hasattr(module, class_name):
                    return ToolReturnResponse(
                        action="TOOL_RETURN",
                        tool=name,
                        result=f'Class {class_name} not found in module {module_name}',
                        success="False"
                    )
                
                cls = getattr(module, class_name)
                if not inspect.isclass(cls):
                    return ToolReturnResponse(
                        action="TOOL_RETURN",
                        tool=name,
                        result=f'{class_name} is not a class in module {module_name}',
                        success="False"
                    )
                
                if not hasattr(cls, method_name):
                    return ToolReturnResponse(
                        action="TOOL_RETURN",
                        tool=name,
                        result=f'Method {method_name} not found in class {class_name}',
                        success="False"
                    )
                
                # Create instance and get method
                instance = cls()
                tool_func = getattr(instance, method_name)
                if not inspect.ismethod(tool_func):
                    return ToolReturnResponse(
                        action="TOOL_RETURN",
                        tool=name,
                        result=f'{method_name} is not a method in class {class_name}',
                        success="False"
                    )
            else:
                return ToolReturnResponse(
                    action="TOOL_RETURN",
                    tool=name,
                    result=f'Function or method {function_or_method_name} not found in module {module_name}',
                    success="False"
                )
        
        # Get tool's signature to match parameters by name
        sig = inspect.signature(tool_func)
        bound_args = {}
        
        for param_name, param in sig.parameters.items():
            if param_name in args:
                # Convert value to proper type based on annotation
                value = args[param_name]
                if param.annotation != inspect.Parameter.empty:
                    bound_args[param_name] = _convert_value_to_type(value, param.annotation)
                else:
                    bound_args[param_name] = value
            elif param.default != inspect.Parameter.empty:
                bound_args[param_name] = param.default
            else:
                raise ValueError(f"Missing required argument: {param_name}")
        
        # Call the tool with matched arguments
        result = tool_func(**bound_args)
        
        # Convert result to string
        if result is None:
            result_str = "None"
        else:
            result_str = str(result)
        
        return ToolReturnResponse(
            action="TOOL_RETURN",
            tool=name,
            result=result_str,
            success="True"
        )
        
    except Exception as e:
        return ToolReturnResponse(
            action="TOOL_RETURN",
            tool=name,
            result=f'Error executing tool: {str(e)}',
            success="False"
        ) 