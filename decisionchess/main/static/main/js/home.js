document.addEventListener('DOMContentLoaded', function () {
    const mainModeMultiplayer = document.getElementById('main-mode-multiplayer');
    const mainModePrivate = document.getElementById('main-mode-private');
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
        iframeContainer.style.height = width + 'px';
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

const soloCheckbox = document.getElementById('solo-play-checkbox');
soloCheckbox.addEventListener('change', function(event) {
    const revealStageCheckbox = document.getElementById('reveal-stage-multiplayer-checkbox');
    const decisionStageCheckbox = document.getElementById('decision-stage-multiplayer-checkbox');
    if (event.target.checked) {
        revealStageCheckbox.checked = false;
        decisionStageCheckbox.checked = false;
        revealStageCheckbox.disabled = true;
        decisionStageCheckbox.disabled = true;
    } else {
        revealStageCheckbox.disabled = false;
        decisionStageCheckbox.disabled = false;
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
            "computer_game": null
        }
        if (body["main_mode"] === "Decision") {
            body["reveal_stage"] = document.getElementById('reveal-stage-multiplayer-checkbox').checked;
            body["decision_stage"] = document.getElementById('decision-stage-multiplayer-checkbox').checked;
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
            "computer_game": true
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
            "computer_game": null
        }
        if (body["main_mode"] === "Decision") {
            body["reveal_stage"] = document.getElementById('reveal-stage-private-checkbox').checked;
            body["decision_stage"] = document.getElementById('decision-stage-private-checkbox').checked;
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
                var noGamesMessage = document.createElement('button');
                noGamesMessage.className = "lobby-row empty";
                noGamesMessage.textContent = 'No games available...';
                noGamesMessage.style.borderBottom = "none";
                noGamesMessage.style.justifyContent = 'center';
                noGamesMessage.style.overflow = 'hidden'
                noGamesMessage.style.cursor = 'auto'
                lobbyListContainer.appendChild(noGamesMessage);
            }
            // Later limit it to a set number
            data.forEach((game, index) => {
                var lobbyRow = document.createElement('button');
                lobbyRow.className = "lobby-row";
                
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
                if (game.game_type === 'Complete') {
                    type.innerHTML = completeSVG;
                } else if (game.game_type === 'Relay') {
                    type.innerHTML = relaySVG;
                } else if (game.game_type === 'Countdown') {
                    type.innerHTML = countdownSVG;
                } else if (game.game_type === 'Standard') {
                    type.innerHTML = standardSVG;
                }
                type.style.minWidth = '10%';
                type.style.width = '10%';
                type.style.paddingBottom = '2px';
                var rightHalf = document.createElement('div');
                rightHalf.textContent = game.timestamp;
                rightHalf.style.minWidth = '50%';
                rightHalf.style.textAlign = 'right';
                rightHalf.style.paddingRight = '1em';
                
                lobbyRow.appendChild(first);
                lobbyRow.appendChild(username);
                lobbyRow.appendChild(type);
                lobbyRow.appendChild(rightHalf);

                var gameLink = document.createElement('a');
                gameLink.className = "lobby-a"
                gameLink.href = '/play/' + game.game_uuid;
                gameLink.onclick = function (event) {
                    event.preventDefault();
                    checkGameAvailability(game.game_uuid, lobbyRow);
                };
                gameLink.appendChild(lobbyRow);

                if (index === data.length - 1) {
                    lobbyRow.style.borderBottom = "none";
                }
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

window.addEventListener('load', updateLobby);
setInterval(updateLobby, 20000);

function scrollToSection(sectionId) {
    var section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView();
    }
}