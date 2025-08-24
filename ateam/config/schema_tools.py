from pydantic import BaseModel, Field, AnyUrl
from typing import List, Optional, Literal
from .schema_security import SecurityCfg

class TransportCfg(BaseModel):
    kind: Literal["redis"] = "redis"
    url: AnyUrl = Field(description="Redis URL")
    
    # Authentication
    username: Optional[str] = Field(None, description="Redis username for ACL authentication")
    password: Optional[str] = Field(None, description="Redis password")
    
    # TLS Configuration
    tls: bool = Field(False, description="Enable TLS/SSL connection")
    ca_file: Optional[str] = Field(None, description="Path to CA certificate file")
    cert_file: Optional[str] = Field(None, description="Path to client certificate file")
    key_file: Optional[str] = Field(None, description="Path to client private key file")
    verify_cert: bool = Field(True, description="Verify server certificate")
    
    # Connection Settings
    socket_timeout: Optional[float] = Field(None, description="Socket timeout in seconds")
    socket_connect_timeout: Optional[float] = Field(None, description="Socket connect timeout in seconds")
    connection_pool_max_connections: Optional[int] = Field(None, description="Maximum connections in pool")
    
    # Security Settings
    require_auth: bool = Field(False, description="Require authentication even if not in URL")
    acl_username: Optional[str] = Field(None, description="ACL username (overrides username)")
    acl_password: Optional[str] = Field(None, description="ACL password (overrides password)")

class ToolsPolicyCfg(BaseModel):
    allow: List[str] = Field(default_factory=list)
    deny: List[str] = Field(default_factory=list)
    unsafe: bool = False  # global unsafe toggle; keep False

class ToolsCfg(BaseModel):
    mcp: TransportCfg
    tools: ToolsPolicyCfg = Field(default_factory=ToolsPolicyCfg)
    security: SecurityCfg = Field(default_factory=SecurityCfg)
