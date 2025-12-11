from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware  # ADD THIS at top
import uvicorn
import json
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Game Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USER_SERVICE_URL = "http://localhost:8000"
ROOM_SERVICE_URL = "http://localhost:8001"


rooms = {}

class ConnectionManager:
    def __init__(self):
        self.game_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str):
        await websocket.accept()
        if room_id not in self.game_connections:
            self.game_connections[room_id] = {}
        self.game_connections[room_id][user_id] = websocket
        logger.info(f"User {user_id} connected to game in room {room_id} via WebSocket")

    def disconnect(self, room_id: str, user_id: str):
        if room_id in self.game_connections and user_id in self.game_connections[room_id]:
            del self.game_connections[room_id][user_id]
            if not self.game_connections[room_id]:  # Remove empty room
                del self.game_connections[room_id]
            logger.info(f"User {user_id} disconnected from game in room {room_id}")

    async def broadcast_to_game(self, message: dict, room_id: str, exclude_user: str = None):
        if room_id in self.game_connections:
            for user_id, websocket in self.game_connections[room_id].items():
                if exclude_user and user_id == exclude_user:
                    continue
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id} in game room {room_id}: {e}")
                    self.disconnect(room_id, user_id)

    async def send_to_user_in_game(self, message: dict, room_id: str, user_id: str):
        if room_id in self.game_connections and user_id in self.game_connections[room_id]:
            try:
                await self.game_connections[room_id][user_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to user {user_id} in game room {room_id}: {e}")
                self.disconnect(room_id, user_id)

manager = ConnectionManager()

def get_username(user_id: str) -> str:
    """Get username from User Service"""
    try:
        response = requests.get(f"{USER_SERVICE_URL}/users/{user_id}")
        if response.status_code == 200:
            return response.json()["username"]
    except Exception as e:
        logger.error(f"Error fetching username for {user_id}: {e}")
    return f"User-{user_id[:8]}"

def calculate_winner(move1: str, move2: str, player1: str, player2: str) -> str:
    """Calculate the winner of rock-paper-scissors"""
    if move1 == move2:
        return "draw"
    elif (
        (move1 == "rock" and move2 == "scissors")
        or (move1 == "scissors" and move2 == "paper")
        or (move1 == "paper" and move2 == "rock")
    ):
        return player1
    else:
        return player2

@app.post("/play")
async def play(request: Request):
    """Submit a move (HTTP endpoint for backward compatibility)"""
    data = await request.json()
    room_id = data["roomId"]
    user_id = data["userId"]
    username = data["username"]
    move = data["move"]

    if room_id not in rooms:
        rooms[room_id] = {"moves": {}, "usernames": {}, "result": None, "seen": set()}

    # Save player's move + username
    rooms[room_id]["moves"][user_id] = move
    rooms[room_id]["usernames"][user_id] = username
    
    logger.info(f"Move received from {username} in room {room_id}: {move}")

    # Broadcast move received to all players in the game
    await manager.broadcast_to_game({
        "type": "move_received",
        "message": f"{username} has made their move",
        "userId": user_id,
        "username": username,
        "roomId": room_id,
        "moves_count": len(rooms[room_id]["moves"])
    }, room_id)

    # Check if we have both moves
    if len(rooms[room_id]["moves"]) == 2:
        await process_game_result(room_id)

    return {"status": "move received"}

async def process_game_result(room_id: str):
    """Process game result when both players have moved"""
    if room_id not in rooms or len(rooms[room_id]["moves"]) < 2:
        return

    moves = rooms[room_id]["moves"]
    usernames = rooms[room_id]["usernames"]
    (p1, m1), (p2, m2) = list(moves.items())

    winner = calculate_winner(m1, m2, usernames[p1], usernames[p2])

    result = {
        "moves": {usernames[p1]: m1, usernames[p2]: m2},
        "winner": winner,
    }
    rooms[room_id]["result"] = result

    # Broadcast result to all players
    await manager.broadcast_to_game({
        "type": "game_result",
        "message": "Game finished!",
        "result": result,
        "roomId": room_id
    }, room_id)

    logger.info(f"Game result for room {room_id}: {result}")

@app.get("/state/{room_id}/{user_id}")
async def get_state(room_id: str, user_id: str):
    """Get game state (HTTP endpoint for backward compatibility)"""
    if room_id not in rooms:
        return {"status": "room not found"}

    # Not enough players yet
    if len(rooms[room_id]["moves"]) < 2:
        return {"status": "waiting"}

    # If winner already calculated → return it
    if rooms[room_id]["result"]:
        result = rooms[room_id]["result"]
    else:
       
        await process_game_result(room_id)
        result = rooms[room_id]["result"]

    # Mark that this user saw the result
    rooms[room_id]["seen"].add(user_id)

    # Reset when both have seen
    if len(rooms[room_id]["seen"]) == 2:
        rooms[room_id] = {"moves": {}, "usernames": {}, "result": None, "seen": set()}
        # Notify players that game is reset
        await manager.broadcast_to_game({
            "type": "game_reset",
            "message": "Game reset - ready for next round!",
            "roomId": room_id
        }, room_id)

    return result

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    """WebSocket endpoint for real-time game communication"""
    await manager.connect(websocket, room_id, user_id)
    username = get_username(user_id)
    
    # Initialize room if it doesn't exist
    if room_id not in rooms:
        rooms[room_id] = {"moves": {}, "usernames": {}, "result": None, "seen": set()}
    
    # Send game status to connecting user
    await manager.send_to_user_in_game({
        "type": "game_connected",
        "message": f"Connected to game in room {room_id}",
        "userId": user_id,
        "username": username,
        "roomId": room_id,
        "game_status": {
            "moves_submitted": len(rooms[room_id]["moves"]),
            "waiting_for_moves": 2 - len(rooms[room_id]["moves"]),
            "has_result": rooms[room_id]["result"] is not None
        }
    }, room_id, user_id)
    
    try:
        while True:
            # Listen for messages from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                logger.info(f"Received game message from user {user_id} in room {room_id}: {message}")
                
                # Handle different message types
                if message.get("type") == "submit_move":
                    move = message.get("move", "").lower()
                    if move in ["rock", "paper", "scissors"]:
                        # Save player's move
                        rooms[room_id]["moves"][user_id] = move
                        rooms[room_id]["usernames"][user_id] = username
                        
                        # Broadcast that move was received
                        await manager.broadcast_to_game({
                            "type": "move_received",
                            "message": f"{username} has made their move",
                            "userId": user_id,
                            "username": username,
                            "roomId": room_id,
                            "moves_count": len(rooms[room_id]["moves"])
                        }, room_id)
                        
                        # Check if we have both moves
                        if len(rooms[room_id]["moves"]) == 2:
                            await process_game_result(room_id)
                    else:
                        await manager.send_to_user_in_game({
                            "type": "error",
                            "message": "Invalid move. Use: rock, paper, or scissors"
                        }, room_id, user_id)
                
                elif message.get("type") == "get_game_status":
                    # Send current game status
                    await manager.send_to_user_in_game({
                        "type": "game_status",
                        "roomId": room_id,
                        "game_status": {
                            "moves_submitted": len(rooms[room_id]["moves"]),
                            "waiting_for_moves": 2 - len(rooms[room_id]["moves"]),
                            "has_result": rooms[room_id]["result"] is not None,
                            "result": rooms[room_id]["result"] if rooms[room_id]["result"] else None
                        }
                    }, room_id, user_id)
                
                elif message.get("type") == "ready_for_next_round":
                    # Mark user as ready for next round
                    rooms[room_id]["seen"].add(user_id)
                    
                    # Reset when both have seen
                    if len(rooms[room_id]["seen"]) == 2:
                        rooms[room_id] = {"moves": {}, "usernames": {}, "result": None, "seen": set()}
                        await manager.broadcast_to_game({
                            "type": "game_reset",
                            "message": "Game reset - ready for next round!",
                            "roomId": room_id
                        }, room_id)
                
            except json.JSONDecodeError:
                await manager.send_to_user_in_game({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, room_id, user_id)
                
    except WebSocketDisconnect:
        manager.disconnect(room_id, user_id)
        # Notify other players that user disconnected
        await manager.broadcast_to_game({
            "type": "player_disconnected",
            "message": f"{username} disconnected from the game",
            "userId": user_id,
            "username": username,
            "roomId": room_id
        }, room_id, exclude_user=user_id)

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "game-service",
        "active_games": len(rooms),
        "games_in_progress": len([r for r in rooms.values() if len(r["moves"]) > 0])
    }

if __name__ == "__main__":
    logger.info("Starting Game Service on port 8002")
    uvicorn.run("main:app", host="127.0.0.1", port=8002, reload=True)
