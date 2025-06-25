let userApiKey = '';

const apiSetup = document.getElementById('apiSetup');
const chatSection = document.getElementById('chatSection');
const apiKeyInput = document.getElementById('apiKeyInput');
const connectButton = document.getElementById('connectButton');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const loading = document.getElementById('loading');

// API endpoint
const API_URL = '/api/chat';

connectButton.addEventListener('click', connectWithApiKey);
sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

function connectWithApiKey() {
    const apiKey = apiKeyInput.value.trim();
    
    if (!apiKey) {
        alert('Please enter your OpenAI API key');
        return;
    }
    
    if (!apiKey.startsWith('sk-')) {
        alert('Invalid API key format. Should start with "sk-"');
        return;
    }
    
    userApiKey = apiKey;
    
    // Hide API setup, show chat
    apiSetup.style.display = 'none';
    chatSection.style.display = 'block';
    
    messageInput.focus();
    
    // Test connection
    testConnection();
}

async function testConnection() {
    try {
        showLoading(true);
        
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                message: 'Test connection',
                api_key: userApiKey
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            addErrorMessage(`Connection failed: ${data.error}`);
        } else {
            addMessage('✅ Connected successfully! You can now ask questions about your pharmaceutical data.', 'bot');
        }
        
    } catch (error) {
        addErrorMessage('Connection test failed. Please check your API key.');
    } finally {
        showLoading(false);
    }
}

function askQuestion(question) {
    messageInput.value = question;
    sendMessage();
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessage(message, 'user');
    messageInput.value = '';
    
    // Show loading
    showLoading(true);
    sendButton.disabled = true;
    
    try {
        // Send request to API
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                message: message,
                api_key: userApiKey
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            addErrorMessage(data.error);
        } else {
            // Add bot response to chat
            addBotResponse(data);
        }
        
    } catch (error) {
        console.error('Error:', error);
        addErrorMessage('Sorry, I encountered an error while processing your request. Please try again.');
    } finally {
        showLoading(false);
        sendButton.disabled = false;
        messageInput.focus();
    }
}

function addMessage(content, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (typeof content === 'string') {
        contentDiv.innerHTML = content.replace(/\n/g, '<br>');
    } else {
        contentDiv.appendChild(content);
    }
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addBotResponse(data) {
    const responseDiv = document.createElement('div');
    
    // Main response
    const responseText = document.createElement('div');
    responseText.innerHTML = data.response.replace(/\n/g, '<br>');
    responseDiv.appendChild(responseText);
    
    // SQL query (if available)
    if (data.sql_query) {
        const sqlDiv = document.createElement('div');
        sqlDiv.className = 'sql-query';
        sqlDiv.innerHTML = `<strong>💻 SQL Query:</strong><br><code>${data.sql_query}</code>`;
        responseDiv.appendChild(sqlDiv);
    }
    
    // Data preview (if available)
    if (data.data && data.data.length > 0) {
        const dataDiv = document.createElement('div');
        dataDiv.innerHTML = `<br><strong>📊 Data Preview (${data.total_rows || data.data.length} rows):</strong>`;
        
        const table = document.createElement('table');
        table.style.marginTop = '10px';
        table.style.borderCollapse = 'collapse';
        table.style.width = '100%';
        table.style.fontSize = '12px';
        
        // Headers
        const headerRow = document.createElement('tr');
        Object.keys(data.data[0]).forEach(key => {
            const th = document.createElement('th');
            th.textContent = key;
            th.style.border = '1px solid #ddd';
            th.style.padding = '5px';
            th.style.background = '#f5f5f5';
            headerRow.appendChild(th);
        });
        table.appendChild(headerRow);
        
        // Data rows (limit to 5)
        data.data.slice(0, 5).forEach(row => {
            const tr = document.createElement('tr');
            Object.values(row).forEach(value => {
                const td = document.createElement('td');
                td.textContent = value !== null ? value : 'N/A';
                td.style.border = '1px solid #ddd';
                td.style.padding = '5px';
                tr.appendChild(td);
            });
            table.appendChild(tr);
        });
        
        dataDiv.appendChild(table);
        responseDiv.appendChild(dataDiv);
    }
    
    addMessage(responseDiv, 'bot');
}

function addErrorMessage(error) {
    const errorDiv = document.createElement('div');
    errorDiv.innerHTML = `<div class="error-message">❌ ${error}</div>`;
    addMessage(errorDiv, 'bot');
}

function showLoading(show) {
    loading.style.display = show ? 'block' : 'none';
}

// Focus API key input on load
apiKeyInput.focus();
