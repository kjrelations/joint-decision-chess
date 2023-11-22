function generateGame(position, private = null, computer_game = null) {
    body = {"position": position}
    if (computer_game) {
        body["computer_game"] = true
    }
    if (private) {
        body["private"] = true
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
const newGameButtons = document.querySelectorAll('[new-game="true"]');
newGameButtons.forEach(button => {
    button.addEventListener('click', () => {
        const position = button.dataset.position;
        generateGame(position)
    });
});

const newComputerGameButtons = document.querySelectorAll('[new-computer-game="true"]');
newComputerGameButtons.forEach(button => {
    button.addEventListener('click', () => {
        const position = button.dataset.position;
        generateGame(position, computer_game = true)
    });
});

const newPrivateGameButtons = document.querySelectorAll('[new-private-game="true"]');
newPrivateGameButtons.forEach(button => {
    button.addEventListener('click', () => {
        const position = button.dataset.position;
        generateGame(position, private = true)
    });
});

function quickPair() {
    fetch('/quick_pair')
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

const quickPairButton = document.getElementById("quick-pair")
quickPairButton.addEventListener('click', quickPair)

function updateLobby() {
    var lobbyListContainer = document.getElementById('lobby-content');

    fetch('/get_lobby_games/')
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
                first.textContent = game.side;
                first.style.minWidth = '10%';
                first.style.textAlign = 'center';
                var username = document.createElement('div');
                username.textContent = game.initiator_name;
                username.style.minWidth = '40%';
                username.style.textAlign = 'center';
                var rightHalf = document.createElement('div');
                rightHalf.textContent = game.timestamp;
                rightHalf.style.minWidth = '50%';
                rightHalf.style.textAlign = 'right';
                rightHalf.style.paddingRight = '1em';
                
                lobbyRow.appendChild(first);
                lobbyRow.appendChild(username);
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