const USER_SERVICE_URL = "http://localhost:8000";
const ROOM_SERVICE_URL = "http://localhost:8001";
const GAME_SERVICE_URL = "http://localhost:8002";


let userId = null;
let username = null;
let roomId = null;
let gameWs = null;
let moveSubmitted = false;

const loginSection = document.getElementById('login-section' );
const roomSection = document.getElementById('room-section');
const gameSection = document.getElementById('game-section');
const loginStatus = document.getElementById('login-status');
const roomStatus = document.getElementById('room-status');
const gameMessage = document.getElementById('game-message');
const resultDisplay = document.getElementById('result-display');
const playAgainButton = document.getElementById('play-again-button');

// Utility
function showSection(section) {
    loginSection.style.display = 'none';
    roomSection.style.display = 'none';
    gameSection.style.display = 'none';
    section.style.display = 'block';
}

// Login
async function login() {
    const usernameInput = document.getElementById('username-input').value.trim();
    if (!usernameInput) {
        loginStatus.textContent = "❌ Please enter a username.";
        loginStatus.style.color = "#dc3545";
        return;
    }

    try {
        const response = await fetch(`${USER_SERVICE_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usernameInput })
        });

        if (response.ok) {
            const data = await response.json();
            userId = data.userId;
            username = data.username;
            
            document.getElementById('current-username').textContent = username;
            
            loginStatus.textContent = `✅ Welcome, ${username}!`;
            loginStatus.style.color = "#28a745";
            
            setTimeout(() => showSection(roomSection), 500);
        } else {
            loginStatus.textContent = `❌ Login failed. Please try again.`;
            loginStatus.style.color = "#dc3545";
        }
    } catch (error) {
        loginStatus.textContent = `❌ Connection error. Make sure services are running.`;
        loginStatus.style.color = "#dc3545";
    }
}

// Create Room
async function createRoom() {
    const roomName = document.getElementById('room-name-input').value || "Game Room";
    
    try {
        const response = await fetch(`${ROOM_SERVICE_URL}/create-room`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: userId, roomName: roomName })
        });

        if (response.ok) {
            const data = await response.json();
            roomId = data.roomId;
            roomStatus.textContent = `✅ Room created! Share this ID with your friend: ${roomId}`;
            roomStatus.style.color = "#28a745";
            
            setTimeout(() => connectToGame(), 1000);
        } else {
            roomStatus.textContent = `❌ Failed to create room. Try again.`;
            roomStatus.style.color = "#dc3545";
        }
    } catch (error) {
        roomStatus.textContent = `❌ Connection error.`;
        roomStatus.style.color = "#dc3545";
    }
}

// Join Room
async function joinRoom() {
    const roomIdInput = document.getElementById('room-id-input').value.trim();
    if (!roomIdInput) {
        roomStatus.textContent = "❌ Please enter a Room ID.";
        roomStatus.style.color = "#dc3545";
        return;
    }

    try {
        const response = await fetch(`${ROOM_SERVICE_URL}/join-room`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: userId, roomId: roomIdInput })
        });

        if (response.ok) {
            const data = await response.json();
            roomId = data.roomId;
            roomStatus.textContent = `✅ Successfully joined room!`;
            roomStatus.style.color = "#28a745";
            
            setTimeout(() => connectToGame(), 1000);
        } else {
            const errorData = await response.json();
            roomStatus.textContent = `❌ ${errorData.detail || 'Failed to join room'}`;
            roomStatus.style.color = "#dc3545";
        }
    } catch (error) {
        roomStatus.textContent = `❌ Connection error.`;
        roomStatus.style.color = "#dc3545";
    }
}

// Connect to Game
async function connectToGame() {
    document.getElementById('current-room-id').textContent = roomId;
    showSection(gameSection);
    resultDisplay.style.display = 'none';
    moveSubmitted = false;

    const wsUrl = `ws://localhost:8002/ws/${roomId}/${userId}`;
    
    try {
        gameWs = new WebSocket(wsUrl);

        gameWs.onopen = () => {
            gameMessage.textContent = "⏳ Waiting for opponent to join...";
            playAgainButton.style.display = 'none';
        };

        gameWs.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleGameMessage(data);
        };

        gameWs.onclose = () => {
            gameMessage.textContent = "❌ Connection lost. Please refresh the page.";
        };

    } catch (error) {
        gameMessage.textContent = "❌ Failed to connect to game.";
    }
}

// Handle Game Messages
function handleGameMessage(data) {
    const type = data.type;
    
    switch (type) {
        case 'game_connected':
            gameMessage.textContent = "✅ Connected! Make your move.";
            break;
            
        case 'move_received':
            if (!moveSubmitted) {
                gameMessage.textContent = "⏳ Opponent is making their move...";
            } else {
                gameMessage.textContent = "⏳ Waiting for opponent's move...";
            }
            break;
            
        case 'game_result':
            displayGameResult(data.result);
            break;
            
        case 'game_reset':
            gameMessage.textContent = "🎮 New round! Make your move.";
            resultDisplay.style.display = 'none';
            playAgainButton.style.display = 'none';
            moveSubmitted = false;
            break;
            
        case 'player_disconnected':
            gameMessage.textContent = "⚠️ Opponent disconnected.";
            break;
    }
}

// Display Result
function displayGameResult(result) {
    moveSubmitted = false;
    
    let resultHtml = '<h3>🏆 Round Result</h3>';
    
    // Show moves
    resultHtml += '<div style="display: flex; justify-content: space-around; margin: 20px 0;">';
    for (const [player, move] of Object.entries(result.moves)) {
        const emoji = move === 'rock' ? '🪨' : move === 'paper' ? '📄' : '✂️';
        resultHtml += `
            <div style="text-align: center;">
                <div style="font-size: 3em;">${emoji}</div>
                <div style="font-weight: bold; margin-top: 10px;">${player}</div>
                <div style="color: #666;">${move}</div>
            </div>
        `;
    }
    resultHtml += '</div>';
    
    // Show winner
    if (result.winner === 'draw') {
        resultHtml += '<p style="font-size: 1.3em; color: #ffc107; font-weight: bold;">🤝 It\'s a Draw!</p>';
        gameMessage.textContent = "🤝 It's a draw!";
    } else {
        const isWinner = result.winner === username;
        resultHtml += `<p style="font-size: 1.3em; color: ${isWinner ? '#28a745' : '#dc3545'}; font-weight: bold;">
            ${isWinner ? '🎉 You Won!' : '😔 You Lost'}
        </p>`;
        gameMessage.textContent = isWinner ? '🎉 You won this round!' : '😔 Better luck next time!';
    }
    
    resultDisplay.innerHTML = resultHtml;
    resultDisplay.style.display = 'block';
    playAgainButton.style.display = 'block';
}

// Submit Move
function submitMove(move) {
    if (moveSubmitted) {
        gameMessage.textContent = "⏳ You already submitted your move!";
        return;
    }
    
    if (gameWs && gameWs.readyState === WebSocket.OPEN) {
        gameWs.send(JSON.stringify({
            type: "submit_move",
            move: move
        }));
        moveSubmitted = true;
        const emoji = move === 'rock' ? '🪨' : move === 'paper' ? '📄' : '✂️';
        gameMessage.textContent = `✅ You chose ${emoji} ${move}! Waiting for opponent...`;
    } else {
        gameMessage.textContent = "❌ Not connected to game.";
    }
}

// Ready for Next Round
function readyForNextRound() {
    if (gameWs && gameWs.readyState === WebSocket.OPEN) {
        gameWs.send(JSON.stringify({
            type: "ready_for_next_round"
        }));
        gameMessage.textContent = "⏳ Waiting for opponent to be ready...";
        playAgainButton.style.display = 'none';
    }
}

// Allow Enter key to login
document.getElementById('username-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') login();
});

document.getElementById('room-id-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') joinRoom();
});
