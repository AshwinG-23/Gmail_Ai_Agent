// Simple AI Email Rewriter - Content Script
console.log('Simple AI Email Rewriter loaded on Gmail');

// Configuration
const API_BASE_URL = 'http://localhost:8000';
let isInitialized = false;

// Initialize the simple rewriter
function initializeSimpleRewriter() {
    if (isInitialized) return;
    console.log('Initializing Simple AI Email Rewriter');
    
    // Add rewrite button to compose areas
    addRewriteButtonsToCompose();
    
    // Listen for messages from popup
    chrome.runtime.onMessage.addListener(handleMessage);
    
    // Watch for new compose windows
    observeForNewCompose();
    
    isInitialized = true;
}

// Add rewrite button to compose areas
function addRewriteButtonsToCompose() {
    // Find all compose text areas
    const composeAreas = document.querySelectorAll('[contenteditable="true"][role="textbox"]');
    
    composeAreas.forEach(addButtonToCompose);
}

// Add button to a specific compose area
function addButtonToCompose(composeArea) {
    // Check if button already exists
    if (composeArea.dataset.aiButtonAdded) return;
    
    // Mark as processed
    composeArea.dataset.aiButtonAdded = 'true';
    
    // Find compose dialog container
    const composeDialog = composeArea.closest('[role="dialog"]');
    if (!composeDialog) return;
    
    // Find a better place to put the button - look for toolbar area
    let toolbar = composeDialog.querySelector('[role="toolbar"]') || 
                  composeDialog.querySelector('.btC') || // Gmail toolbar class
                  composeDialog.querySelector('[data-tooltip]')?.parentElement;
    
    if (!toolbar) {
        // Create our own toolbar container
        toolbar = document.createElement('div');
        toolbar.className = 'ai-toolbar-container';
        toolbar.style.cssText = `
            padding: 8px 16px;
            border-bottom: 1px solid #e0e0e0;
            background: #f8f9fa;
            display: flex;
            justify-content: flex-end;
            align-items: center;
        `;
        
        // Insert at the top of the compose dialog
        const firstChild = composeDialog.firstElementChild;
        if (firstChild) {
            composeDialog.insertBefore(toolbar, firstChild);
        } else {
            composeDialog.appendChild(toolbar);
        }
    }
    
    // Create simple rewrite button
    const rewriteButton = document.createElement('button');
    rewriteButton.innerHTML = '✨ AI Rewrite';
    rewriteButton.className = 'ai-rewrite-btn';
    rewriteButton.type = 'button';
    
    // Style the button
    rewriteButton.style.cssText = `
        padding: 6px 12px;
        background: #1a73e8;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
        font-weight: 500;
        font-family: Google Sans, Roboto, sans-serif;
        margin-left: 8px;
    `;
    
    // Add hover effect
    rewriteButton.addEventListener('mouseover', () => {
        rewriteButton.style.background = '#1557b0';
    });
    rewriteButton.addEventListener('mouseout', () => {
        rewriteButton.style.background = '#1a73e8';
    });
    
    // Add click handler
    rewriteButton.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        rewriteEmailContent(composeArea, composeDialog);
    });
    
    // Add button to toolbar
    toolbar.appendChild(rewriteButton);
    
    console.log('Added rewrite button to compose toolbar');
}

// Watch for new compose windows
function observeForNewCompose() {
    const observer = new MutationObserver(() => {
        addRewriteButtonsToCompose();
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// Main rewrite function
async function rewriteEmailContent(composeArea, composeDialog) {
    try {
        // Get current email content
        const currentContent = composeArea.textContent || composeArea.innerText || '';
        
        if (!currentContent.trim()) {
            showSimpleNotification('Please write some content first!', 'warning');
            return;
        }
        
        // Show loading
        showSimpleNotification('Rewriting your email...', 'info');
        
        // Call the backend API
        const response = await fetch(`${API_BASE_URL}/api/rewrite-email`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                original_content: currentContent,
                tone: 'professional'
            })
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.rewritten_body) {
            // Insert the rewritten content properly
            insertRewrittenEmail(composeArea, composeDialog, data.rewritten_subject, data.rewritten_body);
            showSimpleNotification('Email rewritten successfully!', 'success');
        } else {
            throw new Error('No rewritten content received');
        }
        
    } catch (error) {
        console.error('Rewrite failed:', error);
        showSimpleNotification('Failed to rewrite email. Check if backend is running.', 'error');
    }
}

// Insert rewritten email with proper formatting
function insertRewrittenEmail(composeArea, composeDialog, subject, body) {
    try {
        // Update subject field if exists
        const subjectField = composeDialog.querySelector('[name="subject"]') ||
                            composeDialog.querySelector('[aria-label*="Subject"]') ||
                            composeDialog.querySelector('input[placeholder*="Subject"]');
        
        if (subjectField && subject) {
            subjectField.value = subject;
            subjectField.dispatchEvent(new Event('input', { bubbles: true }));
            subjectField.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        // Clear and update body
        composeArea.innerHTML = '';
        
        // Format body with proper line breaks for professional emails
        const formattedBody = body
            .split('\n')
            .map(line => line.trim())
            .map(line => {
                // Don't filter empty lines - they're important for formatting
                if (line === '') return '<br>';
                return line;
            })
            .join('<br>');
        
        // Insert formatted content with proper structure
        composeArea.innerHTML = `<div style="font-family: Arial, sans-serif; line-height: 1.4;">${formattedBody}</div>`;
        
        // Trigger events to notify Gmail
        composeArea.dispatchEvent(new Event('input', { bubbles: true }));
        composeArea.dispatchEvent(new Event('change', { bubbles: true }));
        
        // Focus the compose area and place cursor at end
        composeArea.focus();
        
        // Move cursor to end
        const range = document.createRange();
        const selection = window.getSelection();
        range.selectNodeContents(composeArea);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
        
        console.log('Email content inserted successfully');
        
    } catch (error) {
        console.error('Failed to insert rewritten content:', error);
        // Fallback: simple text insertion
        composeArea.innerHTML = '';
        composeArea.textContent = body;
        composeArea.dispatchEvent(new Event('input', { bubbles: true }));
    }
}

// Simple notification system
function showSimpleNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelectorAll('.ai-simple-notification');
    existing.forEach(n => n.remove());
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = 'ai-simple-notification';
    notification.textContent = message;
    
    // Style based on type
    const colors = {
        info: { bg: '#e3f2fd', color: '#1976d2', border: '#90caf9' },
        success: { bg: '#e8f5e8', color: '#388e3c', border: '#81c784' },
        warning: { bg: '#fff3e0', color: '#f57c00', border: '#ffb74d' },
        error: { bg: '#ffebee', color: '#d32f2f', border: '#e57373' }
    };
    
    const style = colors[type] || colors.info;
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        padding: 12px 16px;
        background: ${style.bg};
        color: ${style.color};
        border: 1px solid ${style.border};
        border-radius: 4px;
        font-size: 14px;
        font-family: Google Sans, Roboto, sans-serif;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        max-width: 300px;
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 3000);
}

// Handle messages from popup
function handleMessage(request, sender, sendResponse) {
    if (request.action === 'triggerRewrite') {
        // Find active compose area
        const activeCompose = findActiveComposeArea();
        if (activeCompose) {
            const composeDialog = activeCompose.closest('[role="dialog"]');
            rewriteEmailContent(activeCompose, composeDialog);
            sendResponse({ success: true });
        } else {
            sendResponse({ success: false, error: 'No active compose area found' });
        }
    }
    return true;
}

// Find currently active compose area
function findActiveComposeArea() {
    const composeAreas = document.querySelectorAll('[contenteditable="true"][role="textbox"]');
    
    // Return the first visible compose area
    for (const area of composeAreas) {
        const rect = area.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            return area;
        }
    }
    
    return null;
}

// Initialize when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(initializeSimpleRewriter, 1000);
    });
} else {
    setTimeout(initializeSimpleRewriter, 1000);
}

// Re-initialize on URL changes (Gmail SPA)
let currentUrl = location.href;
setInterval(() => {
    if (location.href !== currentUrl) {
        currentUrl = location.href;
        isInitialized = false;
        setTimeout(initializeSimpleRewriter, 1000);
    }
}, 2000);