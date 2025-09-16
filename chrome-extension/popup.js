// AI Email Agent - Fixed Popup JavaScript
console.log('AI Email Agent popup loaded');

// Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const elements = {
    status: document.getElementById('status'),
    statusText: document.getElementById('status-text'),
    errorMessage: document.getElementById('error-message'),
    rewriteEmail: document.getElementById('rewrite-email'),
    downloadLogs: document.getElementById('download-logs')
};

// State
let isConnected = false;

// Initialize popup when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Popup DOM loaded, initializing...');
    
    // Verify all elements exist
    const missingElements = Object.entries(elements).filter(([key, element]) => !element);
    if (missingElements.length > 0) {
        console.error('Missing elements:', missingElements.map(([key]) => key));
        return;
    }
    
    // Set up event listeners
    setupEventListeners();
    
    // Check backend status
    await checkBackendStatus();
});

function setupEventListeners() {
    if (elements.rewriteEmail) {
        elements.rewriteEmail.addEventListener('click', handleRewriteEmail);
        console.log('Rewrite email listener attached');
    }
    
    if (elements.downloadLogs) {
        elements.downloadLogs.addEventListener('click', handleDownloadLogs);
        console.log('Download logs listener attached');
    }
}

// Check backend connection
async function checkBackendStatus() {
    console.log('Checking backend status...');
    updateStatus('checking', 'Checking connection...');
    
    try {
        // Use root endpoint instead of /health which might not exist
        const response = await fetch(`${API_BASE_URL}/`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000) // 5 second timeout
        });
        
        if (response.ok) {
            isConnected = true;
            updateStatus('connected', 'Connected to AI Agent');
            enableButtons();
            console.log('Backend connection successful');
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('Backend status check failed:', error);
        isConnected = false;
        updateStatus('disconnected', 'Backend Disconnected');
        disableButtons();
        showError('Cannot connect to AI Agent backend. Make sure the server is running on localhost:8000');
    }
}

function updateStatus(state, text) {
    if (elements.status && elements.statusText) {
        elements.status.className = `status ${state}`;
        elements.statusText.textContent = text;
    }
}

function enableButtons() {
    if (elements.rewriteEmail) elements.rewriteEmail.disabled = false;
    if (elements.downloadLogs) elements.downloadLogs.disabled = false;
}

function disableButtons() {
    if (elements.rewriteEmail) elements.rewriteEmail.disabled = true;
    if (elements.downloadLogs) elements.downloadLogs.disabled = true;
}

function showError(message) {
    if (elements.errorMessage) {
        elements.errorMessage.textContent = message;
        elements.errorMessage.style.display = 'block';
        
        // Auto-hide after 8 seconds
        setTimeout(() => {
            if (elements.errorMessage) {
                elements.errorMessage.style.display = 'none';
            }
        }, 8000);
    }
}

function setButtonLoading(button, isLoading) {
    if (!button) return;
    
    if (isLoading) {
        button.disabled = true;
        const originalText = button.innerHTML;
        button.dataset.originalText = originalText;
        button.innerHTML = '<span class="loading"></span><span>Processing...</span>';
    } else {
        button.disabled = false;
        if (button.dataset.originalText) {
            button.innerHTML = button.dataset.originalText;
            delete button.dataset.originalText;
        }
    }
}

// Handle rewrite email button click
async function handleRewriteEmail() {
    console.log('Rewrite email button clicked');
    
    setButtonLoading(elements.rewriteEmail, true);
    
    try {
        // Check if we're on Gmail
        const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
        
        if (!tab.url.includes('mail.google.com')) {
            throw new Error('Please navigate to Gmail to use this feature');
        }
        
        // Send message to content script to trigger rewrite
        const response = await chrome.tabs.sendMessage(tab.id, {
            action: 'triggerRewrite'
        });
        
        if (response && response.success) {
            console.log('Rewrite triggered successfully');
            // Close popup after successful trigger
            window.close();
        } else {
            throw new Error(response?.error || 'Failed to trigger email rewrite');
        }
        
    } catch (error) {
        console.error('Rewrite email failed:', error);
        showError(error.message);
    } finally {
        setButtonLoading(elements.rewriteEmail, false);
    }
}

// Handle download logs button click
async function handleDownloadLogs() {
    console.log('Download logs button clicked');
    
    setButtonLoading(elements.downloadLogs, true);
    
    try {
        // Fetch logs from backend
        const response = await fetch(`${API_BASE_URL}/agent/sessions?limit=100`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
            signal: AbortSignal.timeout(10000) // 10 second timeout
        });
        
        if (!response.ok) {
            throw new Error(`Failed to fetch logs: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Create downloadable JSON file
        const logsData = {
            exported_at: new Date().toISOString(),
            total_sessions: data.total_sessions || 0,
            sessions: data.sessions || [],
            agent_info: {
                version: '3.0.0',
                type: 'AI Email Agent'
            }
        };
        
        // Create and trigger download
        const blob = new Blob([JSON.stringify(logsData, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const filename = `ai-email-agent-logs-${new Date().toISOString().split('T')[0]}.json`;
        
        // Use Chrome downloads API
        await chrome.downloads.download({
            url: url,
            filename: filename,
            saveAs: true
        });
        
        // Clean up
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        
        console.log(`Logs downloaded successfully as ${filename}`);
        
        // Show success message
        showSuccessMessage('Logs downloaded successfully!');
        
    } catch (error) {
        console.error('Download logs failed:', error);
        showError('Failed to download logs: ' + error.message);
    } finally {
        setButtonLoading(elements.downloadLogs, false);
    }
}

function showSuccessMessage(message) {
    if (elements.errorMessage) {
        // Temporarily show success in error div with different styling
        elements.errorMessage.textContent = '✅ ' + message;
        elements.errorMessage.style.background = 'rgba(76, 175, 80, 0.2)';
        elements.errorMessage.style.color = '#4caf50';
        elements.errorMessage.style.borderColor = 'rgba(76, 175, 80, 0.3)';
        elements.errorMessage.style.display = 'block';
        
        setTimeout(() => {
            if (elements.errorMessage) {
                elements.errorMessage.style.display = 'none';
                // Reset error styling
                elements.errorMessage.style.background = 'rgba(244, 67, 54, 0.2)';
                elements.errorMessage.style.color = '#ffcdd2';
                elements.errorMessage.style.borderColor = 'rgba(244, 67, 54, 0.3)';
            }
        }, 3000);
    }
}

// Handle keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Escape key closes popup
    if (e.key === 'Escape') {
        window.close();
    }
});

// Auto-focus first available button when popup opens
setTimeout(() => {
    const firstButton = document.querySelector('button:not([disabled])');
    if (firstButton) {
        firstButton.focus();
    }
}, 100);