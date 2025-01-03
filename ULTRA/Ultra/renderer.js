const io = require('socket.io-client');
const socket = io('http://localhost:3000', {
    reconnection: true, // Default is true, but being explicit for clarity
    reconnectionDelay: 1000, // Attempt to reconnect every 1 second
    reconnectionAttempts: Infinity // Keep trying to reconnect
});
const { shell } = require('electron');
const applocation = "Clearwater"; //This is a beta release, change this city to your city otherwise weather popups won't display the correct info. This doesn't affect Ultra' speech or responses.

let isErrorDetected = false; // Global flag to track error state

const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const outputDiv = document.getElementById('output');
const statusIndicator = document.getElementById('status-indicator');

async function sendMessage() {
    const message = messageInput.value.trim();
    if (message) {
        // Emit message to Python backend for processing
        socket.emit('user_message', {
            type: 'text_input',
            content: message,
        });

        // Clear input and scroll to bottom
        messageInput.value = '';
        outputDiv.scrollTop = outputDiv.scrollHeight;
    }
}

// Send button click handler
sendButton.addEventListener('click', sendMessage);

// Enter key handler
messageInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

// Socket event handlers
socket.on('assistant_response', (response) => {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'ultra common-style';
    messageDiv.innerHTML = `<span class="bold-glow">Ultra:</span> ${response}`;
    outputDiv.appendChild(messageDiv);
    outputDiv.scrollTop = outputDiv.scrollHeight;
});

socket.on('status_update', (status) => {
    statusIndicator.textContent = status;
});

document.addEventListener('click', function(event) {
    if (event.target.tagName === 'A' && event.target.href.startsWith('http')) {
        event.preventDefault();
        shell.openExternal(event.target.href);
    }
});

function scrollToBottom() {
    const appContainer = document.getElementById('app-container');
    const lastChild = appContainer.lastElementChild;
    if (lastChild && typeof lastChild.scrollIntoView === 'function') {
        lastChild.scrollIntoView({ behavior: 'smooth' });
    }
}

socket.on('pythonOutput', (data) => {
    console.log('Received pythonOutput:', data);
    const messageRegex = /(Ultra:|User:|\[.*?\])/g;
    let startIndex = 0;
    let match;

    while ((match = messageRegex.exec(data)) !== null) {
        const message = data.substring(startIndex, match.index).trim();
        if (message) {
            processMessage(message, false);
        }
        startIndex = match.index;
    }
    if (startIndex < data.length) {
        processMessage(data.substring(startIndex).trim(), false);
    }
});

socket.on('pythonError', (errorMessage) => {
    console.log('Received pythonError:', errorMessage);
    let customMessage;
    const rateLimitErrorPattern = /openai\.RateLimitError/;

    // Setting the flag to true regardless of the error type for simplicity
    isErrorDetected = true;

    if (rateLimitErrorPattern.test(errorMessage)) {
        customMessage = "Error Detected: No more OpenAI Credits";
    } else {
        customMessage = "Error Detected: Please Restart Ultra";
    }

    // Process the message with the error flag set to true
    processMessage(customMessage, true);
});

const clearButton = document.getElementById('clear-button');
clearButton.addEventListener('click', () => {
    const outputDiv = document.getElementById('output');
    outputDiv.innerHTML = ''; // Clear all chat messages

    // Reset status indicator
    const statusIndicator = document.getElementById('status-indicator');
    statusIndicator.innerHTML = '<i class="fas fa-robot"></i> Chat Cleared';
    statusIndicator.className = 'status-action';

    // Optional: Emit event to server to clear conversation history
    socket.emit('clear_conversation');
});

function processMessage(message, isError) {
    if (isError) {
        setStatus(message, 'status-error', 'fas fa-exclamation-triangle');
        return;
    }
    let messageClass = '';

    if (message.includes("Listening for 'Alt+I'")) {
        setStatus("Listening for 'Alt+I'", 'status-ultra', 'fas fa-microphone');
        return;
    } else if (message.includes("Listening for prompt...")) {
        setStatus('Listening for Prompt', 'status-prompt', 'fas fa-user');
        return;
    } else if (message.includes("Loading...")) {
        setStatus('Loading', 'status-loading', 'fas fa-cog');
        return;
    } else if (message.includes("Getting mic ready...")) {
        setStatus('Preparing Microphone', 'status-loading', 'fas fa-cog');
        return;
    } else if (message.includes("[Processing request...]")) {
        setStatus('Processing Request', 'status-processing', 'fas fa-cog');
        return;
    } else if (message.startsWith("Ultra:")) {
        messageClass = 'ultra';
    } else if (message.startsWith("User:")) {
        messageClass = 'user';
    } else if (message.startsWith("[Ultra is")) {
        const actionText = message.match(/\[Ultra is (.+)\]/)[1];
        let iconClass;

        if (actionText.startsWith('calculating')) {
            iconClass = 'fas fa-calculator';
        } else if (actionText.startsWith('finding the current weather')) {
            iconClass = 'fas fa-cloud';
        } else if (actionText.startsWith('finding the current time')) {
            iconClass = 'fas fa-clock';
        } else if (actionText.startsWith('retrieving his memory')) {
            iconClass = 'fas fa-server';
        } else if (actionText.startsWith('searching for')) {
            iconClass = 'fab fa-spotify';
        } else if (actionText.startsWith('updating Spotify playback')) {
            iconClass = 'fab fa-spotify';
        } else if (actionText.startsWith('changing Spotify volume')) {
            iconClass = 'fab fa-spotify';
        } else if (actionText.startsWith('setting system volume')) {
            iconClass = 'fas fa-volume-high';
        } else if (actionText.startsWith('generating speech')) {
            iconClass = 'fas fa-cog';
        } else if (actionText.startsWith('speaking a response')) {
            iconClass = 'fas fa-comment-dots';
        } else if (actionText.startsWith('taking longer than expected')) {
            iconClass = 'fas fa-hourglass-half';
        } else {
            iconClass = 'fas fa-robot';
        }


        setStatus(actionText.charAt(0).toUpperCase() + actionText.slice(1), 'status-action', iconClass);
        return;
    }

    function setStatus(text, className, iconClass = '') {
        if (iconClass === 'fas fa-microphone' || iconClass === 'fas fa-user' ||
            iconClass === 'fas fa-comment-dots' ||
            iconClass === 'fas fa-hourglass-half') {
            statusIndicator.innerHTML = `<i class="${iconClass} jiggling"></i> ${text}`;
        } else if (iconClass === 'fas fa-cog') {
            statusIndicator.innerHTML = `<i class="${iconClass} rotating"></i> ${text}`;
        } else if (iconClass) {
            statusIndicator.innerHTML = `<i class="${iconClass} bouncing"></i> ${text}`;
        } else {
            statusIndicator.innerHTML = text;
        }
        statusIndicator.className = className;
    }

    if (messageClass === 'ultra' || messageClass === 'user') {
        const messageDiv = document.createElement('div');
        messageDiv.className = messageClass + ' common-style';

        const formattedText = message
        .replace(/(User:|Ultra:)/g, '<span class="bold-glow">$1</span>')
        .replace(/\n/g, '<br>');

        messageDiv.innerHTML = formattedText;
        messageDiv.style.minHeight = '40px';
        outputDiv.appendChild(messageDiv);
        scrollToBottom();

    }
}
