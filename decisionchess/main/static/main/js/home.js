const soloCheckbox = document.getElementById('solo-play-checkbox');
const revealStageCheckboxMultiplayer = document.getElementById('reveal-stage-multiplayer-checkbox');
const decisionStageCheckboxMultiplayer = document.getElementById('decision-stage-multiplayer-checkbox');
const suggestiveCheckboxMultiplayer = document.getElementById('suggestive-multiplayer-checkbox');
const standardSubvariantDropdownMultiplayer = document.getElementById('timed-mode-multiplayer');
const incrementMultiplayerDropdown = document.getElementById('increment-multiplayer');
const revealStageCheckboxPrivate = document.getElementById('reveal-stage-private-checkbox');
const decisionStageCheckboxPrivate = document.getElementById('decision-stage-private-checkbox');
const suggestiveCheckboxPrivate = document.getElementById('suggestive-private-checkbox');
const standardSubvariantDropdownPrivate = document.getElementById('timed-mode-private');
const incrementPrivateDropdown = document.getElementById('increment-private');
const mainModeMultiplayer = document.getElementById('main-mode-multiplayer');
const mainModePrivate = document.getElementById('main-mode-private');
const ranked = document.getElementById('ranked');
document.addEventListener("DOMContentLoaded", function() {
    soloCheckbox.checked = false;
    revealStageCheckboxMultiplayer.checked = false;
    decisionStageCheckboxMultiplayer.checked = false;
    suggestiveCheckboxMultiplayer.checked = false;
    suggestiveCheckboxMultiplayer.disabled = true;
    standardSubvariantDropdownMultiplayer.value = '';
    incrementMultiplayerDropdown.disabled = true;
    incrementMultiplayerDropdown.value = '0';
    revealStageCheckboxPrivate.checked = false;
    decisionStageCheckboxPrivate.checked = false;
    suggestiveCheckboxPrivate.checked = false;
    suggestiveCheckboxPrivate.disabled = true;
    standardSubvariantDropdownPrivate.value = '';
    incrementPrivateDropdown.disabled = true;
    incrementPrivateDropdown.value = '0';
    mainModeMultiplayer.value = 'Decision';
    mainModePrivate.value = 'Decision';
    ranked.value = 'Casual';
});

document.addEventListener('DOMContentLoaded', function () {
    const decisionContentMultiplayer = document.getElementById('decision-content-multiplayer');
    const decisionContentPrivate = document.getElementById('decision-content-private');

    showGameOptions(mainModeMultiplayer, decisionContentMultiplayer);
    showGameOptions(mainModePrivate, decisionContentPrivate);

    mainModeMultiplayer.addEventListener('change', function() {
        showGameOptions(mainModeMultiplayer, decisionContentMultiplayer)
    });
    mainModePrivate.addEventListener('change', function() {
        showGameOptions(mainModePrivate, decisionContentPrivate)
    });
});

function adjustPreview() {
    var previewContainer = document.getElementById('preview-container');
    var iframeContainer = document.getElementById('iframe-container');
    if (iframeContainer) {
        const computedStyle = window.getComputedStyle(previewContainer);
        const paddingLeft = parseFloat(computedStyle.paddingLeft);
        const paddingRight = parseFloat(computedStyle.paddingRight);
        var width = previewContainer.offsetWidth - (paddingLeft + paddingRight);
        iframeContainer.style.height = width * 1.25 + 'px';
        iframeContainer.style.width = width + 'px';
        document.getElementById('embedded-iframe').style.height = width + 'px';
        document.getElementById('embedded-iframe').style.width = width + 'px';
    }
}

window.addEventListener('load', adjustPreview);

window.addEventListener('resize', adjustPreview);

function showGameOptions(mainMode, decisionContent) {
    const mode = mainMode.value;

    if (mode === 'Classical') {
        decisionContent.classList.add('d-none');
        decisionContent.classList.remove('d-block');
    } else if (mode === 'Decision') {
        decisionContent.classList.add('d-block');
        decisionContent.classList.remove('d-none');
    }
}

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

function updateNonStandardInfo(decisionStageCheckbox, revealStageCheckbox, suggestiveCheckbox, standardSubvariantContainer) {
    if ((decisionStageCheckbox.checked || revealStageCheckbox.checked)) {
        suggestiveCheckbox.disabled = false;
        standardSubvariantContainer.classList.add('d-none');
        standardSubvariantContainer.classList.remove('d-flex');
        // standard timed mode value to none and increment to 0
    } else {
        suggestiveCheckbox.checked = false;
        suggestiveCheckbox.disabled = true;
        standardSubvariantContainer.classList.add('d-flex');
        standardSubvariantContainer.classList.remove('d-none');
    }
}

function updateState(standardSubvariantDropdown, incrementDropdown, revealStageCheckbox, decisionStageCheckbox, suggestiveCheckbox) {
    var isTimedMode = standardSubvariantDropdown.value !== '';
    revealStageCheckbox.checked = false;
    decisionStageCheckbox.checked = false;
    revealStageCheckbox.disabled = isTimedMode;
    decisionStageCheckbox.disabled = isTimedMode;
    suggestiveCheckbox.disabled = true;
    suggestiveCheckbox.checked = false;
    incrementDropdown.disabled = !isTimedMode;
}

const standardSubvariantContainerMultiplayer = document.getElementById('timed-multiplayer');
[revealStageCheckboxMultiplayer, decisionStageCheckboxMultiplayer].forEach(checkbox => {
    checkbox.addEventListener('change', () => 
    updateNonStandardInfo(decisionStageCheckboxMultiplayer, revealStageCheckboxMultiplayer, suggestiveCheckboxMultiplayer, standardSubvariantContainerMultiplayer)
    );
});

const standardSubvariantContainerPrivate = document.getElementById('timed-private');
[revealStageCheckboxPrivate, decisionStageCheckboxPrivate].forEach(checkbox => {
    checkbox.addEventListener('change', () => 
    updateNonStandardInfo(decisionStageCheckboxPrivate, revealStageCheckboxPrivate, suggestiveCheckboxPrivate, standardSubvariantContainerPrivate)
    );
});

standardSubvariantDropdownMultiplayer.addEventListener('change', () => 
updateState(
    standardSubvariantDropdownMultiplayer, 
    incrementMultiplayerDropdown,
    revealStageCheckboxMultiplayer, 
    decisionStageCheckboxMultiplayer, 
    suggestiveCheckboxMultiplayer
    ));
standardSubvariantDropdownPrivate.addEventListener('change', () => 
updateState(
    standardSubvariantDropdownPrivate, 
    incrementPrivateDropdown,
    revealStageCheckboxPrivate, 
    decisionStageCheckboxPrivate, 
    suggestiveCheckboxPrivate
));

soloCheckbox.addEventListener('change', function(event) {
    const revealStageCheckbox = document.getElementById('reveal-stage-multiplayer-checkbox');
    const decisionStageCheckbox = document.getElementById('decision-stage-multiplayer-checkbox');
    if (event.target.checked) {
        revealStageCheckbox.checked = false;
        decisionStageCheckbox.checked = false;
        suggestiveCheckboxMultiplayer.checked = false;
        revealStageCheckbox.disabled = true;
        decisionStageCheckbox.disabled = true;
        suggestiveCheckboxMultiplayer.disabled = true;
        standardSubvariantDropdownMultiplayer.disabled = true;
        standardSubvariantDropdownMultiplayer.value = '';
        incrementMultiplayerDropdown.disabled = true;
        incrementMultiplayerDropdown.value = '0';
        ranked.value = 'Casual';
        ranked.disabled = true;
    } else {
        revealStageCheckbox.disabled = false;
        decisionStageCheckbox.disabled = false;
        standardSubvariantDropdownMultiplayer.disabled = false;
        if (standardSubvariantDropdownMultiplayer.value !== '') {
            incrementMultiplayerDropdown.disabled = false;
        }
        ranked.disabled = false;
    }
});

const newGameButtons = document.querySelectorAll('[new-game="true"]');
newGameButtons.forEach(button => {
    button.addEventListener('click', () => {
        body = {
            "position": button.dataset.position,
            "solo": document.getElementById('solo-play-checkbox').checked ? true : null,
            "main_mode": document.getElementById('main-mode-multiplayer').value,
            "reveal_stage": false,
            "decision_stage": false,
            "private": document.getElementById('solo-play-checkbox').checked ? true : null,
            "computer_game": null,
            "subvariant": "Normal",
            "increment": document.getElementById('increment-multiplayer').value,
            "ranked": "Casual"
        }
        if (body["main_mode"] === "Decision") {
            body["reveal_stage"] = document.getElementById('reveal-stage-multiplayer-checkbox').checked;
            body["decision_stage"] = document.getElementById('decision-stage-multiplayer-checkbox').checked; 
            if (document.getElementById('suggestive-multiplayer-checkbox').checked) {
                body["subvariant"] = "Suggestive";
            } else if (standardSubvariantDropdownMultiplayer.value !== '') {
                body["subvariant"] = standardSubvariantDropdownMultiplayer.value;
            }
            body["ranked"] = ranked.value;
        }
        generateGame(body);
    });
});

const newComputerGameButtons = document.querySelectorAll('[new-computer-game="true"]');
newComputerGameButtons.forEach(button => {
    button.addEventListener('click', () => {
        body = {
            "position": button.dataset.position,
            "solo": null,
            "main_mode": document.getElementById('main-mode-computer').value,
            "reveal_stage": false,
            "decision_stage": false,
            "private": null,
            "computer_game": true,
            "subvariant": "Normal",
            "increment": "0"
        }
        generateGame(body);
    });
});

const newPrivateGameButtons = document.querySelectorAll('[new-private-game="true"]');
newPrivateGameButtons.forEach(button => {
    button.addEventListener('click', () => {
        body = {
            "position": button.dataset.position,
            "solo": null,
            "main_mode": document.getElementById('main-mode-private').value,
            "reveal_stage": false,
            "decision_stage": false,
            "private": true,
            "computer_game": null,
            "subvariant": "Normal",
            "increment": document.getElementById('increment-private').value
        }
        if (body["main_mode"] === "Decision") {
            body["reveal_stage"] = document.getElementById('reveal-stage-private-checkbox').checked;
            body["decision_stage"] = document.getElementById('decision-stage-private-checkbox').checked;
            if (document.getElementById('suggestive-private-checkbox').checked) {
                body["subvariant"] = "Suggestive";
            } else if (standardSubvariantDropdownPrivate.value !== '') {
                body["subvariant"] = standardSubvariantDropdownPrivate.value;
            }
        }
        generateGame(body);
    });
});

function quickPair(event) {
    const gametype = event.currentTarget.dataset.gametype;
    fetch('/quick_pair/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify( { gametype: gametype })
    })
    .then(response => {
        if (response.status === 200) {
            return response.json();
        } else {
            console.error('Error joining game:', response.statusText);
            return Promise.reject('Error joining game');
        }
    })
    .then(data => {
        if (data.redirect) {
            window.location.href = data.url;
        }
    })
    .catch(error => {
        console.error('Error joining game:', error);
    });
}

const quickPairButtonIds = [
    'normalQuickPair', 'classicalQuickPair', 'rapidQuickPair', 'blitzQuickPair', 
    'completeSimpleQuickPair', 'completeSuggestiveQuickPair', 
    'relaySimpleQuickPair', 'relaySuggestiveQuickPair',
    'countdownSimpleQuickPair', 'countdownSuggestiveQuickPair'
];
quickPairButtonIds.forEach(id => {
    const button = document.getElementById(id);
    button.addEventListener('click', quickPair);
});

function createEmptyGamesRow() {
    var noGamesMessage = document.createElement('button');
    noGamesMessage.id = "noGamesMessage";
    noGamesMessage.className = "lobby-row empty";
    noGamesMessage.textContent = 'No games available...';
    noGamesMessage.style.borderBottom = "none";
    noGamesMessage.style.justifyContent = 'center';
    noGamesMessage.style.overflow = 'hidden';
    noGamesMessage.style.cursor = 'auto';
    noGamesMessage.style.borderBottom = "None";
    return noGamesMessage;
}

function createGameLink(game, end_index) {
    var lobbyRow = document.createElement('button');
    lobbyRow.className = "lobby-row";
    lobbyRow.style.paddingTop = '2px';
    lobbyRow.style.paddingBottom = '2px';
    
    var first = document.createElement('div');
    if (game.side === 'white') {
        first.innerHTML = whiteSideSVG;
    } else if (game.side === 'black') {
        first.innerHTML = blackSideSVG;
    } else {
        first.innerHTML = randomSideSVG;
    }
    first.style.minWidth = '10%';
    first.style.width = '10%';
    var username = document.createElement('div');
    username.textContent = game.initiator_name;
    username.style.minWidth = '30%';
    username.style.textAlign = 'left';
    var type = document.createElement('div');
    var gameType = document.createElement('div');
    if (game.game_type === 'Complete') { // Use a map for all this
        gameType.innerHTML = completeSVG;
    } else if (game.game_type === 'Relay') {
        gameType.innerHTML = relaySVG;
    } else if (game.game_type === 'Countdown') {
        gameType.innerHTML = countdownSVG;
    } else if (game.game_type === 'Standard') {
        gameType.innerHTML = standardSVG;
    } else if (game.game_type === 'Classical') {
        gameType.innerHTML = classicSVG;
    }
    var subvariant = document.createElement('div');
    if (game.subvariant === 'Normal') {
        subvariant.innerHTML = normalSVG;
    } else if (game.subvariant === 'Classical') {
        subvariant.innerHTML = classicalSVG;
    } else if (game.subvariant === 'Rapid') {
        subvariant.innerHTML = rapidSVG;
    } else if (game.subvariant === 'Blitz') {
        subvariant.innerHTML = blitzSVG;
    } else if (game.subvariant === 'Simple') {
        subvariant.innerHTML = simpleSVG;
    } else if (game.subvariant === 'Suggestive') {
        subvariant.innerHTML = suggestiveSVG;
    }
    var matchType = document.createElement('div');
    matchType.textContent = game.ranked;
    gameType.style.minWidth = '15%';
    gameType.style.width = '15%';
    subvariant.style.minWidth = '15%';
    subvariant.style.width = '15%';
    type.style.minWidth = '30%';
    type.style.width = '30%';
    type.style.paddingBottom = '2px';
    type.classList.add('d-flex');
    type.setAttribute('name', 'type');
    type.appendChild(gameType);
    type.appendChild(subvariant);
    type.appendChild(matchType);
    var time = document.createElement('div');
    if (['Normal', 'Simple', 'Suggestive'].includes(game.subvariant)) {
        time.textContent = '-';
    } else if (game.subvariant === 'Classical') {
        time.textContent = '30+'+ String(game.increment);
    } else if (game.subvariant === 'Rapid') {
        time.textContent = '10+'+ String(game.increment);
    } else if (game.subvariant === 'Blitz') {
        time.textContent = '5+'+ String(game.increment);
    }
    time.style.minWidth = '10%';
    time.style.textAlign = 'left';
    var rating = document.createElement('div');
    rating.textContent = game.initiator_elo !== null ? game.initiator_elo : '?';
    rating.style.textAlign = 'right';
    rating.style.minWidth = '20%';
    rating.style.width = '20%';
    rating.style.paddingRight = '1em';
    lobbyRow.appendChild(first);
    lobbyRow.appendChild(username);
    lobbyRow.appendChild(type);
    lobbyRow.appendChild(time);
    lobbyRow.appendChild(rating);

    var gameLink = document.createElement('a');
    gameLink.id = game.game_uuid;
    gameLink.className = "lobby-a";
    gameLink.href = '/play/' + game.game_uuid;
    gameLink.onclick = function (event) {
        event.preventDefault();
        checkGameAvailability(game.game_uuid, lobbyRow);
    };
    gameLink.appendChild(lobbyRow);

    if (end_index) {
        lobbyRow.style.borderBottom = "none";
    }
    return gameLink;
}

function updateLobby() {
    var lobbyListContainer = document.getElementById('lobby-content');

    const filters = ['position', 'username'];
    const queryParams = new URLSearchParams();

    filters.forEach(filter => {
        const filterValue = document.getElementById(`${filter}Filter`).value;
        if (filterValue) {
            queryParams.set(filter, filterValue);
        }
    });

    var queryString = queryParams.toString();

    fetch('/get_lobby_games/' + (queryString ? '?' + queryString : ''))
        .then(response => response.json())
        .then(data => {
            lobbyListContainer.innerHTML = ''
            if (data.length === 0) {
                var noGamesMessage = createEmptyGamesRow();
                lobbyListContainer.appendChild(noGamesMessage);
            }
            // Later limit it to a set number
            data.forEach((game, index) => {
                var gameLink = createGameLink(game, index === data.length - 1);
                lobbyListContainer.appendChild(gameLink);
            });
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

document.getElementById('updateFilterButton').addEventListener('click', function () {
    $('#LobbyFilterMenu').modal('hide');
    updateLobby();
});

function checkGameAvailability(gameId, lobbyRow) {
    fetch('/check_game_availability/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ gameId: gameId }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.open) {
                window.location.href = '/play/' + gameId;
            } else {
                lobbyRow.disabled = true
            }
        })
        .catch(error => {
            console.error('Error checking game availability:', error);
        });
}

function isChildWithIdExistsOptionalRemove(parentElement, childId, remove) {
    for (let i = 0; i < parentElement.children.length; i++) {
        if (parentElement.children[i].id === childId) {
            if (remove) {
                parentElement.removeChild(parentElement.children[i]);
            }
            return true;
        }
    }
    return false;
}

function matchesFilter(game, filter, filterValue) {
    if (filter === 'position') {
        return game.side === filterValue;
    } else if (filter === 'username') {
        return game.initiator_name === filterValue;
    }
}

function initSocket() {
    if (window.location.protocol == 'https:') {
        wsProtocol = 'wss://';
    } else {
        wsProtocol = 'ws://';
    }
    
    const socket = new WebSocket(wsProtocol + window.location.host + "/ws/games/");
    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        var gameId = data.id;
        var lobbyListContainer = document.getElementById('lobby-content');
        if (data.action === 'save') {
            if (!data.open_game) {
                // Remove if found
                isChildWithIdExistsOptionalRemove(lobbyListContainer, gameId, true);
                if (lobbyListContainer.children.length === 0) {
                    var noGamesMessage = createEmptyGamesRow();
                    lobbyListContainer.appendChild(noGamesMessage);
                }
                return;
            }
            game = data;
            const exists = isChildWithIdExistsOptionalRemove(lobbyListContainer, gameId, false);
            const filters = ['position', 'username'];
            var match = true;
            filters.forEach(filter => {
                const filterValue = document.getElementById(`${filter}Filter`).value;
                if (filterValue) {
                    var matchSingleFilter = matchesFilter(game, filter, filterValue);
                    if (!matchSingleFilter) {
                        match = false;
                    }
                }
            });
            if (!match) {
                return;
            }
            if (!exists) {
                var gameLink = createGameLink(game, true);
                lobbyListContainer.lastElementChild.style.borderBottom = "solid 0.05em var(--lobby-row-border)";
                lobbyListContainer.appendChild(gameLink);
                var noGamesMessage = document.getElementById("noGamesMessage");
                if (noGamesMessage) {
                    noGamesMessage.remove();
                }
            }
        } else if (data.action === 'delete') {
            isChildWithIdExistsOptionalRemove(lobbyListContainer, gameId, true);
            if (lobbyListContainer.children.length === 0) {
                var noGamesMessage = createEmptyGamesRow();
                lobbyListContainer.appendChild(noGamesMessage);
            }
            return;
        }
    };
}

window.addEventListener('load', updateLobby);
window.addEventListener('load', initSocket);

function scrollToSection(sectionId) {
    var section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView();
    }
}