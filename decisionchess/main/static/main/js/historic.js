function adjustFont() {
    const elements = document.querySelectorAll('.action-button')
    const parent = document.getElementById('command-center')
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
    document.getElementById('command-center').style.height = (width * 0.5) + 'px';
    adjustFont();
});

window.addEventListener('resize', function() {
    var iframeContainer = document.getElementById('iframe-container');
    var width = iframeContainer.offsetWidth;
    document.getElementById('embedded-iframe').style.height = width + 'px';
    document.getElementById('command-center').style.height = (width * 0.5) + 'px';
    adjustFont();
});

function updateCommandCenter() {
    var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = (currentGameID === 'null' ? null : currentGameID);
    if (currentGameID !== null && existingWebGameMetadata.hasOwnProperty(currentGameID)) {
        var webGameMetadata = existingWebGameMetadata[currentGameID];
        var moves = webGameMetadata.alg_moves;
        var movesListContainer = document.getElementById('moves-list');
        var endState = webGameMetadata.end_state;

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
            
            var leftHalf = document.createElement('div');
            leftHalf.style.width = '50%';
            leftHalf.textContent = move1;

            var rightHalf = document.createElement('div');
            rightHalf.style.width = '50%';
            rightHalf.textContent = move2;

            if (move1 !== '1-0' && move1 !== '0-1' && move1 !== '½–½') {
                moveRow.appendChild(leftHalf);
                moveRow.appendChild(rightHalf);

                movesListContainer.appendChild(moveRow);
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
    }
}

function resetCommandCenter() {
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

window.addEventListener('load', resetCommandCenter);
window.addEventListener('load', updateCommandCenter);

setInterval(updateCommandCenter, 100);

function handleWebtoGameAction(buttonId, localStorageObjectName) {
    var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = (currentGameID === 'null' ? null : currentGameID);
    if (currentGameID !== null && existingWebGameMetadata.hasOwnProperty(currentGameID)) { 
        var webGameMetadata = existingWebGameMetadata[currentGameID];
        webGameMetadata[localStorageObjectName].execute = true
        existingWebGameMetadata[currentGameID] = webGameMetadata
        // Could move this into it's own function
        if (localStorageObjectName == "forward") {
            if (move_index + 1 >= comp_moves.length) {
                webGameMetadata[localStorageObjectName].execute = false
                webGameMetadata[localStorageObjectName].index = null
                existingWebGameMetadata[currentGameID] = webGameMetadata
                localStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));
                
                document.getElementById(buttonId).disabled = false;
                return;
            }
            index_number = (buttonId === "forwardButton" ? move_index + 1 : comp_moves.length - 1)
            webGameMetadata[localStorageObjectName].index = index_number
        } else if (localStorageObjectName == "backward") {
            if (move_index < 0) {
                webGameMetadata[localStorageObjectName].execute = false
                webGameMetadata[localStorageObjectName].index = null
                existingWebGameMetadata[currentGameID] = webGameMetadata
                localStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));
                
                document.getElementById(buttonId).disabled = false;
                return;
            }
            index_number = (buttonId === "backwardButton" ? move_index : -1)
            webGameMetadata[localStorageObjectName].index = index_number
        }
        localStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));

        handleActionStatus(buttonId, currentGameID, localStorageObjectName);
    } else {
        console.warn("Failed to execute action")
    }
}

var inputList = [
    { buttonId: "forwardButton", localStorageObjectName: "forward"},
    { buttonId: "backwardButton", localStorageObjectName: "backward"},
    { buttonId: "skipForwardButton", localStorageObjectName: "forward"},
    { buttonId: "skipBackButton", localStorageObjectName: "backward"},
    { buttonId: "cycleThemeButton", localStorageObjectName: "cycle_theme"},
    { buttonId: "flipButton", localStorageObjectName: "flip_board"},
];

function buttonHandling(buttonId, webGameMetadata, localStorageObjectName) {
    if (localStorageObjectName == "forward") {
        webGameMetadata[localStorageObjectName].index = null
        if (buttonId === "forwardButton") {
            move_index++
        } else if (buttonId === "skipForwardButton") {
            move_index = comp_moves.length - 1
        }
        // update move highlighting 
    } else if (localStorageObjectName == "backward") {
        webGameMetadata[localStorageObjectName].index = null
        if (buttonId === "backwardButton") {
            move_index--
        } else if (buttonId === "skipBackButton") {
            move_index = -1
        }
        // update move highlighting 
    }
    return webGameMetadata
}

function handleActionStatus(buttonId, currentGameID, localStorageObjectName) {
    var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
    var webGameMetadata = existingWebGameMetadata[currentGameID];
    var actionCommandStatus = webGameMetadata[localStorageObjectName];
    
    // console.log(localStorageObjectName, actionCommandStatus) // Good dev log, very good boy
    var initialDefaults = (!actionCommandStatus.execute && !actionCommandStatus.update_executed);
    if (!actionCommandStatus.update_executed && !initialDefaults) {
        setTimeout(function () {
            handleActionStatus(buttonId, currentGameID, localStorageObjectName);
        }, 0);
    } else {
        webGameMetadata[localStorageObjectName].execute = false
        webGameMetadata[localStorageObjectName].update_executed = false

        webGameMetadata = buttonHandling(buttonId, webGameMetadata, localStorageObjectName)

        existingWebGameMetadata[currentGameID] = webGameMetadata
        localStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));
        
        document.getElementById(buttonId).disabled = false;
    }
}

inputList.forEach(function(input) {
    document.getElementById(input.buttonId).addEventListener("click", function() {
        handleButton(input.buttonId, input.localStorageObjectName);
    });
});

function handleButton(buttonId, localStorageObjectName) {
    document.getElementById(buttonId).disabled = true;
    handleWebtoGameAction(buttonId, localStorageObjectName)
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