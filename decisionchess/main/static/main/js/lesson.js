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

function adjustSizes() {
    var iframeContainer = document.getElementById('iframe-container');
    var isSmallScreen = window.matchMedia('(max-width: 767px)').matches;
    var padding = (isSmallScreen) ? 30 : 15;
    var width = iframeContainer.parentElement.offsetWidth - padding;
    var maxHeight = (isSmallScreen) ? width : window.innerHeight - 60; // - header padding - 10px
    var size = Math.min(width, maxHeight);
    document.getElementById('embedded-iframe').style.height = size + 'px';
    iframeContainer.style.height = size + 'px';
    iframeContainer.style.width = size + 'px';
    var lessonSize = size - document.getElementById('command-center').offsetHeight;
    var lessonMobileSize = window.innerHeight - size - 80 - document.getElementById('command-center').offsetHeight
    lessonSize = (isSmallScreen) ? lessonMobileSize: lessonSize;
    document.getElementById('lesson-info').style.height = lessonSize + 'px';
    adjustFont();
    if (Math.abs(iframeContainer.style.height - iframeContainer.style.width) > 0.25) {
        adjustSizes();
    }
}

window.addEventListener('load', adjustSizes);

window.addEventListener('resize', adjustSizes);

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

    var whitePlayed = JSON.parse(webGameMetadata.white_played);
    var blackPlayed = JSON.parse(webGameMetadata.black_played);

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
    adjustSizes();
}

function resetCommandCenter() {
    savedMoves = [];
    selectedMoveId = "";
    var movesListContainer = document.getElementById('moves-list');
    while (movesListContainer.firstChild) {
        movesListContainer.removeChild(movesListContainer.firstChild);
    }

    movesListContainer.innerHTML = "";
}

var previousConnected = false;
var initCheck = false;

window.addEventListener('load', resetCommandCenter);
window.addEventListener('load', updateCommandCenter);

setInterval(updateCommandCenter, 100);

function checkNewConnect() {
    var currentConnected = sessionStorage.getItem('connected');
    currentConnected = (currentConnected === 'true' ? true : false);
    
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
        var movesListContainer = document.getElementById('moves-list');
        movesListContainer.scrollTop = movesListContainer.scrollHeight;
        initCheck = initialized;
        adjustSizes();
    }
}

var connectIntervalId = setInterval(checkNewConnect, 1000);

window.onbeforeunload = function () { // check if needed
};

// to defaults, not connected though as that would send a request
window.addEventListener('beforeunload', function () {
    sessionStorage.setItem('current_game_id', game_ids[0]);
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

var inputList = [
    { buttonId: "forwardButton", sessionStorageObjectName: "step"},
    { buttonId: "backwardButton", sessionStorageObjectName: "step"},
    { buttonId: "skipForwardButton", sessionStorageObjectName: "step"},
    { buttonId: "skipBackwardButton", sessionStorageObjectName: "step"},
    { buttonId: "cycleThemeButton", sessionStorageObjectName: "cycle_theme"},
    { buttonId: "flipButton", sessionStorageObjectName: "flip_board"}
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
        flipped = !flipped;
    }
    return webGameMetadata;
}

function handleActionStatus(buttonId, sessionStorageObjectName) {
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
            handleActionStatus(buttonId, sessionStorageObjectName);
        }, 10);
    } else {
        webGameMetadata[sessionStorageObjectName].execute = false;
        webGameMetadata[sessionStorageObjectName].update_executed = false;
        
        webGameMetadata = buttonHandling(buttonId, webGameMetadata, sessionStorageObjectName);

        if (optionalReset === true) {
            resetButtons(buttonId, Options);
            webGameMetadata[sessionStorageObjectName].reset = false;
        }

        sessionStorage.setItem('web_game_metadata', JSON.stringify(webGameMetadata));
        
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

inputList.forEach(function(input) {
    document.getElementById(input.buttonId).addEventListener("click", function() {
        handleButton(input.buttonId, input.sessionStorageObjectName);
    });
});

function handleButton(buttonId, sessionStorageObjectName) {
    document.getElementById(buttonId).disabled = true;
    handleWebtoGameAction(buttonId, sessionStorageObjectName);
}