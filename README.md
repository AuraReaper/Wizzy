# 🤖 Wizzy Bot - Multimodal AI Telegram Bot

A powerful, feature-rich Telegram bot built with modern AI capabilities, including text conversations, voice processing, image analysis, and document interaction.

## ✨ Features

### 🗣️ **Multimodal Communication**
- **Text Chat**: Natural conversations with memory retention
- **Voice Messages**: Speech-to-text transcription and text-to-speech responses
- **Image Analysis**: AI-powered image description and analysis
- **Document Processing**: Upload and chat with PDF, DOCX, and TXT files

### 🧠 **Advanced AI Capabilities**
- **Google Gemini 1.5 Flash**: Core conversational AI
- **Conversation Memory**: Maintains context across chat sessions
- **Document Understanding**: Extract text and answer questions about uploaded documents
- **Multimodal Processing**: Handle text, images, audio, and documents seamlessly

### 🎯 **Personality**
- **Wizzy Character**: Funny, sarcastic, and engaging personality
- **Context-Aware**: Remembers user preferences and conversation history
- **Dynamic Responses**: Adapts tone and content based on interaction type

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Google AI API Key (for Gemini)
- Groq API Key (for text-to-speech)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/AuraReaper/Wizzy.git
   cd Wizzy
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your API keys
   ```

4. **Run the bot**
   ```bash
   python app.py
   ```

## 🔧 Configuration

### Environment Variables (.env)
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here
REDIS_URL=redis://localhost:6379
WEBHOOK_URL=https://your-domain.com/webhook
PORT=8000
```

### API Keys Setup

1. **Telegram Bot Token**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Create a new bot with `/newbot`
   - Copy the provided token

2. **Google AI API Key**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Enable Gemini API access

3. **Groq API Key**
   - Sign up at [Groq Console](https://console.groq.com/)
   - Generate an API key
   - Copy the key for text-to-speech functionality

## 📚 Usage

### Basic Commands
- Send any text message to start a conversation
- Upload images for AI analysis
- Send voice messages for transcription and voice responses
- Upload documents (PDF, DOCX, TXT) to chat with them

### Document Interaction
1. Upload a supported document (PDF, DOCX, TXT)
2. Wait for processing confirmation
3. Ask questions about the document content
4. Get contextual answers based on the document

### Voice Features
- Send voice messages to get voice responses
- Text messages get text responses
- Mixed conversation modes supported

## 🏗️ Architecture

### Core Components
- **Flask Web Server**: Handles Telegram webhooks
- **LangChain Integration**: Modern memory management
- **Multimodal Processing**: Unified handling of different input types
- **Document Processing**: Text extraction and analysis

### Memory System
- **Conversation Memory**: RunnableWithMessageHistory
- **Document Context**: Per-session document storage
- **Session Management**: Individual memory per chat ID

### Supported File Types
- **PDF**: Text extraction with PyPDF2
- **DOCX**: Microsoft Word document processing
- **TXT**: Plain text file support
- **Images**: JPEG, PNG analysis
- **Audio**: OGG voice message transcription

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t wizzy-bot .
docker run -d --env-file .env -p 8000:8000 wizzy-bot
```

## 🔒 Security Features

- **API Key Protection**: Environment variable configuration
- **Input Validation**: File size and type checking
- **Error Handling**: Graceful failure management
- **GitHub Security**: Automatic secret detection prevention

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
- Application logs show processing status
- Error logs for debugging
- Document processing confirmations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **LangChain**: For the AI framework
- **Google AI**: For Gemini API
- **Groq**: For text-to-speech capabilities
- **Telegram**: For the bot platform

## 📞 Support

For support, please open an issue on GitHub or contact the maintainer.

---

**Made with ❤️ by [AuraReaper](https://github.com/AuraReaper)**
