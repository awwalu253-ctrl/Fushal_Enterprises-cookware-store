from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
import json
import uuid

chat_bp = Blueprint('chat', __name__)

# Store chat sessions in memory (for demo - use database in production)
chat_sessions = {}
chat_messages = {}

def get_or_create_session():
    """Get or create a chat session for the current user"""
    session_id = session.get('chat_session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['chat_session_id'] = session_id
        chat_sessions[session_id] = {
            'id': session_id,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'user_email': current_user.email if current_user.is_authenticated else None,
            'user_name': current_user.get_full_name() if current_user.is_authenticated else 'Guest',
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat()
        }
        chat_messages[session_id] = []
    
    # Update last activity
    if session_id in chat_sessions:
        chat_sessions[session_id]['last_activity'] = datetime.now().isoformat()
    
    return session_id

@chat_bp.route('/send', methods=['POST'])
def send_message():
    """Send a chat message"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = get_or_create_session()
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is empty'}), 400
        
        # Save user message
        user_message = {
            'id': str(uuid.uuid4()),
            'session_id': session_id,
            'message': message,
            'sender': 'user',
            'sender_name': 'You',
            'timestamp': datetime.now().isoformat(),
            'is_read': False
        }
        
        if session_id not in chat_messages:
            chat_messages[session_id] = []
        chat_messages[session_id].append(user_message)
        
        # Auto-reply for first message or if no admin has replied
        auto_reply_message = None
        user_messages_count = len([m for m in chat_messages[session_id] if m['sender'] == 'user'])
        
        if user_messages_count == 1:
            # First message - send auto-reply
            auto_reply = {
                'id': str(uuid.uuid4()),
                'session_id': session_id,
                'message': "Thank you for contacting Golden Kitchen Nigeria! 🎉\n\nOur customer support team will respond shortly. In the meantime, please provide your order number if you have one.\n\nWe're here to help! 💪",
                'sender': 'auto',
                'sender_name': 'Auto Reply',
                'timestamp': datetime.now().isoformat(),
                'is_read': False
            }
            chat_messages[session_id].append(auto_reply)
            auto_reply_message = auto_reply
        
        return jsonify({
            'success': True,
            'message': user_message,
            'auto_reply': auto_reply_message
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/messages', methods=['GET'])
def get_messages():
    """Get all messages for the current session"""
    session_id = session.get('chat_session_id')
    if not session_id or session_id not in chat_messages:
        return jsonify({'messages': []})
    
    # Mark messages as read for this session
    for msg in chat_messages[session_id]:
        if msg['sender'] != 'user':
            msg['is_read'] = True
    
    return jsonify({'messages': chat_messages[session_id]})

@chat_bp.route('/unread-count', methods=['GET'])
def get_unread_count():
    """Get unread message count for admin"""
    if current_user.is_authenticated and current_user.is_admin:
        unread_count = 0
        for session_id, messages in chat_messages.items():
            unread_count += len([m for m in messages if not m.get('is_read', False) and m['sender'] != 'admin'])
        return jsonify({'count': unread_count})
    
    # For regular users, get unread replies
    session_id = session.get('chat_session_id')
    if session_id and session_id in chat_messages:
        unread_count = len([m for m in chat_messages[session_id] if not m.get('is_read', False) and m['sender'] != 'user'])
        return jsonify({'count': unread_count})
    
    return jsonify({'count': 0})

@chat_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Get all chat sessions (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    sessions_list = []
    for session_id, session_info in chat_sessions.items():
        messages = chat_messages.get(session_id, [])
        last_message = messages[-1]['message'] if messages else 'No messages'
        last_time = messages[-1]['timestamp'] if messages else session_info['created_at']
        unread = len([m for m in messages if not m.get('is_read', False) and m['sender'] != 'admin'])
        
        sessions_list.append({
            'session_id': session_id,
            'user_name': session_info.get('user_name', 'Guest'),
            'user_email': session_info.get('user_email', 'N/A'),
            'last_message': last_message[:50],
            'last_time': last_time,
            'unread': unread,
            'message_count': len(messages),
            'status': session_info.get('status', 'active')
        })
    
    # Sort by last activity (most recent first)
    sessions_list.sort(key=lambda x: x['last_time'], reverse=True)
    return jsonify({'sessions': sessions_list})

@chat_bp.route('/session/<session_id>/messages', methods=['GET'])
@login_required
def get_session_messages(session_id):
    """Get messages for a specific session (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    messages = chat_messages.get(session_id, [])
    
    # Mark messages as read for this session
    for msg in messages:
        if msg['sender'] != 'admin':
            msg['is_read'] = True
    
    return jsonify({'messages': messages, 'session_id': session_id})

@chat_bp.route('/admin/send', methods=['POST'])
@login_required
def admin_send_message():
    """Send message as admin"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message', '').strip()
    
    if not session_id or not message:
        return jsonify({'success': False, 'error': 'Missing data'}), 400
    
    admin_message = {
        'id': str(uuid.uuid4()),
        'session_id': session_id,
        'message': message,
        'sender': 'admin',
        'sender_name': current_user.get_full_name() or 'Admin',
        'timestamp': datetime.now().isoformat(),
        'is_read': True
    }
    
    if session_id not in chat_messages:
        chat_messages[session_id] = []
    chat_messages[session_id].append(admin_message)
    
    # Update session last activity
    if session_id in chat_sessions:
        chat_sessions[session_id]['last_activity'] = datetime.now().isoformat()
    
    return jsonify({'success': True, 'message': admin_message})

@chat_bp.route('/dashboard')
@login_required
def chat_dashboard():
    """Admin chat dashboard"""
    if not current_user.is_admin:
        return redirect(url_for('main.index'))
    return render_template('admin/chat_dashboard.html')