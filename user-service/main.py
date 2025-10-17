from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI()
users = {}  
counter = 1

class LoginRequest(BaseModel):
    username: str

@app.post("/login")
def login(req: LoginRequest):
    for uid, name in users.items():
        if name == req.username:
            return {"userId": uid}
    user_id = str(uuid.uuid4())
    users[user_id] = req.username
    return {"userId": user_id}

@app.get("/users/{userId}")
def get_user(userId: str):
    if userId in users:
        return {"userId": userId, "username": users[userId]}
    raise HTTPException(status_code=404, detail="User not found")
