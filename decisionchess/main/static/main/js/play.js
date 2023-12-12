function adjustFont() {
    const elements = document.querySelectorAll('.action-button');
    const parent = document.getElementById('command-center');
    elements.forEach(element => {
        if (210 < parent.offsetWidth && parent.offsetWidth < 320) {
            element.style.fontSize = '0.7rem';
        } else if (parent.offsetWidth < 210) {
            element.style.fontSize = '0.65rem';
        } else if (parent.offsetWidth >= 320) {
            element.style.fontSize = '1rem';
        }
    });
}

window.addEventListener('load', function() {
    var iframeContainer = document.getElementById('iframe-container');
    var width = iframeContainer.offsetWidth;
    document.getElementById('embedded-iframe').style.height = width + 'px';
    iframeContainer.style.height = width + 'px';
    document.getElementById('chat-box').style.height = width + 'px';
    document.getElementById('command-center').style.height = (width * 0.6) + 'px';
    adjustFont();

    document.getElementById('chat-input').value = '';
});

window.addEventListener('resize', function() {
    var iframeContainer = document.getElementById('iframe-container');
    var width = iframeContainer.offsetWidth;
    document.getElementById('embedded-iframe').style.height = width + 'px';
    iframeContainer.style.height = width + 'px';
    document.getElementById('chat-box').style.height = width + 'px';
    document.getElementById('command-center').style.height = (width * 0.6) + 'px';
    adjustFont();
});

function areArraysEqual(arr1, arr2) {
    if (arr1.length !== arr2.length) {
        return false;
    }
    for (var i = 0; i < arr1.length; i++) {
        if (arr1[i] !== arr2[i]) {
            return false;
        }
    }
    return true;
}

var gameSaved = false;
var signed_uuid = "";
var rematch_request = false;
var rematch_accepted = false;
var rematch_received = false;
var savedMoves = [];
var comp_moves = [];
var move_index = -1;
var selectedMoveId = "";
var promotion_lock = false;

function updateCommandCenter() {
    var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = (currentGameID === 'null' ? null : currentGameID);
    if (currentGameID !== null && existingWebGameMetadata.hasOwnProperty(currentGameID)) {
        var webGameMetadata = existingWebGameMetadata[currentGameID];
        var moves = webGameMetadata.alg_moves;
        var movesListContainer = document.getElementById('moves-list');
        var endState = webGameMetadata.end_state;
        comp_moves = webGameMetadata.comp_moves;
        const equal_arrays = areArraysEqual(moves, savedMoves)
        if (endState !== '' && !equal_arrays) {
            const buttons = document.querySelectorAll(".action-button:not([post-game=true])");
            clearInterval(requestIntervalId);
            clearInterval(connectIntervalId);
            buttons.forEach(button => {
                button.remove();
            });
        }
        promoting = sessionStorage.getItem('promoting');
        promoting = (promoting === 'true' ? true : false);
        if (promotion_lock !== promoting) {
            const stepButtons = ["skipBackwardButton", "backwardButton", "forwardButton", "skipForwardButton"];
            if (promoting) {
                stepButtons.forEach(buttonId => {
                    document.getElementById(buttonId).classList.add("used");
                    document.getElementById(buttonId).disabled = true;
                });
            } else {
                stepButtons.forEach(buttonId => {
                    document.getElementById(buttonId).classList.remove("used");
                    document.getElementById(buttonId).disabled = false;
                });
            }
            promotion_lock = promoting;
        }
        // Don't keep unnecessarily updating
        if (equal_arrays) {
            return;
        } 
        savedMoves = moves;
        
        movesListContainer.innerHTML = '';

        for (var i = 0; i < moves.length; i += 2) {
            var move1 = moves[i];
            var move2 = (
                (i + 1 < moves.length) && 
                moves[i + 1] !== '1-0' && 
                moves[i + 1] !== '0-1' && 
                moves[i + 1] !== '½–½'
            ) ? moves[i + 1] : '';

            var moveRow = document.createElement('div');
            moveRow.className = 'move-row ' + (i % 4 === 0 ? '' : 'even-move-row');
            
            var leftHalf = document.createElement('button');
            leftHalf.style.width = '50%';
            leftHalf.textContent = move1;
            leftHalf.className = 'move-button';
            leftHalf.setAttribute('move-index', i);
            leftHalf.id = 'move-' + i;

            var rightHalf = (move2 === "" ? document.createElement('div'): document.createElement('button'));
            rightHalf.style.width = '50%';
            rightHalf.textContent = move2;
            if (move2 !== '') {
                rightHalf.className = 'move-button';
                rightHalf.setAttribute('move-index', i + 1);
                rightHalf.id = 'move-' + (i + 1);
            }

            if (move1 !== '1-0' && move1 !== '0-1' && move1 !== '½–½') {
                moveRow.appendChild(leftHalf);
                moveRow.appendChild(rightHalf);

                movesListContainer.appendChild(moveRow);
                movesListContainer.scrollTop = movesListContainer.scrollHeight;
                if (leftHalf.id) {
                    (function(id) {
                        leftHalf.addEventListener("click", function() {
                            handleButton(id, "step");
                        });
                    })(leftHalf.id);
                }
                
                if (rightHalf.id) {
                    (function(id) {
                        rightHalf.addEventListener("click", function() {
                            handleButton(id, "step");
                        });
                    })(rightHalf.id);
                }
            }

        }

        if (endState === "\u00bd\u2013\u00bd") {
            endState = '½–½';
        }
        var forcedEnd = webGameMetadata.forced_end;
        var endMessagebox = document.getElementById('end-message');
        var finalScorebox = document.getElementById('final-score');
        var endmessage = '';
        if (forcedEnd !== '') {
            if (forcedEnd === 'Draw by mutual agreement' || forcedEnd === 'Stalemate by Threefold Repetition') {
                endmessage += forcedEnd;
                finalScorebox.innerHTML = '½–½';
            } else {
                endmessage += forcedEnd + ' • ';
            }
            finalScorebox.classList.add('mt-2');
        }

        if (endState === '1-0') {
            endmessage += `White is Triumphant`;
            endMessagebox.innerHTML = `White is Triumphant`;
            finalScorebox.innerHTML = '1-0';
        } else if (endState === '0-1') {
            endmessage += `Black is Triumphant`;
            finalScorebox.innerHTML = '0-1';
        } else if (endState === '½–½' && forcedEnd !== 'Draw by mutual agreement' && forcedEnd !== 'Stalemate by Threefold Repetition') {
            endmessage += `Stalemate was Reached`;
            finalScorebox.innerHTML = '½–½';
        }

        if (endmessage !== '') {
            endMessagebox.innerHTML = endmessage;
            if (!gameSaved) { // Only execute this once
                gameSaved = true
                comp_moves = webGameMetadata.comp_moves;
                var FEN_final = webGameMetadata.FEN_final_pos;
                saveHistoricGame(moves.join(','), comp_moves.join('-'), endState, FEN_final, forcedEnd);
            }
            
            if (!rematch_received) {
                // Race/page visibility conditions can hit this second if page is returned to after hiding it
                document.getElementById("rematchButton").classList.remove("hidden");
            } 
            document.getElementById("rematchButton").addEventListener("click", function() {
                fetchUUID().then(data => {
                    signed_uuid = data.uuid;
                    sendMessage(signed_uuid, "rematch_request");
                });
                rematch_request = true;
                document.getElementById("rematchButton").disabled = true;
            }, {once: true});
        }
        if (selectedMoveId !== "") {
            var previousMove = document.getElementById(selectedMoveId);
            // Check for existence as undos can remove previously selected move elements
            if (previousMove) {
                previousMove.disabled = false;
            }
        }
        move_index = comp_moves.length - 1;
        moveId = 'move-' + move_index;
        if (move_index !== -1) {
            document.getElementById(moveId).disabled = true;
            selectedMoveId = moveId;
        }
    }
}

function saveHistoricGame(alg_moves_str, comp_moves_str, score, FEN_final, forcedEnd) {
    fetch('/save_game/', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ 
            game_uuid: game_uuid,
            alg_moves: alg_moves_str,
            outcome: score,
            comp_moves: comp_moves_str,
            FEN: FEN_final,
            termination_reason: forcedEnd
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "error") {
            return;
        }
    })
    .catch(error => {
        console.error('Error uploading game:', error);
    });
}

function fetchUUID(signed_uuid = null, current_game_id = null) {
    let optionalData = {}
    if (signed_uuid) {
        optionalData["signed_uuid"] = signed_uuid;
        optionalData["recent_game_id"] = current_game_id;
    }
    return fetch('/get_private_id/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify(optionalData),
        })
        .then(response => {
            if (response.status === 200) {
                return response.json();
            } else {
                console.error('Error generating key:', response.statusText);
                return Promise.reject('Error generating key');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

function resetCommandCenter() {
    savedMoves = [];
    selectedMoveId = "";
    var movesListContainer = document.getElementById('moves-list');
    while (movesListContainer.firstChild) {
        movesListContainer.removeChild(movesListContainer.firstChild);
    }

    var endMessagebox = document.getElementById('end-message');
    var finalScorebox = document.getElementById('final-score');

    movesListContainer.innerHTML = "";
    endMessagebox.innerHTML = ""
    finalScorebox.innerHTML = ""
}

var previousConnected = false
var initCheck = false

window.addEventListener('load', resetCommandCenter);
window.addEventListener('load', updateCommandCenter);

setInterval(updateCommandCenter, 100);

var socket;

function initializeWebSocket() {
    socket = new WebSocket("ws://" + window.location.host + "/ws/chat/" + game_uuid + "/");

    socket.onmessage = function (event) {
        var chat_data = JSON.parse(event.data);
        handleMessage(chat_data["message"]);
    };

    socket.onopen = function () {
        sendMessage("", "initialized");
    }

    socket.onclose = function (event) {
        // add custom chat highlighted message
        $("#chat-input").prop("disabled", true);
    };

    $("#chat-input").prop("disabled", false);
}

$("#chat-input").keypress(function (e) {
    if (e.which === 13) {  // 13 is the Enter key code
        e.preventDefault();  // Prevent the Enter key from creating a new line
        var message = $(this).val();
        if (socket && socket.readyState === WebSocket.OPEN) {
            sendMessage(message);
        }
        $(this).val('');  // Clear the input field
    }
});

function sendMessage(message, type = null) {
    var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = (currentGameID === 'null' ? null : currentGameID);
    if (currentGameID !== null && existingWebGameMetadata.hasOwnProperty(currentGameID)) { 
        var webGameMetadata = existingWebGameMetadata[currentGameID];
        var playerColor = webGameMetadata["player_color"];
        var messageObj = {
            message: {
                text: message,
                color: playerColor,
                sender: sender,
                end_state: webGameMetadata["end_state"]
            }
        };
        if (type !== null) {
            if (type.includes("rematch") || type === "initialized") {
                messageObj["message"]["log"] = type;
                if (type == "initialized") {
                    messageObj["message"]["opponent"] = opponent;
                }
            }
        }
        socket.send(JSON.stringify(messageObj));
    } else {
        console.warn("Cannot send message");
    }
}

function handleMessage(data) {
    if (data.hasOwnProperty('log')) {
        var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
        var currentGameID = sessionStorage.getItem('current_game_id');
        var playerColor;
        currentGameID = (currentGameID === 'null' ? null : currentGameID);
        if (currentGameID !== null && existingWebGameMetadata.hasOwnProperty(currentGameID)) { 
            playerColor = existingWebGameMetadata[currentGameID]["player_color"];
        } else {
            return;
        }
        if (data["log"] === "connect") {
            connect_user = data["user"];
            // Exclude spectators later
            // Add highlighted message to chat if opponent is the same
        } else if (data["log"] === "initialized") {
            connect_user = data["sender"];
            player = data["opponent"];
            opponent_color = data["color"];
            if ((connect_user !== opponent || player !== sender) && opponent_color !== playerColor) {
                // Assuming top is always opponent to start is fine
                opponentContent = document.getElementById('topPlayer');
                opponent = (connect_user !== "black" && connect_user !== "white") ? connect_user : "Anonymous"; // prevent these two usernames
                opponentContent.innerHTML = opponent;
                if (player !== sender) {
                    sendMessage("", "initialized");
                }
            }
        } else if (data["log"] === "disconnect") {
            // Add highlighted message to chat
            if (rematch_accepted) {
                fetchUUID(signed_uuid, currentGameID).then(data => {
                    window.location.href = '/play/' + data.uuid + '/';
                });
            }
            if (rematch_request) {
                document.getElementById("rematchButton").classList.add("used");
            }
        } else if (data["log"] === "rematch_request" && !rematch_request) {
            rematch_received = true
            signed_uuid = data["text"];
            document.getElementById("rematchButton").disabled = true;
            showOptions("rematchButton", "rematchAcceptButton", "rematchDenyButton");
            document.getElementById("rematchAcceptButton").addEventListener("click", function() {
                document.getElementById("rematchAcceptButton").remove();
                document.getElementById("rematchDenyButton").remove();
                document.getElementById("rematchButton").classList.remove("hidden");
                document.getElementById("rematchButton").classList.add("used");
                rematch_accepted = true;
                sendMessage("", "rematch_accepted");
            }, {once: true});
            document.getElementById("rematchDenyButton").addEventListener("click", function() {
                document.getElementById("rematchAcceptButton").remove();
                document.getElementById("rematchDenyButton").remove();
                document.getElementById("rematchButton").classList.remove("hidden");
                document.getElementById("rematchButton").classList.add("used");
                sendMessage("", "rematch_declined");
            }, {once: true});
        } else if (data["log"] === "rematch_accepted") {
            $(".chat-messages").append('<p>Rematch Accepted...</p>');
            rematch_accepted = true;
            if (!rematch_received) {
                let new_game_id;
                fetchUUID(signed_uuid, currentGameID).then(data => {
                    new_game_id = data.uuid;
                    generateRematchURL(playerColor, new_game_id);
                });
                document.getElementById("rematchButton").classList.add("used");
            }
        } else if (data["log"] === "rematch_declined") {
            document.getElementById("rematchButton").classList.add("used");
            $(".chat-messages").append('<p>Declined Rematch</p>');
        }
        return;
    }
    // Prevent XSS script injection attacks by escaping content
    var message = $('<p></p>').text(data["sender"] + ": " + data["text"]);
    $(".chat-messages").append(message);
}

function generateRematchURL(position, game_id) {
    if (position !== "white" && position !== "black") {
        return console.error('Invalid position input')
    }
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = currentGameID.replace(position + '-', '');
    body = {"position": position, "rematch": currentGameID};
    fetch('/create_new_game/' + game_id + '/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify(body),
    })
    .then(response => {
        if (response.status === 200) {
            return response.json();
        } else {
            console.error('Error creating game:', response.statusText);
            return Promise.reject('Error creating game');
        }
    })
    .then(data => {
        if (data.redirect) {
            window.location.href = data.url;
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function updateConnectedStatus(status, playerColor) {
    fetch('/update_connected/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ 
            game_uuid: game_uuid, 
            web_connect: status,
            color: playerColor
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "error" && data.message === "Lobby row DNE") {
            return;
        }
        // Handle the response as needed
        // Put in a "waiting message" if it hasn't been played yet
        // Put a disconnect status if in play
        // Later have reconnects connect to the websocket and 
        // any disconnects disconnect from the websocket can have 
        // a variable tracking socket connection status
    })
    .catch(error => {
        console.error('Error updating connection status:', error);
    });
}

function checkNewConnect() {
    var currentConnected = sessionStorage.getItem('connected');
    var playerColor = sessionStorage.getItem('color');
    currentConnected = (currentConnected === 'true' ? true : false);
    if (currentConnected !== previousConnected) {
        if (playerColor !== null && (playerColor === 'white' || playerColor === 'black')) {
            updateConnectedStatus(currentConnected, playerColor);
        } else {
            return;
        }
    }
    
    var initialized = sessionStorage.getItem('initialized');
    initialized = (initialized === 'true' ? true : false);
    if (initialized === true && initCheck === false) {
        const idStrings = [
            "skipBackwardButton", 
            "backwardButton", 
            "forwardButton", 
            "skipForwardButton", 
            "undoOfferButton", 
            "resignButton", 
            "drawOfferButton", 
            "cycleThemeButton", 
            "flipButton"
        ];

        var buttonsWithMoveIndex = document.querySelectorAll('.move-button');
        buttonsWithMoveIndex.forEach(button => {
            idStrings.push(button.id);
        });

        idStrings.forEach(idString => {
            document.getElementById(idString).classList.remove("hidden");
        })
        initializeWebSocket();
        initCheck = initialized;
    } else if (initialized === true && currentConnected === true) {
        if (typeof socket !== 'undefined' && socket instanceof WebSocket && socket.readyState === WebSocket.CLOSED) {
            initializeWebSocket();
        }
    }

    previousConnected = currentConnected;
}

var connectIntervalId = setInterval(checkNewConnect, 1000);

window.onbeforeunload = function () {
    if (!rematch_accepted) {
        return true;
    }
};

// to defaults, not connected though as that would send a request
window.addEventListener('beforeunload', function () {
    sessionStorage.setItem('current_game_id', game_uuid);
    sessionStorage.setItem('initialized', 'null');
    sessionStorage.setItem('draw_request', 'false');
    sessionStorage.setItem('undo_request', 'false');
    sessionStorage.setItem('total_reset', 'false');
    sessionStorage.setItem('promoting', 'false');
});

var eventExecutionStatus = {};

function handleWebtoGameAction(buttonId, localStorageObjectName, Options = null) {
    var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = (currentGameID === 'null' ? null : currentGameID);
    if (currentGameID !== null && existingWebGameMetadata.hasOwnProperty(currentGameID)) { 
        var webGameMetadata = existingWebGameMetadata[currentGameID];
        webGameMetadata[localStorageObjectName].execute = true;
        existingWebGameMetadata[currentGameID] = webGameMetadata;
        if (localStorageObjectName == "step") {
            // Could move this block into it's own function later
            if (
                move_index + 1 >= comp_moves.length && buttonId.toLowerCase().includes("forward") || 
                move_index < 0 && buttonId === "backwardButton"
            ) {
                webGameMetadata[localStorageObjectName].execute = false;
                webGameMetadata[localStorageObjectName].index = null;
                existingWebGameMetadata[currentGameID] = webGameMetadata;
                localStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));
                
                document.getElementById(buttonId).disabled = false;
                return;
            }
            if (buttonId === "forwardButton" || buttonId === "skipForwardButton") {
                index_number = (buttonId === "forwardButton" ? move_index + 1 : comp_moves.length - 1);

            } else if (buttonId === "backwardButton" || buttonId === "skipBackwardButton") {
                index_number = (buttonId === "backwardButton" ? move_index : -1);
            } else {
                index_number = parseInt(document.getElementById(buttonId).getAttribute('move-index'), 10);
                index_number = (index_number < move_index ? index_number + 1 : index_number);
            }
            webGameMetadata[localStorageObjectName].index = index_number;
        }
        localStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));

        if (!eventExecutionStatus[localStorageObjectName]) {
            eventExecutionStatus[localStorageObjectName] = { isExecuting: false, timeoutId: null };
        }

        handleActionStatus(buttonId, currentGameID, localStorageObjectName, Options);

    } else {
        console.warn("Failed to execute action");
    }
}

// This is filled in the handleButton function later
var offerQueue = [];
function dequeButton(mainButtonId) {
    return new Promise((resolve, reject) => { 
        offerQueue = offerQueue.filter(item => item.mainId !== mainButtonId);
        resolve(offerQueue);
    });
}

var offerEventList = [
    {mainButtonName: "drawOfferButton", eventNames: ["draw_offer", "draw_offer_accept", "draw_offer_deny"]},
    {mainButtonName: "undoOfferButton", eventNames: ["undo_move", "undo_move_accept", "undo_move_deny"]},
]

var actionEventList = [
    {mainButtonName: "drawOfferButton", eventNames: ["draw_offer", "draw_offer_accept", "draw_offer_deny"]},
    {mainButtonName: "undoOfferButton", eventNames: ["undo_move", "undo_move_accept", "undo_move_deny"]},
    {mainButtonName: "resignButton", eventNames: ["resign"]}
]

var inputList = [
    { buttonId: "forwardButton", localStorageObjectName: "step"},
    { buttonId: "backwardButton", localStorageObjectName: "step"},
    { buttonId: "skipForwardButton", localStorageObjectName: "step"},
    { buttonId: "skipBackwardButton", localStorageObjectName: "step"},
    { buttonId: "undoOfferButton", localStorageObjectName: "undo_move", Options: "followups", action: "undo_request"},
    { buttonId: "drawOfferButton", localStorageObjectName: "draw_offer", Options: "followups", action: "draw_request" },
    { buttonId: "resignButton", localStorageObjectName: "resign", Options: "followups"},
    { buttonId: "cycleThemeButton", localStorageObjectName: "cycle_theme"},
    { buttonId: "flipButton", localStorageObjectName: "flip_board"},
];

function buttonHandling(buttonId, webGameMetadata, localStorageObjectName) {
    if (localStorageObjectName == "step") {
        webGameMetadata[localStorageObjectName].index = null;
        if (buttonId === "forwardButton") {
            move_index++;
        } else if (buttonId === "backwardButton") {
            move_index--;
        } else if (buttonId === "skipForwardButton") {
            move_index = comp_moves.length - 1;
        } else if (buttonId === "skipBackwardButton") {
            move_index = -1;
        } else {
            move_index = parseInt(document.getElementById(buttonId).getAttribute('move-index'), 10);
        }
        moveId = 'move-' + move_index;
        if (move_index !== -1) {
            document.getElementById(moveId).disabled = true;
        }
        if (selectedMoveId !== "") {
            document.getElementById(selectedMoveId).disabled = false;
        }
        selectedMoveId = (move_index !== -1 ? moveId: "");
    } else if (localStorageObjectName == "flip_board") {
        topElement = document.getElementById('topPlayer');
        bottomElement = document.getElementById('bottomPlayer');
        topHTML = topElement.innerHTML;
        bottomHTML = bottomElement.innerHTML;
        topElement.innerHTML = bottomHTML;
        bottomElement.innerHTML = topHTML;
    }
    return webGameMetadata;
}

function handleActionStatus(buttonId, currentGameID, localStorageObjectName, Options) {
    var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
    var webGameMetadata = existingWebGameMetadata[currentGameID];
    var actionCommandStatus = webGameMetadata[localStorageObjectName];
    
    // console.log(localStorageObjectName, actionCommandStatus) // Good dev log, very good boy
    var initialDefaults = (!actionCommandStatus.execute && !actionCommandStatus.update_executed);
    var optionalReset = false;
    if (actionCommandStatus.hasOwnProperty("reset")) {
        initialDefaults = initialDefaults && !actionCommandStatus.reset;
        optionalReset = actionCommandStatus.reset;
    }
    if (!actionCommandStatus.update_executed && optionalReset !== true && !initialDefaults) {
        eventExecutionStatus[localStorageObjectName].timeoutId = setTimeout(function () {
            // This can be too fast and execute again right before reset is set to false, 
            // hence the default condition check
            handleActionStatus(buttonId, currentGameID, localStorageObjectName, Options);
        }, 10);
    } else {
        var accept_response_sent = localStorageObjectName.includes("accept") && webGameMetadata[localStorageObjectName].update_executed;
        webGameMetadata[localStorageObjectName].execute = false;
        webGameMetadata[localStorageObjectName].update_executed = false;
        
        webGameMetadata = buttonHandling(buttonId, webGameMetadata, localStorageObjectName);

        if (optionalReset === true) {
            resetButtons(buttonId, localStorageObjectName, Options);
            webGameMetadata[localStorageObjectName].reset = false;
        }
        var totalReset = JSON.parse(sessionStorage.getItem("total_reset"));
        if (totalReset) {
            // Need to reset all active offer buttons
            offerEventList.forEach(function(event) {
                for (var i = 0; i < event.eventNames.length; i++) {
                    var subOptions = i === 0 ? "followups" : "responses";
                    const offerEvent = document.getElementById(event.mainButtonName)
                    // Check for ids that could be removed on end game reached but totalreset is still set
                    if (offerEvent) {
                        offerEvent.classList.remove("waiting");
                        offerEvent.disabled = false;
                        resetButtons(event.mainButtonName, subOptions);
                    }
                }
            });
            sessionStorage.setItem("total_reset", 'false');
        }
        // We don't want to clear the offer queue on follow-ups or simple client actions or deny (individual resets)
        // Only on accepts, main actions accepts, and total resets
        var offer_accepted_received = offerEventList.some(item => item.eventNames[0] === localStorageObjectName)
        if (accept_response_sent || offer_accepted_received || totalReset) {
            offerQueue = [];
        }

        existingWebGameMetadata[currentGameID] = webGameMetadata;
        localStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));
        
        if (buttonId.includes("move")) {
            return;
        }
        // Resign or draw can quickly remove the button before this, even an undo offer if end game is reached
        element = document.getElementById(buttonId);
        if (element) {
            element.disabled = false;
        }
    }
}

function optionStringsHelper(mainbuttonId, Options) {
    var approveString = "Confirm";
    var abandonString = "Cancel";
    var replaceString = "Button";
    if (Options === "responses") {
        approveString = "Accept";
        abandonString = "Deny";
        replaceString = "OfferButton";
    }
    const buttonApproveId = mainbuttonId.replace(replaceString, approveString + "Button");
    const buttonAbandonId = mainbuttonId.replace(replaceString, abandonString + "Button");
    return {ApproveId: buttonApproveId, AbandonId: buttonAbandonId, AbandonStr: abandonString};
}

function hideOptions(buttonId, buttonApproveId, buttonAbandonId) {
    document.getElementById(buttonId).classList.remove("hidden");
    document.getElementById(buttonApproveId).classList.add("hidden");
    document.getElementById(buttonAbandonId).classList.add("hidden");
}

function showOptions(buttonId, buttonApproveId, buttonAbandonId) {
    document.getElementById(buttonId).classList.add("hidden");
    document.getElementById(buttonApproveId).classList.remove("hidden");
    document.getElementById(buttonAbandonId).classList.remove("hidden");
}

function resetButtons(mainbuttonId, Options) {
    result = optionStringsHelper(mainbuttonId, Options);
    const buttonApproveId = result.ApproveId;
    const buttonAbandonId = result.AbandonId;
    hideOptions(mainbuttonId, buttonApproveId, buttonAbandonId);
    var matchingInput = inputList.find(item => item.buttonId === mainbuttonId);
    sessionStorage.setItem(matchingInput["action"], 'false');
}

inputList.forEach(function(input) {
    const optionsValue = (input.hasOwnProperty("Options") ? input.Options: null);
    document.getElementById(input.buttonId).addEventListener("click", function() {
        handleButton(input.buttonId, input.localStorageObjectName, optionsValue);
    });
});

var requestChangeTrackers = {};

function requestDisplay(action, ButtonID, baseStorageName) {
    var currentValue = JSON.parse(sessionStorage.getItem(action));
    var currentGameID = sessionStorage.getItem('current_game_id');
    var initialized = sessionStorage.getItem('initialized');
    currentGameID = (currentGameID === 'null' ? null : currentGameID);
    initialized = (initialized === 'true' ? true : null);
    var resetDisplay = null
    
    var newOptions = (currentValue === true ? "responses": "followups")
    if (currentGameID !== null && initialized === true) {
        const acceptObjectName = baseStorageName + "_accept";
        const denyObjectName = baseStorageName + "_deny";
        var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
        var acceptReset = existingWebGameMetadata[currentGameID][acceptObjectName].reset;
        var denyReset = existingWebGameMetadata[currentGameID][denyObjectName].reset;
        var totalReset = JSON.parse(sessionStorage.getItem("total_reset"));
        resetDisplay = acceptReset || denyReset || totalReset;
    }
    if (currentValue === null || currentValue === requestChangeTrackers[action]) {
        if (resetDisplay === null || resetDisplay === false) {
            return;
        }
    } else {
        requestChangeTrackers[action] = currentValue;
    }
    
    if (currentValue === true || resetDisplay === true) {
        handleButton(ButtonID, baseStorageName, newOptions, resetDisplay, action);
    }
}

var requestIntervalId = setInterval(function() {
    inputList.forEach(function(request) {
        if (request.hasOwnProperty('action')) {
            requestDisplay(request.action, request.buttonId, request.localStorageObjectName);
        }
    });
}, 100);

function eventIsExecuting(obj, eventNames) {
    for (var event of eventNames) {
        if (obj.hasOwnProperty(event) && obj[event]["execute"] === true) {
            return true;
        }
    }
    return false;
}

function showNewOptions(offerQueue) {
    if (offerQueue.length !== 0) {
        var newDisplay = offerQueue[0];
        showOptions(newDisplay.mainId, newDisplay.ApproveId, newDisplay.AbandonId)
    }
}

function handleButton(buttonId, localStorageObjectName, Options = null, resetDisplay = null, currentAction = null) {
    document.getElementById(buttonId).disabled = true;
    if (Options !== null) {
        result = optionStringsHelper(buttonId, Options)
        const buttonApproveId = result.ApproveId;
        const buttonAbandonId = result.AbandonId;
        const abandonString = result.AbandonStr;
        const acceptObjectName = localStorageObjectName + "_accept";
        const denyObjectName = localStorageObjectName + "_deny";
        if (resetDisplay !== true) {
            document.getElementById(buttonId).classList.add("hidden");
            document.getElementById(buttonApproveId).classList.remove("hidden");
            document.getElementById(buttonAbandonId).classList.remove("hidden");
            var otherFollowups = document.querySelectorAll('[followup="true"]');
            if (Options === "responses") {
                document.getElementById(buttonId).classList.add("waiting")
                offerQueue.push({mainId: buttonId, ApproveId: buttonApproveId, AbandonId: buttonAbandonId})
            }
            otherFollowups.forEach(function(element) {
                if (element.id !== buttonApproveId && element.id !== buttonAbandonId) {
                    element.classList.add("hidden");
                }
            });
            var actionbuttons = document.querySelectorAll('[actions="true"]');
            var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
            var currentGameID = sessionStorage.getItem('current_game_id');
            var webGameMetadata = existingWebGameMetadata[currentGameID];
            
            // On followup display only, main buttons are disabled. We need to re-enable them
            // This does not apply to executing or queued actions
            actionbuttons.forEach(function(element) {
                if (element.id !== buttonId) {
                    element.classList.remove("hidden");
                    var actionEvents = actionEventList.find(event => event.mainButtonName === element.id);
                    var notQueued = offerQueue.every(item => item.mainId !== element.id);
                    var notExecuting = !eventIsExecuting(webGameMetadata, actionEvents.eventNames);
                    if (notExecuting && notQueued) {
                        element.disabled = false;
                    }
                }
            });
            document.getElementById(buttonApproveId).addEventListener("click", function() { 
                hideOptions(buttonId, buttonApproveId, buttonAbandonId);
                if (Options === "responses") {
                    document.getElementById(buttonId).classList.remove("waiting");
                    dequeButton(buttonId)
                        .then(updatedQueue => {
                            offerQueue = updatedQueue;
                            showNewOptions(offerQueue);
                        });
                } else {
                    showNewOptions(offerQueue);
                }
                
                var responseName = (Options === "followups" ? localStorageObjectName : acceptObjectName)
                
                handleWebtoGameAction(buttonId, responseName, Options);
            }, { once: true });
            document.getElementById(buttonAbandonId).addEventListener("click", function() {
                hideOptions(buttonId, buttonApproveId, buttonAbandonId);
                if (Options === "responses") {
                    document.getElementById(buttonId).classList.remove("waiting");
                    dequeButton(buttonId)
                        .then(updatedQueue => {
                            offerQueue = updatedQueue;
                            showNewOptions(offerQueue);
                        });
                } else {
                    showNewOptions(offerQueue)
                }
                
                if (abandonString !== "Cancel") {
                    handleWebtoGameAction(buttonId, denyObjectName, Options);
                }
                document.getElementById(buttonId).disabled = false;
            }, { once: true });
        } else {
            hideOptions(buttonId, buttonApproveId, buttonAbandonId)
            // We should not call the second block given a total reset, previously it was first in order but the response was delayed.
            // Hence, it showed the next queued item after the totalReset already hid it
            var totalReset = JSON.parse(sessionStorage.getItem("total_reset"));
            if (totalReset) {
                offerQueue = [];
                // Need to reset all displayed offer buttons
                offerEventList.forEach(function(event) {
                    for (var i = 0; i < event.eventNames.length; i++) {
                        const offerEvent = document.getElementById(event.mainButtonName);
                        // Check for ids that could be removed on end game reached but totalreset is still set
                        if (offerEvent) {
                            offerEvent.classList.remove("waiting");
                            offerEvent.disabled = false;
                            var subOptions = i === 0 ? "followups" : "responses";
                            resetButtons(event.mainButtonName, subOptions);
                        }
                    }
                });
                sessionStorage.setItem("total_reset", 'false');
            } else if (Options === "responses") {
                document.getElementById(buttonId).classList.remove("waiting");
                dequeButton(buttonId)
                    .then(updatedQueue => {
                        offerQueue = updatedQueue;
                        showNewOptions(offerQueue);
                    });
            } else {
                showNewOptions(offerQueue);
            }

            var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
            var currentGameID = sessionStorage.getItem('current_game_id');
            var webGameMetadata = existingWebGameMetadata[currentGameID];
            webGameMetadata[localStorageObjectName].reset = false;
            webGameMetadata[acceptObjectName].reset = false;
            webGameMetadata[denyObjectName].reset = false;
            existingWebGameMetadata[currentGameID] = webGameMetadata;
            
            sessionStorage.setItem(currentAction, 'false');
            localStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));
            document.getElementById(buttonId).disabled = false;
        }
    } else {
        handleWebtoGameAction(buttonId, localStorageObjectName);
    };
}

// // Logging Debug python console messages; Only for development hence keep it commented. Maybe add a global dev flag too
// function pythonDebugLogger() {
//     var logs = webGameMetadata.console_messages
//     for (var i = 0; i < logs.length; i++) {
//         console.log(logs[i])
//     }
// }

// window.addEventListener('load', pythonDebugLogger);

// // Set up an interval to log debug print statements
// setInterval(pythonDebugLogger, 1000);