// AI Email Agent - Background Service Worker
console.log('AI Email Agent background service worker loaded');

// Configuration
const API_BASE_URL = 'http://localhost:8000/api';

// Install/Update handler
chrome.runtime.onInstalled.addListener((details) => {
  console.log('AI Email Agent installed:', details.reason);
  
  // Set default configuration
  chrome.storage.local.set({
    apiBaseUrl: API_BASE_URL,
    autoSuggest: true,
    styleAnalysis: true,
    performanceMonitoring: true
  });
  
  // Create context menu if API is available
  if (chrome.contextMenus) {
    chrome.contextMenus.create({
      id: 'aiEmailAgent',
      title: 'Generate AI Email Draft',
      contexts: ['selection']
    });
  } else {
    console.warn('Context menus API not available');
  }
});

// Message handler for content script and popup communication
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received message:', request);
  
  switch (request.action) {
    case 'generateDraft':
      handleGenerateDraft(request, sendResponse);
      return true; // Keep channel open for async response
      
    case 'generateStyleMatchedDraft':
      handleGenerateStyleMatchedDraft(request, sendResponse);
      return true; // Keep channel open for async response
      
    case 'getStyleProfile':
      handleGetStyleProfile(request, sendResponse);
      return true;
      
    case 'updateStyleProfile':
      handleUpdateStyleProfile(request, sendResponse);
      return true;
      
    case 'exportLogs':
      handleExportLogs(request, sendResponse);
      return true;
      
    case 'getPerformanceMetrics':
      handleGetPerformanceMetrics(request, sendResponse);
      return true;
      
    case 'checkBackendStatus':
      handleCheckBackendStatus(sendResponse);
      return true;
      
    default:
      console.warn('Unknown action:', request.action);
      sendResponse({success: false, error: 'Unknown action'});
  }
});

// API call handlers
async function handleGenerateDraft(request, sendResponse) {
  try {
    const response = await fetch(`${API_BASE_URL}/chrome/draft-ai`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        recipient: request.recipient,
        intent: request.intent
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    sendResponse({
      success: true,
      draft: data.draft,
      styleProfile: data.style_profile,
      confidence: data.confidence
    });
    
  } catch (error) {
    console.error('Draft generation failed:', error);
    sendResponse({
      success: false,
      error: error.message
    });
  }
}

// Handle style-matched draft generation
async function handleGenerateStyleMatchedDraft(request, sendResponse) {
  try {
    console.log('Generating style-matched draft for:', request.recipient);
    
    const response = await fetch(`${API_BASE_URL}/chrome/analyze-style`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        recipient: request.recipient,
        intent: request.intent
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Log the style analysis result for debugging
    console.log('Style analysis result:', {
      recipient: request.recipient,
      confidence: data.confidence,
      past_email_count: data.past_email_count,
      style_analysis: data.style_analysis
    });
    
    sendResponse({
      success: true,
      generated_draft: data.generated_draft,
      style_analysis: data.style_analysis,
      confidence: data.confidence,
      past_email_count: data.past_email_count,
      detected_patterns: data.detected_patterns,
      recipient: data.recipient
    });
    
  } catch (error) {
    console.error('Style-matched draft generation failed:', error);
    
    // Fallback to regular draft generation if style analysis fails
    console.log('Falling back to regular draft generation...');
    await handleGenerateDraft(request, sendResponse);
  }
}

async function handleGetStyleProfile(request, sendResponse) {
  try {
    const response = await fetch(`${API_BASE_URL}/chrome/style-profile/${encodeURIComponent(request.recipient)}`);
    
    if (response.status === 404) {
      sendResponse({success: true, profile: null});
      return;
    }
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    sendResponse({
      success: true,
      profile: data.profile,
      sampleCount: data.sample_count,
      lastUpdated: data.last_updated
    });
    
  } catch (error) {
    console.error('Style profile fetch failed:', error);
    sendResponse({
      success: false,
      error: error.message
    });
  }
}

async function handleUpdateStyleProfile(request, sendResponse) {
  try {
    const response = await fetch(`${API_BASE_URL}/chrome/style-profile/${encodeURIComponent(request.recipient)}/update`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    sendResponse({
      success: true,
      message: data.message,
      profile: data.profile
    });
    
  } catch (error) {
    console.error('Style profile update failed:', error);
    sendResponse({
      success: false,
      error: error.message
    });
  }
}

async function handleExportLogs(request, sendResponse) {
  try {
    const response = await fetch(`${API_BASE_URL}/chrome/logs/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        format: request.format || 'json',
        limit: request.limit || 100,
        include_performance_metrics: request.includeMetrics !== false
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Create and download the file
    const blob = new Blob([data.content], {
      type: data.format === 'txt' ? 'text/plain' : 'application/json'
    });
    
    const url = URL.createObjectURL(blob);
    const filename = `agent_logs_${new Date().toISOString().split('T')[0]}.${data.format}`;
    
    chrome.downloads.download({
      url: url,
      filename: filename
    });
    
    sendResponse({
      success: true,
      filename: filename,
      size: data.content.length
    });
    
  } catch (error) {
    console.error('Log export failed:', error);
    sendResponse({
      success: false,
      error: error.message
    });
  }
}

async function handleGetPerformanceMetrics(request, sendResponse) {
  try {
    const response = await fetch(`${API_BASE_URL}/chrome/performance/summary`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    sendResponse({
      success: true,
      metrics: data
    });
    
  } catch (error) {
    console.error('Performance metrics fetch failed:', error);
    sendResponse({
      success: false,
      error: error.message
    });
  }
}

async function handleCheckBackendStatus(sendResponse) {
  try {
    const response = await fetch(`${API_BASE_URL}/../status`, {
      timeout: 5000
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    sendResponse({
      success: true,
      status: data,
      backendAvailable: true
    });
    
  } catch (error) {
    console.error('Backend status check failed:', error);
    sendResponse({
      success: false,
      error: error.message,
      backendAvailable: false
    });
  }
}

// Context menu click handler
if (chrome.contextMenus) {
  chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'aiEmailAgent') {
      // Send message to content script to show AI compose modal
      chrome.tabs.sendMessage(tab.id, {
        action: 'showAIComposeModal',
        selectedText: info.selectionText
      });
    }
  });
} else {
  console.warn('Context menus API not available for click handler');
}