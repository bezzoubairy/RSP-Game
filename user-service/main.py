from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="User Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory storage
users = {}  # userId -> username
websocket_connections = {}  # userId -> WebSocket connection

class LoginRequest(BaseModel):
    username: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                self.disconnect(user_id)

manager = ConnectionManager()

@app.post("/login")
def login(req: LoginRequest):
    """Login or register a user with username"""
    # Check if user already exists
    for uid, name in users.items():
        if name == req.username:
            logger.info(f"Existing user {req.username} logged in with ID {uid}")
            return {"userId": uid, "username": name}
    
    # Create new user
    user_id = str(uuid.uuid4())
    users[user_id] = req.username
    logger.info(f"New user {req.username} registered with ID {user_id}")
    return {"userId": user_id, "username": req.username}

@app.get("/users/{userId}")
def get_user(userId: str):
    """Get user information by ID"""
    if userId in users:
        return {"userId": userId, "username": users[userId]}
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/users")
def get_all_users():
    """Get all registered users"""
    return {"users": [{"userId": uid, "username": name} for uid, name in users.items()]}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time user communication"""
    if user_id not in users:
        await websocket.close(code=4004, reason="User not found")
        return
    
    await manager.connect(websocket, user_id)
    
    # Send welcome message
    await manager.send_personal_message({
        "type": "connection_established",
        "message": f"Connected to User Service as {users[user_id]}",
        "userId": user_id,
        "username": users[user_id]
    }, user_id)
    
    try:
        while True:
            # Listen for messages from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                logger.info(f"Received message from user {user_id}: {message}")
                
             
                await manager.send_personal_message({
                    "type": "echo",
                    "original_message": message,
                    "timestamp": str(uuid.uuid4())
                }, user_id)
                
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, user_id)
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"User {user_id} disconnected")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "user-service",
        "active_users": len(users),
        "active_connections": len(manager.active_connections)
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting User Service on port 8000")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
