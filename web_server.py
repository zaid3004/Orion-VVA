"""
Aurora Voice Assistant - Web Server Bridge
Flask server to provide web interface and API endpoints for Aurora
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import threading
import subprocess
import time
from datetime import datetime, timedelta
import logging

# Import authentication and database components
from models import db, User, ChatSession, ChatMessage, init_db, create_tables
from auth import auth_bp, init_auth
from chat_manager import chat_bp

# Import your voice assistant
try:
    from voice_assistant import VoiceAssistant
    VOICE_ASSISTANT_AVAILABLE = True
except ImportError:
    VOICE_ASSISTANT_AVAILABLE = False

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'aurora-voice-assistant-2024-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///orion_vva.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

# Initialize database and authentication
init_db(app)
init_auth(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(chat_bp, url_prefix='/api/chat')

# Global variable to hold the assistant instance
assistant = None
assistant_thread = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebVoiceAssistant:
    """
    Web-compatible wrapper for the voice assistant
    """
    def __init__(self):
        self.conversation_history = []
        self.timers = []
        self.status = {
            'listening': False,
            'connected': True,
            'microphone': 'Ready',
            'ai_status': 'Connected'
        }
        
        # Initialize the voice assistant if available
        if VOICE_ASSISTANT_AVAILABLE:
            try:
                self.assistant = VoiceAssistant()
                logger.info("Voice Assistant initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Voice Assistant: {e}")
                self.assistant = None
        else:
            self.assistant = None
            logger.warning("Voice Assistant module not available")

    def process_command(self, command):
        """Process a voice command and return response"""
        try:
            if self.assistant:
                # First check if it's a built-in command
                intent = self.assistant.recognize_command(command)
                logger.info(f"Command intent recognized: {intent}")
                
                # If it's a built-in command, use the voice assistant's proper handling
                if intent in self.assistant.built_in_domains:
                    logger.info(f"Processing built-in command: {intent}")
                    responses = []
                    original_speak = self.assistant.speak
                    
                    def capture_speak(text, log_message=True):
                        responses.append(text)
                        if log_message:
                            logger.info(f"Orion: {text}")
                    
                    self.assistant.speak = capture_speak
                    
                    try:
                        self.assistant.execute_command(intent, command)
                        response = responses[0] if responses else "Command processed"
                    finally:
                        self.assistant.speak = original_speak
                    
                    return {
                        'success': True,
                        'message': response,
                        'intent': intent
                    }
                
                # For unknown/complex queries, send to GROQ
                elif intent == 'unknown':
                    logger.info(f"Sending unknown query to GROQ: {command}")
                    try:
                        groq_response = self.assistant.groq_handler.get_response(command)
                        return {
                            'success': True,
                            'message': groq_response,
                            'intent': 'ai_response'
                        }
                    except Exception as groq_error:
                        logger.error(f"GROQ processing failed: {groq_error}")
                        return {
                            'success': False,
                            'message': "I'm having trouble processing that request right now. Please try again.",
                            'intent': 'error'
                        }
                else:
                    # Shouldn't happen, but handle gracefully
                    logger.warning(f"Unhandled intent: {intent}")
                    return self._process_local_command(command)
            else:
                # Fallback to local processing
                return self._process_local_command(command)
                
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return {
                'success': False,
                'message': f"Sorry, I encountered an error: {str(e)}",
                'intent': 'error'
            }

    def _process_local_command(self, command):
        """Local fallback command processing"""
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
                'message': f"{greeting}, Commander! I am Orion, your strategic voice assistant. What are your orders?",
                'intent': 'greeting'
            }
        
        if 'help' in cmd:
            return {
                'success': True,
                'message': "I stand ready to assist with strategic operations, time queries, weather reconnaissance, mission timers, tactical calculations, system monitoring, and comprehensive analysis. What is your mission, Commander?",
                'intent': 'help'
            }
        
        # Math calculations
        if any(word in cmd for word in ['calculate', 'math', 'plus', 'minus', 'times', 'divide']):
            try:
                # Simple math extraction and evaluation
                import re
                # Extract numbers and operators
                math_expr = re.sub(r'[^\d+\-*/().\s]', '', cmd.replace('plus', '+').replace('minus', '-').replace('times', '*').replace('divide', '/'))
                if math_expr.strip():
                    result = eval(math_expr.strip())
                    return {
                        'success': True,
                        'message': f"The result is {result}",
                        'intent': 'calculate'
                    }
            except:
                pass
        
        return {
            'success': True,
            'message': "Command received and understood, Commander. However, this requires the full Orion system capabilities. The desktop version offers more advanced tactical options.",
            'intent': 'unknown'
        }

    def get_status(self):
        """Get current system status"""
        return {
            'microphone': self.status['microphone'],
            'ai_status': self.status['ai_status'],
            'timer_count': len(self.timers),
            'backend_connected': self.assistant is not None
        }

# Initialize the web assistant
web_assistant = WebVoiceAssistant()

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('.', filename)

@app.route('/api/process-command', methods=['POST'])
def process_command():
    """API endpoint to process voice commands"""
    try:
        data = request.get_json()
        command = data.get('command', '').strip()
        
        if not command:
            return jsonify({
                'success': False,
                'message': 'No command provided'
            }), 400
        
        logger.info(f"Processing command: {command}")
        
        # Process the command
        response = web_assistant.process_command(command)
        
        # Store in conversation history
        web_assistant.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'user_command': command,
            'orion_response': response['message'],
            'intent': response.get('intent', 'unknown')
        })
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in process_command: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@app.route('/api/status')
def get_status():
    """Get system status"""
    return jsonify(web_assistant.get_status())

@app.route('/api/history')
def get_history():
    """Get conversation history"""
    return jsonify({
        'history': web_assistant.conversation_history[-50:]  # Last 50 entries
    })

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    """Clear conversation history"""
    web_assistant.conversation_history.clear()
    return jsonify({'success': True, 'message': 'History cleared'})

@app.route('/api/timers')
def get_timers():
    """Get active timers"""
    if web_assistant.assistant and hasattr(web_assistant.assistant, 'timer_manager'):
        try:
            timers = web_assistant.assistant.timer_manager.list_timers()
            return jsonify({'timers': timers})
        except Exception as e:
            logger.error(f"Error getting timers: {e}")
    
    return jsonify({'timers': []})

@app.route('/api/system-info')
def get_system_info():
    """Get system information for the system panel"""
    try:
        # Get system information if voice assistant is available
        system_data = {
            'audio_status': 'Ready',
            'ai_status': 'Online',
            'memory_usage': '--',
            'cpu_usage': '--',
            'battery_status': '--',
            'network_status': 'Connected'
        }
        
        if web_assistant.assistant and hasattr(web_assistant.assistant, 'get_system_info'):
            try:
                system_data.update(web_assistant.assistant.get_system_info())
            except Exception as e:
                logger.error(f"Error getting system info from assistant: {e}")
        
        # Add basic system info using psutil if available
        try:
            import psutil
            system_data.update({
                'memory_usage': f"{psutil.virtual_memory().percent:.1f}%",
                'cpu_usage': f"{psutil.cpu_percent(interval=1):.1f}%",
            })
            
            # Battery info if available
            battery = psutil.sensors_battery()
            if battery:
                system_data['battery_status'] = f"{battery.percent:.1f}%"
                
        except ImportError:
            logger.warning("psutil not available for system monitoring")
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            
        return jsonify(system_data)
        
    except Exception as e:
        logger.error(f"Error in get_system_info: {e}")
        return jsonify({
            'audio_status': 'Error',
            'ai_status': 'Error', 
            'memory_usage': '--',
            'cpu_usage': '--',
            'battery_status': '--',
            'network_status': '--'
        }), 500

@app.route('/api/chat/history')
def get_chat_history():
    """Get conversation history from database"""
    try:
        # For now, return the in-memory conversation history
        # TODO: Implement database storage with user association
        messages = []
        for entry in web_assistant.conversation_history[-20:]:  # Last 20 messages
            messages.extend([
                {
                    'sender': 'user',
                    'content': entry.get('user_command', ''),
                    'timestamp': entry.get('timestamp', '')
                },
                {
                    'sender': 'orion',
                    'content': entry.get('orion_response', ''),
                    'timestamp': entry.get('timestamp', '')
                }
            ])
            
        return jsonify({
            'success': True,
            'messages': messages
        })
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({
            'success': False,
            'messages': []
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'voice_assistant_available': VOICE_ASSISTANT_AVAILABLE,
        'backend_connected': web_assistant.assistant is not None
    })

if __name__ == '__main__':
    print("🚀 Starting Orion Voice Assistant Web Server...")
    print("🌟 Orion will be available at: http://localhost:5000")
    print("📱 Open this URL in your browser to use the web interface")
    
    # Create database tables
    with app.app_context():
        try:
            create_tables(app)
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"⚠️  Database initialization error: {e}")
    
    if not VOICE_ASSISTANT_AVAILABLE:
        print("⚠️  Voice Assistant backend not found - using local fallback mode")
    else:
        print("✅ Voice Assistant backend connected successfully")
    
    print("\n" + "="*60)
    print("🎙️  Orion Voice Assistant Web Interface with User Accounts")
    print("="*60)
    
    # Run the Flask app
    try:
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True,
            use_reloader=False  # Prevent double initialization
        )
    except KeyboardInterrupt:
        print("\n👋 Orion web server shutting down...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
