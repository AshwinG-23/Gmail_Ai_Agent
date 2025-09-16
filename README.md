# AI Email Agent - Intelligent University Email Automation System

![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Author

Ashwin Gaikwad - IIT Goa - Btech. Mathematics and Computing. 
All needed Delivereables are added as .pdfs. 

[Demo Video](https://drive.google.com/file/d/1mxGFy-MB_vP7VF0FCzeeW5MICVq9w7pX/view?usp=sharing)

An autonomous AI-powered email management system designed specifically for university students and professionals. The system combines **  personally trained models** (DistilBERT classifier + Llama 3 extractor) with Gemini AI for intelligent email processing that understands your specific patterns and preferences.

## 🎯 Key Features

### 🤖 **Autonomous Email Processing**
- **Smart monitoring** of NEW emails only (since server start)
- **  trained DistilBERT** classifies emails into 8 categories (trained on   5,678 emails)
- **  Llama 3 + LoRA** extracts structured data (jobs, events, deadlines)
- **Gemini orchestrates** execution based on   models' analysis
- **Duplicate prevention** - never processes the same email twice
- **Custom rules** (e.g., Google Classroom emails auto-labeling)

### ✨ **AI-Powered Writing Assistant**
- **Style-matched email rewriting** using past email analysis
- **Chrome extension** for seamless Gmail integration
- **Recipient-specific** tone and style adaptation
- **Context-aware** draft generation with Gemini AI

### 📊 **Smart Data Extraction**
- **Structured data extraction** from emails using fine-tuned Llama 3
- **Automatic job tracking** in Google Sheets
- **Event scheduling** in Google Calendar
- **Reminder creation** for deadlines

### 🔧 **Workflow Automation**
- **Multi-tool orchestration** with autonomous decision making
- **Performance monitoring** and logging
- **Chrome extension** with modern glassmorphism UI
- **RESTful API** for external integrations

## 🏗️ System Architecture

```
🚀 NEW WORKFLOW:   MODELS + GEMINI ORCHESTRATION

1️⃣ NEW EMAIL ARRIVES
         │
         ↓
2️⃣   DISTILBERT CLASSIFIER (trained on 5,678   emails)
         │
    [🎩 95.1% accuracy]
         │
         ↓
3️⃣   LLAMA 3 + LORA EXTRACTOR (fine-tuned for   patterns)
         │
    [🤖 Structured data]
         │
         ↓
4️⃣ GEMINI ORCHESTRATION (planning based on   results)
         │
    [📋 Execution plan]
         │
         ↓
┌──────────────┴──────────────────────┴────────────────┐
│   Gmail API     │       Tool Execution         │  Chrome Ext.    │
│                 │                              │   (UI/UX)       │
│ • Email Monitor │    • Google Calendar         │ • Draft Gen.    │
│ • Smart Labels  │    • Google Sheets           │ • Log Export    │
│ • Actions       │    • Notifications           │ • Style Match   │
└─────────────────┘    • Reminders               └─────────────────┘
                        • Job Tracking
```

## 🤖 AI Models & Training

> **🔥 IMPORTANT:** Your trained models now do the heavy lifting, with Gemini handling orchestration!

### Model 1: Email Classifier (DistilBERT) - **PRIMARY CLASSIFIER**
- **Base Model**: `distilbert-base-uncased`
- **Training Data**: 5,678 personal emails (  email patterns)
- **Categories**: 8 university-specific classes
- **Performance**: ~95% accuracy on validation set
- **Location**: `Model_1/my-final-email-classifier/`
- **🎯 Role**: Runs FIRST to classify every email before any other processing

#### Categories:
1. **Urgent** - Time-sensitive communications
2. **Conference/Academic Events** - Conferences, seminars, workshops  
3. **Job Recruitment** - Job applications, interviews, career opportunities
4. **Promotions/Newsletters** - Marketing emails, newsletters
5. **Administrative/Official Notices** - University administration, official notices
6. **Peer/Group Communications** - Student groups, peer discussions
7. **Other/Miscellaneous** - General communications
8. **Classroom** - Course-related communications

### Model 2: Data Extractor (Llama 3 + LoRA) - **PRIMARY EXTRACTOR**
- **Base Model**: `meta-llama/Meta-Llama-3-8B-Instruct`
- **Fine-tuning**: LoRA (Low-Rank Adaptation) with 4-bit quantization
- **Purpose**: Extract structured data (events, jobs, deadlines) from emails
- **Training**: Supervised fine-tuning on custom email extraction dataset
- **Location**: `Model_2/my-final-llama3-extractor/`
- **🎯 Role**: Handles ALL data extraction tasks instead of Gemini analysis

#### LoRA Configuration:
```python
LoraConfig(
    r=16,                    # Rank
    lora_alpha=32,          # Alpha parameter
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.1,
    task_type="CAUSAL_LM"
)
```

### Model 3: Gemini 1.5 Pro - **ORCHESTRATION & PLANNING**
- **Role**: Planning and tool orchestration (NOT classification/extraction)
- **Input**: Pre-classified category + extracted data from   models
- **Output**: Execution plans, tool selection, workflow coordination
- **Advantage**: Focuses on what it does best while   models handle domain-specific tasks
- **🎯 Role**: Creates execution plans based on   models' analysis

## 🛠️ Available Tools

After email classification and data extraction, the system can perform these automated actions:

- **📅 Calendar Events** - Auto-create calendar events from meeting invites and deadlines
- **📊 Job Tracking** - Add job applications to Google Sheets with structured data
- **🏷️ Smart Labeling** - Apply category-based Gmail labels (AI-Urgent, AI-Jobs, etc.)
- **🔔 Notifications** - Send urgent alerts for time-sensitive emails
- **⏰ Reminders** - Create personal reminders for important deadlines
- **📧 Email Actions** - Mark as read, archive, reply, or forward emails
- **📋 Data Sheets** - Update spreadsheets with extracted information

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+
- CUDA-capable GPU (recommended for Model 2)
- Google Cloud Console project with APIs enabled
- Chrome browser for extension

### 1. Clone & Environment Setup
```bash
git clone <repository-url>
cd IBY
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Google API Configuration
1. **Create Google Cloud Project**
   - Enable Gmail API, Calendar API, Sheets API
   - Create OAuth 2.0 credentials
   - Download as `credentials.json`

2. **Run Authentication Setup**
```bash
python regenerate_credentials.py
```

### 3. Environment Configuration
Create `.env` file:
```env
# Google APIs
GEMINI_API_KEY=your_gemini_api_key_here
EMAIL_CLASSIFIER_MODEL=Model_1/my-final-email-classifier
DATA_EXTRACTOR_MODEL=Model_2/my-final-llama3-extractor

# Gmail Settings
EMAIL_CHECK_INTERVAL=300
MAX_EMAILS_PER_BATCH=10

# Optional: Sheets Integration
JOB_TRACKING_SHEET_ID=your_google_sheet_id_here

# Development
DEBUG=true
LOG_LEVEL=INFO
```

### 4. Start the System
```bash
# Using startup script
python start_agent.py

# Or directly
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Chrome Extension Installation
1. Open Chrome → Extensions → Developer mode
2. Click "Load unpacked" → Select `chrome-extension/` folder
3. Pin the extension for easy access

## 📖 Usage Guide

### Autonomous Email Processing
Once running, the agent automatically:

#### 🔄 **Step 1: Smart Monitoring**
- **Monitors Gmail** every 5 minutes for NEW emails only (since server start)
- **Prevents duplicates** by tracking processed email IDs

#### 🤖 **Step 2:   Trained Models**
- **  DistilBERT** classifies email (trained on   5,678 emails)
- **  Llama 3 + LoRA** extracts structured data if needed
- **95%+ accuracy** because it understands   email patterns

#### 📋 **Step 3: Gemini Orchestration**
- **Gemini plans execution** based on   models' analysis
- **Applies appropriate labels** (AI-Urgent, AI-Jobs, etc.)
- **Executes actions** based on   model's classification:
   - Job emails →   extractor → Add to Google Sheets tracker
   - Events →   extractor → Add to Google Calendar
   - Deadlines →   extractor → Create reminders
   - Urgent → Send notifications
   - Google Classroom → Auto-label with special handling

### Chrome Extension Features
- **📝 Rewrite Email**: Click to rewrite your draft with AI style matching
- **📥 Download Logs**: Export agent processing logs as JSON
- **✨ Style Analysis**: Analyzes your past emails to match writing style

### API Endpoints
- `GET /` - System status and health check
- `GET /agent/status` - Agent status with monitoring details
- `POST /agent/process` - Manually process an email
- `POST /agent/manual-check` - Trigger manual check for NEW emails
- `POST /agent/reset-monitoring` - Reset monitoring to start tracking from now
- `GET /agent/sessions` - View recent processing sessions
- `GET /agent/performance` - Detailed performance statistics
- `POST /api/chrome/analyze-style` - Style analysis for Chrome extension
- `GET /health` - Health check endpoint

## 🔧 Model Training

### Training Email Classifier

1. **Fetch Training Data**:
```bash
cd Model_1
python fetch_emails.py  # Fetches all Gmail emails
```

2. **Label with Gemini AI**:
```bash
python classify_dataset_with_gemini.py  # Auto-labels emails
```

3. **Prepare Training Data**:
```bash
python prepare_data.py  # Converts to training format
```

4. **Train Model**:
```bash
python train_classifier.py  # Fine-tunes DistilBERT
```

5. **Test Inference**:
```bash
python inference.py  # Test the trained model
```

### Training Data Extractor

1. **Prepare Dataset**:
```bash
cd Model_2
# Create extractor_dataset.jsonl with email→JSON examples
```

2. **Train LoRA Adapter**:
```bash
python train_extractor.py  # Fine-tunes Llama 3
```

3. **Test Extraction**:
```bash
python inference_extractor.py  # Test structured extraction
```

## 📊 Performance Metrics

# 🤖 Model Performance

## 🧠 Model 1: DistilBERT Email Classifier

This model acts as a rapid triage agent, sorting incoming emails into predefined categories.

- **Validation Accuracy**: **96.1%**
- **F1-Score**: **0.96** (weighted average)
- **Processing Speed**: Extremely fast, at approximately **0.006 seconds per email**.
- **Advantage**: Fine-tuned on personal email data to accurately recognize specific patterns and categories relevant to university life.

## 📝 Model 2: Llama 3 JSON Extractor

This model acts as a specialist agent, pulling structured information from emails that have been categorized by Model 1.

*For this generative task, accuracy is measured differently to reflect the model's ability to create structured data.*

- **JSON Validity Rate**: **100%**
- **Exact Match Rate**: **26.3%**
- **F1-Score**: **0.69** (Field-Level) (Can be improved further)
- **Advantage**: Fine-tuned to extract information into specific JSON schemas tailored to the user's needs (e.g., academic events, job recruitment).

### System Performance
- **Email Processing Rate**: ~20 emails/minute
- **Memory Usage**: ~2GB (with   models loaded)
- **GPU Usage**: ~3GB VRAM for   Llama 3 inference
- **API Response Time**: <500ms average
- **Smart Monitoring**: Only processes NEW emails (99% reduction in redundant processing)
- **Duplicate Prevention**: 100% accuracy in avoiding reprocessing
- **🎯 Model Efficiency**:   models do 80% of work, Gemini handles 20% (orchestration)
- **💰 Cost Optimization**: Reduced Gemini API calls by using   local models

## 🗂️ Project Structure

```
IBY/
├── 📁 backend/                 # Core system backend
│   ├── 🐍 main.py             # FastAPI server & agent brain with smart monitoring
│   ├── 🐍 tools.py            # Enhanced tool implementations (8 tools)
│   ├── 🐍 models.py           # Data models with monitoring fields
│   └── 🐍 config.py           # Configuration
├── 📁 chrome-extension/        # Chrome extension
│   ├── 🌐 manifest.json       # Extension manifest
│   ├── 🐍 content.js          # Gmail integration
│   ├── 🐍 popup.js            # Extension popup
│   └── 🎨 styles.css          # Modern UI styles
├── 📁 Model_1/                 # Email classifier
│   ├── 🐍 train_classifier.py # Training script
│   ├── 🐍 inference.py        # Inference script
│   └── 📁 my-final-email-classifier/ # Trained model
├── 📁 Model_2/                 # Data extractor  
│   ├── 🐍 train_extractor.py  # LoRA training
│   ├── 🐍 inference_extractor.py # Extraction inference
│   └── 📁 my-final-llama3-extractor/ # LoRA adapter
├── 📁 data/                    # Application data
│   ├── 📄 agent_logs.json     # Processing logs
│   └── 📄 reminders.json      # Reminder storage
├── 🔧 config.json             # System configuration
├── 🔐 credentials.json        # Google API credentials
├── 🎯 requirements.txt        # Python dependencies
├── 🚀 start_agent.py          # System startup script
└── 📖 README.md               # This file
```

## 🔧 Configuration Options

### Email Processing
- `EMAIL_CHECK_INTERVAL`: Seconds between Gmail checks (default: 300)
- `MAX_EMAILS_PER_BATCH`: Max emails per processing batch (default: 10)

### Model Paths
- `EMAIL_CLASSIFIER_MODEL`: Path to classifier model
- `DATA_EXTRACTOR_MODEL`: Path to extractor model

### API Keys
- `GEMINI_API_KEY`: Google Gemini API key for agent brain
- `JOB_TRACKING_SHEET_ID`: Google Sheet for job tracking

## 🛠️ Troubleshooting

### Common Issues

**"Failed to initialize Gmail service"**
- Run `python regenerate_credentials.py`
- Check `credentials.json` exists and is valid
- Verify Gmail API is enabled in Google Cloud Console

**"Model not found" errors**
- Check model paths in `.env` file
- Ensure models are trained and saved correctly
- Verify CUDA availability for GPU models

**Chrome Extension not working**
- Check if backend server is running (port 8000)
- Verify extension is loaded in developer mode
- Check browser console for errors

**High memory usage**
- Consider using CPU-only inference: Set `CUDA_VISIBLE_DEVICES=""`
- Reduce batch sizes in model configs
- Close other GPU-intensive applications

## 🔮 Future Enhancements

- [ ] **Multi-language Support**: Extend to non-English emails
- [ ] **Advanced Scheduling**: Smarter calendar integration  
- [ ] **Team Collaboration**: Multi-user agent sharing
- [ ] **Mobile App**: Native iOS/Android companion
- [ ] **Voice Interface**: Voice commands for email actions
- [ ] **Advanced Analytics**: Email pattern analysis dashboard


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Research** for Gemini AI and BERT architectures
- **Meta** for Llama 3 language model
- **Hugging Face** for Transformers library and model hosting
- **FastAPI** team for the excellent web framework
- **Chrome Extensions** community for development resources

## 📞 Support

For support, questions, or feature requests:
- 📧 Email: [ashwingaikwad53@gmail.com]

---

<div align="center">

**Built with ❤️ for the university community**

Made by Ashwin | 🎓 IIT Goa 

</div>
