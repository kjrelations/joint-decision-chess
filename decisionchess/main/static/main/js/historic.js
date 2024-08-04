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
    var commandCenterHeight = isSmallScreen ? (width * 0.3) : (width * 0.6);
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
    var commandCenterHeight = isSmallScreen ? (width * 0.3) : (width * 0.6);
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
            if (obj1[i] !== obj2[i]) {
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

var savedMoves = [];
var savedPieces = {};
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
    var existingWebGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = (currentGameID === 'null' ? null : currentGameID);
    if (currentGameID !== null && existingWebGameMetadata.hasOwnProperty(currentGameID)) {
        var webGameMetadata = existingWebGameMetadata[currentGameID];
        
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
        
        var moves = webGameMetadata.alg_moves;
        // Don't keep unnecessarily updating
        if (areEqual(moves, savedMoves, 'array')) {
            return;
        }
        savedMoves = moves
        var movesListContainer = document.getElementById('moves-list');
        var endState = webGameMetadata.end_state;
        
        movesListContainer.innerHTML = '';
        
        var initialized = sessionStorage.getItem('initialized');
        initialized = (initialized === 'true' ? true : false);
        var j = 1;
        for (var i = 0; i < moves.length; i += 2) {
            var move1 = movePieceTranslation(moves[i]);
            var move2 = (
                (i + 1 < moves.length) && 
                moves[i + 1] !== '1-0' && 
                moves[i + 1] !== '0-1' && 
                moves[i + 1] !== '½–½'
            ) ? moves[i + 1] : '';
            move2 = movePieceTranslation(move2);

            var moveRow = document.createElement('div');
            moveRow.className = 'move-row ' + (i % 4 === 0 ? '' : 'even-move-row');
            
            var pairNumber = document.createElement('div');
            pairNumber.style.width = '10%';
            pairNumber.textContent = j;
            pairNumber.style.textAlign = 'center'
            pairNumber.style.backgroundColor = 'var(--command-center-background)';
            pairNumber.className = 'move-number';
            pairNumber.id = 'move-number-' + j;

            var leftHalf = document.createElement('button');
            leftHalf.style.width = '45%';
            leftHalf.textContent = move1;
            leftHalf.className = 'move-button';
            leftHalf.setAttribute('move-index', i);
            leftHalf.id = 'move-' + i;

            var rightHalf = (move2 === "" ? document.createElement('div'): document.createElement('button'));
            rightHalf.style.width = '45%';
            rightHalf.textContent = move2;
            if (move2 !== '') {
                rightHalf.className = 'move-button';
                rightHalf.setAttribute('move-index', i + 1);
                rightHalf.id = 'move-' + (i + 1);
            }

            if (!initialized) {
                pairNumber.classList.add('hidden');
                leftHalf.classList.add('hidden');
                rightHalf.classList.add('hidden');
            }

            if (move1 !== '1-0' && move1 !== '0-1' && move1 !== '½–½') {
                moveRow.appendChild(pairNumber);
                moveRow.appendChild(leftHalf);
                moveRow.appendChild(rightHalf);

                movesListContainer.appendChild(moveRow);
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
        } else if (endState === '½–½' && forcedEnd !== 'Draw by mutual agreement' && forcedEnd !== 'Stalemate by Threefold Repetition') {
            endmessage += `Stalemate was Reached`;
            finalScorebox.innerHTML = '½–½';
        }

        if (endmessage !== '') {
            endMessagebox.innerHTML = endmessage;
        }
        move_index = comp_moves.length - 1;
        moveId = 'move-' + move_index;
        if (move_index !== -1) {
            document.getElementById(moveId).disabled = true;
            selectedMoveId = moveId;
        }
    }
}

var selectedMoveId = "";
var initCheck = false;

function resetCommandCenter() {
    savedMoves = [];
    selectedMoveId = "";
    initCheck = false;
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

window.addEventListener('load', resetCommandCenter);
window.addEventListener('load', updateCommandCenter);

setInterval(updateCommandCenter, 100);

function checkInit() {
    var initialized = sessionStorage.getItem('initialized');
    initialized = (initialized === 'true' ? true : false);
    if (initialized === true && initCheck === false) {
        const idStrings = [
            "skipBackwardButton", 
            "backwardButton", 
            "forwardButton", 
            "skipForwardButton", 
            "cycleThemeButton", 
            "flipButton"
        ];
        
        var buttonsWithMoveIndex = document.querySelectorAll('.move-button');
        buttonsWithMoveIndex.forEach(button => {
            idStrings.push(button.id);
        });
        
        var elementsWithMoveNumber = document.querySelectorAll('.move-number');
        elementsWithMoveNumber.forEach(element => {
            idStrings.push(element.id);
        });

        idStrings.forEach(idString => {
            document.getElementById(idString).classList.remove("hidden");
        })
        var movesListContainer = document.getElementById('moves-list');
        movesListContainer.scrollTop = movesListContainer.scrollHeight;
        initCheck = initialized;
        clearInterval(initIntervalId);
    }
}

window.addEventListener('beforeunload', function () {
    sessionStorage.setItem('initialized', 'null');
});

var initIntervalId = setInterval(checkInit, 1000);

function handlestep(webGameMetadata, sessionStorageObjectName, existingWebGameMetadata, currentGameID, buttonId) {
    var early_exit = false;
    if (
        move_index + 1 >= comp_moves.length && buttonId.toLowerCase().includes("forward") || 
        move_index < 0 && buttonId === "backwardButton"
    ) {
        webGameMetadata[sessionStorageObjectName].execute = false;
        webGameMetadata[sessionStorageObjectName].index = null;
        existingWebGameMetadata[currentGameID] = webGameMetadata;
        sessionStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));
        
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

function handleWebtoGameAction(buttonId, sessionStorageObjectName) {
    var existingWebGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = (currentGameID === 'null' ? null : currentGameID);
    if (currentGameID !== null && existingWebGameMetadata.hasOwnProperty(currentGameID)) { 
        var webGameMetadata = existingWebGameMetadata[currentGameID];
        webGameMetadata[sessionStorageObjectName].execute = true;
        existingWebGameMetadata[currentGameID] = webGameMetadata;
        if (sessionStorageObjectName == "step") {
            const stepResults = handlestep(
                webGameMetadata, 
                sessionStorageObjectName, 
                existingWebGameMetadata, 
                currentGameID, 
                buttonId
            );
            if (stepResults.early_exit) {
                return;
            }
            webGameMetadata[sessionStorageObjectName].index = stepResults.index_number;
        }
        sessionStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));

        handleActionStatus(buttonId, currentGameID, sessionStorageObjectName);
    } else {
        console.warn("Failed to execute action");
    }
}

var inputList = [
    { buttonId: "forwardButton", sessionStorageObjectName: "step"},
    { buttonId: "backwardButton", sessionStorageObjectName: "step"},
    { buttonId: "skipForwardButton", sessionStorageObjectName: "step"},
    { buttonId: "skipBackwardButton", sessionStorageObjectName: "step"},
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

function handleActionStatus(buttonId, currentGameID, sessionStorageObjectName) {
    var existingWebGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    var webGameMetadata = existingWebGameMetadata[currentGameID];
    var actionCommandStatus = webGameMetadata[sessionStorageObjectName];
    
    // console.log(sessionStorageObjectName, actionCommandStatus) // Good dev log, very good boy
    var initialDefaults = (!actionCommandStatus.execute && !actionCommandStatus.update_executed);
    if (!actionCommandStatus.update_executed && !initialDefaults) {
        setTimeout(function () {
            handleActionStatus(buttonId, currentGameID, sessionStorageObjectName);
        }, 0);
    } else {
        webGameMetadata[sessionStorageObjectName].execute = false;
        webGameMetadata[sessionStorageObjectName].update_executed = false;

        webGameMetadata = buttonHandling(buttonId, webGameMetadata, sessionStorageObjectName);

        existingWebGameMetadata[currentGameID] = webGameMetadata;
        sessionStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));
        
        if (buttonId.includes("move")) {
            return;
        }
        document.getElementById(buttonId).disabled = false;
    }
}

inputList.forEach(function(input) {
    document.getElementById(input.buttonId).addEventListener("click", function() {
        handleButton(input.buttonId, input.sessionStorageObjectName);
    });
});

function handleButton(buttonId, sessionStorageObjectName) {
    document.getElementById(buttonId).disabled = true;
    handleWebtoGameAction(buttonId, sessionStorageObjectName);
}