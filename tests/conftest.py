"""Pytest configuration for ATeam tests."""

import pytest
import pytest_asyncio
import subprocess
import time


class RedisTestManager:
    """Manages Redis Docker container for tests."""
    
    def __init__(self):
        self.container_name = "redis-ateam-pytests"
        self.port = 6379
        self.redis_url = f"redis://localhost:{self.port}"
    
    def start_redis(self):
        """Start Redis container."""
        try:
            # First, ensure any existing container is cleaned up
            self.stop_redis()
            
            # Create and start new container
            subprocess.run([
                "docker", "run", "-d",
                "--name", self.container_name,
                "-p", f"{self.port}:6379",
                "redis:7-alpine",
                "redis-server", "--save", "", "--appendonly", "no"
            ], check=True)
            
            # Wait for Redis to be ready
            time.sleep(3)
            
            # Test connection with retries
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    result = subprocess.run([
                        "docker", "exec", self.container_name,
                        "redis-cli", "ping"
                    ], capture_output=True, text=True, timeout=10)
                    
                    if "PONG" in result.stdout:
                        print(f"Redis container '{self.container_name}' started successfully")
                        return True
                    else:
                        print(f"Redis ping failed (attempt {attempt + 1}/{max_retries})")
                        
                except subprocess.TimeoutExpired:
                    print(f"Redis ping timeout (attempt {attempt + 1}/{max_retries})")
                
                if attempt < max_retries - 1:
                    time.sleep(2)
            
            raise Exception("Redis not responding to ping after multiple attempts")
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to start Redis: {e}")
    
    def stop_redis(self):
        """Stop and remove Redis container."""
        try:
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self.container_name}"],
                capture_output=True, text=True
            )
            
            if self.container_name in result.stdout:
                # Stop container
                subprocess.run(
                    ["docker", "stop", self.container_name],
                    capture_output=True, timeout=10
                )
                
                # Remove container
                subprocess.run(
                    ["docker", "rm", self.container_name],
                    capture_output=True, timeout=10
                )
                
                print(f"Redis container '{self.container_name}' stopped and removed")
            else:
                print(f"Redis container '{self.container_name}' not found")
                
        except Exception as e:
            print(f"Warning: Error during Redis cleanup: {e}")
            # Try force removal as last resort
            try:
                subprocess.run(
                    ["docker", "rm", "-f", self.container_name],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass


# Global Redis manager
redis_manager = RedisTestManager()


def pytest_configure(config):
    """Start Redis before running tests."""
    try:
        print("Starting Redis container for tests...")
        redis_manager.start_redis()
    except Exception as e:
        pytest.exit(f"Failed to start Redis: {e}")


def pytest_unconfigure(config):
    """Stop Redis after tests complete."""
    print("Cleaning up Redis container...")
    redis_manager.stop_redis()


@pytest.fixture(scope="session")
def redis_url():
    """Provide Redis URL for tests."""
    return redis_manager.redis_url

@pytest_asyncio.fixture(autouse=True)
async def clear_redis_keys(redis_url):
    """Clear Redis keys before each test to ensure clean state."""
    try:
        from ateam.mcp.redis_transport import RedisTransport
        transport = RedisTransport(redis_url)
        await transport.connect()
        
        # Clear all keys that might interfere with tests
        keys_to_clear = [
            "mcp:agent:lock:*",
            "mcp:agent:owner:*", 
            "mcp:heartbeat:*",
            "mcp:agents:*"
        ]
        
        for pattern in keys_to_clear:
            keys_result = await transport.scan_keys(pattern)
            if keys_result.ok:
                for key in keys_result.value:
                    await transport.delete_key(key)
        
        await transport.disconnect()
    except Exception as e:
        print(f"Warning: Failed to clear Redis keys: {e}")
    
    yield
