"""
Aurora Voice Assistant - Chat Session Management
Handles multiple chat sessions and conversation history
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
import time

from models import db, ChatSession, ChatMessage

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/sessions', methods=['GET'])
@login_required
def get_chat_sessions():
    """Get user's chat sessions"""
    try:
        sessions = current_user.get_chat_sessions()
        
        session_list = []
        for session in sessions:
            last_message = session.get_last_message()
            session_list.append({
                'id': session.id,
                'title': session.title,
                'description': session.description,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'message_count': session.message_count(),
                'last_message': {
                    'content': last_message.content[:100] + ('...' if len(last_message.content) > 100 else ''),
                    'sender': last_message.sender,
                    'timestamp': last_message.timestamp.isoformat()
                } if last_message else None
            })
        
        return jsonify({
            'success': True,
            'sessions': session_list
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get sessions error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get chat sessions'}), 500

@chat_bp.route('/sessions', methods=['POST'])
@login_required
def create_chat_session():
    """Create a new chat session"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        
        if not title:
            return jsonify({'success': False, 'message': 'Session title is required'}), 400
        
        if len(title) > 200:
            return jsonify({'success': False, 'message': 'Title must be less than 200 characters'}), 400
        
        # Create new session
        session = ChatSession(
            user_id=current_user.id,
            title=title,
            description=description or None
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Chat session created successfully',
            'session': {
                'id': session.id,
                'title': session.title,
                'description': session.description,
                'created_at': session.created_at.isoformat(),
                'message_count': 0
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create session error: {e}")
        return jsonify({'success': False, 'message': 'Failed to create chat session'}), 500

@chat_bp.route('/sessions/<session_id>', methods=['GET'])
@login_required
def get_chat_session(session_id):
    """Get specific chat session with messages"""
    try:
        session = ChatSession.query.filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({'success': False, 'message': 'Chat session not found'}), 404
        
        messages = session.get_messages()
        
        message_list = []
        for message in messages:
            message_list.append({
                'id': message.id,
                'sender': message.sender,
                'content': message.content,
                'message_type': message.message_type,
                'timestamp': message.timestamp.isoformat(),
                'intent': message.intent,
                'processing_time': message.processing_time,
                'groq_used': message.groq_used
            })
        
        return jsonify({
            'success': True,
            'session': {
                'id': session.id,
                'title': session.title,
                'description': session.description,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'messages': message_list
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get session error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get chat session'}), 500

@chat_bp.route('/sessions/<session_id>', methods=['PUT'])
@login_required
def update_chat_session(session_id):
    """Update chat session details"""
    try:
        session = ChatSession.query.filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({'success': False, 'message': 'Chat session not found'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return jsonify({'success': False, 'message': 'Session title cannot be empty'}), 400
            if len(title) > 200:
                return jsonify({'success': False, 'message': 'Title must be less than 200 characters'}), 400
            session.title = title
        
        if 'description' in data:
            session.description = data['description'].strip() or None
        
        session.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Chat session updated successfully',
            'session': {
                'id': session.id,
                'title': session.title,
                'description': session.description,
                'updated_at': session.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update session error: {e}")
        return jsonify({'success': False, 'message': 'Failed to update chat session'}), 500

@chat_bp.route('/sessions/<session_id>', methods=['DELETE'])
@login_required
def delete_chat_session(session_id):
    """Delete chat session and all its messages"""
    try:
        session = ChatSession.query.filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({'success': False, 'message': 'Chat session not found'}), 404
        
        # Check if this is the last session (prevent deleting all sessions)
        session_count = ChatSession.query.filter_by(user_id=current_user.id).count()
        if session_count <= 1:
            return jsonify({
                'success': False, 
                'message': 'Cannot delete the last chat session. Create a new one first.'
            }), 400
        
        db.session.delete(session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Chat session deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete session error: {e}")
        return jsonify({'success': False, 'message': 'Failed to delete chat session'}), 500

@chat_bp.route('/sessions/<session_id>/messages', methods=['POST'])
@login_required
def add_message(session_id):
    """Add a message to a chat session"""
    try:
        session = ChatSession.query.filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({'success': False, 'message': 'Chat session not found'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        sender = data.get('sender', '').strip()
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        intent = data.get('intent')
        processing_time = data.get('processing_time')
        groq_used = data.get('groq_used', False)
        
        if not sender or not content:
            return jsonify({'success': False, 'message': 'Sender and content are required'}), 400
        
        if sender not in ['user', 'aurora']:
            return jsonify({'success': False, 'message': 'Sender must be "user" or "aurora"'}), 400
        
        # Create message
        message = ChatMessage(
            session_id=session.id,
            sender=sender,
            content=content,
            message_type=message_type,
            intent=intent,
            processing_time=processing_time,
            groq_used=groq_used
        )
        
        db.session.add(message)
        
        # Update session timestamp
        session.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_obj': {
                'id': message.id,
                'sender': message.sender,
                'content': message.content,
                'timestamp': message.timestamp.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add message error: {e}")
        return jsonify({'success': False, 'message': 'Failed to add message'}), 500

@chat_bp.route('/process-command', methods=['POST'])
@login_required
def process_command_with_session():
    """Process a voice command with session tracking"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        command = data.get('command', '').strip()
        session_id = data.get('session_id')
        
        if not command:
            return jsonify({'success': False, 'message': 'No command provided'}), 400
        
        # Get or create session
        if session_id:
            session = ChatSession.query.filter_by(
                id=session_id,
                user_id=current_user.id
            ).first()
            
            if not session:
                return jsonify({'success': False, 'message': 'Chat session not found'}), 404
        else:
            # Use the first available session or create one
            session = current_user.chat_sessions.first()
            if not session:
                session = ChatSession(
                    user_id=current_user.id,
                    title="General Chat",
                    description="Your default chat session with Aurora"
                )
                db.session.add(session)
                db.session.commit()
        
        # Process command (import here to avoid circular imports)
        from web_server import web_assistant
        
        start_time = time.time()
        response = web_assistant.process_command(command)
        processing_time = time.time() - start_time
        
        # Store user message
        user_message = ChatMessage(
            session_id=session.id,
            sender='user',
            content=command,
            message_type='command',
            processing_time=processing_time
        )
        db.session.add(user_message)
        
        # Store Aurora's response
        aurora_message = ChatMessage(
            session_id=session.id,
            sender='aurora',
            content=response['message'],
            message_type='text',
            intent=response.get('intent'),
            processing_time=processing_time,
            groq_used='groq' in response.get('intent', '').lower()
        )
        db.session.add(aurora_message)
        
        # Update session timestamp
        session.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Return response with session info
        response['session_id'] = session.id
        response['message_id'] = aurora_message.id
        
        return jsonify(response), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Process command error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@chat_bp.route('/export/<session_id>', methods=['GET'])
@login_required
def export_chat_session(session_id):
    """Export chat session as JSON"""
    try:
        session = ChatSession.query.filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({'success': False, 'message': 'Chat session not found'}), 404
        
        messages = session.get_messages()
        
        export_data = {
            'session': {
                'id': session.id,
                'title': session.title,
                'description': session.description,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat()
            },
            'user': {
                'username': current_user.username,
                'full_name': current_user.full_name
            },
            'messages': [
                {
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'intent': msg.intent,
                    'processing_time': msg.processing_time
                } for msg in messages
            ],
            'exported_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': export_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Export session error: {e}")
        return jsonify({'success': False, 'message': 'Failed to export chat session'}), 500