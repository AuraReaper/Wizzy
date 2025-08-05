import os
import io
import logging
import requests
import base64
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Document processing imports
import PyPDF2
from docx import Document
import tempfile

import redis
from flask import Flask, request, jsonify
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WizzyBot:
    def __init__(self):
        # Initialize credentials (set these as environment variables)
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

        # Initialize services
        self.bot = Bot(token=self.telegram_token)
        self.redis_client = redis.from_url(self.redis_url)

        # Initialize LLM models
        self.chat_model = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=self.google_api_key,
            temperature=0.7
        )

        # Use requests for direct API calls instead of deprecated GoogleGenerativeAI
        self.gemini_api_base = "https://generativelanguage.googleapis.com/v1beta"

        # Memory storage for conversations
        self.chat_histories = {}
        
        # Document storage for sessions
        self.document_contexts = {}
        
        # Create the chat prompt template with memory
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_message}"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Create the chain with memory
        self.chain = self.prompt | self.chat_model
        
        # Create the chain with message history
        self.chain_with_history = RunnableWithMessageHistory(
            self.chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    def get_session_history(self, session_id: str) -> ChatMessageHistory:
        """Get or create chat message history for a session"""
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = ChatMessageHistory()
            logger.info(f"Created conversation history for session {session_id}")
        return self.chat_histories[session_id]

    def create_system_message(self, user_name: str, chat_id: str = None) -> str:
        """Create dynamic system message with optional document context"""
        current_time = datetime.now().isoformat()
        base_message = f"""You are a helpful assistant called Wizzy.
Respond in a natural funny tone.
Be sarcastic when required.
Don't give very long messages.

You are currently talking to {user_name}.

The current date and time is {current_time}"""
        
        # Add document context if available
        if chat_id and chat_id in self.document_contexts:
            doc_info = self.document_contexts[chat_id]
            base_message += f"""

## Document Context Available:
The user has uploaded a document: {doc_info['filename']}
You can reference and answer questions about this document.
Document summary: {doc_info.get('summary', 'Content available for discussion')}"""
        
        return base_message

    def download_telegram_file(self, file_id: str) -> bytes:
        """Download file from Telegram"""
        try:
            # Use direct HTTP request to get file info to avoid async issues
            url = f"https://api.telegram.org/bot{self.telegram_token}/getFile"
            data = {'file_id': file_id}
            response = requests.post(url, json=data)
            response.raise_for_status()
            
            file_info = response.json()['result']['file_path']
            
            # Download the actual file
            file_url = f"https://api.telegram.org/file/bot{self.telegram_token}/{file_info}"
            file_response = requests.get(file_url)
            file_response.raise_for_status()
            return file_response.content
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise

    def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using Google Gemini API directly"""
        try:
            # Convert audio to base64
            audio_b64 = base64.b64encode(audio_data).decode()

            url = f"{self.gemini_api_base}/models/gemini-1.5-flash:generateContent"

            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Please transcribe this audio:"},
                        {
                            "inline_data": {
                                "mime_type": "audio/ogg",
                                "data": audio_b64
                            }
                        }
                    ]
                }]
            }

            headers = {"Content-Type": "application/json"}

            response = requests.post(
                f"{url}?key={self.google_api_key}",
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return "Sorry, I couldn't transcribe the audio."

    def analyze_image(self, image_data: bytes, caption: Optional[str] = None) -> str:
        """Analyze image using Google Gemini Vision API directly"""
        try:
            # Convert image to base64
            image_b64 = base64.b64encode(image_data).decode()

            prompt = caption if caption else "Describe this image in detail."

            url = f"{self.gemini_api_base}/models/gemini-1.5-flash:generateContent"

            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_b64
                            }
                        }
                    ]
                }]
            }

            headers = {"Content-Type": "application/json"}

            response = requests.post(
                f"{url}?key={self.google_api_key}",
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()

        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return "Sorry, I couldn't analyze the image."

    def generate_speech(self, text: str) -> bytes:
        """Generate speech using Groq TTS API"""
        try:
            url = "https://api.groq.com/openai/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "playai-tts",
                "input": text,
                "voice": "Celeste-PlayAI",
                "response_format": "mp3"
            }

            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            return None

    def extract_text_from_pdf(self, pdf_data: bytes) -> str:
        """Extract text from PDF document"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(pdf_data)
                temp_file.flush()
                
                with open(temp_file.name, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                
                os.unlink(temp_file.name)  # Clean up temp file
                return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""

    def extract_text_from_docx(self, docx_data: bytes) -> str:
        """Extract text from DOCX document"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(docx_data)
                temp_file.flush()
                
                doc = Document(temp_file.name)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                
                os.unlink(temp_file.name)  # Clean up temp file
                return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            return ""

    def extract_text_from_txt(self, txt_data: bytes) -> str:
        """Extract text from TXT document"""
        try:
            return txt_data.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            logger.error(f"Error extracting text from TXT: {e}")
            return ""

    def process_document(self, document_data: bytes, filename: str, chat_id: str) -> str:
        """Process uploaded document and extract text"""
        try:
            file_extension = Path(filename).suffix.lower()
            
            if file_extension == '.pdf':
                text = self.extract_text_from_pdf(document_data)
            elif file_extension == '.docx':
                text = self.extract_text_from_docx(document_data)
            elif file_extension == '.txt':
                text = self.extract_text_from_txt(document_data)
            else:
                return f"Unsupported document format: {file_extension}. I support PDF, DOCX, and TXT files."
            
            if not text:
                return f"Sorry, I couldn't extract any text from {filename}. The document might be empty or corrupted."
            
            # Generate a summary of the document
            summary_prompt = f"Please provide a brief summary (2-3 sentences) of this document:\n\n{text[:2000]}..."
            
            try:
                summary_response = self.chat_model.invoke([HumanMessage(content=summary_prompt)])
                summary = summary_response.content
            except:
                summary = f"Document with {len(text.split())} words uploaded."
            
            # Store document context
            self.document_contexts[chat_id] = {
                'filename': filename,
                'content': text,
                'summary': summary,
                'uploaded_at': datetime.now().isoformat()
            }
            
            logger.info(f"Document {filename} processed for chat {chat_id}")
            
            return f"📄 Great! I've processed your document '{filename}' and I'm ready to answer questions about it!\n\n📝 **Summary:** {summary}\n\nJust ask me anything about the document!"
        
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return f"Sorry, I encountered an error processing {filename}. Please try uploading it again."

    def process_document_message(self, message_data: Dict[str, Any]) -> str:
        """Process document message"""
        try:
            document = message_data['document']
            file_id = document['file_id']
            filename = document.get('file_name', 'unknown_document')
            
            # Check file size (Telegram API has limits)
            file_size = document.get('file_size', 0)
            if file_size > 20 * 1024 * 1024:  # 20MB limit
                return "Sorry, the document is too large. Please upload files smaller than 20MB."
            
            # Download document
            document_data = self.download_telegram_file(file_id)
            
            # Process the document
            chat_id = str(message_data['chat']['id'])
            return self.process_document(document_data, filename, chat_id)
            
        except Exception as e:
            logger.error(f"Error processing document message: {e}")
            return "Sorry, I couldn't process your document. Please try again."

    def process_text_message(self, message_data: Dict[str, Any]) -> str:
        """Process text message through AI agent with memory"""
        try:
            chat_id = str(message_data['chat']['id'])
            user_name = message_data['from']['first_name'].split(' ')[0]
            text = message_data['text']

            # Create system message with context (including document context if available)
            system_message = self.create_system_message(user_name, chat_id)

            # Generate response using chain with memory
            response = self.chain_with_history.invoke(
                {
                    "input": text,
                    "system_message": system_message
                },
                config={"configurable": {"session_id": chat_id}}
            )

            return response.content

        except Exception as e:
            logger.error(f"Error processing text message: {e}")
            return "Sorry, I encountered an error processing your message."

    def process_audio_message(self, message_data: Dict[str, Any]) -> str:
        """Process voice message"""
        try:
            voice_file_id = message_data['voice']['file_id']

            # Download and transcribe audio
            audio_data = self.download_telegram_file(voice_file_id)
            transcribed_text = self.transcribe_audio(audio_data)

            # Create fake text message for processing
            fake_message = message_data.copy()
            fake_message['text'] = transcribed_text

            return self.process_text_message(fake_message)

        except Exception as e:
            logger.error(f"Error processing audio message: {e}")
            return "Sorry, I couldn't process your voice message."

    def process_image_message(self, message_data: Dict[str, Any]) -> str:
        """Process image message"""
        try:
            # Get the highest resolution photo
            photos = message_data['photo']
            largest_photo = max(photos, key=lambda x: x['file_size'])
            photo_file_id = largest_photo['file_id']

            # Download image
            image_data = self.download_telegram_file(photo_file_id)

            # Analyze image
            caption = message_data.get('caption', 'Describe this image in detail.')
            image_description = self.analyze_image(image_data, caption)

            # Create enhanced prompt
            enhanced_prompt = f"""# The user provided the following image and text.

## Image Description:
{image_description}

## User Message:
{caption}"""

            # Process as text message
            fake_message = message_data.copy()
            fake_message['text'] = enhanced_prompt

            return self.process_text_message(fake_message)

        except Exception as e:
            logger.error(f"Error processing image message: {e}")
            return "Sorry, I couldn't process your image."

    def should_respond_with_audio(self, message_data: Dict[str, Any]) -> bool:
        """Check if original message was voice to respond with voice"""
        return 'voice' in message_data

    def send_text_response(self, chat_id: int, text: str):
        """Send text response to Telegram"""
        try:
            # Use requests for synchronous HTTP call to avoid async issues
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text
            }
            response = requests.post(url, json=data)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error sending text message: {e}")

    def send_audio_response(self, chat_id: int, text: str):
        """Send audio response to Telegram"""
        try:
            audio_data = self.generate_speech(text)
            if audio_data:
                # Use requests for synchronous HTTP call to avoid async issues
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendAudio"
                files = {'audio': ('response.mp3', io.BytesIO(audio_data), 'audio/mpeg')}
                data = {'chat_id': chat_id}
                response = requests.post(url, files=files, data=data)
                response.raise_for_status()
            else:
                # Fallback to text if TTS fails
                self.send_text_response(chat_id, text)
        except Exception as e:
            logger.error(f"Error sending audio message: {e}")
            # Fallback to text
            self.send_text_response(chat_id, text)

    def process_webhook(self, update_data: Dict[str, Any]):
        """Main webhook processing function"""
        try:
            message = update_data.get('message', {})
            chat_id = message.get('chat', {}).get('id')

            if not chat_id:
                return

            # Determine message type and process accordingly
            if 'voice' in message:
                # Audio message
                response_text = self.process_audio_message(message)
                self.send_audio_response(chat_id, response_text)

            elif 'photo' in message:
                # Image message
                response_text = self.process_image_message(message)
                self.send_text_response(chat_id, response_text)
            
            elif 'document' in message:
                # Document message
                response_text = self.process_document_message(message)
                self.send_text_response(chat_id, response_text)

            elif 'text' in message:
                # Text message
                response_text = self.process_text_message(message)

                # Check if we should respond with audio (if original was voice)
                if self.should_respond_with_audio(message):
                    self.send_audio_response(chat_id, response_text)
                else:
                    self.send_text_response(chat_id, response_text)

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            if chat_id:
                self.send_text_response(chat_id, "Sorry, I encountered an error.")

# Flask app setup
app = Flask(__name__)
wizzy = WizzyBot()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint"""
    try:
        update_data = request.get_json()
        wizzy.process_webhook(update_data)
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Wizzy Bot'})

if __name__ == '__main__':
    # Set up webhook URL with your domain
    webhook_url = os.getenv('WEBHOOK_URL', 'https://your-domain.com/webhook')

    try:
        # Set webhook using requests to avoid async issues
        url = f"https://api.telegram.org/bot{wizzy.telegram_token}/setWebhook"
        data = {'url': webhook_url}
        response = requests.post(url, json=data)
        response.raise_for_status()
        logger.info(f"Webhook set to: {webhook_url}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

    # Run Flask app
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
