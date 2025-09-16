# AI Email Agent - Chrome Extension 🤖

Interactive Chrome extension for AI-powered email composition with personalized style analysis.

## 🌟 Features

### ✍️ **AI Email Drafts**
- **Personalized Writing Style**: Analyzes your past emails to match your writing patterns
- **Recipient-Specific Tones**: Adapts formality, greeting, and sign-off based on who you're writing to
- **Context-Aware Generation**: Uses Gemini API to create relevant, professional email drafts
- **Seamless Gmail Integration**: AI Draft button appears directly in Gmail compose windows

### 📊 **Performance Monitoring**
- **Real-time Metrics**: View processing statistics and success rates
- **Agent Logs Export**: Download comprehensive logs for analysis
- **Backend Status**: Monitor AI agent connection and health
- **Style Profile Management**: View and manage recipient-specific writing styles

### 🎯 **Smart Integration**
- **Auto-Detection**: Automatically detects Gmail compose windows
- **Recipient Extraction**: Smart extraction of recipient emails from compose fields
- **Style Profiles**: Builds and maintains writing style profiles for each recipient
- **One-Click Usage**: Generate, review, and use AI drafts with simple clicks

## 📦 Installation

### Prerequisites
- Chrome browser (latest version recommended)
- AI Email Agent backend running on `localhost:8000`
- Gmail account

### Install Steps

1. **Download Extension**
   ```bash
   # Navigate to the extension directory
   cd chrome-extension
   ```

2. **Enable Developer Mode**
   - Open Chrome and go to `chrome://extensions/`
   - Toggle "Developer mode" in the top-right corner

3. **Load Extension**
   - Click "Load unpacked" button
   - Select the `chrome-extension` folder
   - The AI Email Agent extension should appear in your extensions list

4. **Pin Extension**
   - Click the extensions puzzle icon in Chrome toolbar
   - Click the pin icon next to "AI Email Agent"
   - The 🤖 icon will appear in your toolbar

## 🚀 Usage

### **Gmail Integration**

1. **Open Gmail**
   - Navigate to `https://mail.google.com`
   - Click "Compose" to start a new email

2. **AI Draft Button**
   - Look for the **"AI Draft"** button in the compose window
   - If not visible, refresh the page and try again

3. **Generate AI Draft**
   - Click the "AI Draft" button
   - Fill in the recipient email
   - Describe your intent (e.g., "Request meeting for project discussion")
   - Click "Generate Draft"

4. **Review and Use**
   - Review the generated draft
   - Click "Use This Draft" to insert it into your email
   - Or "Copy to Clipboard" to use elsewhere

### **Extension Popup**

Click the 🤖 extension icon to access:

- **🧠 AI Features**
  - Open AI Compose (redirects to Gmail)
  - Manage Style Profiles

- **📊 Performance**
  - View real-time metrics
  - Export agent logs
  - Monitor processing statistics

- **⚙️ System**
  - Check backend connection
  - Refresh status
  - Open evaluation dashboard

### **Style Profile Management**

1. **Automatic Creation**
   - Style profiles are created automatically when you generate drafts
   - The system analyzes your past emails with each recipient

2. **View Profiles**
   - Click "Manage Style Profiles" in the extension popup
   - Or click "View Style Profile" in the AI compose modal

3. **Update Profiles**
   - Profiles update automatically as you send more emails
   - Manual refresh available through "Update Style" button

## ⚡ Features in Detail

### **AI Compose Modal**

| Feature | Description |
|---------|-------------|
| **Recipient Field** | Auto-extracted from Gmail or manually entered |
| **Intent Description** | Natural language description of your email purpose |
| **Generate Draft** | Uses Gemini API + your style profile |
| **View Style Profile** | Shows current writing style analysis |
| **Update Style** | Refreshes style analysis from recent emails |

### **Style Profile System**

| Element | What It Tracks |
|---------|----------------|
| **Greeting** | "Dear Prof.", "Hi", "Respected Sir" |
| **Formality** | Formal, semi-formal, casual |
| **Tone** | Professional, academic, friendly |
| **Sign-off** | "Best regards", "Thanks", "Sincerely" |
| **Sentence Style** | Short, medium, long sentences |

### **Performance Dashboard**

| Metric | Description |
|--------|-------------|
| **Emails Processed** | Total emails handled by the agent |
| **Success Rate** | Percentage of successful operations |
| **Avg Confidence** | Average classification confidence |
| **Avg Latency** | Average processing time (ms) |

## 🔧 Configuration

### **Backend Connection**

The extension connects to your AI Email Agent backend at:
- **URL**: `http://localhost:8000`
- **API Base**: `http://localhost:8000/api/chrome/`

### **Required Backend APIs**

Make sure your backend supports these endpoints:

```
POST /api/chrome/draft-ai              - Generate email drafts
GET  /api/chrome/style-profile/{email} - Get style profile
POST /api/chrome/style-profile/{email}/update - Update style
POST /api/chrome/logs/export           - Export logs
GET  /api/chrome/performance/summary   - Performance metrics
GET  /api/status                      - Backend health check
```

## 🛠️ Troubleshooting

### **Extension Not Working**

1. **Check Backend**
   - Ensure AI agent is running on `localhost:8000`
   - Visit `http://localhost:8000/docs` to test

2. **Refresh Extension**
   - Go to `chrome://extensions/`
   - Click reload button for AI Email Agent

3. **Check Permissions**
   - Extension needs access to `mail.google.com`
   - Check permissions in `chrome://extensions/`

### **AI Draft Button Missing**

1. **Refresh Gmail**
   - Reload the Gmail tab
   - Extension injects on page load

2. **Check Console**
   - Press F12 in Gmail
   - Look for AI Agent console messages

3. **Try Different Compose**
   - Use full compose window (not quick compose)
   - Some Gmail layouts work better

### **Backend Connection Issues**

1. **CORS Policy**
   - Backend must allow `chrome-extension://*` origins
   - Or use `allow_origins=["*"]` for development

2. **Port Issues**
   - Default port is 8000
   - Update `background.js` if using different port

3. **API Availability**
   - Ensure Gemini API key is configured
   - Check backend logs for errors

## 📁 Extension Structure

```
chrome-extension/
├── manifest.json           # Extension configuration
├── background.js          # Service worker (API calls)
├── content.js            # Gmail integration
├── popup.html            # Extension popup UI
├── popup.js              # Popup functionality  
├── styles.css            # Gmail modal styles
├── style-manager.html    # Style management page
├── icons/                # Extension icons
│   ├── icon16.png
│   ├── icon32.png
│   ├── icon48.png
│   └── icon128.png
└── README.md            # This file
```

## 🔐 Privacy & Security

- **Local Processing**: Style analysis happens on your local backend
- **No Data Collection**: Extension doesn't store or transmit personal data
- **Gmail Permissions**: Only accesses compose windows when active
- **Secure Communication**: All API calls use localhost (not external servers)

## 🎯 Next Steps

1. **Install the extension** following the steps above
2. **Start your AI agent backend** with `python run_server.py`
3. **Configure your Gemini API key** in the backend
4. **Open Gmail and try composing** an email with AI assistance
5. **Check the extension popup** for performance metrics and settings

## 🐛 Issues & Support

If you encounter issues:

1. Check the browser console for error messages
2. Verify backend is running and accessible
3. Ensure all required APIs are implemented
4. Test with simple emails before complex ones

**Happy AI-powered emailing!** 🚀✉️