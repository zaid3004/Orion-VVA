"""
Orion Voice Assistant - Vercel Deployment Entry Point
Serverless Flask app optimized for Vercel deployment
"""

import os
import sys
import json
from datetime import datetime, timedelta
import logging

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, send_from_directory

# Configure app for Vercel
app = Flask(__name__, 
           static_folder='../static', 
           template_folder='../templates')

# Configuration for production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'orion-voice-assistant-2024-production-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///orion_vva.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database not available in serverless - using in-memory storage
DATABASE_AVAILABLE = False

# Simple in-memory user storage (for demo purposes)
USERS_STORAGE = {
    'demo': {
        'username': 'demo',
        'email': 'demo@orion.ai',
        'password': 'demo123',  # In production, this would be hashed
        'full_name': 'Demo User'
    }
}

CHAT_HISTORY = []

# Try to import GROQ for AI responses
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Groq not available in serverless: {e}")
    GROQ_AVAILABLE = False

# Try to import voice assistant (may not work in serverless environment)
try:
    from voice_assistant import VoiceAssistant
    VOICE_ASSISTANT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Voice Assistant not available in serverless: {e}")
    VOICE_ASSISTANT_AVAILABLE = False

# Database not available in serverless environment
logger.info("Running in serverless mode without persistent database")

class GroqHandler:
    """Simplified GROQ handler for serverless deployment"""
    def __init__(self):
        self.client = None
        self.available = False
        
        if GROQ_AVAILABLE:
            api_key = os.environ.get('GROQ_API_KEY')
            if api_key:
                try:
                    self.client = Groq(api_key=api_key)
                    self.available = True
                    logger.info("GROQ initialized for serverless deployment")
                except Exception as e:
                    logger.error(f"Failed to initialize GROQ: {e}")
            else:
                logger.warning("GROQ_API_KEY not found in environment")
    
    def get_response(self, query):
        """Get AI response from GROQ"""
        if not self.available:
            return "AI assistant is not available in this serverless environment."
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are Orion, a commanding and strategic voice assistant with the authority of a military commander. Address users as 'Commander' and provide clear, decisive responses suitable for text-to-speech. Be helpful, knowledgeable, and maintain a tone of respectful authority."},
                    {"role": "user", "content": query}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"GROQ API error: {e}")
            return "I'm having trouble accessing my AI capabilities right now, Commander."

class WebVoiceAssistant:
    """
    Simplified web-compatible voice assistant for serverless deployment
    """
    def __init__(self):
        self.conversation_history = []
        self.groq_handler = GroqHandler()
        self.status = {
            'listening': False,
            'connected': True,
            'microphone': 'Ready',
            'ai_status': 'Connected (Serverless)'
        }

    def process_command(self, command):
        """Process a voice command with fallback for serverless environment"""
        try:
            # First try local command processing
            local_result = self._process_local_command(command)
            
            # If it's an unknown command, try GROQ
            if local_result['intent'] == 'unknown' and self.groq_handler.available:
                logger.info(f"Sending to GROQ: {command}")
                groq_response = self.groq_handler.get_response(command)
                return {
                    'success': True,
                    'message': groq_response,
                    'intent': 'ai_response'
                }
            
            return local_result
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return {
                'success': False,
                'message': f"Sorry, I encountered an error: {str(e)}",
                'intent': 'error'
            }

    def _process_local_command(self, command):
        """Local command processing optimized for serverless"""
        cmd = command.lower()
        
        if any(word in cmd for word in ['time', 'clock']):
            current_time = datetime.now().strftime("%I:%M %p")
            return {
                'success': True,
                'message': f"The current time is {current_time}",
                'intent': 'time'
            }
        
        if any(word in cmd for word in ['date', 'today']):
            current_date = datetime.now().strftime("%A, %B %d, %Y")
            return {
                'success': True,
                'message': f"Today is {current_date}",
                'intent': 'date'
            }
        
        if any(word in cmd for word in ['hello', 'hi', 'hey']):
            hour = datetime.now().hour
            if hour < 12:
                greeting = "Good morning"
            elif hour < 17:
                greeting = "Good afternoon"
            else:
                greeting = "Good evening"
            
            return {
                'success': True,
                'message': f"{greeting}, Commander! I am Orion, your strategic voice assistant. How can I assist you today?",
                'intent': 'greeting'
            }
        
        if 'help' in cmd:
            return {
                'success': True,
                'message': "I can help you with time, date, basic calculations, and more. Note: This is the web version of Orion with limited capabilities.",
                'intent': 'help'
            }
        
        # Basic math calculations
        if any(word in cmd for word in ['calculate', 'math', 'plus', 'minus', 'times', 'divide']):
            try:
                import re
                math_expr = re.sub(r'[^\\d+\\-*/().\\s]', '', cmd.replace('plus', '+').replace('minus', '-').replace('times', '*').replace('divide', '/'))
                if math_expr.strip():
                    result = eval(math_expr.strip())
                    return {
                        'success': True,
                        'message': f"The calculation result is {result}",
                        'intent': 'calculate'
                    }
            except:
                pass
        
        return {
            'success': True,
            'message': "I understand your command, Commander. This is the serverless version of Orion with limited capabilities. The full desktop version offers more advanced features.",
            'intent': 'unknown'
        }

    def get_status(self):
        """Get current system status"""
        return {
            'microphone': self.status['microphone'],
            'ai_status': self.status['ai_status'],
            'timer_count': 0,
            'backend_connected': True,
            'serverless': True
        }

# Initialize the web assistant
web_assistant = WebVoiceAssistant()

@app.route('/')
def index():
    """Serve the main page"""
    try:
        return render_template('index.html')
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Orion Voice Assistant</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .error {{ color: #ff6b6b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Orion Voice Assistant</h1>
                <p>Welcome to the serverless version of Orion!</p>
                <div class="error">
                    <p>Template not found. This is a minimal version running on Vercel.</p>
                    <p>API endpoints are available at:</p>
                    <ul style="text-align: left;">
                        <li>POST /api/process-command</li>
                        <li>GET /api/status</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """

@app.route('/api/process-command', methods=['POST'])
def process_command():
    """Process voice commands"""
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({'error': 'No command provided'}), 400
        
        command = data['command']
        logger.info(f"Processing command: {command}")
        
        result = web_assistant.process_command(command)
        
        return jsonify({
            'success': result['success'],
            'message': result['message'],  # Changed from 'response' to 'message' to match frontend
            'intent': result['intent'],
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in process_command: {e}")
        return jsonify({
            'success': False,
            'response': f"Commander, I encountered an error: {str(e)}",
            'intent': 'error'
        }), 500

@app.route('/api/status')
def get_status():
    """Get system status"""
    try:
        status = web_assistant.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Orion Voice Assistant',
        'version': '1.0.0',
        'environment': 'serverless'
    })

# For static files
@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    try:
        if filename.endswith('.js'):
            return send_from_directory('../static', filename, mimetype='application/javascript')
        elif filename.endswith('.css'):
            return send_from_directory('../static', filename, mimetype='text/css')
        else:
            return send_from_directory('../static', filename)
    except Exception as e:
        return jsonify({'error': f'File not found: {filename}'}), 404

# Simple authentication endpoints for serverless
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Simple login for serverless demo"""
    try:
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
        
        # Check against demo user
        if username == 'demo' and password == 'demo123':
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'username': 'demo',
                    'email': 'demo@orion.ai',
                    'full_name': 'Demo User'
                },
                'session_token': 'demo_session_token'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials. Use username: demo, password: demo123'
            }), 401
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Login failed'
        }), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Simple registration for serverless demo"""
    return jsonify({
        'success': False,
        'message': 'Registration not available in demo mode. Use username: demo, password: demo123'
    }), 400

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Simple logout for serverless demo"""
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })

# Export the Flask app for Vercel
app = app

if __name__ == '__main__':
    # This won't be used in Vercel but useful for local testing
    app.run(debug=False, host='0.0.0.0', port=5000)