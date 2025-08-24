import asyncio
import msgpack
import ssl
import time
import uuid
from typing import Any, Callable, Optional, Union, List
from redis.asyncio import Redis, ConnectionPool
from ..util.types import Result, ErrorInfo
from ..util.const import DEFAULTS
from ..util.logging import log

class RedisTransport:
    def __init__(self, url: str, username: str = "", password: str = "", tls: bool = False, config=None) -> None:
        self.url = url
        self.config = config
        
        # Legacy parameters (for backward compatibility)
        self.username = username
        self.password = password
        self.tls = tls
        
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._subscriptions: dict = {}
        self._running = False

    @classmethod
    def from_config(cls, config) -> 'RedisTransport':
        """Create RedisTransport from TransportCfg configuration."""
        return cls(
            url=str(config.url),
            username=config.username or "",
            password=config.password or "",
            tls=config.tls,
            config=config
        )

    async def connect(self) -> Result[None]:
        """Connect to Redis and create connection pool."""
        try:
            # Parse URL to extract components
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            
            # Build connection parameters
            conn_params = {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 6379,
                "db": int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
                "decode_responses": False,  # We handle msgpack encoding
                "max_connections": 10
            }
            
            # Use enhanced config if available
            if self.config:
                # Authentication (ACL takes precedence)
                username = self.config.acl_username or self.config.username
                password = self.config.acl_password or self.config.password
                
                if username:
                    conn_params["username"] = username
                if password:
                    conn_params["password"] = password
                elif parsed.password:
                    conn_params["password"] = parsed.password
                if parsed.username and not username:
                    conn_params["username"] = parsed.username
                
                # Connection settings
                if self.config.socket_timeout:
                    conn_params["socket_timeout"] = self.config.socket_timeout
                if self.config.socket_connect_timeout:
                    conn_params["socket_connect_timeout"] = self.config.socket_connect_timeout
                if self.config.connection_pool_max_connections:
                    conn_params["max_connections"] = self.config.connection_pool_max_connections
                
                # TLS/SSL configuration
                if self.config.tls:
                    ssl_context = ssl.create_default_context()
                    
                    # Configure certificate verification
                    if not self.config.verify_cert:
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                    
                    # Load CA certificate
                    if self.config.ca_file:
                        ssl_context.load_verify_locations(cafile=self.config.ca_file)
                    
                    # Load client certificate and key
                    if self.config.cert_file and self.config.key_file:
                        ssl_context.load_cert_chain(self.config.cert_file, self.config.key_file)
                    
                    conn_params["ssl"] = ssl_context
                    
            else:
                # Legacy authentication
                if self.username:
                    conn_params["username"] = self.username
                if self.password:
                    conn_params["password"] = self.password
                elif parsed.password:
                    conn_params["password"] = parsed.password
                if parsed.username:
                    conn_params["username"] = parsed.username
                    
                # Legacy SSL
                if self.tls:
                    conn_params["ssl"] = True
                
            self._pool = ConnectionPool(**conn_params)
            self._redis = Redis(connection_pool=self._pool)
            await self._redis.ping()
            self._running = True
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("redis.connect_failed", str(e)))

    async def disconnect(self) -> Result[None]:
        """Disconnect from Redis."""
        try:
            self._running = False
            if self._redis:
                await self._redis.aclose()
            if self._pool:
                await self._pool.disconnect()
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("redis.disconnect_failed", str(e)))

    async def publish(self, channel: str, data: bytes) -> Result[None]:
        """Publish data to a Redis channel."""
        if not self._running or not self._redis:
            return Result(ok=False, error=ErrorInfo("redis.not_connected", "Not connected"))
        
        try:
            await self._redis.publish(channel, data)
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("redis.publish_failed", str(e)))

    async def subscribe(self, channel: str, callback: Callable[[bytes], None]) -> Result[None]:
        """Subscribe to a Redis channel."""
        if not self._running or not self._redis:
            return Result(ok=False, error=ErrorInfo("redis.not_connected", "Not connected"))
        
        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(channel)
            self._subscriptions[channel] = pubsub
            
            # Start listening in background
            asyncio.create_task(self._listen_channel(channel, pubsub, callback))
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("redis.subscribe_failed", str(e)))

    async def _listen_channel(self, channel: str, pubsub, callback: Callable[[bytes], None]) -> None:
        """Listen for messages on a channel."""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    callback(message["data"])
        except Exception as e:
            log("ERROR", "redis.transport", "listen_failed", channel=channel, error=str(e))

    async def call(self, method: str, params: dict, timeout: float = None) -> Result[Any]:
        """Make an RPC call via Redis."""
        if not self._running or not self._redis:
            return Result(ok=False, error=ErrorInfo("redis.not_connected", "Not connected"))
        
        if timeout is None:
            timeout = DEFAULTS["RPC_TIMEOUT_SEC"]
        
        try:
            req_id = str(uuid.uuid4())
            request = {
                "req_id": req_id,
                "method": method,
                "params": params,
                "ts": time.time()
            }
            
            # Pack request
            req_data = msgpack.packb(request, use_bin_type=True)
            
            # Response channel
            res_channel = f"mcp:res:{req_id}"
            
            # Subscribe to response channel
            response_received = asyncio.Event()
            response_data = None
            
            def on_response(data: bytes):
                nonlocal response_data
                response_data = data
                response_received.set()
            
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(res_channel)
            
            # Send request
            await self._redis.publish(f"mcp:req:{method}", req_data)
            
            # Wait for response with timeout
            try:
                await asyncio.wait_for(response_received.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                await pubsub.unsubscribe(res_channel)
                await pubsub.aclose()
                return Result(ok=False, error=ErrorInfo("redis.rpc_timeout", f"RPC call to {method} timed out"))
            
            # Unsubscribe and close
            await pubsub.unsubscribe(res_channel)
            await pubsub.aclose()
            
            if response_data:
                response = msgpack.unpackb(response_data, raw=False)
                if response.get("ok", False):
                    return Result(ok=True, value=response.get("value"))
                else:
                    error = response.get("error", {})
                    return Result(ok=False, error=ErrorInfo(
                        error.get("code", "rpc.error"),
                        error.get("message", "Unknown RPC error")
                    ))
            else:
                return Result(ok=False, error=ErrorInfo("redis.no_response", "No response received"))
                
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("redis.call_failed", str(e)))

    async def set_key(self, key: str, value: Any, ttl: int = None) -> Result[None]:
        """Set a Redis key with optional TTL."""
        if not self._running or not self._redis:
            return Result(ok=False, error=ErrorInfo("redis.not_connected", "Not connected"))
        
        try:
            if ttl:
                await self._redis.setex(key, ttl, value)
            else:
                await self._redis.set(key, value)
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("redis.set_failed", str(e)))

    async def get_key(self, key: str) -> Result[Any]:
        """Get a Redis key value."""
        if not self._running or not self._redis:
            return Result(ok=False, error=ErrorInfo("redis.not_connected", "Not connected"))
        
        try:
            value = await self._redis.get(key)
            return Result(ok=True, value=value)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("redis.get_failed", str(e)))

    async def delete_key(self, key: str) -> Result[None]:
        """Delete a Redis key."""
        if not self._running or not self._redis:
            return Result(ok=False, error=ErrorInfo("redis.not_connected", "Not connected"))
        
        try:
            await self._redis.delete(key)
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("redis.delete_failed", str(e)))

    async def scan_keys(self, pattern: str) -> Result[List[str]]:
        """Scan for Redis keys matching a pattern."""
        if not self._running or not self._redis:
            return Result(ok=False, error=ErrorInfo("redis.not_connected", "Not connected"))
        
        try:
            keys = []
            cursor = 0
            while True:
                cursor, batch = await self._redis.scan(cursor, match=pattern, count=100)
                keys.extend([key.decode('utf-8') if isinstance(key, bytes) else key for key in batch])
                if cursor == 0:
                    break
            return Result(ok=True, value=keys)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("redis.scan_failed", str(e)))
