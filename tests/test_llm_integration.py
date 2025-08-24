"""Tests for LLM integration with the llm package."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os

from ateam.llm.base import LLMProvider, LLMResponse, LLMStreamResponse
from ateam.llm.echo import EchoProvider
from ateam.models.manager import ModelManager, ModelInfo
from ateam.util.types import Result


class TestLLMProvider:
    """Test LLMProvider using the llm package."""
    
    @pytest.mark.asyncio
    async def test_echo_provider_generate(self):
        """Test echo provider generate method."""
        provider = EchoProvider(model_id="echo")
        
        response = await provider.generate("Hello, world!")
        
        assert isinstance(response, LLMResponse)
        assert response.text == "Echo: Hello, world!"
        assert response.model == "echo"
        assert response.metadata["provider"] == "echo"
        assert response.tokens_used > 0
    
    @pytest.mark.asyncio
    async def test_echo_provider_stream(self):
        """Test echo provider stream method."""
        provider = EchoProvider(model_id="echo")
        
        chunks = []
        async for chunk in provider.stream("Hello, world!"):
            chunks.append(chunk)
        
        # Should have multiple chunks plus final completion chunk
        assert len(chunks) > 1
        
        # All chunks should be LLMStreamResponse
        for chunk in chunks:
            assert isinstance(chunk, LLMStreamResponse)
            assert chunk.model == "echo"
            assert chunk.metadata["provider"] == "echo"
        
        # Last chunk should be completion
        assert chunks[-1].is_complete is True
        assert chunks[-1].text == ""
    
    def test_echo_provider_estimate_tokens(self):
        """Test echo provider token estimation."""
        provider = EchoProvider(model_id="echo")
        
        tokens = provider.estimate_tokens("Hello, world!")
        assert tokens == 3  # "Hello, world!" has 13 chars, 13 // 4 = 3
    
    def test_echo_provider_get_model_info(self):
        """Test echo provider model info."""
        provider = EchoProvider(model_id="echo")
        
        info = provider.get_model_info()
        assert info["model_id"] == "echo"
        assert info["provider"] == "echo"
        assert info["model"] is None


class TestModelManager:
    """Test ModelManager using the llm package."""
    
    @pytest.fixture
    def temp_models_yaml(self):
        """Create a temporary models.yaml file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
models:
  gpt-4:
    name: "GPT-4"
    provider: "openai"
    description: "GPT-4 model"
    context_window_size: 8192
    model_settings:
      temperature: 0.7
    default_inference:
      max_tokens: 1000
  echo:
    name: "Echo Test"
    provider: "echo"
    description: "Echo test model"
    context_window_size: 4096
""")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        os.unlink(temp_path)
    
    def test_model_manager_load_models(self, temp_models_yaml):
        """Test model manager loading from YAML."""
        manager = ModelManager(temp_models_yaml)
        
        # Should have loaded models
        assert "gpt-4" in manager.models
        assert "echo" in manager.models
        
        # Check model info
        gpt4_model = manager.models["gpt-4"]
        assert gpt4_model.name == "GPT-4"
        assert gpt4_model.provider == "openai"
        assert gpt4_model.context_window_size == 8192
        
        echo_model = manager.models["echo"]
        assert echo_model.name == "Echo Test"
        assert echo_model.provider == "echo"
        assert echo_model.context_window_size == 4096
    
    def test_model_manager_get_model_configured(self, temp_models_yaml):
        """Test getting configured model."""
        manager = ModelManager(temp_models_yaml)
        
        model = manager.get_model("gpt-4")
        assert model is not None
        assert model.model_id == "gpt-4"
        assert model.name == "GPT-4"
        assert model.provider == "openai"
    
    def test_model_manager_get_model_not_found(self, temp_models_yaml):
        """Test getting non-existent model."""
        manager = ModelManager(temp_models_yaml)
        
        model = manager.get_model("non-existent")
        assert model is None
    
    @patch('ateam.models.manager.llm')
    def test_model_manager_discover_models(self, mock_llm, temp_models_yaml):
        """Test model discovery from llm package."""
        # Mock llm.get_models() to return a mock model
        mock_model = Mock()
        mock_model.model_id = "gpt-3.5-turbo"
        mock_model.model_name = "GPT-3.5 Turbo"
        # Set the module name properly
        type(mock_model).__module__ = "llm.default_plugins.openai_models"
        # Set up proper attributes that the discovery code expects
        mock_model.attachment_types = set()  # Make it iterable
        mock_model.supports_schema = False
        mock_model.supports_tools = False
        mock_model.can_stream = True
        mock_model.vision = False
        mock_llm.get_models.return_value = [mock_model]
        mock_llm.get_embedding_models.return_value = []
        
        manager = ModelManager(temp_models_yaml)
        discovered = manager.discover_models_from_llm()
        
        assert "gpt-3.5-turbo" in discovered
        model_info = discovered["gpt-3.5-turbo"]
        assert model_info["name"] == "GPT-3.5 Turbo"
        assert model_info["provider"] == "openai"
        assert model_info["is_chat_model"] is True
        assert model_info["is_embedding_model"] is False
    
    @patch('ateam.models.manager.llm')
    def test_model_manager_list_models(self, mock_llm, temp_models_yaml):
        """Test listing all models."""
        # Mock llm.get_models() to return a mock model
        mock_model = Mock()
        mock_model.model_id = "gpt-3.5-turbo"
        mock_model.model_name = "GPT-3.5 Turbo"
        # Set the module name properly
        type(mock_model).__module__ = "llm.default_plugins.openai_models"
        # Set up proper attributes that the discovery code expects
        mock_model.attachment_types = set()  # Make it iterable
        mock_model.supports_schema = False
        mock_model.supports_tools = False
        mock_model.can_stream = True
        mock_model.vision = False
        mock_llm.get_models.return_value = [mock_model]
        mock_llm.get_embedding_models.return_value = []
        
        manager = ModelManager(temp_models_yaml)
        result = manager.list_models()
        
        assert result.ok
        models = result.value
        
        # Should have both configured and discovered models
        assert "gpt-4" in models  # Configured
        assert "echo" in models   # Configured
        assert "gpt-3.5-turbo" in models  # Discovered
        
        # Check configured model
        gpt4_info = models["gpt-4"]
        assert gpt4_info["configured"] is True
        assert gpt4_info["name"] == "GPT-4"
        
        # Check discovered model
        gpt35_info = models["gpt-3.5-turbo"]
        assert gpt35_info["configured"] is False
        assert gpt35_info["name"] == "GPT-3.5 Turbo"
    
    def test_model_manager_resolve_success(self, temp_models_yaml):
        """Test successful model resolution."""
        manager = ModelManager(temp_models_yaml)
        result = manager.resolve("gpt-4")
        
        assert result.ok
        model_info = result.value
        assert model_info["model_id"] == "gpt-4"
        assert model_info["name"] == "GPT-4"
        assert model_info["provider"] == "openai"
    
    def test_model_manager_resolve_not_found(self, temp_models_yaml):
        """Test model resolution for non-existent model."""
        manager = ModelManager(temp_models_yaml)
        result = manager.resolve("non-existent")
        
        assert not result.ok
        assert result.error.code == "model.not_found"
        assert "non-existent" in result.error.message


class TestLLMIntegration:
    """Test LLM integration in agent context."""
    
    @pytest.mark.asyncio
    async def test_agent_llm_provider_initialization(self):
        """Test that agent can initialize with LLM provider."""
        from ateam.agent.main import AgentApp
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .ateam structure
            ateam_dir = os.path.join(temp_dir, ".ateam")
            os.makedirs(ateam_dir)
            
            # Create agent config
            agent_dir = os.path.join(ateam_dir, "agents", "test")
            os.makedirs(agent_dir)
            
            # Create minimal agent config
            agent_config = Mock()
            agent_config.model = "echo"  # Use echo for testing
            
            # Initialize agent app
            app = AgentApp(
                redis_url="redis://localhost:6379/0",
                cwd=temp_dir,
                name_override="test",
                project_override="test"
            )
            
            # Mock the config loading
            mock_agent_config = Mock()
            mock_agent_config.model = "echo"
            mock_agents = {"test": mock_agent_config}
            
            with patch('ateam.agent.main.load_stack', return_value=Result(ok=True, value=(
                {}, {}, {}, mock_agents  # project, models, tools, agents
            ))):
                result = await app.bootstrap()
                
                # Should succeed
                assert result.ok
                
                # Should have LLM provider set
                assert app.runner.llm is not None
                assert app.runner.llm.model_id == "echo"
