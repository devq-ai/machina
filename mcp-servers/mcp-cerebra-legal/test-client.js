#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Path to the MCP server executable
const serverPath = path.join(__dirname, 'build', 'index.js');

// Spawn the server process
const serverProcess = spawn('node', [serverPath], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Handle server output
serverProcess.stdout.on('data', (data) => {
  console.log(`Server output: ${data}`);
});

serverProcess.stderr.on('data', (data) => {
  console.error(`Server log: ${data}`);
});

// Send a tools/list request
const listToolsRequest = {
  jsonrpc: '2.0',
  id: 1,
  method: 'tools/list',
  params: {}
};

// Send the request to the server
serverProcess.stdin.write(JSON.stringify(listToolsRequest) + '\n');

// Wait for a response
let responseData = '';
serverProcess.stdout.on('data', (data) => {
  responseData += data.toString();
  
  try {
    // Try to parse the response
    const response = JSON.parse(responseData);
    console.log('Received response:', JSON.stringify(response, null, 2));
    
    // Test the legal_think tool
    const thinkRequest = {
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/call',
      params: {
        name: 'legal_think',
        arguments: {
          thought: 'Analyzing ANSC contestation where claimant argues technical specifications were too restrictive.',
          thoughtNumber: 1,
          totalThoughts: 5,
          nextThoughtNeeded: true,
          requestTemplate: true
        }
      }
    };
    
    // Send the think request
    serverProcess.stdin.write(JSON.stringify(thinkRequest) + '\n');
    
    // Clear the response data for the next response
    responseData = '';
  } catch (error) {
    // Not a complete JSON response yet, continue collecting data
  }
});

// Handle process exit
serverProcess.on('close', (code) => {
  console.log(`Server process exited with code ${code}`);
});

// Terminate the server after 10 seconds
setTimeout(() => {
  console.log('Terminating server...');
  serverProcess.kill();
}, 10000);