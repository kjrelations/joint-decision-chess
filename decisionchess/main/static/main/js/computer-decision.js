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
    document.getElementById('chat-box-mobile').style.height = (width * 0.3) + 'px';
    var isSmallScreen = window.matchMedia('(max-width: 767px)').matches;
    var commandCenterHeight = isSmallScreen ? (width * 0.5) : (width * 0.6);
    document.getElementById('command-center').style.height = commandCenterHeight + 'px';
    adjustFont();
});

window.addEventListener('resize', function() {
    var iframeContainer = document.getElementById('iframe-container');
    var width = iframeContainer.offsetWidth;
    document.getElementById('embedded-iframe').style.height = width + 'px';
    iframeContainer.style.height = width + 'px';
    document.getElementById('chat-box').style.height = width + 'px';
    var isSmallScreen = window.matchMedia('(max-width: 767px)').matches;
    var commandCenterHeight = isSmallScreen ? (width * 0.5) : (width * 0.6);
    document.getElementById('command-center').style.height = commandCenterHeight + 'px';
    adjustFont();
});

function handleVisibilityChange() {
    if (document.hidden) {
      sessionStorage.setItem('muted', 'true');
    } else {
      sessionStorage.setItem('muted', 'false');
  }
}

document.addEventListener('visibilitychange', handleVisibilityChange);

function areEqual(obj1, obj2, type) {
    if (type === 'array') {
        if (obj1.length !== obj2.length) {
            return false;
        }

        for (var i = 0; i < obj1.length; i++) {
            if (Array.isArray(obj1[i])) {
                return areEqual(obj1[i], obj2[i], 'array');
            } else if (obj1[i] !== obj2[i]) {
                return false;
            }
        }
    } else if (type === 'object') {
        const keys1 = Object.keys(obj1);
        const keys2 = Object.keys(obj2);

        if (keys1.length !== keys2.length) {
            return false;
        }

        for (let key of keys1) {
            if (obj1[key] !== obj2[key]) {
                return false;
            }
        }
    }
    return true;
}

function changeFavicon(index) {
    const favicon = document.getElementById('favicon');
    const faviconShort = document.getElementById('favicon-short');
    if (index >= 0 && index < faviconImages.length) {
        favicon.href = faviconImages[index];
        faviconShort.href = faviconImages[index];
    }
}

let currentIndex = 0;
var alternatingFavicon = false;
function faviconInterval() {
    changeFavicon(currentIndex);
    currentIndex = (currentIndex + 1) % faviconImages.length;
}

var faviconIntervalId;

var gameSaved = false;
var rematch_accepted = false;
var savedMoves = [];
var savedPieces = {};
var savedStates = [];
var comp_moves = [];
var move_index = -1;
var selectedMoveId = "";
var promotion_lock = false;
var flipped = false;

function movePieceTranslation(move) {
    var newMove = move
        .replace('K', '♔')
        .replace('Q', '♕')
        .replace('R', '♖')
        .replace('B', '♗')
        .replace('N', '♘')
        .replace('P', '♙');
    return newMove;
}

function updateCommandCenter() {
    var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    if (webGameMetadata === null || Object.keys(webGameMetadata).length === 0) {
        return;
    }
    var moves = webGameMetadata.alg_moves;
    var movesListContainer = document.getElementById('moves-list');
    var endState = webGameMetadata.end_state;
    comp_moves = webGameMetadata.comp_moves;
    const equal_arrays = areEqual(moves, savedMoves, 'array');
    if (endState !== '' && !equal_arrays) {
        const buttons = document.querySelectorAll(".action-button:not([post-game=true])");
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

    var netPieces = webGameMetadata.net_pieces;
    if (!areEqual(savedPieces, netPieces, 'object')) {
        savedPieces = netPieces;
        var topPieces = document.getElementById('topPieces');
        var bottomPieces = document.getElementById('bottomPieces');
        topPieces.innerHTML = '';
        bottomPieces.innerHTML = '';
        var playerPieces = !flipped ? bottomPieces : topPieces;
        var opponentPieces = !flipped ? topPieces : bottomPieces;
        pawnSum = netPieces['p'];
        bishopSum = netPieces['b'];
        knightSum = netPieces['n'];
        rookSum = netPieces['r'];
        queenSum = netPieces['q'];
        const piecesList = [queenSum, rookSum, knightSum, bishopSum, pawnSum];
        var score = 0;
        const color = webGameMetadata.player_color;

        for (let i = 0; i < piecesList.length; i++) {
            if (piecesList[i] !== 0) {
                var content = document.createElement('img');
                content.className = 'scaled-pieces';
                if (i === 0) {
                    content.src = queensrc;
                    score += piecesList[i] * 9;
                } else if (i === 1) {
                    content.src = rooksrc;
                    score += piecesList[i] * 5;
                } else if (i === 2) {
                    content.src = knightsrc;
                    score += piecesList[i] * 3;
                } else if (i === 3) {
                    content.src = bishopsrc;
                    score += piecesList[i] * 3;
                } else {
                    content.src = pawnsrc;
                    score += piecesList[i];
                }
                const playerSum = color === 'white' ? piecesList[i] > 0 : piecesList[i] < 0;
                if (playerSum) {
                    for (let j = 0; j < Math.abs(piecesList[i]); j++) {
                        const clone = content.cloneNode(true);
                        if (j === piecesList[i] - 1) {
                            clone.style.marginRight = '2px';
                        }
                        playerPieces.appendChild(clone);
                    }
                } else if (piecesList[i] !== 0) {
                    for (let j = 0; j < Math.abs(piecesList[i]); j++) {
                        const clone = content.cloneNode(true);
                        if (j === piecesList[i] - 1) {
                            clone.style.marginRight = '2px';
                        }
                        opponentPieces.appendChild(clone);
                    }
                }
            }
        }
        const scoreCompare = color === 'white' ? score > 0 : score < 0;
        const scoreElement = document.createElement('div')
        scoreElement.textContent = '+' + Math.abs(score);
        if (scoreCompare) {
            playerPieces.appendChild(scoreElement);
        } else if (score !== 0) {
            opponentPieces.appendChild(scoreElement);
        }
    }

    var whitePlayed = JSON.parse(webGameMetadata.white_played);
    var blackPlayed = JSON.parse(webGameMetadata.black_played);
    const color = webGameMetadata.player_color;
    var currentTurn = !whitePlayed && color === 'white' || !blackPlayed && color === 'black';
    var theirTurn = !whitePlayed && color === 'black' || !blackPlayed && color === 'white';
    var currentIndicator = document.getElementById('playerIndicator');
    var opponentIndicator = document.getElementById('opponentIndicator');
    if (currentIndicator !== null && currentTurn && !alternatingFavicon) {
        const title = document.getElementById('title');
        title.text = "Your Turn";
        faviconIntervalId = setInterval(faviconInterval, 2000);
        currentIndicator.classList.remove('hidden');
        alternatingFavicon = true;
    } else if (currentIndicator !== null && !currentTurn && alternatingFavicon) {
        clearInterval(faviconIntervalId);
        changeFavicon(0);
        const title = document.getElementById('title');
        title.text = "Playing"
        currentIndicator.classList.add('hidden');
        alternatingFavicon = false;
    }
    if (opponentIndicator !== null && theirTurn && opponentIndicator.classList.contains('hidden')) {
        opponentIndicator.classList.remove('hidden');
    } else if (opponentIndicator !== null && !theirTurn) {
        opponentIndicator.classList.add('hidden');
    }

    if (savedStates.length === 0 || whitePlayed !== savedStates[0] || blackPlayed !== savedStates[1]) {
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
            selectedMove = document.getElementById(moveId);
            if (selectedMove) {
                selectedMove.disabled = true;
                selectedMoveId = moveId;
            }
        }
        savedStates = [whitePlayed, blackPlayed];
    }

    // Don't keep unnecessarily updating
    if (equal_arrays) {
        return;
    } 
    savedMoves = moves;
    
    movesListContainer.innerHTML = '';
    
    var parentHeader = document.createElement('div');
    parentHeader.style.width = '100%';
    parentHeader.classList.add('d-flex');
    parentHeader.style.position = 'sticky';
    parentHeader.style.top = '0';
    parentHeader.style.backgroundColor = 'var(--command-center-background)';
    parentHeader.setAttribute('name', 'initHiddenDflex');

    var emptyDiv = document.createElement('div');
    emptyDiv.style.width = '10%';
    emptyDiv.setAttribute('name', 'initHidden');

    var leftHeader = document.createElement('div');
    leftHeader.style.width = '45%';
    leftHeader.style.color = 'var(--move-row-text)';
    leftHeader.style.textAlign = 'left';
    leftHeader.textContent = 'White';
    leftHeader.setAttribute('name', 'initHidden');

    var rightHeader = leftHeader.cloneNode(true);
    rightHeader.textContent = 'Black';
    rightHeader.setAttribute('name', 'initHidden');

    var initialized = sessionStorage.getItem('initialized');
    initialized = (initialized === 'true' ? true : false);
    if (initialized && moves.length !== 0) {
        parentHeader.appendChild(emptyDiv);
        parentHeader.appendChild(leftHeader);
        parentHeader.appendChild(rightHeader);
        movesListContainer.appendChild(parentHeader);
    }

    var j = 1;
    for (var i = 0; i < moves.length; i += 1) {
        var move1 = ( Array.isArray(moves[i])) ? movePieceTranslation(moves[i][0]) : moves[i];
        var move2 = (
            moves[i] !== '1-0' && 
            moves[i] !== '0-1' && 
            moves[i] !== '1-1' &&
            moves[i] !== '½–½'
        ) ? moves[i][1] : '';
        move2 = movePieceTranslation(move2);

        var moveRow = document.createElement('div');
        moveRow.className = 'move-row ' + (i % 2 === 0 ? '' : 'even-move-row');
        moveRow.setAttribute('name', 'initHidden');
                    
        var pairNumber = document.createElement('div');
        pairNumber.style.width = '10%';
        pairNumber.textContent = j;
        pairNumber.style.textAlign = 'center'
        pairNumber.style.backgroundColor = 'var(--command-center-background)';
        pairNumber.className = 'move-number';
        pairNumber.id = 'move-number-' + j;
        pairNumber.setAttribute('name', 'initHidden');

        var parent = document.createElement('button');
        parent.style.width = '90%';
        parent.className = 'move-button';
        parent.classList.add('d-flex');
        parent.setAttribute('move-index', j - 1);
        parent.id = 'move-' + (j - 1);
        parent.setAttribute('name', 'initHiddenDflex');

        var leftHalf = document.createElement('div');
        leftHalf.style.width = '50%';
        leftHalf.textContent = move1;
        leftHalf.className = 'move-child';
        leftHalf.setAttribute('name', 'initHidden');

        var rightHalf = document.createElement('div');
        rightHalf.style.width = '50%';
        rightHalf.textContent = move2;
        rightHalf.className = 'move-child';
        rightHalf.setAttribute('name', 'initHidden');

        if (!initialized) {
            pairNumber.classList.add('hidden');
            parent.style.setProperty('display', 'none', 'important');
            leftHalf.classList.add('hidden');
            rightHalf.classList.add('hidden');
        }

        if (move1 !== '1-0' && move1 !== '0-1' && move1 !== '1-1' && move1 !== '½–½') {
            moveRow.appendChild(pairNumber);
            parent.appendChild(leftHalf);
            parent.appendChild(rightHalf)
            moveRow.appendChild(parent);

            movesListContainer.appendChild(moveRow);
            movesListContainer.scrollTop = movesListContainer.scrollHeight;
            if (parent.id) {
                (function(id) {
                    parent.addEventListener("click", function() {
                        handleButton(id, "step");
                    });
                })(parent.id);
            }
        }
        j += 1;
    }
    movesListContainer.scrollTop = movesListContainer.scrollHeight;

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
    } else if (endState === '1-1') {
        endmessage += `Both are Victorious`
        finalScorebox.innerHTML = '1-1'
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
            saveHistoricGame(JSON.stringify(moves), JSON.stringify(comp_moves), endState, FEN_final, forcedEnd);
        }
        
        var playerColor = webGameMetadata["player_color"]
        var computer_game = JSON.parse(computerGame);
        if (computer_game) {
            document.getElementById("rematchButton").classList.remove("hidden");
            document.getElementById("rematchButton").addEventListener("click", function() {
                rematch_accepted = true;
                generateRematchURL(playerColor);
                document.getElementById("rematchButton").disabled = true;
            }, {once: true});
        }
        const title = document.getElementById('title');
        currentTurn = null;
        title.text = "Game Over";
        clearInterval(faviconIntervalId);
        changeFavicon(0);
        document.getElementById('playerIndicator').remove();
        document.getElementById('opponentIndicator').remove();
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
    endMessagebox.innerHTML = "";
    finalScorebox.innerHTML = "";
}

var previousConnected = false;
var initCheck = false;

window.addEventListener('load', resetCommandCenter);
window.addEventListener('load', updateCommandCenter);

setInterval(updateCommandCenter, 100);

var socket;

function initializeWebSocket() {
    if (window.location.protocol == 'https:') {
        wsProtocol = 'wss://';
    } else {
        wsProtocol = 'ws://';
    }

    socket = new WebSocket(wsProtocol + window.location.host + "/ws/chat/" + game_uuid + "/");

    socket.onmessage = function (event) {
        var chat_data = JSON.parse(event.data);
        handleMessage(chat_data["message"]);
    };

    socket.onclose = function (event) {
        appendChatLog("Disconnected...")
    };

}

function sendMessage(message, type = null) {
    var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
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
        }
    }
    socket.send(JSON.stringify(messageObj));
}

function handleMessage(data) {
    if (data.hasOwnProperty('log')) {
        return;
    }
    // Prevent XSS script injection attacks by escaping content
    var message = $('<p></p>').text(data["sender"] + ": " + data["text"]);
    $(".chat-messages").append(message);
}

function appendChatLog(message) {
    var log = $('<p></p>').text(message);
    log.css({
        'background-color': 'var(--chat-box-log)',
        'text-align': 'center'
    });
    $(".chat-messages").append(log);
}

function generateRematchURL(position) {
    if (position !== "white" && position !== "black") {
        return console.error('Invalid position input')
    }
    body = { // to eventually replace with game id and rematch param
        "position": position,
        "computer_game": true,
        "main_mode": "Standard",
        "subvariant": "Normal"
    }
    fetch('/create_new_game/', {
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
    body_mssg = {
        game_uuid: game_uuid, 
        web_connect: status,
        color: playerColor,
        computer_game: JSON.parse(computerGame)
    }
    fetch('/update_connected/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify(body_mssg),
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
            "cycleThemeButton", 
            "flipButton"
        ];

        var hiddenDflexElements = document.getElementsByName('initHiddenDflex');
        hiddenDflexElements.forEach(element => {
            element.style.display = '';
        });

        var hiddenElements = document.getElementsByName('initHidden');
        hiddenElements.forEach(element => {
            element.classList.remove('hidden');
        })

        idStrings.forEach(idString => {
            document.getElementById(idString).classList.remove("hidden");
        })
        initializeWebSocket();
        var movesListContainer = document.getElementById('moves-list');
        movesListContainer.scrollTop = movesListContainer.scrollHeight;
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

// to defaults
window.addEventListener('beforeunload', function () {
    sessionStorage.setItem('connected', 'false');
    sessionStorage.setItem('current_game_id', game_uuid);
    sessionStorage.setItem('initialized', 'null');
    sessionStorage.setItem('promoting', 'false');
});

function handlestep(webGameMetadata, sessionStorageObjectName, buttonId) {
    var early_exit = false;
    if (
        move_index + 1 >= comp_moves.length && buttonId.toLowerCase().includes("forward") || 
        move_index < 0 && buttonId === "backwardButton"
    ) {
        webGameMetadata[sessionStorageObjectName].execute = false;
        webGameMetadata[sessionStorageObjectName].index = null;
        sessionStorage.setItem('web_game_metadata', JSON.stringify(webGameMetadata));
        
        document.getElementById(buttonId).disabled = false;
        early_exit = true;
        return {'index_number': null, 'early_exit': early_exit};
    }
    if (buttonId === "forwardButton" || buttonId === "skipForwardButton") {
        index_number = (buttonId === "forwardButton" ? move_index + 1 : comp_moves.length - 1);

    } else if (buttonId === "backwardButton" || buttonId === "skipBackwardButton") {
        index_number = (buttonId === "backwardButton" ? move_index : -1);
    } else {
        index_number = parseInt(document.getElementById(buttonId).getAttribute('move-index'), 10);
        index_number = (index_number < move_index ? index_number + 1 : index_number);
    }
    return {'index_number': index_number, 'early_exit': early_exit}
}

function handleWebtoGameAction(buttonId, sessionStorageObjectName, Options = null) {
    var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    webGameMetadata[sessionStorageObjectName].execute = true;
    if (sessionStorageObjectName == "step") {
        const stepResults = handlestep(
            webGameMetadata, 
            sessionStorageObjectName,
            buttonId
        );
        if (stepResults.early_exit) {
            return;
        }
        webGameMetadata[sessionStorageObjectName].index = stepResults.index_number;
    }
    sessionStorage.setItem('web_game_metadata', JSON.stringify(webGameMetadata));

    handleActionStatus(buttonId, sessionStorageObjectName, Options);
}

var actionEventList = [
    {mainButtonName: "undoOfferButton", eventNames: ["undo_move"]},
    {mainButtonName: "resignButton", eventNames: ["resign"]}
]

var inputList = [
    { buttonId: "forwardButton", sessionStorageObjectName: "step"},
    { buttonId: "backwardButton", sessionStorageObjectName: "step"},
    { buttonId: "skipForwardButton", sessionStorageObjectName: "step"},
    { buttonId: "skipBackwardButton", sessionStorageObjectName: "step"},
    { buttonId: "undoOfferButton", sessionStorageObjectName: "undo_move", Options: "followups"},
    { buttonId: "resignButton", sessionStorageObjectName: "resign", Options: "followups"},
    { buttonId: "cycleThemeButton", sessionStorageObjectName: "cycle_theme"},
    { buttonId: "flipButton", sessionStorageObjectName: "flip_board"},
];

function buttonHandling(buttonId, webGameMetadata, sessionStorageObjectName) {
    if (sessionStorageObjectName == "step") {
        webGameMetadata[sessionStorageObjectName].index = null;
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
        } else {
            var movesListContainer = document.getElementById('moves-list');
            movesListContainer.scrollTop = 0;
        }
        if (selectedMoveId !== "") {
            document.getElementById(selectedMoveId).disabled = false;
        }
        selectedMoveId = (move_index !== -1 ? moveId: "");
        if (selectedMoveId !== "") {
            var movesListContainer = document.getElementById('moves-list');
            var selectedMove = document.getElementById(selectedMoveId);

            var containerHeight = movesListContainer.clientHeight;
            var moveHeight = selectedMove.clientHeight;

            // Don't need to scroll, if the element is already visible
            if (!(selectedMove.offsetTop - moveHeight >= 0 && selectedMove.offsetTop + moveHeight <= containerHeight)) {
                movesListContainer.scrollTop = selectedMove.offsetTop - (containerHeight - moveHeight) / 2 - containerHeight;
            }

        }
    } else if (sessionStorageObjectName == "flip_board") {
        topElement = document.getElementById('topPlayer');
        bottomElement = document.getElementById('bottomPlayer');
        topHTML = topElement.innerHTML;
        bottomHTML = bottomElement.innerHTML;
        topElement.innerHTML = bottomHTML;
        bottomElement.innerHTML = topHTML;

        topPiecesRow = document.getElementById('topPieces');
        bottomPiecesRow = document.getElementById('bottomPieces');
        topPiecesHTML = topPiecesRow.innerHTML;
        bottomPiecesHTML = bottomPiecesRow.innerHTML;
        topPiecesRow.innerHTML = bottomPiecesHTML;
        bottomPiecesRow.innerHTML = topPiecesHTML;

        flipped = !flipped;
    }
    return webGameMetadata;
}

function handleActionStatus(buttonId, sessionStorageObjectName, Options) {
    var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    var actionCommandStatus = webGameMetadata[sessionStorageObjectName];
    
    // console.log(sessionStorageObjectName, actionCommandStatus) // Good dev log, very good boy
    var initialDefaults = (!actionCommandStatus.execute && !actionCommandStatus.update_executed);
    if (!actionCommandStatus.update_executed && !initialDefaults) {
        setTimeout(function () {
            // This can be too fast and execute again right before reset is set to false, 
            // hence the default condition check
            handleActionStatus(buttonId, sessionStorageObjectName, Options);
        }, 10);
    } else {
        webGameMetadata[sessionStorageObjectName].execute = false;
        webGameMetadata[sessionStorageObjectName].update_executed = false;
        
        webGameMetadata = buttonHandling(buttonId, webGameMetadata, sessionStorageObjectName);

        sessionStorage.setItem('web_game_metadata', JSON.stringify(webGameMetadata));
        
        if (buttonId.includes("move")) {
            return;
        }
        // Resign or draw can quickly remove the button before this
        element = document.getElementById(buttonId);
        if (element && (buttonId !== 'readyButton' && buttonId !== 'redoButton')) {
            element.disabled = false;
        }
    }
}

function optionStringsHelper(mainbuttonId) {
    var approveString = "Confirm";
    var abandonString = "Cancel";
    var replaceString = "Button";
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

inputList.forEach(function(input) {
    const optionsValue = (input.hasOwnProperty("Options") ? input.Options: null);
    document.getElementById(input.buttonId).addEventListener("click", function() {
        handleButton(input.buttonId, input.sessionStorageObjectName, optionsValue);
    });
});

function eventIsExecuting(obj, eventNames) {
    for (var event of eventNames) {
        if (obj.hasOwnProperty(event) && obj[event]["execute"] === true) {
            return true;
        }
    }
    return false;
}

function handleButton(buttonId, sessionStorageObjectName, Options = null, resetDisplay = null, currentAction = null) {
    document.getElementById(buttonId).disabled = true;
    if (Options !== null) {
        result = optionStringsHelper(buttonId, Options)
        const buttonApproveId = result.ApproveId;
        const buttonAbandonId = result.AbandonId;
        document.getElementById(buttonId).classList.add("hidden");
        document.getElementById(buttonApproveId).classList.remove("hidden");
        document.getElementById(buttonAbandonId).classList.remove("hidden");
        var otherFollowups = document.querySelectorAll('[followup="true"]');

        otherFollowups.forEach(function(element) {
            if (element.id !== buttonApproveId && element.id !== buttonAbandonId) {
                element.classList.add("hidden");
            }
        });
        var actionbuttons = document.querySelectorAll('[actions="true"]');
        var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
        
        // On followup display only, main buttons are disabled. We need to re-enable them
        // This does not apply to executing or queued actions
        actionbuttons.forEach(function(element) {
            if (element.id !== buttonId) {
                element.classList.remove("hidden");
                var actionEvents = actionEventList.find(event => event.mainButtonName === element.id);
                var notExecuting = !eventIsExecuting(webGameMetadata, actionEvents.eventNames);
                if (notExecuting) {
                    element.disabled = false;
                }
            }
        });
        document.getElementById(buttonApproveId).addEventListener("click", function() { 
            hideOptions(buttonId, buttonApproveId, buttonAbandonId);
            handleWebtoGameAction(buttonId, sessionStorageObjectName, Options);
        }, { once: true });
        document.getElementById(buttonAbandonId).addEventListener("click", function() {
            hideOptions(buttonId, buttonApproveId, buttonAbandonId);
            document.getElementById(buttonId).disabled = false;
        }, { once: true });
    } else {
        handleWebtoGameAction(buttonId, sessionStorageObjectName);
    };
}