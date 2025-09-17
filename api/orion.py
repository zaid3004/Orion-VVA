#!/usr/bin/env python3
"""
Orion Voice Assistant - MongoDB-Integrated Serverless API
Complete serverless Flask app with MongoDB Atlas integration
"""

import os
import sys
import json
from datetime import datetime, timedelta
import logging
import time

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available in serverless environment

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, send_from_directory

# Configure app for Vercel
app = Flask(__name__, 
           static_folder='../static', 
           template_folder='../templates')

# Configuration for production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'orion-voice-assistant-2024-production-key')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import MongoDB models and authentication
try:
    from mongo_models import init_mongo_db, get_mongo_models
    from mongo_auth import init_mongo_auth, create_auth_blueprint, require_auth, get_current_user
    MONGODB_AVAILABLE = True
    logger.info("✅ MongoDB modules imported successfully")
except ImportError as e:
    logger.error(f"❌ MongoDB modules not available: {e}")
    MONGODB_AVAILABLE = False

# Try to import GROQ for AI responses
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Groq not available in serverless: {e}")
    GROQ_AVAILABLE = False

# Initialize MongoDB connection
mongo_models = None
if MONGODB_AVAILABLE:
    mongodb_uri = os.environ.get('MONGODB_URI')
    if mongodb_uri:
        try:
            if init_mongo_db(mongodb_uri):
                mongo_models = get_mongo_models()
                init_mongo_auth(mongo_models)
                auth_bp = create_auth_blueprint()
                app.register_blueprint(auth_bp, url_prefix='/api/auth')
                logger.info("🔗 MongoDB connected and authentication initialized")
            else:
                logger.error("❌ Failed to connect to MongoDB")
                MONGODB_AVAILABLE = False
        except Exception as e:
            logger.error(f"❌ MongoDB initialization failed: {e}")
            MONGODB_AVAILABLE = False
    else:
        logger.warning("⚠️  MONGODB_URI environment variable not set")
        MONGODB_AVAILABLE = False

class GroqHandler:
    """GROQ AI handler for serverless deployment"""
    def __init__(self):
        self.client = None
        self.available = False
        
        if GROQ_AVAILABLE:
            api_key = os.environ.get('GROQ_API_KEY')
            if api_key:
                try:
                    # Initialize GROQ client with just the API key
                    self.client = Groq(api_key=api_key)
                    # Test the connection with a simple request
                    test_response = self.client.chat.completions.create(
                        messages=[{"role": "user", "content": "test"}],
                        model="llama-3.3-70b-versatile",
                        max_tokens=1
                    )
                    self.available = True
                    logger.info("✅ GROQ initialized and tested successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize or test GROQ: {e}")
                    # Try with different initialization
                    try:
                        import groq
                        self.client = groq.Groq(api_key=api_key)
                        self.available = True
                        logger.info("✅ GROQ initialized with alternate method")
                    except Exception as e2:
                        logger.error(f"❌ Alternate GROQ initialization failed: {e2}")
            else:
                logger.warning("⚠️  GROQ_API_KEY not found in environment")
    
    def get_response(self, query, user_context=None):
        """Get AI response from GROQ"""
        if not self.available:
            return "AI assistant is not available in this environment, Commander."
        
        try:
            system_message = (
                "You are Orion, a commanding and strategic voice assistant with the authority of a military commander. "
                "Address users as 'Commander' and provide clear, decisive responses suitable for text-to-speech. "
                "Be helpful, knowledgeable, and maintain a tone of respectful authority and strategic thinking."
            )
            
            if user_context:
                system_message += f" User context: {user_context}"
            
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": query}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"GROQ API error: {e}")
            return "I'm having trouble accessing my AI capabilities right now, Commander. Please try again."

class OrionVoiceAssistant:
    """MongoDB-integrated voice assistant for serverless deployment"""
    
    def __init__(self):
        self.groq_handler = GroqHandler()
        self.status = {
            'listening': False,
            'connected': True,
            'microphone': 'Ready',
            'ai_status': 'Connected (MongoDB + Serverless)',
            'database_status': 'Connected' if MONGODB_AVAILABLE else 'Local Mode'
        }

    def process_command(self, command, user_id=None):
        """Process a voice command with MongoDB integration"""
        start_time = time.time()
        
        try:
            # First try local command processing
            local_result = self._process_local_command(command)
            
            # If it's an unknown command and we have GROQ, use AI
            if local_result['intent'] == 'unknown' and self.groq_handler.available:
                logger.info(f"🤖 Sending to GROQ: {command}")
                
                # Get user context if available
                user_context = None
                if MONGODB_AVAILABLE and mongo_models and user_id:
                    try:
                        user = mongo_models['users'].get_user_by_id(user_id)
                        if user:
                            user_context = f"Username: {user['username']}, Preferences: {user.get('theme_preference', 'aurora')}"
                    except Exception as e:
                        logger.warning(f"Failed to get user context: {e}")
                
                groq_response = self.groq_handler.get_response(command, user_context)
                processing_time = time.time() - start_time
                
                # Store message in database if available
                if MONGODB_AVAILABLE and mongo_models and user_id:
                    try:
                        # Get or create default session
                        sessions = mongo_models['chat_sessions'].get_user_sessions(user_id, limit=1)
                        if sessions:
                            session_id = sessions[0]['id']
                        else:
                            # Create default session
                            session = mongo_models['chat_sessions'].create_session(
                                user_id=user_id,
                                title="General Chat",
                                description="Default chat session"
                            )
                            session_id = session['id'] if session else None
                        
                        if session_id:
                            # Store user message
                            mongo_models['chat_messages'].create_message(
                                session_id=session_id,
                                sender='user',
                                content=command,
                                intent='ai_query',
                                processing_time=processing_time
                            )
                            
                            # Store Orion response
                            mongo_models['chat_messages'].create_message(
                                session_id=session_id,
                                sender='orion',
                                content=groq_response,
                                intent='ai_response',
                                groq_used=True,
                                processing_time=processing_time
                            )
                            
                    except Exception as e:
                        logger.error(f"Failed to store chat message: {e}")
                
                return {
                    'success': True,
                    'message': groq_response,
                    'intent': 'ai_response',
                    'processing_time': processing_time,
                    'groq_used': True
                }
            
            return local_result
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return {
                'success': False,
                'message': f"Sorry Commander, I encountered an error: {str(e)}",
                'intent': 'error'
            }

    def _process_local_command(self, command):
        """Local command processing for basic functions"""
        cmd = command.lower()
        
        # Check for timer commands first
        if any(word in cmd for word in ['timer', 'countdown', 'remind']) and any(word in cmd for word in ['set', 'create', 'start']):
            return {
                'success': True,
                'message': "Timer functionality is available in the full Orion system, Commander. This web version has limited capabilities.",
                'intent': 'timer_info'
            }
        
        if any(word in cmd for word in ['time', 'clock']) and 'timer' not in cmd:
            current_time = datetime.now().strftime("%I:%M %p")
            return {
                'success': True,
                'message': f"The current time is {current_time}, Commander.",
                'intent': 'time'
            }
        
        if any(word in cmd for word in ['date', 'today']):
            current_date = datetime.now().strftime("%A, %B %d, %Y")
            return {
                'success': True,
                'message': f"Today is {current_date}, Commander.",
                'intent': 'date'
            }
        
        if any(word in cmd for word in ['hello', 'hi', 'hey', 'greeting']):
            hour = datetime.now().hour
            if hour < 12:
                greeting = "Good morning"
            elif hour < 17:
                greeting = "Good afternoon"
            else:
                greeting = "Good evening"
            
            return {
                'success': True,
                'message': f"{greeting}, Commander! I am Orion, your strategic voice assistant. How may I assist you with your mission today?",
                'intent': 'greeting'
            }
        
        if 'help' in cmd or 'commands' in cmd:
            return {
                'success': True,
                'message': "I stand ready to assist with strategic operations, time queries, calculations, weather reconnaissance, and comprehensive analysis. I can also engage in tactical conversations and provide intelligence briefings. What is your mission, Commander?",
                'intent': 'help'
            }
        
        # Basic math calculations
        if any(word in cmd for word in ['calculate', 'math', 'plus', 'minus', 'times', 'divide', 'what is']):
            try:
                import re
                # Extract mathematical expressions
                math_expr = re.sub(r'[^\\d+\\-*/().\\s]', '', cmd.replace('plus', '+').replace('minus', '-').replace('times', '*').replace('divide', '/').replace('what is', ''))
                if math_expr.strip() and any(op in math_expr for op in ['+', '-', '*', '/']):
                    result = eval(math_expr.strip())
                    return {
                        'success': True,
                        'message': f"The tactical calculation result is {result}, Commander.",
                        'intent': 'calculate'
                    }
            except:
                pass
        
        return {
            'success': True,
            'message': "Command received and processed, Commander. For advanced tactical operations and full system capabilities, I recommend the desktop version of Orion.",
            'intent': 'unknown'
        }

    def get_status(self):
        """Get current system status"""
        return self.status

# Initialize the Orion assistant
orion_assistant = OrionVoiceAssistant()

# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/')
def index():
    """Serve the main page"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Template error: {e}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>🤖 Orion Voice Assistant</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: 'Segoe UI', system-ui, sans-serif; 
                    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
                    color: #f8fafc;
                    text-align: center; 
                    padding: 2rem;
                    min-height: 100vh;
                    margin: 0;
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background: rgba(30, 41, 59, 0.8);
                    padding: 2rem;
                    border-radius: 16px;
                    backdrop-filter: blur(10px);
                }}
                h1 {{ color: #60a5fa; margin-bottom: 1rem; }}
                .status {{ color: #10b981; margin: 1rem 0; }}
                .error {{ color: #ef4444; }}
                .feature {{ 
                    background: rgba(59, 130, 246, 0.1);
                    padding: 1rem;
                    margin: 1rem 0;
                    border-radius: 8px;
                    border: 1px solid rgba(59, 130, 246, 0.3);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Orion Voice Assistant</h1>
                <div class="status">✅ Serverless API Online</div>
                <div class="status">{'✅ MongoDB Connected' if MONGODB_AVAILABLE else '⚠️ MongoDB Not Connected'}</div>
                <div class="status">{'✅ GROQ AI Connected' if orion_assistant.groq_handler.available else '⚠️ GROQ AI Not Connected'}</div>
                
                <div class="feature">
                    <h3>🎯 Available Endpoints:</h3>
                    <ul style="text-align: left;">
                        <li>POST /api/auth/register - User registration</li>
                        <li>POST /api/auth/login - User login</li>
                        <li>POST /api/process-command - Process voice commands</li>
                        <li>GET /api/status - System status</li>
                    </ul>
                </div>
                
                <p>Welcome to Orion, Commander! Your strategic voice assistant is ready for deployment.</p>
            </div>
        </body>
        </html>
        """

@app.route('/api/process-command', methods=['POST'])
def process_command():
    """Process voice commands with user context"""
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({'success': False, 'message': 'No command provided'}), 400
        
        command = data['command']
        logger.info(f"🎤 Processing command: {command}")
        
        # Get current user if authenticated
        user = None
        user_id = None
        if MONGODB_AVAILABLE:
            user = get_current_user()
            user_id = user['id'] if user else None
        
        # Process the command
        result = orion_assistant.process_command(command, user_id)
        
        return jsonify({
            'success': result['success'],
            'message': result['message'],
            'intent': result['intent'],
            'timestamp': datetime.utcnow().isoformat(),
            'processing_time': result.get('processing_time'),
            'groq_used': result.get('groq_used', False),
            'user_authenticated': user is not None
        })
        
    except Exception as e:
        logger.error(f"Error in process_command: {e}")
        return jsonify({
            'success': False,
            'message': f"Commander, I encountered an error: {str(e)}",
            'intent': 'error'
        }), 500

@app.route('/api/status')
def get_status():
    """Get system status"""
    try:
        status = orion_assistant.get_status()
        status.update({
            'mongodb_connected': MONGODB_AVAILABLE,
            'groq_connected': orion_assistant.groq_handler.available,
            'environment': 'serverless',
            'timestamp': datetime.utcnow().isoformat()
        })
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/history', methods=['GET'])
@require_auth
def get_chat_history():
    """Get user's chat history"""
    if not MONGODB_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Chat history requires database connection'
        }), 503
    
    try:
        user = request.current_user
        messages = mongo_models['chat_messages'].get_recent_messages(user['id'], limit=50)
        
        return jsonify({
            'success': True,
            'messages': [{
                'id': msg['id'],
                'sender': msg['sender'],
                'content': msg['content'],
                'timestamp': msg['timestamp'].isoformat(),
                'intent': msg.get('intent'),
                'groq_used': msg.get('groq_used', False)
            } for msg in messages]
        })
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve chat history'
        }), 500

@app.route('/api/system-info', methods=['GET'])
def get_system_info():
    """Get system information"""
    try:
        system_info = {
            'audio_status': 'Ready',
            'ai_status': 'Connected' if orion_assistant.groq_handler.available else 'Local Mode',
            'memory_usage': 'N/A (Serverless)',
            'cpu_usage': 'N/A (Serverless)',
            'battery_status': 'N/A (Cloud)',
            'network_status': 'Connected'
        }
        return jsonify(system_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/timers', methods=['GET'])
@require_auth
def get_timers():
    """Get active timers for authenticated user"""
    try:
        user = request.current_user
        # For now, return empty as timers are managed client-side
        # In a full implementation, this would fetch from database
        return jsonify({
            'success': True,
            'timers': []
        })
    except Exception as e:
        logger.error(f"Error getting timers: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve timers'
        }), 500

@app.route('/api/timers', methods=['POST'])
@require_auth
def create_timer():
    """Create a new timer"""
    try:
        data = request.get_json()
        if not data or 'duration' not in data:
            return jsonify({
                'success': False,
                'message': 'Timer duration is required'
            }), 400
        
        user = request.current_user
        duration = data['duration']
        description = data.get('description', f'{duration} second timer')
        
        # Create timer record (would be stored in database in full implementation)
        timer_data = {
            'id': f"timer_{int(datetime.now().timestamp() * 1000)}",
            'user_id': user['id'],
            'duration': duration,
            'description': description,
            'created_at': datetime.utcnow().isoformat(),
            'end_time': (datetime.utcnow() + timedelta(seconds=duration)).isoformat()
        }
        
        return jsonify({
            'success': True,
            'timer': timer_data,
            'message': f'Timer created for {description}'
        })
        
    except Exception as e:
        logger.error(f"Error creating timer: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to create timer'
        }), 500

@app.route('/api/timers/<timer_id>', methods=['DELETE'])
@require_auth
def delete_timer(timer_id):
    """Delete/cancel a timer"""
    try:
        user = request.current_user
        # In full implementation, would remove from database
        
        return jsonify({
            'success': True,
            'message': f'Timer {timer_id} cancelled'
        })
        
    except Exception as e:
        logger.error(f"Error deleting timer: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to cancel timer'
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Orion Voice Assistant',
        'version': '2.0.0-mongodb',
        'environment': 'serverless',
        'mongodb': MONGODB_AVAILABLE,
        'groq': orion_assistant.groq_handler.available,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/analytics', methods=['POST'])
def store_analytics():
    """Store analytics data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # Log analytics event
        logger.info(f"📊 Analytics Event: {data.get('event_name', 'unknown')} - {data.get('properties', {})}")
        
        # In a full implementation, you would store this in a database
        # For now, we'll just acknowledge receipt
        return jsonify({
            'success': True,
            'message': 'Analytics data received',
            'event_id': f"event_{int(datetime.now().timestamp())}"
        })
        
    except Exception as e:
        logger.error(f"Error storing analytics: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to store analytics data'
        }), 500

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

# Export the Flask app for Vercel
app = app

if __name__ == '__main__':
    # This won't be used in Vercel but useful for local testing
    app.run(debug=False, host='0.0.0.0', port=5000)