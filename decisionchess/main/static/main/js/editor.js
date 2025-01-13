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
    document.getElementById('embedded-iframe').style.height = 0.8 * width + 'px';
    var isSmallScreen = window.matchMedia('(max-width: 767px)').matches;
    var commandCenterHeight = isSmallScreen ? (width * 0.8) : (width * 0.6);
    document.getElementById('command-center').style.height = commandCenterHeight + 'px';
    adjustFont();
});

window.addEventListener('resize', function() {
    var iframeContainer = document.getElementById('iframe-container');
    var width = iframeContainer.offsetWidth;
    document.getElementById('embedded-iframe').style.height = 0.8 * width + 'px';
    var isSmallScreen = window.matchMedia('(max-width: 767px)').matches;
    var commandCenterHeight = isSmallScreen ? (width * 0.8) : (width * 0.6);
    document.getElementById('command-center').style.height = commandCenterHeight + 'px';
    adjustFont();
});

document.getElementById('FENInput').addEventListener('input', function () {
    sessionStorage.setItem('FEN', document.getElementById('FENInput').value);
});

const multiplayerRadio = document.getElementById('id_match_type_0');
const computerRadio = document.getElementById('id_match_type_1');
const soloRadio = document.getElementById('id_match_type_2');
const privateText = document.getElementById('multiplayer-modal-text');

const revealStageCheckbox = document.getElementById('reveal-stage-private-checkbox');
const decisionStageCheckbox = document.getElementById('decision-stage-private-checkbox');
const suggestiveCheckbox = document.getElementById('suggestive-private-checkbox');

document.addEventListener("DOMContentLoaded", function() {
    multiplayerRadio.checked = false;
    computerRadio.checked = false;
    soloRadio.checked = false;
    revealStageCheckbox.checked = false;
    decisionStageCheckbox.checked = false;
    suggestiveCheckbox.checked = false;
    suggestiveCheckbox.disabled = true;
});


function updateState(selectedRadio) {
    var isDisabled = selectedRadio.checked;
    if (selectedRadio.id === 'id_match_type_0') {
        isDisabled = false;
    }
    revealStageCheckbox.checked = false;
    decisionStageCheckbox.checked = false;
    revealStageCheckbox.disabled = isDisabled;
    decisionStageCheckbox.disabled = isDisabled;
    suggestiveCheckbox.disabled = true;
    suggestiveCheckbox.checked = false;
    privateText.classList.add('d-none');
    if (selectedRadio.id === 'id_match_type_0' && selectedRadio.checked) {
        privateText.classList.remove('d-none');
    }
}

function updateSuggested() {
    if (decisionStageCheckbox.checked || revealStageCheckbox.checked) {
        suggestiveCheckbox.disabled = false;
    } else {
        suggestiveCheckbox.checked = false;
        suggestiveCheckbox.disabled = true;
    }
}

[multiplayerRadio, computerRadio, soloRadio].forEach(radio => {
    radio.addEventListener('change', (event) => updateState(event.target));
});

[revealStageCheckbox, decisionStageCheckbox].forEach(checkbox => {
    checkbox.addEventListener('change', () => updateSuggested());
});

function updateCommandCenter() {
    var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    if (webGameMetadata === null || Object.keys(webGameMetadata).length === 0) {
        return;
    }

    var game_FEN = webGameMetadata.FEN;
    if (game_FEN !== sessionStorage.getItem('game_FEN')) {
        sessionStorage.setItem('game_FEN', game_FEN);
    }
}

window.addEventListener('load', updateCommandCenter);

setInterval(updateCommandCenter, 100);

var initCheck = false;
function checkNewConnect() {    
    var initialized = sessionStorage.getItem('initialized');
    initialized = (initialized === 'true' ? true : false);
    if (initialized === true && initCheck === false) {
        const idStrings = [
            "cycleThemeButton", 
            "flipButton"
        ];

        idStrings.forEach(idString => {
            document.getElementById(idString).classList.remove("hidden");
        })
        
        initCheck = initialized;
        clearInterval(connectIntervalId);
    }
}

var connectIntervalId = setInterval(checkNewConnect, 1000);

window.onbeforeunload = function () {

};

// to defaults, not connected though as that would send a request
window.addEventListener('beforeunload', function () {
    sessionStorage.setItem('initialized', 'null');
    sessionStorage.setItem('FEN', 'null');
    sessionStorage.setItem('game_FEN', 'null');
});

function handleWebtoGameAction(buttonId, sessionStorageObjectName) {
    var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    webGameMetadata[sessionStorageObjectName].execute = true;
    sessionStorage.setItem('web_game_metadata', JSON.stringify(webGameMetadata));

    handleActionStatus(buttonId, sessionStorageObjectName);
}

var inputList = [
    { buttonId: "cycleThemeButton", sessionStorageObjectName: "cycle_theme"},
    { buttonId: "flipButton", sessionStorageObjectName: "flip_board"}
];

function handleActionStatus(buttonId, sessionStorageObjectName) {
    var webGameMetadata = JSON.parse(sessionStorage.getItem('web_game_metadata'));
    var actionCommandStatus = webGameMetadata[sessionStorageObjectName];
    
    // console.log(sessionStorageObjectName, actionCommandStatus) // Good dev log, very good boy
    var initialDefaults = (!actionCommandStatus.execute && !actionCommandStatus.update_executed);
    if (!actionCommandStatus.update_executed && !initialDefaults) {
        setTimeout(function () {
            // This can be too fast and execute again right before reset is set to false, 
            // hence the default condition check
            handleActionStatus(buttonId, sessionStorageObjectName);
        }, 10);
    } else {
        webGameMetadata[sessionStorageObjectName].execute = false;
        webGameMetadata[sessionStorageObjectName].update_executed = false;

        sessionStorage.setItem('web_game_metadata', JSON.stringify(webGameMetadata));

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

function eventIsExecuting(obj, eventNames) {
    for (var event of eventNames) {
        if (obj.hasOwnProperty(event) && obj[event]["execute"] === true) {
            return true;
        }
    }
    return false;
}

function handleButton(buttonId, sessionStorageObjectName) {
    document.getElementById(buttonId).disabled = true;
    handleWebtoGameAction(buttonId, sessionStorageObjectName);
}

function getCastleRights() {
    return {
        "white_kingside": document.getElementById('white-kingside-castle').checked,
        "white_queenside": document.getElementById('white-queenside-castle').checked,
        "black_kingside": document.getElementById('black-kingside-castle').checked,
        "black_queenside": document.getElementById('black-queenside-castle').checked
    }
}

const newChallengeButtons = document.querySelectorAll('[new-challenge="true"]');
    newChallengeButtons.forEach(button => {
        button.addEventListener('click', () => {
            var solo = null;
            var computer = null;
            if (document.getElementById('id_match_type_2').checked) {
                solo = true;
            } else if (document.getElementById('id_match_type_1').checked) {
                computer = true;
            } else if (!document.getElementById('id_match_type_0').checked) {
                console.error('No Match Type selection');
                return;
            }
            body = {
                "position": button.dataset.position,
                "solo": solo,
                "main_mode": 'Decision',
                "reveal_stage": false,
                "decision_stage": false,
                "private": true,
                "computer_game": computer,
                "FEN": sessionStorage.getItem('game_FEN'),
                "castling_rights": getCastleRights(),
                "subvariant": "Normal",
                "increment": "0"
            }
            if (body["main_mode"] === "Decision") {
                body["reveal_stage"] = document.getElementById('reveal-stage-private-checkbox').checked;
                body["decision_stage"] = document.getElementById('decision-stage-private-checkbox').checked;
                body["subvariant"] = document.getElementById('suggestive-private-checkbox').checked ? "Suggestive": "Normal";
            }
            generateGame(body);
        });
    });

    function generateGame(body) {
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