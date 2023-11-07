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

var gameSaved = false;

function updateCommandCenter() {
    var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = (currentGameID === 'null' ? null : currentGameID);
    if (currentGameID !== null && existingWebGameMetadata.hasOwnProperty(currentGameID)) {
        var webGameMetadata = existingWebGameMetadata[currentGameID];
        var moves = webGameMetadata.alg_moves;
        var movesListContainer = document.getElementById('moves-list');
        var endState = webGameMetadata.end_state;
        if (endState !== '') {
            const buttons = document.querySelectorAll(".action-button");
            clearInterval(requestIntervalId);
            clearInterval(connectIntervalId);
            buttons.forEach(button => {
                button.remove();
            });
        }

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
            if (!gameSaved) { // Only execute this once
                gameSaved = true
                var comp_moves = webGameMetadata.comp_moves;
                var FEN_final = webGameMetadata.FEN_final_pos;
                saveHistoricGame(moves.join(','), comp_moves.join('-'), endState, FEN_final, forcedEnd);
            }
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

var previousConnected = false
var initCheck = false

window.addEventListener('load', resetCommandCenter);
window.addEventListener('load', updateCommandCenter);

setInterval(updateCommandCenter, 100);

function updateConnectedStatus(status) {
    fetch('/update_connected/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ 
            game_uuid: game_uuid, 
            web_connect: status
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
    })
    .catch(error => {
        console.error('Error updating connection status:', error);
    });
}

function checkNewConnect() {
    var currentConnected = sessionStorage.getItem('connected');
    currentConnected = (currentConnected === 'true' ? true : false);
    if (currentConnected === true && previousConnected === false) {
        updateConnectedStatus(true)
    }
    
    var initialized = sessionStorage.getItem('initialized');
    initialized = (initialized === 'true' ? true : false);
    if (initialized === true && initCheck === false) {
        const idStrings = ["undoOfferButton", "resignButton", "drawOfferButton", "cycleThemeButton", "flipButton"];
        idStrings.forEach(idString => {
            document.getElementById(idString).classList.remove("hidden")
        })
        initCheck = initialized
    }

    previousConnected = currentConnected;
}

var connectIntervalId = setInterval(checkNewConnect, 1000);

window.onbeforeunload = function (e) {
    var confirmationMessage = 'You have unsaved changes. Are you sure you want to leave this page?';
    e.returnValue = confirmationMessage; // For legacy browsers
    return confirmationMessage;

    var userConfirmed = confirm(confirmationMessage);
    if (userConfirmed) {
        updateConnectedStatus(false); // This simply won't work so we'll just need web-sockets
    }
};

// to defaults
window.addEventListener('beforeunload', function () {
    sessionStorage.setItem('connected', 'false');
    sessionStorage.setItem('current_game_id', game_uuid);
    sessionStorage.setItem('initialized', 'null');
    sessionStorage.setItem('draw_request', 'false');
    sessionStorage.setItem('undo_request', 'false');
    sessionStorage.setItem('total_reset', 'false');
});

var eventExecutionStatus = {};

function handleWebtoGameAction(buttonId, localStorageObjectName, Options = null) {
    var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
    var currentGameID = sessionStorage.getItem('current_game_id');
    currentGameID = (currentGameID === 'null' ? null : currentGameID);
    if (currentGameID !== null && existingWebGameMetadata.hasOwnProperty(currentGameID)) { 
        var webGameMetadata = existingWebGameMetadata[currentGameID];
        webGameMetadata[localStorageObjectName].execute = true
        existingWebGameMetadata[currentGameID] = webGameMetadata
        localStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));

        if (!eventExecutionStatus[localStorageObjectName]) {
            eventExecutionStatus[localStorageObjectName] = { isExecuting: false, timeoutId: null };
        }

        handleActionStatus(buttonId, currentGameID, localStorageObjectName, Options);

    } else {
        console.warn("Failed to execute action")
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
    { buttonId: "undoOfferButton", localStorageObjectName: "undo_move", Options: "followups", action: "undo_request"},
    { buttonId: "drawOfferButton", localStorageObjectName: "draw_offer", Options: "followups", action: "draw_request" },
    { buttonId: "resignButton", localStorageObjectName: "resign", Options: "followups"},
    { buttonId: "cycleThemeButton", localStorageObjectName: "cycle_theme"},
    { buttonId: "flipButton", localStorageObjectName: "flip_board"},
];

function handleActionStatus(buttonId, currentGameID, localStorageObjectName, Options) {
    var existingWebGameMetadata = JSON.parse(localStorage.getItem('web_game_metadata'));
    var webGameMetadata = existingWebGameMetadata[currentGameID];
    var actionCommandStatus = webGameMetadata[localStorageObjectName];
    
    // console.log(localStorageObjectName, actionCommandStatus) // Good dev log, very good boy
    var initialDefaults = (!actionCommandStatus.execute && !actionCommandStatus.update_executed);
    var optionalReset = false
    if (actionCommandStatus.hasOwnProperty("reset")) {
        initialDefaults = initialDefaults && !actionCommandStatus.reset
        optionalReset = actionCommandStatus.reset
    }
    if (!actionCommandStatus.update_executed && optionalReset !== true && !initialDefaults) {
        eventExecutionStatus[localStorageObjectName].timeoutId = setTimeout(function () {
            // This can be too fast and execute again right before reset is set to false, 
            // hence the default condition check
            handleActionStatus(buttonId, currentGameID, localStorageObjectName, Options);
        }, 10);
    } else {
        var accept_response_sent = localStorageObjectName.includes("accept") && webGameMetadata[localStorageObjectName].update_executed
        webGameMetadata[localStorageObjectName].execute = false
        webGameMetadata[localStorageObjectName].update_executed = false
        
        if (optionalReset === true) {
            resetButtons(buttonId, localStorageObjectName, Options)
            webGameMetadata[localStorageObjectName].reset = false
        }
        var totalReset = JSON.parse(sessionStorage.getItem("total_reset"));
        if (totalReset) {
            // Need to reset all active offer buttons
            offerEventList.forEach(function(event) {
                for (var i = 0; i < event.eventNames.length; i++) {
                    var subevent = event.eventNames[i];
                    var subOptions = i === 0 ? "followups" : "responses";
                    document.getElementById(event.mainButtonName).classList.remove("waiting")
                    document.getElementById(event.mainButtonName).disabled = false
                    resetButtons(event.mainButtonName, subevent, subOptions)
                }
            });
            sessionStorage.setItem("total_reset", 'false')
        }
        // We don't want to clear the offer queue on follow-ups or simple client actions or deny (individual resets)
        // Only on accepts, main actions accepts, and total resets
        var offer_accepted_received = offerEventList.some(item => item.eventNames[0] === localStorageObjectName)
        if (accept_response_sent || offer_accepted_received || totalReset) {
            offerQueue = [];
        }

        existingWebGameMetadata[currentGameID] = webGameMetadata
        localStorage.setItem('web_game_metadata', JSON.stringify(existingWebGameMetadata));
        
        document.getElementById(buttonId).disabled = false;
    }
}

function optionStringsHelper(mainbuttonId, Options) {
    var approveString = "Confirm";
    var abandonString = "Cancel";
    var replaceString = "Button";
    if (Options === "responses") {
        approveString = "Accept";
        abandonString = "Deny";
        replaceString = "OfferButton"
    }
    const buttonApproveId = mainbuttonId.replace(replaceString, approveString + "Button");
    const buttonAbandonId = mainbuttonId.replace(replaceString, abandonString + "Button");
    return {ApproveId: buttonApproveId, AbandonId: buttonAbandonId, AbandonStr: abandonString}
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

function resetButtons(mainbuttonId, localStorageObjectName, Options) {
    result = optionStringsHelper(mainbuttonId, Options)
    const buttonApproveId = result.ApproveId
    const buttonAbandonId = result.AbandonId
    hideOptions(mainbuttonId, buttonApproveId, buttonAbandonId)
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
        const acceptObjectName = baseStorageName + "_accept"
        const denyObjectName = baseStorageName + "_deny"
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
        handleButton(ButtonID, baseStorageName, newOptions, resetDisplay, action)
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
        const buttonApproveId = result.ApproveId
        const buttonAbandonId = result.AbandonId
        const abandonString = result.AbandonStr
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
            
            actionbuttons.forEach(function(element) {
                if (element.id !== buttonId) {
                    element.classList.remove("hidden");
                    var actionEvents = actionEventList.find(event => event.mainButtonName === element.id)
                    var notQueued = offerQueue.every(item => item.mainId !== element.id)
                    var notExecuting = !eventIsExecuting(webGameMetadata, actionEvents.eventNames)
                    if (notExecuting && notQueued) {
                        element.disabled = false;
                    }
                }
            });
            document.getElementById(buttonApproveId).addEventListener("click", function() { 
                hideOptions(buttonId, buttonApproveId, buttonAbandonId)
                if (Options === "responses") {
                    document.getElementById(buttonId).classList.remove("waiting")
                    dequeButton(buttonId)
                        .then(updatedQueue => {
                        offerQueue = updatedQueue;
                        showNewOptions(offerQueue);
                        });
                } else {
                    showNewOptions(offerQueue)
                }
                
                var responseName = (Options === "followups" ? localStorageObjectName : acceptObjectName)
                
                handleWebtoGameAction(buttonId, responseName, Options);
            }, { once: true });
            document.getElementById(buttonAbandonId).addEventListener("click", function() {
                hideOptions(buttonId, buttonApproveId, buttonAbandonId)
                if (Options === "responses") {
                    document.getElementById(buttonId).classList.remove("waiting")
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
                        document.getElementById(event.mainButtonName).classList.remove("waiting");
                        document.getElementById(event.mainButtonName).disabled = false;
                        var subevent = event.eventNames[i];
                        var subOptions = i === 0 ? "followups" : "responses";
                        resetButtons(event.mainButtonName, subevent, subOptions)
                    }
                });
                sessionStorage.setItem("total_reset", 'false')
            } else if (Options === "responses") {
                document.getElementById(buttonId).classList.remove("waiting")
                dequeButton(buttonId)
                    .then(updatedQueue => {
                    offerQueue = updatedQueue;
                    showNewOptions(offerQueue);
                    });
            } else {
                showNewOptions(offerQueue)
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
        handleWebtoGameAction(buttonId, localStorageObjectName)
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