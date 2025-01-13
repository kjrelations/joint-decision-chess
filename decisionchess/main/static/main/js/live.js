var previewRing = [];

function getRandomGame(games) {
    var availableGames = games.filter(game => !previewRing.includes(game.id));
    if (availableGames.length !== 0) {
        const randomIndex = Math.floor(Math.random() * availableGames.length);
        return availableGames[randomIndex];
    }
    return null;
}

function replaceRow(game, prevId) {
    var feedIndex = active_games.indexOf(game);
    if (feedIndex !== -1 && document.getElementById('feed-content').children[feedIndex]) {
        var feedButton = document.getElementById('feed-content').children[feedIndex];
        var gameLink = createFeedRow(game);
        feedButton.parentNode.replaceChild(gameLink, feedButton);
    }
    const oldFeedIndex = active_games.findIndex(game => game.id === prevId);
    if (oldFeedIndex !== -1) {
        var feedButton = document.getElementById('feed-content').children[oldFeedIndex];
        var gameLink = createFeedRow(active_games[oldFeedIndex]);
        feedButton.parentNode.replaceChild(gameLink, feedButton);
    }
}

var previewBatchIntervalId = null;
var batchLoadingCancelled = false;
var loadingIds = [];
var loading = 0;
var loaded = 0;
function loadPreviews() {
    if (previewBatchIntervalId !== null) {
        clearTimeout(previewBatchIntervalId);
        previewBatchIntervalId = null;
    }
    loaded = 0;
    loading = 0;
    loadingIds = [];
    batchLoadingCancelled = true;
    previewRing = [];
    const gamesToLoad = Math.min(10, active_games.length);
    for (let i = 1; i <= 10; i++) {
        game = getRandomGame(active_games);
        var iframeContainer = document.getElementById(`embedded-iframe-${i}`);
        const iframeKey = `game-${i}`;
        if (iframeContainer) { 
            if (i < gamesToLoad + 1 && game !== null) {
                const gameId = sessionStorage.getItem(iframeKey);
                sessionStorage.setItem(iframeKey, game.id)
                sessionStorage.removeItem(`waiting-${iframeKey}`);
                document.getElementById(`black-metadata-${i}`).textContent = `${game.black_user}`;
                document.getElementById(`white-metadata-${i}`).textContent = `${game.white_user}`;
                previewRing[i - 1] = game.id;
                replaceRow(game, gameId);
            } else {
                if (document.getElementById(`embedded-iframe-${i}`) !== null) {
                    sessionStorage.setItem(iframeKey, "");
                    sessionStorage.removeItem(`waiting-${iframeKey}`);
                    document.getElementById(`black-metadata-${i}`).textContent = "";
                    document.getElementById(`white-metadata-${i}`).textContent = "";
                } else {
                    document.getElementById(`game-${i}`).innerHTML = "";
                }
                previewRing[i - 1] = "";
            }
        }
    }
    runBatchInvervals();
}


function getPreviewLink(key) {
    const previewValue = sessionStorage.getItem(key);
    return previewValue !== "" && previewValue !== null ? `/play/${previewValue}` : null;
}

function addHrefHandler(key) {
    const preview = document.getElementById(key);
    preview.addEventListener("mouseover", function() {
        const newHref = getPreviewLink(key);
        preview.href = newHref || "#";
    });
    
    preview.addEventListener("click", function(event) {
        event.preventDefault();
        const newHref = getPreviewLink(key);
        preview.href = newHref || "#";
        window.location.assign(preview.href);
    });
}

async function loadNewPreviewBatch() {
    const batch = 4;
    for (let i = 1; i <= 10; i++) {
        if (batchLoadingCancelled) {
            return;
        }
        if (loading === batch && loaded >= batch) {
            loaded = 0;
            loading = 0;
        }
        gameContainer = document.getElementById(`game-${i}`);
        const waiting = document.getElementById(`embedded-iframe-${i}`) === null;
        const previousLoaded = false;
        const iframeKey = `game-${i}`;
        if (!waiting) {
            var iframeContainer = document.getElementById(`embedded-iframe-${i}`);
            const gameId = sessionStorage.getItem(iframeKey);
            const status = sessionStorage.getItem(`waiting-${iframeKey}`);
            if (status === "true") {
                waiting = true;
                previousLoaded = true;
                if (loadingIds.includes(gameId)) {
                    loaded += 1;
                    loadingIds.splice(loadingIds.indexOf(gameId), 1);
                }
            } else if (status === "false" && loadingIds.includes(gameId)) {
                loaded += 1;
                loadingIds.splice(loadingIds.indexOf(gameId), 1);
            }
        }
        if (loading === batch && loaded < batch) {
            continue;
        }
        if (waiting) {
            game = getRandomGame(active_games);
            if (game === null) {
                for (j = i; j <= 10; j++) {
                    if (document.getElementById(`embedded-iframe-${j}`) === null) {
                        document.getElementById(`game-${j}`).innerHTML = "";
                    }
                }
                return;
            }
            var iframeContainer = document.getElementById(`embedded-iframe-${i}`);
            var prevId = "";
            if (iframeContainer) {
                if (previousLoaded) {
                    const gameId = sessionStorage.getItem(iframeKey);
                    sessionStorage.removeItem(`waiting-${iframeKey}`);
                    prevId = gameId;
                    document.getElementById(`black-metadata-${i}`).textContent = `${game.black_user}`;
                    document.getElementById(`white-metadata-${i}`).textContent = `${game.white_user}`;
                }
            } else {
                var content = `
                <div class="metadata" id="black-metadata-${i}">${game.black_user}</div>
                <iframe 
                id="embedded-iframe-${i}" 
                style="pointer-events: none;"
                src="${preview_src}key=game-${i}" 
                frameborder=0 
                scrolling="no" 
                sandbox="allow-same-origin 
                allow-scripts">
                </iframe>
                <div class="metadata" id="white-metadata-${i}">${game.white_user}</div>
                `;
                gameContainer.innerHTML = content;
                addHrefHandler(`game-${i}`);
                adjustSizes();
            }
            sessionStorage.setItem(iframeKey, game.id);
            previewRing[i - 1] = game.id;
            replaceRow(game, prevId);
            loading += 1;
            loadingIds.push(game.id);
        }
    }
}

function adjustSizes() {
    var contentContainer = document.getElementById("multiview-matrix");
    const computedStyle = window.getComputedStyle(contentContainer);
    const paddingLeft = parseFloat(computedStyle.paddingLeft);
    const paddingRight = parseFloat(computedStyle.paddingRight);
    const parentWidth = contentContainer.parentElement.offsetWidth;
    const parentHeight = contentContainer.parentElement.offsetHeight;
    var matrixDimension = Math.min(parentWidth, parentHeight) - (paddingLeft + paddingRight);
    contentContainer.style.width = matrixDimension + 'px';
    var containerWidth = matrixDimension / 5;
    gameContainerHeight = matrixDimension * 1.25 / 4;
    var isSmallScreen = window.matchMedia('(max-width: 767px)').matches;
    contentContainer.style.height = isSmallScreen ? (gameContainerHeight * 7.5) + 'px': (gameContainerHeight * 4.1) + 'px';
    var gameDimension = containerWidth * 0.9;
    for (let i = 1; i <= 10; i++) {
        var gameContainer = document.getElementById(`game-${i}`);
        var iframeContainer = document.getElementById(`embedded-iframe-${i}`);
        if (gameContainer) {
            gameContainer.style.width = containerWidth + 'px';
            gameContainer.style.height = gameContainerHeight + 'px';
        }
        if (iframeContainer) {
            iframeContainer.style.width = gameDimension + 'px';
            iframeContainer.style.height = gameDimension + 'px';
        }
    }
    var centerIframe = document.getElementById("center-iframe");
    if (centerIframe) {
        const centerHeight = centerIframe.parentElement.offsetHeight;
        centerIframe.style.width = centerHeight * 0.8 + 'px';
        centerIframe.style.height = centerHeight * 0.8 + 'px';
    }
}

function backToFeed() {
    var feedContent = document.getElementById("feed");
    feedContent.classList.add("d-flex");
    feedContent.classList.remove("d-none");
    var centerPreview = document.getElementById("center-preview");
    sessionStorage.removeItem(`waiting-center-game`);
    sessionStorage.setItem("center-game", "");
    document.getElementById(`black-center-metadata`).textContent = "";
    document.getElementById(`white-center-metadata`).textContent = "";
    centerPreview.classList.remove("d-flex");
    centerPreview.classList.add("d-none");
}

function loadCenterPreview(game) {
    var feedContent = document.getElementById("feed");
    feedContent.classList.remove("d-flex");
    feedContent.classList.add("d-none");
    var centerPreview = document.getElementById("center-preview");
    var centerIframe = document.getElementById("center-iframe");
    if (centerIframe) {
        sessionStorage.removeItem(`waiting-center-game`);
        document.getElementById(`black-center-metadata`).textContent = `${game.black_user}`;
        document.getElementById(`white-center-metadata`).textContent = `${game.white_user}`;
    }
    else {
        var content = `
        <div class="back-button mr-auto ml-auto" onclick="backToFeed()"><i class="fa-solid fa-chevron-left"></i></div>
        <a class="game-container" id="center-game" style="height: 100%">
            <div class="center-metadata" id="black-center-metadata">${game.black_user}</div>
            <iframe 
                id="center-iframe"
                src="${preview_src}key=center-game" 
                style="pointer-events: none;"
                frameborder=0 
                scrolling="no" 
                sandbox="allow-same-origin 
                allow-scripts">
            </iframe>
            <div class="center-metadata" id="white-center-metadata">${game.white_user}</div>
        </a>
        <div class="mr-auto ml-auto" ></div>
        `;
        centerPreview.innerHTML = content;
        addHrefHandler("center-game");
    }
    sessionStorage.setItem("center-game", game.id);
    centerPreview.classList.add("d-flex");
    centerPreview.classList.remove("d-none");
    adjustSizes();
}

function createFeedRow(game) {
    var feedRow = document.createElement('div');
    feedRow.className = "feed-row";
    
    var type = document.createElement('div');
    if (game.gametype === 'Complete') {
        type.innerHTML = completeSVG;
    } else if (game.gametype === 'Relay') {
        type.innerHTML = relaySVG;
    } else if (game.gametype === 'Countdown') {
        type.innerHTML = countdownSVG;
    } else if (game.gametype === 'Standard') {
        type.innerHTML = standardSVG;
    }
    type.style.minWidth = '20%';
    type.style.width = '20%';
    type.style.paddingBottom = '2px';
    type.className = 'd-flex justify-content-center align-content-center';
    var whiteUsername = document.createElement('div');
    whiteUsername.textContent = game.white_user;
    whiteUsername.style.minWidth = '25%';
    whiteUsername.style.textAlign = 'left';
    whiteUsername.className = "d-flex-inline align-content-center";
    var blackUsername = document.createElement('div');
    blackUsername.textContent = game.black_user;
    blackUsername.style.minWidth = '25%';
    blackUsername.style.textAlign = 'left';
    blackUsername.className = "d-flex-inline align-content-center";
    var startTime = document.createElement('div');
    startTime.textContent = game.start_time;
    startTime.style.minWidth = '30%';
    startTime.style.textAlign = 'right';
    startTime.className = "d-flex-inline align-content-center";
    if (startTime.textContent === "New") {
        startTime.style.color = 'var(--homebutton-decision)';
    }
    
    feedRow.appendChild(type);
    feedRow.appendChild(whiteUsername);
    feedRow.appendChild(blackUsername);
    feedRow.appendChild(startTime);

    var gameLink = document.createElement('div');
    
    if (previewRing.includes(game.id)) {
        gameLink.className = "selected";
        var previewIndex = previewRing.indexOf(game.id) + 1;
        gameLink.addEventListener('mouseover', () => {
            document.querySelector(`#game-${previewIndex}`).classList.add('hover-active');
        });
        
        gameLink.addEventListener('mouseout', () => {
            document.querySelector(`#game-${previewIndex}`).classList.remove('hover-active');
        });
    } else {
        gameLink = document.createElement('button');
        gameLink.className = "feed-button";
        gameLink.onclick = function() {
            loadCenterPreview(game);
        };
    }

    gameLink.appendChild(feedRow);
    return gameLink;
}

function loadFeed() {
    var feedListContainer = document.getElementById('feed-content');
    feedListContainer.innerHTML = "";
    active_games.forEach(game => {
        var gameLink = createFeedRow(game);
        feedListContainer.appendChild(gameLink);
    });
}

function appendNewGame(game) {
    var feedListContainer = document.getElementById('feed-content');
    gameLink = createFeedRow(game);
    feedListContainer.appendChild(gameLink);
}

var filters = {
    "types": ["Standard, Normal"],
    "user_type": "any",
    "user": ""
}

function matchesFilter(game) {
    if (!filters.types.includes(game.gametype)) {
        return false;
    }
    if (filters.user !== "") {
        console.log(game.white_user !== filters.user && game.black_user !== filters.user)
        console.log(game)
        if (filters.user_type === "any" && 
           (game.white_user !== filters.user && game.black_user !== filters.user)) 
        {
            return false;
        } else if (filters.user_type === "white" && 
                  (game.white_user !== filters.user)) 
        {
            return false;
        } else if (filters.user_type === "black" && 
                  (game.black_user !== filters.user)) 
        {
            return false;
        }
    }
    return true;
}

var bufferGames = [];
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
        if (data.action === 'save') {
            if (!data.new_multiplayer) {
                return;
            }
            const exists1 = active_games.some(game => game.id === gameId);
            const exists2 = bufferGames.some(game => game.id === gameId);
            if (exists1 || exists2) {
                return;
            }
            game = {
                "id": gameId, 
                "gametype": data.gametype, 
                "white_user": data.white_username,
                "black_user": data.black_username,
                "start_time": data.start_time
            };
            var match = matchesFilter(game);
            if (!match) {
                return;
            }
            if (active_games.length == 100) {
                if (bufferGames.length < 10) {
                    bufferGames.push(game);
                }
            } else {
                if (bufferGames.length > 0) {
                    var bufferGame = bufferGames.pop();
                    active_games.push(bufferGame);
                    appendNewGame(bufferGame);
                    bufferGames.push(game);
                } else {
                    if (game.start_time === null) {
                        game.start_time = "New";
                    }
                    active_games.push(game);
                    appendNewGame(game);
                }
            }
        } else if (data.action === 'delete') {
            var existsIndex = active_games.findIndex(game => game.id === gameId);
            if (existsIndex !== -1) {
                active_games = active_games.filter(game => game.id !== gameId);
                document.getElementById('feed-content').children[existsIndex].remove();
                return;
            }
            existsIndex = bufferGames.findIndex(game => game.id === gameId);
            if (existsIndex !== -1) {
                bufferGames = bufferGames.filter(game => game.id !== gameId);
            }
            return;
        }
    };
}

// Need to await previous batch or else can asynchronously fire and have same id fed in 
async function runBatchInvervals() {
    batchLoadingCancelled = false;
    await loadNewPreviewBatch();
    previewBatchIntervalId = setTimeout(runBatchInvervals, 1000);
}

function loadBatchesAndFeedAndResize() {
    runBatchInvervals();
    adjustSizes();
    loadFeed();
    initSocket();
}

window.addEventListener('load', loadBatchesAndFeedAndResize);

window.addEventListener('resize', adjustSizes);

function selectHeader(header) {
    const mode = header.dataset.mainMode;
    if (mode === undefined) {
        header.classList.toggle('active');
        return;
    }
    header.classList.toggle('focused');
    if (header.classList.contains('focused')) {
        header.classList.add('active');
    } else {
        header.classList.remove('active');
    }
    var unfocusHeaders = [
        'Standard',
        'Complete',
        'Relay',
        'Countdown'
    ]
    var hideSubHeaders = [
        'standard-variants', 
        'complete-variants', 
        'relay-variants', 
        'countdown-variants'
    ];
    if (header.classList.contains('active')) {
        // TODO: Make this DRY later
        if (mode === "Standard") {
            var subheaders = document.getElementById('standard-variants');
            subheaders.classList.add('d-flex');
            subheaders.classList.remove('d-none');
            const index = hideSubHeaders.indexOf('standard-variants');
            if (index !== -1) {
                hideSubHeaders.splice(index, 1);
            }
        } else if (mode === "Complete") {
            var subheaders = document.getElementById('complete-variants');
            subheaders.classList.add('d-flex');
            subheaders.classList.remove('d-none');
            const index = hideSubHeaders.indexOf('complete-variants');
            if (index !== -1) {
                hideSubHeaders.splice(index, 1);
            }
        } else if (mode === "Relay") {
            var subheaders = document.getElementById('relay-variants');
            subheaders.classList.add('d-flex');
            subheaders.classList.remove('d-none');
            const index = hideSubHeaders.indexOf('relay-variants');
            if (index !== -1) {
                hideSubHeaders.splice(index, 1);
            }
        } else if (mode === "Countdown") {
            var subheaders = document.getElementById('countdown-variants');
            subheaders.classList.add('d-flex');
            subheaders.classList.remove('d-none');
            const index = hideSubHeaders.indexOf('countdown-variants');
            if (index !== -1) {
                hideSubHeaders.splice(index, 1);
            }
        } else {
            return;
        }
    }
    unfocusHeaders = unfocusHeaders.filter(id => id !== header.id);
    unfocusHeaders.forEach(id => {
        document.getElementById(id).classList.remove('focused');
    })
    hideSubHeaders.forEach(id => {
        var subheaders= document.getElementById(id);
        subheaders.classList.add('d-none');
        subheaders.classList.remove('d-flex');
    })
}

async function searchResults() {
    var headerIds = [
        {
            "Standard": [
                "Normal", 
                "Classical", 
                "Rapid", 
                "Blitz"
            ]
        }, 
        {
            "Complete": [
                "Complete-Simple",
                "Complete-Suggestive"
            ]
        }, 
        {
            "Relay": [
                "Relay-Simple",
                "Relay-Suggestive"
            ]
        }, 
        {
            "Countdown": [
                "Countdown-Simple",
                "Countdown-Suggestive"
            ]
        }
    ];
    var types = [];
    headerIds.forEach(headerObj => {
        var headerKey = Object.keys(headerObj)[0];
        var subvariantIds = headerObj[headerKey];
        var header = document.getElementById(headerKey);
        if (header.classList.contains('active')) {
            types.push(headerKey);
            var subIdsCopy = subvariantIds;
            subIdsCopy.forEach(subId => {
                var subElement = document.getElementById(subId);
                if (!subElement.classList.contains('active')) {
                    subvariantIds = subvariantIds.filter(id => id !== subId);
                }
            });
            types.push(...subvariantIds);
        }
    });
    var queryParams = 'type=';
    types.forEach((type, index) => {
        queryParams += type;
        if (index !== types.length - 1) {
            queryParams += ',';
        }
    })

    var userInput = document.getElementById('user-input').value;
    userTypeFilter = filters.user_type;
    userFilter = filters.user;
    if (userInput !== "" && userInput !== null) {
        var userType = document.getElementById('user-select').value;
        if (!['white', 'black', 'any'].includes(userType)) {
            throw new Error('Invalid user selection');
        }
        userFilter = userInput;
        userTypeFilter = userType;
        queryParams += `&user_type=${userType}&user=${userInput}`;
    }

    var result = await getGames(queryParams);
    filters = {
        "types": types,
        "user_type": userTypeFilter,
        "user": userFilter
    }
    var newGames = [];
    result.forEach(game => {
        newGames.push({
                "id": `${game.active_game_id}`,
                "gametype": `${game.gametype}`,
                "white_user": `${game.white_username}`,
                "black_user": `${game.black_username}`,
                "start_time": `${game.start_time}`
        });
    });
    active_games = newGames;
    loadFeed();
}

async function getGames(filters) {
    let response = await fetch(`/live/?${filters}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        }
    });
    let data = await response.json();
    if (data.status === "error") {
        return new Error(data.message);
    } else if (data.status === "DNE") {
        throw new Error(data.message);
    }
    return data.active_games;
}