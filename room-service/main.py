from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import random
import string 
import uuid
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Room Service", version="1.0.0")

USER_SERVICE_URL = "http://localhost:8000"
rooms = {}  # roomId -> {"roomName": str, "players": [userId], "connections": {userId: WebSocket}}

class CreateRoomRequest(BaseModel):
    userId: str
    roomName: str

class JoinRoomRequest(BaseModel):
    roomId: str
    userId: str

class ConnectionManager:
    def __init__(self):
        self.room_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str):
        await websocket.accept()
        if room_id not in self.room_connections:
            self.room_connections[room_id] = {}
        self.room_connections[room_id][user_id] = websocket
        logger.info(f"User {user_id} connected to room {room_id} via WebSocket")

    def disconnect(self, room_id: str, user_id: str):
        if room_id in self.room_connections and user_id in self.room_connections[room_id]:
            del self.room_connections[room_id][user_id]
            if not self.room_connections[room_id]:  # Remove empty room
                del self.room_connections[room_id]
            logger.info(f"User {user_id} disconnected from room {room_id}")

    async def broadcast_to_room(self, message: dict, room_id: str, exclude_user: str = None):
        if room_id in self.room_connections:
            for user_id, websocket in self.room_connections[room_id].items():
                if exclude_user and user_id == exclude_user:
                    continue
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id} in room {room_id}: {e}")
                    self.disconnect(room_id, user_id)

    async def send_to_user_in_room(self, message: dict, room_id: str, user_id: str):
        if room_id in self.room_connections and user_id in self.room_connections[room_id]:
            try:
                await self.room_connections[room_id][user_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to user {user_id} in room {room_id}: {e}")
                self.disconnect(room_id, user_id)

manager = ConnectionManager()

def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def get_username(user_id: str) -> str:
    """Get username from User Service"""
    try:
        response = requests.get(f"{USER_SERVICE_URL}/users/{user_id}")
        if response.status_code == 200:
            return response.json()["username"]
    except Exception as e:
        logger.error(f"Error fetching username for {user_id}: {e}")
    return f"User-{user_id[:8]}"

@app.post("/create-room")
def create_room(req: dict):
    """Create a new game room"""
    user_id = req["userId"]
    room_name = req.get("roomName", "Room")
    room_id = generate_room_id()
    
    rooms[room_id] = {
        "roomName": room_name, 
        "players": [user_id],
        "created_by": user_id
    }
    
    logger.info(f"Room {room_id} created by user {user_id}")
    return {
        "roomId": room_id, 
        "roomName": room_name, 
        "players": rooms[room_id]["players"]
    }

@app.post("/join-room")
def join_room(req: dict):
    """Join an existing game room"""
    room_id = req["roomId"]
    user_id = req["userId"]
    
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Only 2 players allowed
    if len(rooms[room_id]["players"]) >= 2:
        raise HTTPException(status_code=400, detail="Room is full")
    
    # Add player if not already in room
    if user_id not in rooms[room_id]["players"]:
        rooms[room_id]["players"].append(user_id)
        logger.info(f"User {user_id} joined room {room_id}")
    
    return {
        "roomId": room_id,
        "roomName": rooms[room_id]["roomName"],
        "players": rooms[room_id]["players"]
    }

@app.get("/rooms/{roomId}/players")
def get_room_status(roomId: str):
    """Get room status and player list"""
    if roomId not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return rooms[roomId]

@app.get("/rooms")
def get_all_rooms():
    """Get all available rooms"""
    return {"rooms": rooms}

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    """WebSocket endpoint for room communication"""
    # Verify room exists
    if room_id not in rooms:
        await websocket.close(code=4004, reason="Room not found")
        return
    
    # Verify user is in room
    if user_id not in rooms[room_id]["players"]:
        await websocket.close(code=4003, reason="User not in room")
        return
    
    await manager.connect(websocket, room_id, user_id)
    username = get_username(user_id)
    
    # Notify room that user connected
    await manager.broadcast_to_room({
        "type": "user_connected",
        "message": f"{username} connected to room",
        "userId": user_id,
        "username": username,
        "roomId": room_id,
        "players": rooms[room_id]["players"]
    }, room_id)
    
    try:
        while True:
            # Listen for messages from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                logger.info(f"Received message in room {room_id} from user {user_id}: {message}")
                
                # Handle different message types
                if message.get("type") == "chat":
                    # Broadcast chat message to room
                    await manager.broadcast_to_room({
                        "type": "chat_message",
                        "message": message.get("content", ""),
                        "userId": user_id,
                        "username": username,
                        "roomId": room_id
                    }, room_id)
                
                elif message.get("type") == "room_status":
                    # Send room status to requesting user
                    await manager.send_to_user_in_room({
                        "type": "room_status",
                        "roomId": room_id,
                        "roomName": rooms[room_id]["roomName"],
                        "players": rooms[room_id]["players"],
                        "player_count": len(rooms[room_id]["players"])
                    }, room_id, user_id)
                
            except json.JSONDecodeError:
                await manager.send_to_user_in_room({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, room_id, user_id)
                
    except WebSocketDisconnect:
        manager.disconnect(room_id, user_id)
        # Notify room that user disconnected
        await manager.broadcast_to_room({
            "type": "user_disconnected",
            "message": f"{username} disconnected from room",
            "userId": user_id,
            "username": username,
            "roomId": room_id
        }, room_id, exclude_user=user_id)

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "room-service",
        "active_rooms": len(rooms),
        "total_players": sum(len(room["players"]) for room in rooms.values())
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Room Service on port 8001")
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
