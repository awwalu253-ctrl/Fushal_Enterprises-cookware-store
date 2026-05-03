// Real-time chat functionality
class ChatManager {
    constructor() {
        this.socket = null;
        this.sessionId = localStorage.getItem('chat_session_id') || this.generateSessionId();
        this.isConnected = false;
        this.init();
    }
    
    generateSessionId() {
        const id = 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('chat_session_id', id);
        return id;
    }
    
    init() {
        this.socket = io(window.location.origin, {
            transports: ['websocket', 'polling']
        });
        
        this.socket.on('connect', () => {
            this.isConnected = true;
            this.socket.emit('join', { session_id: this.sessionId });
        });
        
        this.socket.on('message', (data) => {
            this.displayMessage(data);
        });
        
        this.socket.on('agent_joined', (data) => {
            this.showSystemMessage(`Agent ${data.agent_name} has joined the chat`);
        });
        
        this.socket.on('typing', () => {
            this.showTypingIndicator();
        });
        
        this.socket.on('disconnect', () => {
            this.isConnected = false;
        });
    }
    
    sendMessage(message) {
        if (!this.isConnected) {
            this.showSystemMessage('Reconnecting...');
            this.init();
            setTimeout(() => this.sendMessage(message), 1000);
            return;
        }
        
        this.socket.emit('message', {
            session_id: this.sessionId,
            message: message,
            sender: 'user'
        });
        
        this.displayMessage({
            message: message,
            sender: 'user',
            timestamp: new Date()
        });
    }
    
    displayMessage(data) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${data.sender === 'user' ? 'user-message' : 'admin-message'}`;
        
        const time = data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
        
        messageDiv.innerHTML = `
            <div class="message-content">${this.escapeHtml(data.message)}</div>
            <div class="message-time">${time}</div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    showSystemMessage(message) {
        const messagesContainer = document.getElementById('chatMessages');
        const systemDiv = document.createElement('div');
        systemDiv.className = 'system-message';
        systemDiv.innerHTML = `<i class="fas fa-info-circle"></i> ${message}`;
        messagesContainer.appendChild(systemDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    showTypingIndicator() {
        const messagesContainer = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = '<span></span><span></span><span></span>';
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        setTimeout(() => {
            const indicator = document.getElementById('typingIndicator');
            if (indicator) indicator.remove();
        }, 3000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chat when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const chatToggle = document.getElementById('chatToggle');
    const chatWindow = document.getElementById('chatWindow');
    const sendBtn = document.getElementById('sendMessage');
    const chatInput = document.getElementById('chatInput');
    
    let chatManager = null;
    
    chatToggle.addEventListener('click', () => {
        chatWindow.classList.toggle('active');
        if (!chatManager) {
            chatManager = new ChatManager();
        }
    });
    
    if (sendBtn && chatInput) {
        sendBtn.addEventListener('click', () => {
            const message = chatInput.value.trim();
            if (message) {
                chatManager.sendMessage(message);
                chatInput.value = '';
            }
        });
        
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const message = chatInput.value.trim();
                if (message) {
                    chatManager.sendMessage(message);
                    chatInput.value = '';
                }
            }
        });
    }
});