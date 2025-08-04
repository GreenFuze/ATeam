import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useParams, useNavigate, useLocation } from 'react-router-dom';
import { MantineProvider, createTheme } from '@mantine/core';
import '@mantine/core/styles.css';
import './index.css';

import Sidebar from './components/Sidebar';
import AgentChat from './components/AgentChat';
import AgentsPage from './components/AgentsPage';
import SettingsPage from './components/SettingsPage';
import AgentSettingsModal from './components/AgentSettingsModal';
import { connectionManager } from './services/ConnectionManager';
import { notifications } from '@mantine/notifications';


// Dark theme configuration
const theme = createTheme({
  primaryColor: 'blue',
  colors: {
    dark: [
      '#C1C2C5',
      '#A6A7AB',
      '#909296',
      '#5C5F66',
      '#373A40',
      '#2C2E33',
      '#25262B',
      '#1A1B1E',
      '#141517',
      '#101113',
    ],
  },
});

// Wrapper component for AgentChat to get agentId from URL params
const AgentChatWrapper = () => {
  const { agentId } = useParams<{ agentId: string }>();
  return agentId ? <AgentChat agentId={agentId} /> : <div>No agent selected</div>;
};

function App() {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<any>(null);
  const [_connectionStatus, setConnectionStatus] = useState({ frontendAPI: false, backendAPI: false, isConnecting: false });
  const navigate = useNavigate();
  const location = useLocation();

  // Initialize global WebSocket connections on app startup
  useEffect(() => {
    const initializeConnections = async () => {
      try {
        // Set up connection status callbacks
        connectionManager.setCallbacks({
          onStatusChange: (status) => {
            setConnectionStatus(status);
            console.log('Connection status changed:', status);
          },
          onConnectionLost: () => {
            notifications.show({
              title: 'Connection Lost',
              message: 'WebSocket connections have been lost. Attempting to reconnect...',
              color: 'red',
            });
          },
          onConnectionRestored: () => {
            notifications.show({
              title: 'Connected',
              message: 'WebSocket connections have been restored.',
              color: 'green',
            });
          },
        });

        // Connect to WebSocket services
        await connectionManager.connect();
        console.log('Global WebSocket connections established');
        
        // Load initial data via WebSocket
        connectionManager.sendGetAgents();
        
      } catch (error) {
        console.error('Failed to initialize WebSocket connections:', error);
        notifications.show({
          title: 'Connection Error',
          message: 'Failed to establish WebSocket connections. Some features may not work properly.',
          color: 'red',
        });
      }
    };

    initializeConnections();

    // Cleanup on unmount
    return () => {
      connectionManager.disconnect();
    };
  }, []);

  // Update selected agent when URL changes
  useEffect(() => {
    const pathParts = location.pathname.split('/');
    if (pathParts[1] === 'chat' && pathParts[2]) {
      setSelectedAgent(pathParts[2]);
    } else {
      setSelectedAgent(null);
    }
  }, [location.pathname]);

  const handleAgentSelect = (agentId: string) => {
    setSelectedAgent(agentId);
    // Navigate to the chat route for the selected agent
    navigate(`/chat/${agentId}`);
  };

  const handleAddAgent = () => {
    setEditingAgent(null);
    setSettingsModalOpen(true);
  };

  const handleAgentSettings = (agentId: string) => {
    // Fetch agent data and open settings modal
    fetch(`/api/agents/${agentId}`)
      .then(response => response.json())
      .then(agent => {
        setEditingAgent(agent);
        setSettingsModalOpen(true);
      })
      .catch(error => {
        console.error('Failed to fetch agent:', error);
      });
  };

  const handleSettingsSuccess = () => {
    // Refresh the page or reload data as needed
    window.location.reload();
  };

  return (
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <div className="app">
        <Sidebar
          onAgentSelect={handleAgentSelect}
          selectedAgentId={selectedAgent}
          onAddAgent={handleAddAgent}
          onAgentSettings={handleAgentSettings}
        />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/agents" replace />} />
            <Route path="/agents" element={<AgentsPage onAgentSelect={handleAgentSelect} />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/chat/:agentId" element={<AgentChatWrapper />} />
          </Routes>
        </main>
      </div>

      {/* Global Agent Settings Modal */}
      <AgentSettingsModal
        opened={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        agent={editingAgent}
        onSuccess={handleSettingsSuccess}
      />
    </MantineProvider>
  );
}

// Wrap App with Router since we need useNavigate
const AppWithRouter = () => (
  <Router>
    <App />
  </Router>
);

export default AppWithRouter; 