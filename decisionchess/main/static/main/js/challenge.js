const optionsDate = {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
};

const optionsTime = {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
};

document.addEventListener("DOMContentLoaded", function() {
    const timestampElements = document.querySelectorAll('.timestamp');
    timestampElements.forEach(element => {
        const isoTimestamp = element.getAttribute('data-timestamp');
        const utcDate = new Date(isoTimestamp);
        const localDate = utcDate.toLocaleDateString(undefined, optionsDate);
        const localTime = utcDate.toLocaleTimeString(undefined, optionsTime);
        element.textContent = `${localDate} ${localTime}`;
    });
});

function respondChallenge(accepted) {
    const urlSegments = window.location.pathname.split('/');
    const challengeId = urlSegments[urlSegments.length - 1];
    fetch('/save_challenge/', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({'accepted': accepted, 'challenge_id': challengeId}),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.message);
                });
            }
            return response.json();
        })
        .then(data => {                
            if (data.redirect) {
                window.location.href = data.url;
            } else if (!data.accepted) {
                clearInterval(connectIntervalId);
                document.getElementById('challenge-status').innerHTML = "Challenge Denied";
            }
        })
        .catch(error => {
            console.error('Error fetching message:', error);
        });
};

var socket;

function initializeWebSocket() {
    if (responded) {
        return;
    }
    if (window.location.protocol == 'https:') {
        wsProtocol = 'wss://';
    } else {
        wsProtocol = 'ws://';
    }
    const urlSegments = window.location.pathname.split('/');
    const challengeId = urlSegments[urlSegments.length - 1];
    socket = new WebSocket(wsProtocol + window.location.host + "/ws/challenge/" + challengeId + "/");

    socket.onmessage = function (event) {
        var chat_data = JSON.parse(event.data);
        handleMessage(chat_data["message"]);
    };

    socket.onclose = function (event) {
        $(".chat-input").prop("disabled", true);
    };

    $(".chat-input").prop("disabled", false);
}

var initialized = false;
function connect() {
    if (!initialized) {
        initializeWebSocket();
        initialized = true;
    } else if (initialized === true) {
        if (typeof socket !== 'undefined' && socket instanceof WebSocket && socket.readyState === WebSocket.CLOSED) {
            initializeWebSocket();
        }
    }
}

var connectIntervalId = setInterval(connect, 1000);

$(".chat-input").on('keydown', function (e) {
    if (e.keyCode === 13 || e.key === 'Enter') {
        e.preventDefault();  // Prevent the Enter key from creating a new line
        var message = $(this).val();
        if (socket && socket.readyState === WebSocket.OPEN) {
            sendMessage(message);
        }
        $(this).val('');  // Clear the input field
    }
});

function sendMessage(message) {
    var messageObj = {
        message: {
            text: message
        }
    };
    socket.send(JSON.stringify(messageObj));
}

function handleMessage(data) {
    if (data.hasOwnProperty('log')) {
        if (data["log"] === "connect") {
            challenger_connected = data["is_challenger"]
            if (challenger_connected && !is_challenger ||
                !challenger_connected && is_challenger) {
                appendChatLog(data["user"] + " connected", challenger_connected);
            }
        } else if (data["log"] === "disconnect") {
            challenger_disconnected = data["is_challenger"]
            if (challenger_disconnected && !is_challenger ||
                !challenger_disconnected && is_challenger) {
                appendChatLog(data["user"] + " disconnected...", challenger_disconnected);
            }
        } else if (data["log"] === "accepted") {
            window.location.href = data.url;
        } else if (data["log"] === "denied") {
            clearInterval(connectIntervalId);
            socket.close();
        } else if (
            data["log"] === "spam"
            ) {
            appendChatLog(data["text"], data["is_challenger"]);
        };
        return;
    }
    sender_is_challenger = data["is_challenger"];
    // Prevent XSS script injection attacks by escaping content
    var message = $('<p class="chat-message"></p>').text(data["text"])
        .addClass(sender_is_challenger ? 'ml-auto' : 'mr-auto');
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper';
    const newDiv = document.createElement('div');
    newDiv.className = 'chat-fill';
    if (sender_is_challenger) {  
        wrapper.appendChild(message[0]);
        wrapper.appendChild(newDiv);
    } else {
        wrapper.appendChild(newDiv);
        wrapper.appendChild(message[0]);
    };
    $(".chat-messages").append(wrapper);
}

function appendChatLog(message, sender_is_challenger) {
    var log = $('<p class="chat-message" style="width: 50%; text-align: center;"></p>').text(message);
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper';
    const newDiv = document.createElement('div');
    newDiv.className = 'chat-fill';
    if (sender_is_challenger) {  
        wrapper.appendChild(log[0]);
        wrapper.appendChild(newDiv);
    } else {
        wrapper.appendChild(newDiv);
        wrapper.appendChild(log[0]);
    };
    $(".chat-messages").append(wrapper);
}