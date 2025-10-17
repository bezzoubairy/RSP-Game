from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import random
import string 
import uuid
import requests

app = FastAPI()

USER_SERVICE_URL = "http://localhost:8000"
rooms = {}  # roomId -> list of userIds

class CreateRoomRequest(BaseModel):
    userId: str
    roomName: str

class JoinRoomRequest(BaseModel):
    roomId: str
    userId: str

def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

@app.post("/create-room")
def create_room(req: dict):
    user_id = req["userId"]
    room_name = req.get("roomName", "Room")
    room_id = generate_room_id()
    rooms[room_id] = {"roomName": room_name, "players": [user_id]}
    return {"roomId": room_id, "roomName": room_name, "players": rooms[room_id]["players"]}

@app.post("/join-room")
def join_room(req: dict):
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
    
    return {
        "roomId": room_id,
        "roomName": rooms[room_id]["roomName"],
        "players": rooms[room_id]["players"]
    }

@app.get("/rooms/{roomId}/players")
def get_room_status(roomId: str):
    if roomId not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return rooms[roomId]
