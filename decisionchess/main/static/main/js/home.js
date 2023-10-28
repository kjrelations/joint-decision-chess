// Generic fetch GET redirect function maybe
function generateGameURL() {
    fetch('/create_new_game/')
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
const newGameButtons = document.querySelectorAll('.new-game');
newGameButtons.forEach(button => {
    button.addEventListener('click', generateGameURL);
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
                
                var leftHalf = document.createElement('div');
                leftHalf.textContent = game.initiator_name;
                leftHalf.style.minWidth = '50%'
                leftHalf.style.textAlign = 'center';
                var rightHalf = document.createElement('div');
                rightHalf.textContent = game.timestamp;
                rightHalf.style.minWidth = '50%'
                rightHalf.style.textAlign = 'right';
                rightHalf.style.paddingRight = '1em'
                
                lobbyRow.appendChild(leftHalf);
                lobbyRow.appendChild(rightHalf);

                var gameLink = document.createElement('a');
                gameLink.className = "lobby-a"
                gameLink.href = '/play/' + game.game_uuid;
                gameLink.onclick = function (event) {
                    event.preventDefault();
                    checkGameAvailability(game.game_uuid, gameLink, lobbyRow);
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

var csrftoken = "{{ csrf_token|escapejs }}";

function checkGameAvailability(gameId, gameLink, lobbyRow) {
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