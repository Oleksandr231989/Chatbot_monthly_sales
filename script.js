let userApiKey = '';

const apiSetup = document.getElementById('apiSetup');
const chatSection = document.getElementById('chatSection');
const apiKeyInput = document.getElementById('apiKeyInput');
const connectButton = document.getElementById('connectButton');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const resetButton = document.getElementById('resetButton');
const loading = document.getElementById('loading');

// API endpoint
const API_URL = '/api/chat';

// Add debug logging
console.log('Script loaded, API_URL:', API_URL);

connectButton.addEventListener('click', function(e) {
    console.log('Connect button event listener triggered');
    e.preventDefault();
    connectWithApiKey();
});

sendButton.addEventListener('click', function(e) {
    console.log('Send button clicked');
    e.preventDefault();
    sendMessage();
});

resetButton.addEventListener('click', function(e) {
    console.log('Reset button clicked');
    e.preventDefault();
    resetChat();
});
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

function connectWithApiKey() {
    const apiKey = apiKeyInput.value.trim();
    
    console.log('Connect button clicked'); // Debug log
    console.log('API Key length:', apiKey.length); // Debug log
    
    if (!apiKey) {
        alert('Please enter your OpenAI API key');
        return;
    }
    
    if (!apiKey.startsWith('sk-')) {
        alert('Invalid API key format. Should start with "sk-"');
        return;
    }
    
    console.log('API key validation passed'); // Debug log
    
    userApiKey = apiKey;
    
    // Hide API setup, show chat
    apiSetup.style.display = 'none';
    chatSection.style.display = 'block';
    
    console.log('UI updated, starting connection test'); // Debug log
    
    messageInput.focus();
    
    // Test connection
    testConnection();
}

async function testConnection() {
    console.log('Testing connection...'); // Debug log
    
    try {
        showLoading(true);
        
        console.log('Sending request to:', API_URL); // Debug log
        
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
        
        console.log('Response status:', response.status); // Debug log
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data); // Debug log
        
        if (data.error) {
            console.error('API error:', data.error); // Debug log
            addErrorMessage(`Connection failed: ${data.error}`);
        } else {
            console.log('Connection successful'); // Debug log
            addMessage('✅ Connected successfully! You can now ask questions about your pharmaceutical data.', 'bot');
        }
        
    } catch (error) {
        console.error('Connection error:', error); // Debug log
        addErrorMessage(`Connection test failed: ${error.message}. Please check your API key and try again.`);
    } finally {
        showLoading(false);
    }
}

function askQuestion(question) {
    messageInput.value = question;
    sendMessage();
}

function resetChat() {
    // Clear all messages
    chatMessages.innerHTML = '';
    
    // Clear input field
    messageInput.value = '';
    
    // Add welcome message back
    addMessage('✅ Chat reset! You can now ask new questions about your pharmaceutical data.', 'bot');
    
    // Focus on input
    messageInput.focus();
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
    
    // Main response with markdown processing
    const responseText = document.createElement('div');
    let processedResponse = data.response.replace(/\n/g, '<br>');
    
    // Convert **bold** markdown to HTML bold tags
    processedResponse = processedResponse.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    responseText.innerHTML = processedResponse;
    responseDiv.appendChild(responseText);
    
    // SQL query (hidden by default with show button)
    if (data.sql_query) {
        const sqlContainer = document.createElement('div');
        sqlContainer.style.margin = '15px 0';
        
        // Show SQL button
        const showSqlBtn = document.createElement('button');
        showSqlBtn.textContent = '📝 Show SQL Query';
        showSqlBtn.className = 'show-sql-btn';
        showSqlBtn.style.cssText = `
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
            color: white;
            border: none;
            border-radius: 20px;
            padding: 8px 16px;
            font-size: 12px;
            cursor: pointer;
            margin-bottom: 10px;
            transition: transform 0.2s;
        `;
        
        // Hidden SQL query div
        const sqlDiv = document.createElement('div');
        sqlDiv.className = 'sql-query';
        sqlDiv.style.display = 'none';
        sqlDiv.innerHTML = `<strong>💻 SQL Query:</strong><br><code>${data.sql_query}</code>`;
        
        // Toggle functionality
        showSqlBtn.addEventListener('click', function() {
            if (sqlDiv.style.display === 'none') {
                sqlDiv.style.display = 'block';
                showSqlBtn.textContent = '📝 Hide SQL Query';
            } else {
                sqlDiv.style.display = 'none';
                showSqlBtn.textContent = '📝 Show SQL Query';
            }
        });
        
        showSqlBtn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        showSqlBtn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
        
        sqlContainer.appendChild(showSqlBtn);
        sqlContainer.appendChild(sqlDiv);
        responseDiv.appendChild(sqlContainer);
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
    console.log('Show loading:', show); // Debug log
    if (loading) {
        loading.style.display = show ? 'block' : 'none';
    } else {
        console.error('Loading element not found');
    }
}

// Focus API key input on load
apiKeyInput.focus();
