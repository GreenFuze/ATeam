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
import ErrorDialog from './components/ErrorDialog';
import StartupScreen from './components/StartupScreen';
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
  const [error, setError] = useState<string | null>(null);
  const [isStartupComplete, setIsStartupComplete] = useState(false);
  const [_startupError, setStartupError] = useState<Error | null>(null);
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
          onError: (errorMessage) => {
            setError(errorMessage);
          },
        });

        // Set up FrontendAPI error handlers
        connectionManager.setFrontendAPIHandlers({
          onError: (_agentId: string, _sessionId: string, error: any) => {
            // Assert that error is properly structured - if not, there's a backend bug
            if (!error) {
              throw new Error('Backend sent undefined error data - this indicates a backend bug');
            }
            if (!error.message) {
              throw new Error('Backend sent malformed error data - missing message - this indicates a backend bug');
            }
            
            setError(`WebSocket Error: ${error.message}`);
          },
        });
        
        // Note: Connection and data loading will be handled by StartupScreen
        console.log('App initialization complete - waiting for startup screen');
      } catch (error) {
        console.error('Error during app initialization:', error);
        setError(`Initialization Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
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
    // Get agent data from ConnectionManager (already loaded via WebSocket)
    const agents = connectionManager.getAgents();
    const agent = agents.find(a => a.id === agentId);
    
    if (!agent) {
      throw new Error(`Agent with ID '${agentId}' not found in ConnectionManager - this indicates a frontend bug`);
    }
    
    setEditingAgent(agent);
    setSettingsModalOpen(true);
  };

  const handleSettingsSuccess = () => {
    // Close modal and refresh agents list without full page reload
    setSettingsModalOpen(false);
    try {
      connectionManager.sendGetAgents();
      notifications.show({ title: 'Agent saved', message: 'Agent list refreshed', color: 'green' });
    } catch (e) {
      console.error('Failed to refresh agents after save:', e);
    }
  };

  const handleStartupComplete = () => {
    setIsStartupComplete(true);
    console.log('Startup completed successfully - application ready');
  };

  const handleStartupError = (error: Error) => {
    setStartupError(error);
    console.error('Fatal startup error:', error);
  };

  return (
    <MantineProvider theme={theme} defaultColorScheme="dark">
      {!isStartupComplete ? (
        <StartupScreen
          onStartupComplete={handleStartupComplete}
          onStartupError={handleStartupError}
        />
      ) : (
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
      )}

      {/* Global Agent Settings Modal */}
      <AgentSettingsModal
        opened={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        agent={editingAgent}
        onSuccess={handleSettingsSuccess}
      />

      {/* Global Error Dialog */}
      <ErrorDialog
        isOpen={!!error}
        error={error}
        onClose={() => setError(null)}
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