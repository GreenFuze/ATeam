import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

class SchemaManager:
    """Manages JSON schema files for structured outputs"""
    
    def __init__(self, schemas_dir: str = "backend/schemas"):
        self.schemas_dir = schemas_dir
        self._ensure_schemas_directory()
    
    def _ensure_schemas_directory(self) -> None:
        """Ensure the schemas directory exists"""
        os.makedirs(self.schemas_dir, exist_ok=True)
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get all schema files"""
        schemas = []
        
        try:
            for file_path in Path(self.schemas_dir).glob("*.schema.json"):
                schema_name = file_path.stem.replace('.schema', '')
                schema_content = self._read_schema_file(file_path)
                
                if schema_content:
                    schemas.append({
                        'name': schema_name,
                        'content': schema_content,
                        'file_path': str(file_path),
                        'created_at': self._get_file_creation_time(file_path),
                        'updated_at': self._get_file_modification_time(file_path)
                    })
        except Exception as e:
            print(f"Error loading schemas: {e}")
        
        return schemas
    
    def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific schema by name"""
        try:
            file_path = Path(self.schemas_dir) / f"{schema_name}.schema.json"
            
            if not file_path.exists():
                return None
            
            schema_content = self._read_schema_file(file_path)
            
            if schema_content:
                return {
                    'name': schema_name,
                    'content': schema_content,
                    'file_path': str(file_path),
                    'created_at': self._get_file_creation_time(file_path),
                    'updated_at': self._get_file_modification_time(file_path)
                }
        except Exception as e:
            print(f"Error loading schema '{schema_name}': {e}")
        
        return None
    
    def create_schema(self, schema_name: str, schema_content: Dict[str, Any]) -> str:
        """Create a new schema file"""
        try:
            # Validate JSON schema
            if not self._validate_json_schema(schema_content):
                raise ValueError("Invalid JSON schema format")
            
            file_path = Path(self.schemas_dir) / f"{schema_name}.schema.json"
            
            if file_path.exists():
                raise ValueError(f"Schema '{schema_name}' already exists")
            
            # Write schema to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(schema_content, f, indent=2)
            
            return schema_name
        except Exception as e:
            print(f"Error creating schema '{schema_name}': {e}")
            raise
    
    def update_schema(self, schema_name: str, schema_content: Dict[str, Any]) -> None:
        """Update an existing schema file"""
        try:
            # Validate JSON schema
            if not self._validate_json_schema(schema_content):
                raise ValueError("Invalid JSON schema format")
            
            file_path = Path(self.schemas_dir) / f"{schema_name}.schema.json"
            
            if not file_path.exists():
                raise ValueError(f"Schema '{schema_name}' not found")
            
            # Write updated schema to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(schema_content, f, indent=2)
        except Exception as e:
            print(f"Error updating schema '{schema_name}': {e}")
            raise
    
    def delete_schema(self, schema_name: str) -> None:
        """Delete a schema file"""
        try:
            file_path = Path(self.schemas_dir) / f"{schema_name}.schema.json"
            
            if not file_path.exists():
                raise ValueError(f"Schema '{schema_name}' not found")
            
            file_path.unlink()
        except Exception as e:
            print(f"Error deleting schema '{schema_name}': {e}")
            raise
    
    def _read_schema_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Read and parse a schema file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading schema file {file_path}: {e}")
            return None
    
    def _validate_json_schema(self, schema_content: Dict[str, Any]) -> bool:
        """Basic validation of JSON schema format"""
        try:
            # Check if it has required JSON Schema fields
            if not isinstance(schema_content, dict):
                return False
            
            # Basic validation - should have $schema or type field
            if '$schema' not in schema_content and 'type' not in schema_content:
                return False
            
            return True
        except Exception:
            return False
    
    def _get_file_creation_time(self, file_path: Path) -> str:
        """Get file creation time as ISO string"""
        try:
            return str(file_path.stat().st_ctime)
        except Exception:
            return ""
    
    def _get_file_modification_time(self, file_path: Path) -> str:
        """Get file modification time as ISO string"""
        try:
            return str(file_path.stat().st_mtime)
        except Exception:
            return "" 