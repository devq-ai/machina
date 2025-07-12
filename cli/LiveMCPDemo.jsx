import React, { useState, useEffect } from 'react';
import './LiveMCPDemo.css';

const LiveMCPDemo = ({ endpoint = 'http://localhost:8080/api/v1' }) => {
  const [servers, setServers] = useState([]);
  const [health, setHealth] = useState(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // DevGen API client
  const apiClient = {
    async getServers() {
      const response = await fetch(`${endpoint}/mcp/servers`);
      if (!response.ok) throw new Error('Failed to fetch servers');
      return await response.json();
    },

    async getHealth() {
      const response = await fetch(`${endpoint}/health`);
      if (!response.ok) throw new Error('Failed to fetch health');
      return await response.json();
    },

    async toggleServer(serverName) {
      const response = await fetch(`${endpoint}/mcp/servers/${serverName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'toggle' })
      });
      if (!response.ok) throw new Error('Failed to toggle server');
      return await response.json();
    },

    async getRegistry() {
      const response = await fetch(`${endpoint}/mcp/registry`);
      if (!response.ok) throw new Error('Failed to fetch registry');
      return await response.json();
    }
  };

  // Fetch data from DevGen local instance
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [healthData, registryData] = await Promise.all([
        apiClient.getHealth(),
        apiClient.getRegistry()
      ]);

      setHealth(healthData);
      setServers(registryData.servers || []);
      setConnected(true);
    } catch (err) {
      console.error('Failed to connect to DevGen:', err);
      setError(err.message);
      setConnected(false);
    } finally {
      setLoading(false);
    }
  };

  // Handle server toggle
  const handleToggleServer = async (serverName) => {
    try {
      await apiClient.toggleServer(serverName);
      await fetchData(); // Refresh data after toggle
    } catch (err) {
      console.error('Failed to toggle server:', err);
      setError(`Failed to toggle ${serverName}: ${err.message}`);
    }
  };

  // Auto-refresh data every 3 seconds
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [endpoint]);

  // Loading state
  if (loading) {
    return (
      <div className="live-mcp-demo loading">
        <div className="loading-spinner"></div>
        <p>Connecting to DevGen local instance...</p>
      </div>
    );
  }

  // Offline state
  if (!connected) {
    return (
      <div className="live-mcp-demo offline">
        <div className="offline-header">
          <h3>🔌 Live Demo Offline</h3>
          <p>To experience the live demo, start your local DevGen instance:</p>
        </div>

        <div className="setup-instructions">
          <div className="code-block">
            <h4>1. Start DevGen Web Server:</h4>
            <code>devgen web --web-port 8080 --allow-origin "*"</code>
          </div>

          <div className="code-block">
            <h4>2. Start DevGen SSH Server:</h4>
            <code>devgen ssh --ssh-port 2222</code>
          </div>

          <div className="ssh-demo">
            <h4>3. Try SSH Access:</h4>
            <code>ssh -p 2222 demo@localhost</code>
            <p className="ssh-note">Password: <strong>demo</strong> or <strong>devq</strong></p>
          </div>
        </div>

        <div className="demo-features">
          <h4>🚀 What You'll Experience:</h4>
          <ul>
            <li>✅ Real-time MCP server management</li>
            <li>✅ Interactive web dashboard</li>
            <li>✅ Authentic SSH terminal access</li>
            <li>✅ Live server health monitoring</li>
            <li>✅ Professional development environment</li>
          </ul>
        </div>

        {error && (
          <div className="error-message">
            <strong>Connection Error:</strong> {error}
          </div>
        )}

        <button onClick={fetchData} className="retry-button">
          🔄 Retry Connection
        </button>
      </div>
    );
  }

  // Connected state - show live demo
  return (
    <div className="live-mcp-demo connected">
      <div className="demo-header">
        <h2>🚀 Live MCP Registry Demo</h2>
        <div className="connection-status">
          <span className="status-dot connected"></span>
          <span>Connected to DevGen</span>
        </div>
        <div className="health-summary">
          {health && (
            <span className="health-badge">
              {health.healthy_count}/{health.total_count} servers healthy
            </span>
          )}
        </div>
      </div>

      <div className="demo-controls">
        <div className="control-section">
          <h4>🌐 Web API Access</h4>
          <p>This dashboard connects to your local DevGen instance via REST API</p>
        </div>

        <div className="control-section">
          <h4>🔐 SSH Terminal Access</h4>
          <div className="ssh-access">
            <code>ssh -p 2222 demo@localhost</code>
            <span className="ssh-password">Password: demo</span>
          </div>
        </div>
      </div>

      <div className="servers-grid">
        {servers.map(server => (
          <div key={server.name} className={`server-card ${getServerHealthClass(server)}`}>
            <div className="server-header">
              <h3>{server.name}</h3>
              <div className="server-badges">
                <span className={`status-badge ${getStatusClass(server.status)}`}>
                  {server.status}
                </span>
                <span className="category-badge">{server.metadata?.category || 'unknown'}</span>
              </div>
            </div>

            <p className="server-description">{server.description}</p>

            <div className="server-stats">
              <div className="stat">
                <span className="stat-label">Tools:</span>
                <span className="stat-value">{server.tools?.length || 0}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Framework:</span>
                <span className="stat-value">{server.metadata?.framework || 'Unknown'}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Version:</span>
                <span className="stat-value">{server.version || '1.0.0'}</span>
              </div>
            </div>

            <div className="server-actions">
              <button
                onClick={() => handleToggleServer(server.name)}
                className={`toggle-btn ${server.status === 'active' ? 'stop' : 'start'}`}
                disabled={loading}
              >
                {server.status === 'active' ? '⏹️ Stop' : '▶️ Start'}
              </button>
            </div>

            <div className="server-footer">
              <span className="last-check">
                Last checked: {formatLastCheck(server.last_health_check)}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="demo-footer">
        <div className="footer-section">
          <h4>🎯 Live Demo Features</h4>
          <ul>
            <li>Real MCP servers (not mocked)</li>
            <li>Live server management</li>
            <li>Authentic SSH terminal access</li>
            <li>Professional development environment</li>
          </ul>
        </div>

        <div className="footer-section">
          <h4>🔧 Try SSH Commands</h4>
          <div className="ssh-commands">
            <code>list</code> - List all servers<br/>
            <code>health</code> - Check server health<br/>
            <code>toggle &lt;name&gt;</code> - Toggle server<br/>
            <code>status &lt;name&gt;</code> - Server details<br/>
            <code>help</code> - Show all commands
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper functions
const getServerHealthClass = (server) => {
  if (server.status === 'active' || server.status === 'production-ready') {
    return 'healthy';
  }
  return 'unhealthy';
};

const getStatusClass = (status) => {
  switch (status) {
    case 'active': return 'active';
    case 'production-ready': return 'production-ready';
    case 'inactive': return 'inactive';
    default: return 'unknown';
  }
};

const formatLastCheck = (lastCheck) => {
  if (!lastCheck) return 'Never';
  const date = new Date(lastCheck);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
  return date.toLocaleDateString();
};

export default LiveMCPDemo;
