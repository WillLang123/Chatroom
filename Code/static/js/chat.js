let currentUserId = null;
let currentUsername = null;
let messageStreams = {};

// Track delete operations in progress
let deleteInProgress = new Set();

// Form toggle function
function toggleForm(formType) {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    
    if (formType === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
    }
}

// Authentication functions
async function register() {
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            await login(username, password);
        } else {
            document.getElementById('register-error').textContent = data.message;
        }
    } catch (error) {
        document.getElementById('register-error').textContent = 'An error occurred during registration';
    }
}

async function login(username = null, password = null) {
    if (!username || !password) {
        username = document.getElementById('login-username').value;
        password = document.getElementById('login-password').value;
    }
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            document.getElementById('auth-section').style.display = 'none';
            document.getElementById('chat-section').style.display = 'block';
            currentUserId = data.user.id;
            currentUsername = data.user.username;
            await loadChatrooms();
        } else {
            document.getElementById('login-error').textContent = data.message;
        }
    } catch (error) {
        document.getElementById('login-error').textContent = 'An error occurred during login';
    }
}

async function logout() {
    try {
        const response = await fetch('/logout', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'success') {
            document.getElementById('auth-section').style.display = 'block';
            document.getElementById('chat-section').style.display = 'none';
            currentUserId = null;
            currentUsername = null;
            
            // Clear form fields
            document.getElementById('login-username').value = '';
            document.getElementById('login-password').value = '';
            document.getElementById('register-username').value = '';
            document.getElementById('register-password').value = '';
            
            // Clear error messages
            document.getElementById('login-error').textContent = '';
            document.getElementById('register-error').textContent = '';
            
            // Close all message streams
            Object.values(messageStreams).forEach(stream => stream.close());
            messageStreams = {};
        }
    } catch (error) {
        console.error('Error during logout:', error);
    }
}

async function checkAuth() {
    try {
        const response = await fetch('/check_auth');
        const data = await response.json();
        
        if (data.status === 'success' && data.authenticated) {
            document.getElementById('auth-section').style.display = 'none';
            document.getElementById('chat-section').style.display = 'block';
            currentUserId = data.user.id;
            currentUsername = data.user.username;
            await loadChatrooms();
        }
    } catch (error) {
        console.error('Error checking authentication:', error);
    }
}

// Chatroom functions
async function createChatroom() {
    const name = document.getElementById('chatroom-name').value;
    if (!name) return;
    
    try {
        const response = await fetch('/create_chatroom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            document.getElementById('chatroom-name').value = '';
            await loadChatrooms();
        } else {
            alert(data.message);
        }
    } catch (error) {
        console.error('Error creating chatroom:', error);
        alert('Failed to create chatroom. Please try again.');
    }
}

async function joinChatroom() {
    const id = document.getElementById('chatroom-id').value;
    if (!id) return;
    
    try {
        const response = await fetch('/join_chatroom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chatroom_id: parseInt(id) })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            document.getElementById('chatroom-id').value = '';
            await loadChatrooms();
        } else {
            alert(data.message);
        }
    } catch (error) {
        console.error('Error joining chatroom:', error);
        alert('Failed to join chatroom. Please try again.');
    }
}

async function deleteChatroom(chatroomId) {
    // Prevent multiple delete requests for the same chatroom
    if (deleteInProgress.has(chatroomId)) {
        console.log('Delete already in progress for chatroom:', chatroomId);
        return;
    }
    
    if (!confirm('Are you sure you want to delete this chatroom?')) return;
    
    try {
        deleteInProgress.add(chatroomId);
        console.log('Deleting chatroom:', chatroomId);
        
        // Close SSE connection before deletion
        if (messageStreams[chatroomId]) {
            console.log('Closing SSE connection for chatroom:', chatroomId);
            messageStreams[chatroomId].close();
            delete messageStreams[chatroomId];
        }
        
        // Disable the delete button
        const deleteButton = document.querySelector(`#chatroom-tabs .tab[data-chatroom-id="${chatroomId}"] .btn-delete`);
        if (deleteButton) {
            deleteButton.disabled = true;
            deleteButton.style.opacity = '0.5';
        }
        
        const response = await fetch(`/delete_chatroom/${chatroomId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        console.log('Delete response:', data);
        
        if (data.status === 'success') {
            // Remove the tab and chat area
            const tab = document.querySelector(`.tab[data-chatroom-id="${chatroomId}"]`);
            const chatArea = document.getElementById(`chat-${chatroomId}`);
            
            if (tab) {
                // If this was the active tab, activate another tab
                if (tab.classList.contains('active')) {
                    const nextTab = tab.nextElementSibling || tab.previousElementSibling;
                    if (nextTab) {
                        const nextChatroomId = nextTab.getAttribute('data-chatroom-id');
                        switchTab(nextChatroomId);
                    }
                }
                tab.remove();
            }
            if (chatArea) {
                chatArea.remove();
            }
            
            // If no more chatrooms, show welcome message
            const tabs = document.querySelectorAll('.tab');
            if (tabs.length === 0) {
                document.getElementById('tab-content').innerHTML = `
                    <div class="welcome-message">
                        <h2>Welcome to the Chat App!</h2>
                        <p>Create a new chatroom or join an existing one to start chatting.</p>
                    </div>
                `;
            }
        } else {
            alert(data.message || 'Failed to delete chatroom');
        }
    } catch (error) {
        console.error('Error deleting chatroom:', error);
        alert('Failed to delete chatroom. Please try again.');
    } finally {
        deleteInProgress.delete(chatroomId);
        // Re-enable the delete button if it still exists
        const deleteButton = document.querySelector(`#chatroom-tabs .tab[data-chatroom-id="${chatroomId}"] .btn-delete`);
        if (deleteButton) {
            deleteButton.disabled = false;
            deleteButton.style.opacity = '1';
        }
    }
}

async function loadChatrooms() {
    try {
        console.log('Loading chatrooms...');
        const response = await fetch('/chatrooms');
        const data = await response.json();
        console.log('Chatrooms response:', data);
        
        const tabsContainer = document.getElementById('chatroom-tabs');
        const contentContainer = document.getElementById('tab-content');
        
        if (!tabsContainer || !contentContainer) {
            console.error('Could not find tabs or content container');
            return;
        }
        
        tabsContainer.innerHTML = '';
        contentContainer.innerHTML = '';
        
        if (!data.chatrooms || data.chatrooms.length === 0) {
            console.log('No chatrooms found');
            contentContainer.innerHTML = `
                <div class="welcome-message">
                    <h2>Welcome to the Chat App!</h2>
                    <p>Create a new chatroom or join an existing one to start chatting.</p>
                </div>
            `;
            return;
        }
        
        data.chatrooms.forEach((chatroom, index) => {
            console.log('Creating tab for chatroom:', chatroom);
            
            // Create tab
            const tab = document.createElement('div');
            tab.className = `tab ${index === 0 ? 'active' : ''}`;
            tab.setAttribute('data-chatroom-id', chatroom.id);
            tab.onclick = () => switchTab(chatroom.id);
            
            tab.innerHTML = `
                <div class="tab-content" style="display: flex; align-items: center; gap: 10px;">
                    <span>${chatroom.name}</span>
                    ${chatroom.isAdmin ? `
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <span style="font-size: 12px; color: #95a5a6;">(ID: ${chatroom.id})</span>
                            <button class="btn btn-delete" onclick="event.stopPropagation(); deleteChatroom(${chatroom.id})">
                                Delete
                            </button>
                        </div>
                    ` : ''}
                </div>
            `;
            
            tabsContainer.appendChild(tab);
            
            // Create chat area
            const chatArea = document.createElement('div');
            chatArea.className = `chat-area ${index === 0 ? 'active' : ''}`;
            chatArea.id = `chat-${chatroom.id}`;
            chatArea.setAttribute('data-chatroom-id', chatroom.id);
            
            chatArea.innerHTML = `
                <div class="chat-header">
                    <h3>${chatroom.name}</h3>
                    ${chatroom.isAdmin ? `<small>Chatroom ID: ${chatroom.id}</small>` : ''}
                </div>
                <div class="messages" id="messages-${chatroom.id}"></div>
                <div class="chat-input">
                    <input type="text" placeholder="Type your message...">
                    <button class="btn btn-primary" onclick="sendMessage(${chatroom.id})">Send</button>
                </div>
            `;
            
            contentContainer.appendChild(chatArea);
            
            // Set up message input event listener
            const input = chatArea.querySelector('.chat-input input');
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    sendMessage(chatroom.id);
                }
            });
            
            // Load messages and set up SSE for this chatroom
            loadMessages(chatroom.id);
            setupMessageStream(chatroom.id);
        });
    } catch (error) {
        console.error('Error loading chatrooms:', error);
    }
}

function switchTab(chatroomId) {
    console.log('Switching to chatroom:', chatroomId);
    
    // Update tabs
    document.querySelectorAll('.tab').forEach(tab => {
        if (tab.getAttribute('data-chatroom-id') == chatroomId) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // Update chat areas
    document.querySelectorAll('.chat-area').forEach(area => {
        if (area.getAttribute('data-chatroom-id') == chatroomId) {
            area.classList.add('active');
        } else {
            area.classList.remove('active');
        }
    });
}

// Message functions
async function loadMessages(chatroomId) {
    try {
        console.log('Loading messages for chatroom:', chatroomId);
        const response = await fetch(`/chatroom/${chatroomId}/messages`);
        const data = await response.json();
        
        if (data.status === 'success') {
            const messageContainer = document.querySelector(`#messages-${chatroomId}`);
            if (!messageContainer) {
                console.error('Could not find message container for chatroom', chatroomId);
                return;
            }
            
            // Clear existing messages
            messageContainer.innerHTML = '';
            
            // Add each message
            data.messages.forEach(message => {
                appendMessage(chatroomId, message);
            });
            
            // Scroll to bottom
            messageContainer.scrollTop = messageContainer.scrollHeight;
        } else {
            console.error('Error loading messages:', data.message);
        }
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

async function sendMessage(chatroomId) {
    const input = document.querySelector(`#chat-${chatroomId} .chat-input input`);
    const message = input.value.trim();
    
    if (!message) return;
    
    try {
        console.log('Sending message to chatroom', chatroomId);
        const response = await fetch(`/chatroom/${chatroomId}/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        console.log('Send message response:', data);
        
        if (data.status === 'success') {
            input.value = '';
            // The message will be added through the SSE stream
        } else {
            alert(data.message);
        }
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Failed to send message. Please try again.');
    }
}

function setupMessageStream(chatroomId) {
    // Close existing stream if any
    if (messageStreams[chatroomId]) {
        console.log('Closing existing stream for chatroom:', chatroomId);
        messageStreams[chatroomId].close();
        delete messageStreams[chatroomId];
    }
    
    console.log('Setting up message stream for chatroom', chatroomId);
    const eventSource = new EventSource(`/chatroom/${chatroomId}/stream`);
    
    eventSource.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            console.log('Received message:', message);
            
            if (message.error) {
                console.error('Error from server:', message.error);
                return;
            }
            
            appendMessage(chatroomId, message);
        } catch (error) {
            console.error('Error processing message:', error);
        }
    };
    
    eventSource.onerror = (error) => {
        console.error('SSE Error for chatroom', chatroomId, ':', error);
        
        // Check if the chatroom still exists in the UI
        const chatArea = document.getElementById(`chat-${chatroomId}`);
        if (!chatArea) {
            console.log('Chatroom no longer exists in UI, closing stream');
            eventSource.close();
            delete messageStreams[chatroomId];
            return;
        }
        
        // Close and retry connection
        eventSource.close();
        delete messageStreams[chatroomId];
        
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
            // Check again if chatroom still exists before reconnecting
            if (document.getElementById(`chat-${chatroomId}`)) {
                console.log('Attempting to reconnect to chatroom:', chatroomId);
                setupMessageStream(chatroomId);
            }
        }, 5000);
    };
    
    messageStreams[chatroomId] = eventSource;
}

function appendMessage(chatroomId, message) {
    const messageContainer = document.querySelector(`#messages-${chatroomId}`);
    if (!messageContainer) {
        console.error('Could not find message container for chatroom', chatroomId);
        return;
    }
    
    const messageElement = document.createElement('div');
    messageElement.className = `message ${message.user_id === currentUserId ? 'sent' : 'received'}`;
    
    const timestamp = new Date(message.timestamp).toLocaleTimeString();
    messageElement.innerHTML = `
        <div class="sender">${message.username}</div>
        <div class="content">${escapeHtml(message.message)}</div>
        <div class="timestamp">${timestamp}</div>
    `;
    
    messageContainer.appendChild(messageElement);
    
    // Scroll to bottom if user is near bottom
    const isNearBottom = messageContainer.scrollHeight - messageContainer.scrollTop - messageContainer.clientHeight < 100;
    if (isNearBottom) {
        messageContainer.scrollTop = messageContainer.scrollHeight;
    }
}

// Utility function to escape HTML
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Initialize by checking authentication
document.addEventListener('DOMContentLoaded', checkAuth);