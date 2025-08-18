"""
Frontend Mock for Backend Testing

This module provides pytest fixtures and tests that mock the frontend
to test backend functionality by:
1. Running main.py as a subprocess
2. Establishing WebSocket connections to frontend_api and backend_api
3. Sending test messages and verifying responses
"""

import asyncio
import json
import os
import pytest
import pytest_asyncio
import subprocess
import time
import websockets
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WebSocketMessage:
    """Represents a WebSocket message for testing"""
    type: str
    data: Dict[str, Any]
    message_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None


class FrontendMock:
    """Mock frontend that connects to backend WebSocket endpoints"""
    
    def __init__(self):
        self.frontend_ws = None
        self.backend_ws = None
        self.frontend_messages: List[WebSocketMessage] = []
        self.backend_messages: List[WebSocketMessage] = []
        self.process = None
    
    async def start_backend(self):
        """Start the backend server as a subprocess"""
        # Kill any existing process
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        # Start backend/main.py
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        self.process = subprocess.Popen(
            ["python", "backend/main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Wait for server to start
        await asyncio.sleep(3)
        
        # Check if process is still running
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(f"Backend failed to start. stdout: {stdout}, stderr: {stderr}")
        
        # Print any startup logs
        if self.process.stdout:
            try:
                # Non-blocking read of any available output
                import select
                if select.select([self.process.stdout], [], [], 0.1)[0]:
                    output = self.process.stdout.read()
                    if output:
                        print(f"Backend startup output: {output}")
            except:
                pass
    
    def read_backend_log(self) -> List[str]:
        """Read the backend log file and return log lines"""
        try:
            with open("backend/ateam.log", "r", encoding="utf-8") as f:
                return f.readlines()
        except FileNotFoundError:
            return []
        except UnicodeDecodeError:
            # Fallback to binary read and decode with errors='ignore'
            try:
                with open("backend/ateam.log", "rb") as f:
                    content = f.read().decode('utf-8', errors='ignore')
                    return content.splitlines()
            except:
                return []
    
    def check_log_frontend_consistency(self, expected_actions: List[str]):
        """Check if backend log actions match frontend messages"""
        log_lines = self.read_backend_log()
        log_actions = []
        
        # Extract actions from log
        for line in log_lines:
            if '"action":' in line:
                # Extract action from JSON in log
                import re
                match = re.search(r'"action":\s*"([^"]+)"', line)
                if match:
                    log_actions.append(match.group(1))
        
        # Extract actions from frontend messages
        frontend_actions = []
        for msg in self.frontend_messages:
            if msg.data and "action" in msg.data:
                frontend_actions.append(msg.data["action"])
        
        # Compare
        missing_in_frontend = [action for action in log_actions if action not in frontend_actions]
        missing_in_log = [action for action in frontend_actions if action not in log_actions]
        
        if missing_in_frontend or missing_in_log:
            raise AssertionError(
                f"Log-Frontend mismatch!\n"
                f"Actions in log but not in frontend: {missing_in_frontend}\n"
                f"Actions in frontend but not in log: {missing_in_log}\n"
                f"Log actions: {log_actions}\n"
                f"Frontend actions: {frontend_actions}"
            )
    
    async def connect_frontend_ws(self):
        """Connect to frontend_api WebSocket"""
        try:
            self.frontend_ws = await websockets.connect("ws://localhost:8000/ws/frontend-api")
            print("✅ Connected to frontend WebSocket")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to frontend WebSocket: {e}")
    
    async def connect_backend_ws(self):
        """Connect to backend_api WebSocket"""
        try:
            self.backend_ws = await websockets.connect("ws://localhost:8000/ws/backend-api")
            print("✅ Connected to backend WebSocket")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to backend WebSocket: {e}")
    
    async def send_frontend_message(self, message: WebSocketMessage):
        """Send message to frontend WebSocket"""
        if not self.frontend_ws:
            raise RuntimeError("Frontend WebSocket not connected")
        
        payload = {
            "type": message.type,
            "data": message.data
        }
        if message.message_id:
            payload["message_id"] = message.message_id
        if message.agent_id:
            payload["agent_id"] = message.agent_id
        if message.session_id:
            payload["session_id"] = message.session_id
        
        await self.frontend_ws.send(json.dumps(payload))
        print(f"📤 Sent frontend message: {message.type}")
    
    async def send_backend_message(self, message: WebSocketMessage):
        """Send message to backend WebSocket"""
        if not self.backend_ws:
            raise RuntimeError("Backend WebSocket not connected")
        
        payload = {
            "type": message.type,
            "data": message.data
        }
        if message.message_id:
            payload["message_id"] = message.message_id
        if message.agent_id:
            payload["agent_id"] = message.agent_id
        if message.session_id:
            payload["session_id"] = message.session_id
        
        await self.backend_ws.send(json.dumps(payload))
        print(f"📤 Sent backend message: {message.type}")
    
    async def receive_frontend_message(self, timeout: float = 5.0) -> Optional[WebSocketMessage]:
        """Receive message from frontend WebSocket"""
        if not self.frontend_ws:
            raise RuntimeError("Frontend WebSocket not connected")
        
        try:
            message = await asyncio.wait_for(self.frontend_ws.recv(), timeout=timeout)
            data = json.loads(message)
            
            ws_message = WebSocketMessage(
                type=data.get("type"),
                data=data.get("data", {}),
                message_id=data.get("message_id"),
                agent_id=data.get("agent_id"),
                session_id=data.get("session_id")
            )
            
            self.frontend_messages.append(ws_message)
            print(f"📥 Received frontend message: {ws_message.type}")
            return ws_message
        except asyncio.TimeoutError:
            print("⏰ Timeout waiting for frontend message")
            return None
    
    async def receive_backend_message(self, timeout: float = 5.0) -> Optional[WebSocketMessage]:
        """Receive message from backend WebSocket"""
        if not self.backend_ws:
            raise RuntimeError("Backend WebSocket not connected")
        
        try:
            message = await asyncio.wait_for(self.backend_ws.recv(), timeout=timeout)
            data = json.loads(message)
            
            ws_message = WebSocketMessage(
                type=data.get("type"),
                data=data.get("data", {}),
                message_id=data.get("message_id"),
                agent_id=data.get("agent_id"),
                session_id=data.get("session_id")
            )
            
            self.backend_messages.append(ws_message)
            print(f"📥 Received backend message: {ws_message.type}")
            return ws_message
        except asyncio.TimeoutError:
            print("⏰ Timeout waiting for backend message")
            return None
    
    async def wait_for_agent_message(self, agent_id: str, timeout: float = 10.0) -> Optional[WebSocketMessage]:
        """Wait for a message from a specific agent"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            message = await self.receive_frontend_message(timeout=1.0)
            if message:
                print(f"📥 Received message: type={message.type}, agent_id={message.agent_id}, data={message.data}")
                if message.agent_id == agent_id:
                    return message
        return None
    
    async def cleanup(self):
        """Clean up connections and stop backend"""
        if self.frontend_ws:
            await self.frontend_ws.close()
        if self.backend_ws:
            await self.backend_ws.close()
        if self.process:
            self.process.terminate()
            self.process.wait()


@pytest_asyncio.fixture
async def frontend_mock():
    """Pytest fixture that provides a FrontendMock instance"""
    mock = FrontendMock()
    try:
        await mock.start_backend()
        await mock.connect_frontend_ws()
        await mock.connect_backend_ws()
        yield mock
    finally:
        await mock.cleanup()


@pytest.mark.asyncio
async def test_coordinator_build_metaffi(frontend_mock: FrontendMock):
    """
    Test that when Coordinator agent receives "Please build MetaFFI",
    it sends a message to the "system-build-and-test" agent.
    """
    
    # Step 1: Create agent instance (refresh will create a new instance)
    refresh_message = WebSocketMessage(
        type="agent_refresh",
        data={},
        agent_id="coordinator",
        session_id="test-session"
    )
    await frontend_mock.send_backend_message(refresh_message)
    
    # Step 2: Wait for session creation and capture the new session ID
    # The session_created message should be broadcast to all connections
    session_created_message = await frontend_mock.receive_frontend_message(timeout=5.0)
    assert session_created_message is not None, "No session_created message received"
    assert session_created_message.type == "session_created", f"Expected session_created, got {session_created_message.type}"
    
    new_session_id = session_created_message.data.get("session_id")
    assert new_session_id is not None, "No session_id in session_created message"
    print(f"📋 New session ID: {new_session_id}")
    
    # Step 3: Subscribe to the new session ID on the frontend WebSocket
    subscribe_message = WebSocketMessage(
        type="subscribe",
        data={},
        agent_id="coordinator",
        session_id=new_session_id
    )
    await frontend_mock.send_frontend_message(subscribe_message)
    
    # Step 4: Wait a moment for agent to fully initialize
    await asyncio.sleep(2)
    
    # Step 5: Send chat message to Coordinator using the new session ID
    chat_message = WebSocketMessage(
        type="chat_message",
        data={"content": "Please build MetaFFI"},
        agent_id="coordinator",
        session_id=new_session_id
    )
    await frontend_mock.send_backend_message(chat_message)
    
    # Step 3: Wait for response from Coordinator
    coordinator_response = await frontend_mock.wait_for_agent_message("coordinator", timeout=15.0)
    assert coordinator_response is not None, "No response received from Coordinator Agent"
    
    # Print the coordinator's response for debugging
    print(f"📋 Coordinator response: {coordinator_response.type}")
    print(f"📋 Coordinator response data: {coordinator_response.data}")
    
    # Print all messages to see what's happening
    print(f"📋 All messages received: {[msg.type for msg in frontend_mock.frontend_messages]}")
    for i, msg in enumerate(frontend_mock.frontend_messages):
        if msg.type in ["agent_response", "agent_stream"]:
            print(f"📋 Message {i}: {msg.type} - {msg.data}")
            if msg.data and "content" in msg.data:
                print(f"📋 Content: {msg.data['content']}")
    
    # Step 4: Check if Coordinator sent a message to system-build-and-test
    # We need to look for agent delegation or agent call messages
    system_build_test_message = None
    start_time = time.time()
    
    while time.time() - start_time < 10.0:
        message = await frontend_mock.receive_frontend_message(timeout=1.0)
        if message:
            # Check if this is a message to system-build-and-test agent
            if (message.data.get("agent_id") == "system-build-and-test" or 
                message.data.get("target_agent_id") == "system-build-and-test" or
                message.data.get("agent") == "System Builder and Tester"):
                system_build_test_message = message
                break
            
            # Also check for agent delegation or call announcements
            if (message.type in ["agent_delegate_announcement", "agent_call_announcement"] and
                ("system-build-and-test" in str(message.data) or "System Builder and Tester" in str(message.data))):
                system_build_test_message = message
                break
            
            # Check for AGENT_DELEGATE messages specifically
            if (message.type == "agent_response" and 
                message.data.get("action") == "AGENT_DELEGATE" and
                (message.data.get("target_agent_id") == "system-build-and-test" or 
                 message.data.get("metadata", {}).get("target_agent") == "system-build-and-test")):
                system_build_test_message = message
                break
            
            # Check for messages with system-build-and-test in the content
            if ("system-build-and-test" in str(message.data) or "System Builder and Tester" in str(message.data)):
                system_build_test_message = message
                break
    
    # Assert that Coordinator communicated with system-build-and-test
    assert system_build_test_message is not None, (
        f"Coordinator did not send message to system-build-and-test agent. "
        f"Received messages: {[msg.type for msg in frontend_mock.frontend_messages]}"
    )
    
    # Check log-frontend consistency
    frontend_mock.check_log_frontend_consistency(["TOOL_CALL", "TOOL_RETURN", "AGENT_DELEGATE"])
    
    print(f"✅ Coordinator successfully communicated with system-build-and-test: {system_build_test_message.type}")


@pytest.mark.asyncio
async def test_agent_list_retrieval(frontend_mock: FrontendMock):
    """Test that we can retrieve the list of available agents"""
    
    # Send get_agents message
    get_agents_message = WebSocketMessage(
        type="get_agents",
        data={}
    )
    await frontend_mock.send_backend_message(get_agents_message)
    
    # Wait for response (should come through frontend WebSocket)
    response = await frontend_mock.receive_frontend_message(timeout=5.0)
    assert response is not None, "No response received for get_agents"
    assert response.type == "agent_list_update", f"Expected agent_list_update, got {response.type}"
    
    # Check that agents are in the response
    agents = response.data.get("agents", [])
    assert len(agents) > 0, "No agents found in response"
    
    # Check for specific agents
    agent_ids = [agent.get("id") for agent in agents]
    assert "coordinator" in agent_ids, "coordinator agent not found"
    assert "system-build-and-test" in agent_ids, "system-build-and-test agent not found"
    
    print(f"✅ Successfully retrieved {len(agents)} agents: {agent_ids}")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
