import os
import inspect
import importlib.util
from typing import Dict, List, Optional, Any
from schemas import ToolConfig
import json
import ast

class ToolManager:
    def __init__(self, tools_dir: str = "tools"):
        self.tools_dir = tools_dir
        self.tools: Dict[str, Any] = {}
        self.discover_tools()
        
    def discover_tools(self):
        """Discover tools from Python files in the tools directory"""
        if not os.path.exists(self.tools_dir):
            print(f"Warning: Tools directory {self.tools_dir} not found")
            return
            
        # Get the absolute path of the tools directory
        tools_abs_path = os.path.abspath(self.tools_dir)
        
        for filename in os.listdir(self.tools_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                file_path = os.path.join(self.tools_dir, filename)
                self._discover_tools_from_file(file_path, tools_abs_path)
    
    def _discover_tools_from_file(self, file_path: str, tools_abs_path: str):
        """Discover tools from a single Python file"""
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location("tools_module", file_path)
            if spec is None or spec.loader is None:
                print(f"Could not load module from {file_path}")
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Discover functions (public functions not starting with _)
            for name, obj in inspect.getmembers(module):
                if (inspect.isfunction(obj) and 
                    not name.startswith('_') and 
                    obj.__module__ == module.__name__):
                    
                    # Get function signature
                    signature = self._get_function_signature(obj)
                    
                    tool_info = {
                        'name': name,
                        'type': 'function',
                        'description': obj.__doc__ or None,
                        'file_path': file_path,
                        'relative_path': os.path.relpath(file_path, tools_abs_path),
                        'has_docstring': bool(obj.__doc__),
                        'signature': signature
                    }
                    self.tools[name] = tool_info
            
            # Discover classes that implement llm.Toolbox
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    obj.__module__ == module.__name__):
                    
                    # Check if the class implements llm.Toolbox
                    if self._implements_llm_toolbox(obj):
                        methods = self._get_public_methods(obj)
                        tool_info = {
                            'name': name,
                            'type': 'class',
                            'description': obj.__doc__ or None,
                            'file_path': file_path,
                            'relative_path': os.path.relpath(file_path, tools_abs_path),
                            'has_docstring': bool(obj.__doc__),
                            'methods': methods
                        }
                        self.tools[name] = tool_info
                        
        except Exception as e:
            print(f"Error discovering tools from {file_path}: {e}")
    
    def _implements_llm_toolbox(self, cls) -> bool:
        """Check if a class implements llm.Toolbox"""
        try:
            # Check if the class has llm.Toolbox in its bases
            for base in cls.__mro__:
                if base.__name__ == 'Toolbox' and 'llm' in str(base.__module__):
                    return True
            return False
        except:
            return False
    
    def _get_public_methods(self, cls) -> List[Dict[str, Any]]:
        """Get all public methods from a class"""
        methods = []
        for name, method in inspect.getmembers(cls):
            if (inspect.isfunction(method) and 
                not name.startswith('_') and
                method.__module__ == cls.__module__):
                
                # Get method signature
                signature = self._get_function_signature(method)
                
                method_info = {
                    'name': name,
                    'description': method.__doc__ or None,
                    'has_docstring': bool(method.__doc__),
                    'signature': signature
                }
                methods.append(method_info)
        return methods
    
    def _get_function_signature(self, func) -> str:
        """Extract function signature as a string"""
        try:
            # Get the signature using inspect
            sig = inspect.signature(func)
            
            # Convert signature to string, but clean it up
            sig_str = str(sig)
            
            # Remove 'self' parameter for methods (it's not useful for display)
            if sig_str.startswith('(self, '):
                sig_str = '(' + sig_str[7:]
            elif sig_str.startswith('(self)'):
                sig_str = '()'
            
            return sig_str
        except Exception as e:
            # Fallback: try to get basic info
            try:
                # Try to get the source and parse it
                source = inspect.getsource(func)
                # This is a simple fallback - in practice, inspect.signature should work
                return "(...)"
            except:
                return "(...)"
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all discovered tools"""
        return list(self.tools.values())
    
    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool by name"""
        return self.tools.get(tool_name)
    
    def get_tools_directory_path(self) -> str:
        """Get the full path of the tools directory"""
        return os.path.abspath(self.tools_dir) 