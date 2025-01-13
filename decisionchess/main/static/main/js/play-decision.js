function adjustFont() {
    const elements = document.querySelectorAll('.action-button');
    const parent = document.getElementById('command-center');
    elements.forEach(element => {
        if (element.id !== 'readyButton' && element.id !== 'redoButton') {
            if (210 < parent.offsetWidth && parent.offsetWidth < 320) {
                element.style.fontSize = '0.7rem';
            } else if (parent.offsetWidth < 210) {
                element.style.fontSize = '0.65rem';
            } else if (parent.offsetWidth >= 320) {
                element.style.fontSize = '1rem';
            }
        }
    });
}

window.addEventListener('load', function() {
    var iframeContainer = document.getElementById('iframe-container');
    var width = iframeContainer.offsetWidth;
    document.getElementById('embedded-iframe').style.height = width + 'px';
    iframeContainer.style.height = width + 'px';
    var isSmallScreen = window.matchMedia('(max-width: 767px)').matches;
    var commandCenterHeight = width * 0.6;
    document.getElementById('command-center').style.height = commandCenterHeight + 'px';
    document.getElementById('chat-box').style.height = isSmallScreen ? `20vh` : `calc(95vh - 50px - ${commandCenterHeight}px)`;
    adjustFont();

    var inputs = document.getElementsByClassName('chat-input');
    for (var i = 0; i < inputs.length; i++) {
        inputs[i].value = '';
    }
});

window.addEventListener('resize', function() {
    var iframeContainer = document.getElementById('iframe-container');
    var width = iframeContainer.offsetWidth;
    document.getElementById('embedded-iframe').style.height = width + 'px';
    iframeContainer.style.height = width + 'px';
    var isSmallScreen = window.matchMedia('(max-width: 767px)').matches;
    var commandCenterHeight = width * 0.6;
    document.getElementById('command-center').style.height = commandCenterHeight + 'px';
    document.getElementById('chat-box').style.height = isSmallScreen ? `20vh` : `calc(95vh - 50px - ${commandCenterHeight}px)`;
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

const shareButton = document.getElementById("toggleShareArrows");

shareButton.addEventListener('click', () => {
    shareButton.classList.toggle('active');
    if (sessionStorage.getItem('toggle-arrows') === 'true') {
        sessionStorage.setItem('toggle-arrows', 'false');
    } else {
        sessionStorage.setItem('toggle-arrows', 'true');
    }
})

var gameSaved = false;
var signed_uuid = "";
var rematch_request = false;
var rematch_accepted = false;
var rematch_received = false;
var savedMoves = [];
var savedPieces = {};
var savedStates = [];
var savedDecisionStage = false;
var comp_moves = [];
var move_index = -1;
var selectedMoveId = "";
var promotion_lock = false;
var flipped = false;
var timeIntervalId = null;

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
    const color = webGameMetadata.player_color;
    if (JSON.parse(sessionStorage.getItem('white_time')) && timeIntervalId === null && endState === '') {
        var hiddenElements = document.getElementsByName('initClockHidden');
        hiddenElements.forEach(element => {
            element.classList.remove('hidden');
        })
        timeIntervalId = setInterval(function() {
            updateClocks(color);
        }, 1);
    }
    comp_moves = webGameMetadata.comp_moves;
    const equal_arrays = areEqual(moves, savedMoves, 'array');
    if (endState !== '' && !equal_arrays) {
        const buttons = document.querySelectorAll(".action-button:not([post-game=true])");
        clearInterval(requestIntervalId);
        clearInterval(connectIntervalId);
        buttons.forEach(button => {
            button.remove();
        });
        document.getElementById("toggleShareArrows").remove();
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

    if (webGameMetadata['decision_stage'] !== savedDecisionStage) {
        if (webGameMetadata['decision_stage']) {
            document.getElementById('decision-timer').classList.remove('hidden');
            startTimer();
        } else {
            clearInterval(timerInterval);
            document.getElementById('decision-timer').innerText = '0';
            document.getElementById('decision-timer').classList.add('hidden');
        }
        savedDecisionStage = webGameMetadata['decision_stage'];
    }

    var playerDisplayedMove = color === 'white' ? document.getElementById('displayed-move-bottom'): document.getElementById('displayed-move-top');
    var opponentDisplayedMove = color === 'white' ? document.getElementById('displayed-move-top'): document.getElementById('displayed-move-bottom');
    var playerActiveMove = color === 'white' ? webGameMetadata['white_active_move']: webGameMetadata['black_active_move'];
    var opponentActiveMove = color === 'white' ? webGameMetadata['black_active_move']: webGameMetadata['white_active_move'];
    if (!webGameMetadata['playing_stage']) {
        if (playerDisplayedMove.textContent !== playerActiveMove) {
            playerDisplayedMove.textContent = playerActiveMove;
            opponentDisplayedMove.textContent = opponentActiveMove;
            playerDisplayedMove.classList.remove('hidden');
            opponentDisplayedMove.classList.remove('hidden');
        }
    } else if (playerDisplayedMove.textContent !== '') {
        playerDisplayedMove.textContent = '';
        opponentDisplayedMove.textContent = '';
        playerDisplayedMove.classList.add('hidden');
        opponentDisplayedMove.classList.add('hidden');
    }

    var white1 = color === 'white' ? document.getElementById('bottom-undo-1') : document.getElementById('top-undo-1');
    var white2 = color === 'white' ? document.getElementById('bottom-undo-2') : document.getElementById('top-undo-2');
    var white3 = color === 'white' ? document.getElementById('bottom-undo-3') : document.getElementById('top-undo-3');
    var black1 = color === 'white' ? document.getElementById('top-undo-1') : document.getElementById('bottom-undo-1');
    var black2 = color === 'white' ? document.getElementById('top-undo-2') : document.getElementById('bottom-undo-2');
    var black3 = color === 'white' ? document.getElementById('top-undo-3') : document.getElementById('bottom-undo-3');
    if (webGameMetadata['decision_stage_enabled'] && white1.classList.contains('hidden')) {
        white1.classList.remove('hidden');
        white2.classList.remove('hidden');
        white3.classList.remove('hidden');
        black1.classList.remove('hidden');
        black2.classList.remove('hidden');
        black3.classList.remove('hidden');
    } else if (!webGameMetadata['decision_stage_enabled'] && !white1.classList.contains('hidden')) {
        white1.classList.add('hidden');
        white2.classList.add('hidden');
        white3.classList.add('hidden');
        black1.classList.add('hidden');
        black2.classList.add('hidden');
        black3.classList.add('hidden');
    }
    if (webGameMetadata['white_undo'] >= 1) {
        if (window.getComputedStyle(white1, null).getPropertyValue("background-color") === 'rgb(97, 97, 97)') {
            white1.style.backgroundColor = 'green';
        }
    } 
    if (webGameMetadata['white_undo'] >= 2) {
        if (window.getComputedStyle(white2, null).getPropertyValue("background-color") === 'rgb(97, 97, 97)') {
            white2.style.backgroundColor = 'green';
        }
    } 
    if (webGameMetadata['white_undo'] >= 3) {
        if (window.getComputedStyle(white3, null).getPropertyValue("background-color") === 'rgb(97, 97, 97)') {
            white3.style.backgroundColor = 'green';
        }
    } 
    if (webGameMetadata['black_undo'] >= 1) {
        if (window.getComputedStyle(black1, null).getPropertyValue("background-color") === 'rgb(97, 97, 97)') {
            black1.style.backgroundColor = 'green';
        }
    } 
    if (webGameMetadata['black_undo'] >= 2) {
        if (window.getComputedStyle(black2, null).getPropertyValue("background-color") === 'rgb(97, 97, 97)') {
            black2.style.backgroundColor = 'green';
        }
    } 
    if (webGameMetadata['black_undo'] >= 3) {
        if (window.getComputedStyle(black3, null).getPropertyValue("background-color") === 'rgb(97, 97, 97)') {
            black3.style.backgroundColor = 'green';
        }
    } 
    if (document.getElementById('readyButton') !== null) {
        if (webGameMetadata['reveal_stage'] && document.getElementById('readyButton').classList.contains('hidden')) {
            document.getElementById('readyButton').classList.remove('hidden');
            document.getElementById('readyButton').disabled = false;
        } else if (!webGameMetadata['reveal_stage'] && !document.getElementById('readyButton').classList.contains('hidden')) {
            document.getElementById('readyButton').classList.add('hidden');
            document.getElementById('readyButton').disabled = true;
        }
    }
    if (document.getElementById('redoButton') !== null) {
        if (webGameMetadata['decision_stage'] && document.getElementById('redoButton').classList.contains('hidden')) {
            document.getElementById('redoButton').classList.remove('hidden');
            document.getElementById('redoButton').disabled = false;
        } else if (!webGameMetadata['decision_stage'] && !document.getElementById('redoButton').classList.contains('hidden')) {
            document.getElementById('redoButton').classList.add('hidden');
            document.getElementById('redoButton').disabled = true;
        }
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
    endMessagebox.innerHTML = "";
    finalScorebox.innerHTML = "";
}

let timerInterval;
let startTime;
let countdownTime;
let remainingTime;

function updateTimer() {
    const now = new Date().getTime();
    remainingTime = countdownTime - (now - startTime);

    var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    if (remainingTime <= 0 || webGameMetadata['reset_timer']) {
        clearInterval(timerInterval);
        document.getElementById('decision-timer').innerText = '0';
        if (!webGameMetadata['reset_timer']) {
            webGameMetadata['next_stage'] = true;
            sessionStorage.setItem('web_game_metadata', JSON.stringify(webGameMetadata))
        } else {
            webGameMetadata['reset_timer'] = false;
            sessionStorage.setItem('web_game_metadata', JSON.stringify(webGameMetadata))
        }
        document.getElementById('decision-timer').classList.add('hidden');
        return;
    }

    const time = new Date(remainingTime);
    const seconds = String(time.getUTCSeconds());
    document.getElementById('decision-timer').innerText = `${seconds}`;
}

function startTimer() {
    const minutes = 0;
    const seconds = 5;
    countdownTime = (minutes * 60 + seconds) * 1000;
    startTime = new Date().getTime();
    remainingTime = countdownTime;
    timerInterval = setInterval(updateTimer, 1);
}

var previousConnected = false;
var initCheck = false;

window.addEventListener('load', resetCommandCenter);
window.addEventListener('load', updateCommandCenter);

setInterval(updateCommandCenter, 100);

function duplicateCheck() {
    var duplicate = sessionStorage.getItem('duplicate');
    if (duplicate === 'true') {
        appendChatLog("Game already opened");
        sessionStorage.setItem('duplicate', 'false');
        clearInterval(duplicateIntervalID);
    }
}
var duplicateIntervalID = setInterval(duplicateCheck, 100);

function formatTime(time) {
    let totalMilliseconds = Math.round(time * 1000);
    
    let minutes = Math.floor(totalMilliseconds / 60000);
    let seconds = Math.floor((totalMilliseconds % 60000) / 1000);
    let milliseconds = totalMilliseconds % 1000;
    
    let minutesStr = String(minutes).padStart(2, '0');
    let secondsStr = String(seconds).padStart(2, '0');
    
    let millisecondsStr = `.<small>${String(milliseconds).padStart(3, '0')}</small>`;

    return [`${minutesStr}:${secondsStr}${millisecondsStr}`, minutes];
}

function updateClockBorders(clockElement, remainingMilliseconds) {
    if (clockElement.style.color !== 'red') {
        clockElement.style.color = 'red';
    }
    const secondColorPercentage = ((60000 - remainingMilliseconds) / 60000) * 100;
    
    const gradients = `
    linear-gradient(var(--clock-background), var(--clock-background)),
    conic-gradient(
        from 180deg,
        var(--clock-border) 0deg,
        var(--clock-border) ${360 - (secondColorPercentage * 3.6)}deg,
        red ${360 - (secondColorPercentage * 3.6)}deg,
        red 360deg
    )`;
    
    clockElement.style.backgroundImage = `${gradients}`;
}

const defaultGradients = `
linear-gradient(var(--clock-background), var(--clock-background)),
conic-gradient(var(--clock-border), var(--clock-border))
`;

function updateClocks(playerColor) {
    var whiteSeconds = JSON.parse(sessionStorage.getItem('white_time'));
    if (whiteSeconds === null) {
        return;
    }
    var blackSeconds = JSON.parse(sessionStorage.getItem('black_time'));
    console.log(whiteSeconds);
    const [whiteTime, whiteMinutes] = formatTime(whiteSeconds);
    const [blackTime, blackMinutes] = formatTime(blackSeconds);
    const playerClock = document.getElementById('playerClock');
    const opponentClock = document.getElementById('opponentClock');
    if (playerColor === 'white') {
        playerClock.innerHTML = whiteTime;
        opponentClock.innerHTML = blackTime;
        if (whiteMinutes === 0) {
            updateClockBorders(playerClock, Math.round(whiteSeconds * 1000) % 60000);
        } else if (playerClock.style.color === 'red') {
            playerClock.style.color = 'var(--body-text)';
            playerClock.style.backgroundImage = `${defaultGradients}`;
        }
        if (blackMinutes === 0) {
            updateClockBorders(opponentClock, Math.round(blackSeconds * 1000) % 60000);
        } else if (opponentClock.style.color === 'red') {
            opponentClock.style.color = 'var(--body-text)';
            opponentClock.style.backgroundImage = `${defaultGradients}`;
        }
    } else {
        playerClock.innerHTML = blackTime;
        opponentClock.innerHTML = whiteTime;
        if (blackMinutes === 0) {
            updateClockBorders(playerClock, Math.round(blackSeconds * 1000));
        } else if (playerClock.style.color === 'red') {
            playerClock.style.color = 'var(--body-text)';
            playerClock.style.backgroundImage = `${defaultGradients}`;
        }
        if (whiteMinutes === 0) {
            updateClockBorders(opponentClock, Math.round(whiteSeconds * 1000));
        } else if (opponentClock.style.color === 'red') {
            opponentClock.style.color = 'var(--body-text)';
            opponentClock.style.backgroundImage = `${defaultGradients}`;
        }
    }
}

var reportElement = document.getElementById('reportButton');
reportElement.addEventListener("click", function () {
    const segments = window.location.href.split('/');
    const game_id = segments[segments.length - 2];
    fetch('/report_chat/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ 
            game_id: game_id, 
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "Unauthorized") {
            throw new Error('Unauthorized');
        }
        appendChatLog('Chat reported');
        return;
    })
    .catch(error => {
        appendChatLog('Chat already reported');
    });
    $('#reportChat').modal('hide');
    $(".chat-wrapper").each(function() {
        $(this).scrollTop($(this)[0].scrollHeight);
    });
});

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

    socket.onopen = function () {
        sendMessage("", "initialized");
    }

    socket.onclose = function (event) {
        $(".chat-input").prop("disabled", true);
    };

    $(".chat-input").prop("disabled", false);
}

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
        if (
            type.includes("rematch") || 
            type === "initialized" ||
            type === "undo_sent" ||
            type === "draw_sent"
        ) {
            messageObj["message"]["log"] = type;
            if (type == "initialized") {
                messageObj["message"]["opponent"] = opponent;
            }
        }
    }
    socket.send(JSON.stringify(messageObj));
}

function handleMessage(data) {
    if (data.hasOwnProperty('log')) {
        var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
        var currentGameID = sessionStorage.getItem('current_game_id');
        var playerColor;
        currentGameID = (currentGameID === 'null' ? null : currentGameID);
        playerColor = webGameMetadata["player_color"];
        if (data["log"] === "connect") {
            connect_user = data["user"];
            // Exclude spectators by adding highlighted message
            // to chat if opponent is the same
            if (connect_user === opponent) {
                var log = $('<p></p>').text(data["user"] + " connected");
                log.css({
                    'background-color': 'var(--chat-box-log)',
                    'text-align': 'center'
                });
                // Don't include initial connect messages
                if ($(".chat-messages").children().length !== 0) {
                    $(".chat-messages").append(log);
                }
            }
        } else if (data["log"] === "initialized") {
            connect_user = data["sender"];
            player = data["opponent"];
            opponent_color = data["color"];
            if ((connect_user !== opponent || player !== sender) && opponent_color !== playerColor) {
                // Assuming top is always opponent to start is fine as no flips occurred preinit
                opponentContent = document.getElementById('topPlayer');
                opponent = (connect_user !== "black" && connect_user !== "white") ? connect_user : "Anonymous"; // prevent these two usernames
                opponentContent.innerHTML = opponent;
                if (player !== sender) {
                    sendMessage("", "initialized");
                }
            }
        } else if (data["log"] === "disconnect") {
            disconnect_user = data["user"];
            if (disconnect_user === opponent) {
                // Add highlighted message to chat
                var log = $('<p></p>').text(data["user"] + " disconnected...");
                log.css({
                    'background-color': 'var(--chat-box-log)',
                    'text-align': 'center'
                });
                $(".chat-messages").append(log);

                if (rematch_accepted) {
                    fetchUUID(signed_uuid, currentGameID).then(data => {
                        window.location.href = '/play/' + data.uuid + '/';
                    });
                }
                if (rematch_request) {
                    document.getElementById("rematchButton").classList.add("used");
                }
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
            appendChatLog("Rematch Received");
        } else if (data["log"] === "rematch_accepted") {
            appendChatLog("Rematch Accepted");
            rematch_accepted = true;
            if (!rematch_received) {
                let new_game_id;
                fetchUUID(signed_uuid, currentGameID).then(data => {
                    new_game_id = data.uuid;
                    generateRematchURL(new_game_id);
                });
                document.getElementById("rematchButton").classList.add("used");
            }
        } else if (data["log"] === "rematch_declined") {
            document.getElementById("rematchButton").classList.add("used");
            appendChatLog("Rematch Declined");
        } else if (
            data["log"] === "undo_sent" || 
            data["log"] === "draw_sent" ||
            data["log"] === "spam"
            ) {
            appendChatLog(data["text"]);
        }
        return;
    }
    // Prevent XSS script injection attacks by escaping content
    var message = $('<p></p>').text(data["sender"] + ": " + data["text"]);
    $(".chat-messages").append(message);
    $(".chat-wrapper").each(function() {
        $(this).scrollTop($(this)[0].scrollHeight);
      });
}

function appendChatLog(message) {
    var log = $('<p></p>').text(message);
    log.css({
        'background-color': 'var(--chat-box-log)',
        'text-align': 'center'
    });
    $(".chat-messages").append(log);
}

function generateRematchURL(game_id) {
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = currentGameID.replace("white" + '-', '').replace("black" + '-', '');
    body = {"rematch": currentGameID};
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
            "flipButton",
            "toggleShareArrows"
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

// to defaults, not connected though as that would send a request
window.addEventListener('beforeunload', function () {
    sessionStorage.setItem('current_game_id', game_uuid);
    sessionStorage.setItem('initialized', 'null');
    sessionStorage.setItem('draw_request', 'false');
    sessionStorage.setItem('undo_request', 'false');
    sessionStorage.setItem('total_reset', 'false');
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

    if (sessionStorageObjectName === "undo_move") {
        appendChatLog("Undo Offer Sent");
    }

    if (sessionStorageObjectName === "draw_offer") {
        appendChatLog("Draw Offer Sent");
    }

    handleActionStatus(buttonId, sessionStorageObjectName, Options);
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
    {mainButtonName: "resignButton", eventNames: ["resign"]},
    {mainButtonName: "readyButton", eventNames: ["ready"]},
    {mainButtonName: "redoButton", eventNames: ["redo_stages"]}
]

var inputList = [
    { buttonId: "forwardButton", sessionStorageObjectName: "step"},
    { buttonId: "backwardButton", sessionStorageObjectName: "step"},
    { buttonId: "skipForwardButton", sessionStorageObjectName: "step"},
    { buttonId: "skipBackwardButton", sessionStorageObjectName: "step"},
    { buttonId: "undoOfferButton", sessionStorageObjectName: "undo_move", Options: "followups", action: "undo_request"},
    { buttonId: "drawOfferButton", sessionStorageObjectName: "draw_offer", Options: "followups", action: "draw_request" },
    { buttonId: "resignButton", sessionStorageObjectName: "resign", Options: "followups"},
    { buttonId: "cycleThemeButton", sessionStorageObjectName: "cycle_theme"},
    { buttonId: "flipButton", sessionStorageObjectName: "flip_board"},
    { buttonId: "readyButton", sessionStorageObjectName: "ready"},
    { buttonId: "redoButton", sessionStorageObjectName: "redo_stages"}
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

            var containerRect = movesListContainer.getBoundingClientRect();
            var moveRect = selectedMove.getBoundingClientRect();

            // Don't need to scroll, if the element is already visible
            if (moveRect.top < containerRect.top || moveRect.bottom > containerRect.bottom) {
                movesListContainer.scrollTop = selectedMove.offsetTop - (movesListContainer.clientHeight - selectedMove.clientHeight);
            }

        }
    } else if (sessionStorageObjectName == "flip_board") {
        topUser = document.getElementById('topUserMetadata');
        bottomUser = document.getElementById('bottomUserMetadata');
        topHTML = topUser.innerHTML;
        bottomHTML = bottomUser.innerHTML;
        topUser.innerHTML = bottomHTML;
        bottomUser.innerHTML = topHTML;

        flipped = !flipped;
    } else if (sessionStorageObjectName === "undo_move_accept") {
        sendMessage("Undo Offer Accepted", "undo_sent");
    } else if (sessionStorageObjectName === "undo_move_deny") {
        sendMessage("Undo Offer Declined", "undo_sent");
    } else if (sessionStorageObjectName === "draw_offer_accept") {
        sendMessage("Draw Offer Accepted", "draw_sent");
    } else if (sessionStorageObjectName === "draw_offer_deny") {
        sendMessage("Draw Offer Declined", "draw_sent");
    } else if (sessionStorageObjectName === "resign") {
        appendChatLog("Resigned");
    }
    return webGameMetadata;
}

function handleActionStatus(buttonId, sessionStorageObjectName, Options) {
    var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    var actionCommandStatus = webGameMetadata[sessionStorageObjectName];
    
    // console.log(sessionStorageObjectName, actionCommandStatus) // Good dev log, very good boy
    var initialDefaults = (!actionCommandStatus.execute && !actionCommandStatus.update_executed);
    var optionalReset = false;
    if (actionCommandStatus.hasOwnProperty("reset")) {
        initialDefaults = initialDefaults && !actionCommandStatus.reset;
        optionalReset = actionCommandStatus.reset;
    }
    if (!actionCommandStatus.update_executed && optionalReset !== true && !initialDefaults) {
        setTimeout(function () {
            // This can be too fast and execute again right before reset is set to false, 
            // hence the default condition check
            handleActionStatus(buttonId, sessionStorageObjectName, Options);
        }, 10);
    } else {
        var accept_response_sent = sessionStorageObjectName.includes("accept") && webGameMetadata[sessionStorageObjectName].update_executed;
        webGameMetadata[sessionStorageObjectName].execute = false;
        webGameMetadata[sessionStorageObjectName].update_executed = false;
        
        webGameMetadata = buttonHandling(buttonId, webGameMetadata, sessionStorageObjectName);

        if (optionalReset === true) {
            resetButtons(buttonId, Options);
            webGameMetadata[sessionStorageObjectName].reset = false;
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
        var offer_accepted_received = offerEventList.some(item => item.eventNames[0] === sessionStorageObjectName)
        if (accept_response_sent || offer_accepted_received || totalReset) {
            offerQueue = [];
        }

        sessionStorage.setItem('web_game_metadata', JSON.stringify(webGameMetadata));
        
        if (buttonId.includes("move")) {
            return;
        }
        // Resign or draw can quickly remove the button before this, even an undo offer if end game is reached
        element = document.getElementById(buttonId);
        if (element && (buttonId !== 'readyButton' && buttonId !== 'redoButton')) {
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
        handleButton(input.buttonId, input.sessionStorageObjectName, optionsValue);
    });
});

var requestChangeTrackers = {};

function requestDisplay(action, ButtonID, baseStorageName) {
    var currentValue = JSON.parse(sessionStorage.getItem(action));
    var initialized = sessionStorage.getItem('initialized');
    initialized = (initialized === 'true' ? true : null);
    var resetDisplay = null
    
    var newOptions = (currentValue === true ? "responses": "followups")
    if (initialized === true) {
        const acceptObjectName = baseStorageName + "_accept";
        const denyObjectName = baseStorageName + "_deny";
        var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
        var acceptReset = webGameMetadata[acceptObjectName].reset;
        var denyReset = webGameMetadata[denyObjectName].reset;
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
            requestDisplay(request.action, request.buttonId, request.sessionStorageObjectName);
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

function displayChatLog(sessionStorageObjectName) {
    if (sessionStorageObjectName === "undo_move") {
        appendChatLog("Undo Offer Received");
    } else if (sessionStorageObjectName === "draw_offer") {
        appendChatLog("Draw Offer Received");
    }
}

function handleButton(buttonId, sessionStorageObjectName, Options = null, resetDisplay = null, currentAction = null) {
    document.getElementById(buttonId).disabled = true;
    if (Options !== null) {
        result = optionStringsHelper(buttonId, Options)
        const buttonApproveId = result.ApproveId;
        const buttonAbandonId = result.AbandonId;
        const abandonString = result.AbandonStr;
        const acceptObjectName = sessionStorageObjectName + "_accept";
        const denyObjectName = sessionStorageObjectName + "_deny";
        if (resetDisplay !== true) {
            document.getElementById(buttonId).classList.add("hidden");
            document.getElementById(buttonApproveId).classList.remove("hidden");
            document.getElementById(buttonAbandonId).classList.remove("hidden");
            var otherFollowups = document.querySelectorAll('[followup="true"]');
            if (Options === "responses") {
                document.getElementById(buttonId).classList.add("waiting")
                offerQueue.push({mainId: buttonId, ApproveId: buttonApproveId, AbandonId: buttonAbandonId})
                displayChatLog(sessionStorageObjectName);
            }
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
                    if ((element.id !== 'readyButton' && element.id !== 'redoButton')) {
                        element.classList.remove("hidden");
                    }
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
                
                var responseName = (Options === "followups" ? sessionStorageObjectName : acceptObjectName)
                
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

            var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
            webGameMetadata[sessionStorageObjectName].reset = false;
            webGameMetadata[acceptObjectName].reset = false;
            webGameMetadata[denyObjectName].reset = false;
            
            sessionStorage.setItem(currentAction, 'false');
            sessionStorage.setItem('web_game_metadata', JSON.stringify(webGameMetadata));
            document.getElementById(buttonId).disabled = false;
        }
    } else {
        handleWebtoGameAction(buttonId, sessionStorageObjectName);
    };
}