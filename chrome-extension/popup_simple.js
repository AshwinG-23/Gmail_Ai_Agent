// Simple AI Email Rewriter - Popup
console.log('Simple AI Email Rewriter popup loaded');

// Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Popup DOM loaded');
    
    const rewriteButton = document.getElementById('rewrite-email');
    const downloadButton = document.getElementById('download-logs');
    const statusText = document.getElementById('status-text');
    const errorMessage = document.getElementById('error-message');
    
    // Check backend status
    await checkBackendStatus();
    
    // Rewrite email button
    if (rewriteButton) {
        rewriteButton.addEventListener('click', async () => {
            try {
                setButtonLoading(rewriteButton, true);
                
                // Check if we're on Gmail
                const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
                
                if (!tab.url.includes('mail.google.com')) {
                    throw new Error('Please navigate to Gmail first');
                }
                
                // Send message to content script
                const response = await chrome.tabs.sendMessage(tab.id, {
                    action: 'triggerRewrite'
                });
                
                if (response && response.success) {
                    console.log('Rewrite triggered successfully');
                    window.close();
                } else {
                    throw new Error(response?.error || 'Failed to trigger rewrite');
                }
                
            } catch (error) {
                console.error('Rewrite failed:', error);
                showError(error.message);
            } finally {
                setButtonLoading(rewriteButton, false);
            }
        });
    }
    
    // Download logs button
    if (downloadButton) {
        downloadButton.addEventListener('click', async () => {
            try {
                setButtonLoading(downloadButton, true);
                
                const response = await fetch(`${API_BASE_URL}/agent/sessions?limit=100`);
                
                if (!response.ok) {
                    throw new Error(`Server error: ${response.status}`);
                }
                
                const data = await response.json();
                
                // Create downloadable file
                const logsData = {
                    exported_at: new Date().toISOString(),
                    total_sessions: data.total_sessions || 0,
                    sessions: data.sessions || []
                };
                
                const blob = new Blob([JSON.stringify(logsData, null, 2)], {
                    type: 'application/json'
                });
                
                const url = URL.createObjectURL(blob);
                const filename = `ai-email-logs-${new Date().toISOString().split('T')[0]}.json`;
                
                // Download file
                await chrome.downloads.download({
                    url: url,
                    filename: filename,
                    saveAs: true
                });
                
                setTimeout(() => URL.revokeObjectURL(url), 1000);
                showSuccess('Logs downloaded successfully!');
                
            } catch (error) {
                console.error('Download failed:', error);
                showError('Failed to download logs: ' + error.message);
            } finally {
                setButtonLoading(downloadButton, false);
            }
        });
    }
    
    async function checkBackendStatus() {
        try {
            const response = await fetch(`${API_BASE_URL}/`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });
            
            if (response.ok) {
                updateStatus('✅ Connected to AI Agent', 'success');
                enableButtons();
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('Backend check failed:', error);
            updateStatus('❌ Backend Disconnected', 'error');
            disableButtons();
            showError('Cannot connect to AI Agent backend. Make sure the server is running on localhost:8000');
        }
    }
    
    function updateStatus(text, type) {
        if (statusText) {
            statusText.textContent = text;
            statusText.className = type;
        }
    }
    
    function enableButtons() {
        if (rewriteButton) rewriteButton.disabled = false;
        if (downloadButton) downloadButton.disabled = false;
    }
    
    function disableButtons() {
        if (rewriteButton) rewriteButton.disabled = true;
        if (downloadButton) downloadButton.disabled = true;
    }
    
    function setButtonLoading(button, loading) {
        if (!button) return;
        
        if (loading) {
            button.disabled = true;
            const originalText = button.innerHTML;
            button.dataset.originalText = originalText;
            button.innerHTML = '<span class="loading"></span> Processing...';
        } else {
            button.disabled = false;
            if (button.dataset.originalText) {
                button.innerHTML = button.dataset.originalText;
                delete button.dataset.originalText;
            }
        }
    }
    
    function showError(message) {
        if (errorMessage) {
            errorMessage.textContent = message;
            errorMessage.style.display = 'block';
            errorMessage.style.background = 'rgba(244, 67, 54, 0.2)';
            errorMessage.style.color = '#ffcdd2';
            
            setTimeout(() => {
                errorMessage.style.display = 'none';
            }, 5000);
        }
    }
    
    function showSuccess(message) {
        if (errorMessage) {
            errorMessage.textContent = '✅ ' + message;
            errorMessage.style.display = 'block';
            errorMessage.style.background = 'rgba(76, 175, 80, 0.2)';
            errorMessage.style.color = '#c8e6c9';
            
            setTimeout(() => {
                errorMessage.style.display = 'none';
            }, 3000);
        }
    }
});