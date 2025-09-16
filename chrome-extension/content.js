// Simple AI Email Rewriter - Content Script
console.log('Simple AI Email Rewriter loaded on Gmail');

// Configuration
const API_BASE_URL = 'http://localhost:8000';
let isInitialized = false;

// Initialize when Gmail is ready
function initializeAIAgent() {
  if (isGmailLoaded) return;
  
  console.log('Initializing AI Email Agent for Gmail');
  isGmailLoaded = true;
  
  // Monitor for compose windows
  observeComposeWindows();
  
  // Add AI compose button to existing compose windows
  addAIButtonsToExistingComposes();
  
  // Listen for messages from background script
  chrome.runtime.onMessage.addListener(handleMessage);
}

// Observe for new compose windows
function observeComposeWindows() {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          // Look for compose windows
          if (node.matches && node.matches('[role="dialog"]') || 
              node.querySelector && node.querySelector('[role="dialog"]')) {
            setTimeout(() => addAIButtonToCompose(node), 500);
          }
          
          // Also check for compose buttons/toolbars
          const composeAreas = node.querySelectorAll ? node.querySelectorAll('[role="textbox"][contenteditable="true"]') : [];
          composeAreas.forEach(addAIButtonToCompose);
        }
      });
    });
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

// Add AI buttons to existing compose windows
function addAIButtonsToExistingComposes() {
  const composeDialogs = document.querySelectorAll('[role="dialog"]');
  composeDialogs.forEach(dialog => {
    addAIButtonToCompose(dialog);
  });
}

// Add AI compose button to a specific compose window
function addAIButtonToCompose(element) {
  if (!element) return;
  
  // Find the compose area
  let composeArea = element.querySelector ? element.querySelector('[role="textbox"][contenteditable="true"]') : null;
  if (!composeArea && element.matches && element.matches('[role="textbox"][contenteditable="true"]')) {
    composeArea = element;
  }
  
  if (!composeArea || composeElements.has(composeArea)) return;
  
  console.log('Adding AI button to compose area');
  composeElements.add(composeArea);
  
  // Find the toolbar area (usually parent containers)
  let toolbar = findComposeToolbar(composeArea);
  
  if (toolbar) {
    // Create AI compose button
    const aiButton = createAIComposeButton();
    toolbar.appendChild(aiButton);
    
    // Add event listener
    aiButton.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      showAIComposeModal(composeArea);
    });
  }
}

// Find the compose toolbar
function findComposeToolbar(composeArea) {
  let current = composeArea;
  let attempts = 0;
  
  while (current && attempts < 10) {
    // Look for toolbar patterns in Gmail
    const toolbar = current.querySelector('[role="toolbar"]') || 
                   current.querySelector('.btC') || // Gmail compose toolbar class
                   current.querySelector('[data-tooltip]')?.parentElement;
    
    if (toolbar) return toolbar;
    
    // Try parent elements
    current = current.parentElement;
    attempts++;
  }
  
  // Fallback: create toolbar container
  const toolbarContainer = document.createElement('div');
  toolbarContainer.className = 'ai-agent-toolbar';
  toolbarContainer.style.cssText = `
    padding: 8px;
    border-top: 1px solid #e0e0e0;
    background: #f8f9fa;
    display: flex;
    gap: 8px;
    align-items: center;
  `;
  
  composeArea.parentElement.insertBefore(toolbarContainer, composeArea.nextSibling);
  return toolbarContainer;
}

// Create AI compose button with modern design
function createAIComposeButton() {
  const button = document.createElement('button');
  button.className = 'ai-compose-button';
  button.innerHTML = `
    <span class="ai-button-icon">✨</span>
    <span class="ai-button-text">AI Rewrite</span>
  `;
  
  button.style.cssText = `
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 8px 16px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 20px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    position: relative;
    overflow: hidden;
    min-width: 100px;
  `;
  
  // Add hover effects
  button.addEventListener('mouseover', () => {
    button.style.transform = 'translateY(-2px) scale(1.02)';
    button.style.boxShadow = '0 8px 20px rgba(102, 126, 234, 0.4)';
  });
  
  button.addEventListener('mouseout', () => {
    button.style.transform = 'translateY(0) scale(1)';
    button.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.3)';
  });
  
  button.addEventListener('mousedown', () => {
    button.style.transform = 'translateY(0) scale(0.98)';
  });
  
  button.addEventListener('mouseup', () => {
    button.style.transform = 'translateY(-2px) scale(1.02)';
  });
  
  button.title = '✨ AI-powered email rewriting with personalized style matching';
  
  return button;
}

// Show AI compose modal
function showAIComposeModal(composeArea) {
  console.log('Starting direct AI compose integration');
  
  // Extract recipient and existing content from compose window
  const composeData = extractComposeData(composeArea);
  
  if (!composeData.recipient) {
    showModernNotification('Please enter a recipient email address first.', 'warning');
    return;
  }
  
  if (!composeData.body.trim() && !composeData.intent) {
    showModernNotification('Please write some content in the compose box to indicate your intent.', 'info');
    return;
  }
  
  // Use existing body content as intent if no specific intent provided
  const intent = composeData.intent || composeData.body || 'Professional email communication';
  
  showModernNotification('✨ Analyzing your writing style and generating draft...', 'info');
  
  // Generate draft directly without modal
  generateAndInsertDraft(composeArea, composeData.recipient, intent);
}

// Trigger rewrite from popup
function triggerEmailRewrite() {
  console.log('Triggering email rewrite from popup');
  
  // Find the active compose area
  const activeComposeArea = findActiveComposeArea();
  
  if (!activeComposeArea) {
    showModernNotification('No active compose window found. Please open Gmail compose.', 'error');
    return false;
  }
  
  // Trigger the rewrite
  showAIComposeModal(activeComposeArea);
  return true;
}

// Find active compose area
function findActiveComposeArea() {
  // Look for compose areas in order of preference
  const selectors = [
    '[role="textbox"][contenteditable="true"][aria-label*="compose"]',  // Gmail compose body
    '[role="textbox"][contenteditable="true"][aria-label*="Message"]',   // Gmail compose body
    '[role="textbox"][contenteditable="true"]',  // Any compose area
    '.editable[contenteditable="true"]',  // Fallback
    '[contenteditable="true"]'  // Last resort
  ];
  
  for (const selector of selectors) {
    const elements = document.querySelectorAll(selector);
    
    // Find the most likely compose area (visible and not read-only)
    for (const element of elements) {
      const rect = element.getBoundingClientRect();
      const isVisible = rect.width > 100 && rect.height > 50 && 
                       window.getComputedStyle(element).display !== 'none';
      
      if (isVisible && !element.readOnly) {
        console.log('Found active compose area:', selector);
        return element;
      }
    }
  }
  
  console.log('No active compose area found');
  return null;
}

// Extract comprehensive compose data from Gmail compose window
function extractComposeData(composeArea) {
  const composeData = {
    recipient: '',
    subject: '',
    body: '',
    intent: ''
  };
  
  try {
    // Find the compose dialog container
    const composeDialog = composeArea.closest('[role="dialog"]') || 
                         composeArea.closest('.M9') || // Gmail compose window class
                         composeArea.closest('[aria-label*="compose"]');
    
    if (composeDialog) {
      // Extract recipient (To field)
      const toSelectors = [
        '[name="to"]',
        '[aria-label*="To"]', 
        '[aria-label*="Recipients"]',
        '.vR .vT', // Gmail To field classes
        'input[type="email"]',
        '[data-tooltip*="To"]'
      ];
      
      for (const selector of toSelectors) {
        const toField = composeDialog.querySelector(selector);
        if (toField) {
          composeData.recipient = toField.value || toField.textContent || toField.innerText || '';
          if (composeData.recipient.trim()) break;
        }
      }
      
      // Extract subject
      const subjectSelectors = [
        '[name="subject"]',
        '[aria-label*="Subject"]',
        'input[placeholder*="Subject"]',
        '.aoT' // Gmail subject field class
      ];
      
      for (const selector of subjectSelectors) {
        const subjectField = composeDialog.querySelector(selector);
        if (subjectField) {
          composeData.subject = subjectField.value || subjectField.textContent || subjectField.innerText || '';
          if (composeData.subject.trim()) break;
        }
      }
      
      // Extract body content (existing text in compose area)
      if (composeArea) {
        composeData.body = composeArea.textContent || composeArea.innerText || '';
        // Clean up the body text
        composeData.body = composeData.body.replace(/\n\s*\n/g, '\n').trim();
      }
    }
    
    // If no recipient found, try email regex on whole dialog
    if (!composeData.recipient && composeDialog) {
      const emailRegex = /[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}/;
      const match = composeDialog.textContent.match(emailRegex);
      if (match) {
        composeData.recipient = match[0];
      }
    }
    
  } catch (error) {
    console.warn('Could not extract compose data:', error);
  }
  
  console.log('Extracted compose data:', composeData);
  return composeData;
}

// Generate AI draft with style matching and insert directly into compose area
async function generateAndInsertDraft(composeArea, recipient, intent) {
  try {
    // Show style analysis notification
    showNotification('🔍 Analyzing your writing style...', 'info');
    
    // First try style-matched draft generation
    const styleResponse = await new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({
        action: 'generateStyleMatchedDraft',
        recipient: recipient,
        intent: intent
      }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response);
        }
      });
    });
    
    if (styleResponse.success && styleResponse.style_analysis) {
      // Insert the style-matched draft into the compose area
      insertDraftIntoCompose(composeArea, styleResponse.generated_draft, recipient, styleResponse);
      
      // Show style analysis info
      showStyleAnalysisNotification(styleResponse);
    } else {
      // Fallback to regular draft generation
      showNotification('📝 Generating generic draft...', 'info');
      
      const fallbackResponse = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({
          action: 'generateDraft',
          recipient: recipient,
          intent: intent
        }, (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(response);
          }
        });
      });
      
      if (fallbackResponse.success) {
        insertDraftIntoCompose(composeArea, fallbackResponse.draft, recipient);
        showNotification('✅ AI draft generated (generic style)', 'success');
      } else {
        showNotification('❌ Failed to generate draft: ' + (fallbackResponse.error || 'Unknown error'), 'error');
      }
    }
  } catch (error) {
    console.error('Draft generation error:', error);
    showNotification('❌ Failed to connect to AI agent. Make sure the server is running.', 'error');
  }
}

// Show style analysis notification with details
function showStyleAnalysisNotification(styleResponse) {
  const pastEmailCount = styleResponse.past_email_count || 0;
  const confidence = Math.round((styleResponse.confidence || 0) * 100);
  const patterns = styleResponse.detected_patterns || {};
  
  let message = '';
  
  if (pastEmailCount >= 3) {
    message = `✨ Style matched! Found ${pastEmailCount} past emails. ${confidence}% confidence.`;
    if (patterns.formality) {
      message += ` Detected ${patterns.formality} style with ${patterns.tone || 'neutral'} tone.`;
    }
  } else if (pastEmailCount > 0) {
    message = `📧 Limited history: Only ${pastEmailCount} past email(s) found. Using general style.`;
  } else {
    message = `🎯 First time emailing this person. Using smart professional style.`;
  }
  
  showNotification(message, 'success');
  
  // Show style adjustment options after a delay
  setTimeout(() => {
    showStyleAdjustmentOptions(styleResponse.recipient);
  }, 3000);
}

// Show style adjustment options
function showStyleAdjustmentOptions(recipient) {
  // Remove existing adjustment panel
  const existingPanel = document.querySelector('.ai-style-adjustment-panel');
  if (existingPanel) existingPanel.remove();
  
  const panel = document.createElement('div');
  panel.className = 'ai-style-adjustment-panel';
  panel.innerHTML = `
    <div class="ai-style-header">
      🎨 Style Adjustments
      <button class="ai-close-btn" onclick="this.closest('.ai-style-adjustment-panel').remove()">&times;</button>
    </div>
    <div class="ai-style-buttons">
      <button class="ai-style-btn" data-adjustment="more_formal">More Formal</button>
      <button class="ai-style-btn" data-adjustment="more_casual">More Casual</button>
      <button class="ai-style-btn" data-adjustment="add_urgency">Add Urgency</button>
      <button class="ai-style-btn" data-adjustment="more_polite">More Polite</button>
    </div>
  `;
  
  panel.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: white;
    border: 1px solid #dadce0;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    z-index: 10001;
    min-width: 250px;
    font-family: 'Google Sans', Roboto, sans-serif;
  `;
  
  // Add styles for the panel elements
  const panelStyle = document.createElement('style');
  panelStyle.textContent = `
    .ai-style-header {
      padding: 12px 16px;
      background: #f8f9fa;
      border-bottom: 1px solid #dadce0;
      font-weight: 500;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .ai-close-btn {
      background: none;
      border: none;
      font-size: 18px;
      cursor: pointer;
      color: #5f6368;
    }
    .ai-style-buttons {
      padding: 16px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .ai-style-btn {
      padding: 8px 12px;
      border: 1px solid #dadce0;
      border-radius: 4px;
      background: white;
      cursor: pointer;
      font-size: 12px;
      transition: all 0.2s;
    }
    .ai-style-btn:hover {
      background: #f8f9fa;
      border-color: #1a73e8;
    }
  `;
  
  if (!document.getElementById('ai-style-panel-styles')) {
    panelStyle.id = 'ai-style-panel-styles';
    document.head.appendChild(panelStyle);
  }
  
  document.body.appendChild(panel);
  
  // Add event listeners to adjustment buttons
  panel.querySelectorAll('.ai-style-btn').forEach(button => {
    button.addEventListener('click', async (e) => {
      const adjustment = e.target.dataset.adjustment;
      await applyStyleAdjustment(recipient, adjustment);
      panel.remove();
    });
  });
  
  // Auto-remove after 10 seconds
  setTimeout(() => {
    if (panel.parentElement) panel.remove();
  }, 10000);
}

// Apply style adjustment
async function applyStyleAdjustment(recipient, adjustment) {
  try {
    showNotification(`🎨 Applying ${adjustment.replace('_', ' ')} style...`, 'info');
    
    // This would need to be implemented in the background script and backend
    // For now, show a placeholder message
    setTimeout(() => {
      showNotification('✨ Style adjustment applied! (Feature coming soon)', 'success');
    }, 1500);
    
  } catch (error) {
    showNotification('Failed to apply style adjustment', 'error');
  }
}

// Insert generated draft into Gmail compose window
function insertDraftIntoCompose(composeArea, draft, recipient, styleResponse = null) {
  try {
    // Clear existing content
    composeArea.innerHTML = '';
    
    // Insert the generated draft
    // Convert line breaks to proper HTML
    const htmlDraft = draft
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>')
      .replace(/^/, '<p>')
      .replace(/$/, '</p>');
    
    composeArea.innerHTML = htmlDraft;
    
    // Set subject if we can find the subject field
    const composeDialog = composeArea.closest('[role="dialog"]');
    if (composeDialog) {
      const subjectField = composeDialog.querySelector('[name="subject"]') ||
                          composeDialog.querySelector('[aria-label*="Subject"]');
      
      if (subjectField && !subjectField.value.trim()) {
        // Generate a simple subject if none exists
        const recipientName = recipient.split('@')[0].replace(/[._]/g, ' ');
        subjectField.value = `Communication with ${recipientName}`;
        subjectField.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }
    
    // Trigger input events to notify Gmail of changes
    composeArea.dispatchEvent(new Event('input', { bubbles: true }));
    composeArea.dispatchEvent(new Event('change', { bubbles: true }));
    
    // Focus the compose area
    composeArea.focus();
    
    // Move cursor to end
    const range = document.createRange();
    const selection = window.getSelection();
    range.selectNodeContents(composeArea);
    range.collapse(false);
    selection.removeAllRanges();
    selection.addRange(range);
    
    console.log('Draft inserted successfully into compose area');
    
  } catch (error) {
    console.error('Failed to insert draft:', error);
    showNotification('Failed to insert draft into compose window', 'error');
  }
}

// Show notification to user
function showNotification(message, type = 'info') {
  // Remove existing notifications
  const existingNotifications = document.querySelectorAll('.ai-agent-notification');
  existingNotifications.forEach(notification => notification.remove());
  
  const notification = document.createElement('div');
  notification.className = 'ai-agent-notification';
  notification.textContent = message;
  
  // Style based on type
  const styles = {
    info: { backgroundColor: '#e3f2fd', color: '#1565c0', borderColor: '#90caf9' },
    success: { backgroundColor: '#e8f5e8', color: '#2e7d32', borderColor: '#81c784' },
    warning: { backgroundColor: '#fff3e0', color: '#ef6c00', borderColor: '#ffb74d' },
    error: { backgroundColor: '#fce4ec', color: '#c2185b', borderColor: '#f48fb1' }
  };
  
  const style = styles[type] || styles.info;
  
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: ${style.backgroundColor};
    color: ${style.color};
    border: 1px solid ${style.borderColor};
    border-radius: 4px;
    padding: 12px 16px;
    font-size: 14px;
    font-family: 'Google Sans', Roboto, sans-serif;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    z-index: 10000;
    max-width: 400px;
    animation: slideIn 0.3s ease-out;
  `;
  
  // Add CSS animations if not already added
  if (!document.getElementById('ai-agent-animations')) {
    const animationStyle = document.createElement('style');
    animationStyle.id = 'ai-agent-animations';
    animationStyle.textContent = `
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
      .ai-agent-notification {
        animation: slideIn 0.3s ease-out;
      }
      .ai-agent-notification.removing {
        animation: slideOut 0.3s ease-in;
      }
    `;
    document.head.appendChild(animationStyle);
  }
  
  document.body.appendChild(notification);
  
  // Auto-remove after 5 seconds with animation
  setTimeout(() => {
    if (notification.parentElement) {
      notification.classList.add('removing');
      setTimeout(() => notification.remove(), 300);
    }
  }, 5000);
}

// Legacy function removed - now using direct compose integration

// Old modal-related functions removed - now using direct compose integration

// Modern notification system
function showModernNotification(message, type = 'info') {
  // Remove existing notifications
  const existingNotifications = document.querySelectorAll('.ai-modern-notification');
  existingNotifications.forEach(notification => notification.remove());
  
  const notification = document.createElement('div');
  notification.className = 'ai-modern-notification';
  
  // Icon based on type
  const icons = {
    info: 'ℹ️',
    success: '✓',
    warning: '⚠️',
    error: '❌'
  };
  
  notification.innerHTML = `
    <div class="ai-notification-content">
      <span class="ai-notification-icon">${icons[type] || icons.info}</span>
      <span class="ai-notification-text">${message}</span>
    </div>
  `;
  
  // Modern glassmorphism styles
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 16px;
    padding: 16px 20px;
    font-size: 14px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    z-index: 10000;
    max-width: 400px;
    animation: slideInFromRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    color: #333;
  `;
  
  // Type-specific styling
  const typeStyles = {
    info: { background: 'rgba(79, 172, 254, 0.1)', borderColor: 'rgba(79, 172, 254, 0.3)' },
    success: { background: 'rgba(76, 175, 80, 0.1)', borderColor: 'rgba(76, 175, 80, 0.3)' },
    warning: { background: 'rgba(255, 193, 7, 0.1)', borderColor: 'rgba(255, 193, 7, 0.3)' },
    error: { background: 'rgba(244, 67, 54, 0.1)', borderColor: 'rgba(244, 67, 54, 0.3)' }
  };
  
  if (typeStyles[type]) {
    notification.style.background = typeStyles[type].background;
    notification.style.borderColor = typeStyles[type].borderColor;
  }
  
  // Add modern CSS animations if not already added
  if (!document.getElementById('ai-modern-animations')) {
    const animationStyle = document.createElement('style');
    animationStyle.id = 'ai-modern-animations';
    animationStyle.textContent = `
      @keyframes slideInFromRight {
        from { 
          transform: translateX(100%) scale(0.9); 
          opacity: 0;
        }
        to { 
          transform: translateX(0) scale(1); 
          opacity: 1;
        }
      }
      @keyframes slideOutToRight {
        from { 
          transform: translateX(0) scale(1); 
          opacity: 1;
        }
        to { 
          transform: translateX(100%) scale(0.9); 
          opacity: 0;
        }
      }
      .ai-notification-content {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .ai-notification-icon {
        font-size: 18px;
        flex-shrink: 0;
      }
      .ai-notification-text {
        font-weight: 500;
        line-height: 1.4;
      }
    `;
    document.head.appendChild(animationStyle);
  }
  
  document.body.appendChild(notification);
  
  // Auto-remove after 5 seconds with animation
  setTimeout(() => {
    if (notification.parentElement) {
      notification.style.animation = 'slideOutToRight 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
      setTimeout(() => notification.remove(), 300);
    }
  }, 5000);
}

// Handle messages from background script
function handleMessage(request, sender, sendResponse) {
  console.log('Content script received message:', request);
  
  switch (request.action) {
    case 'showAIComposeModal':
      showAIComposeModal();
      sendResponse({success: true});
      break;
      
    case 'triggerRewrite':
      const success = triggerEmailRewrite();
      sendResponse({success: success});
      break;
      
    default:
      console.warn('Unknown message action:', request.action);
      sendResponse({success: false, error: 'Unknown action'});
  }
  
  return true; // Keep message channel open for async response
}

// Initialize when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initializeAIAgent, 1000);
  });
} else {
  setTimeout(initializeAIAgent, 1000);
}

// Also initialize on URL changes (Gmail SPA navigation)
let currentUrl = location.href;
const urlObserver = new MutationObserver(() => {
  if (location.href !== currentUrl) {
    currentUrl = location.href;
    setTimeout(initializeAIAgent, 1000);
  }
});

urlObserver.observe(document, { subtree: true, childList: true });