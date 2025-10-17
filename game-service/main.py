from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()


rooms = {}

@app.post("/play")
async def play(request: Request):
    data = await request.json()
    room_id = data["roomId"]
    user_id = data["userId"]
    username = data["username"]   
    move = data["move"]

    if room_id not in rooms:
        rooms[room_id] = {"moves": {}, "usernames": {}, "result": None, "seen": set()}

    # Save player’s move + username
    rooms[room_id]["moves"][user_id] = move
    rooms[room_id]["usernames"][user_id] = username

    return {"status": "move received"}  


@app.get("/state/{room_id}/{user_id}")
async def get_state(room_id: str, user_id: str):
    if room_id not in rooms:
        return {"status": "room not found"}

    # Not enough players yet
    if len(rooms[room_id]["moves"]) < 2:
        return {"status": "waiting"}

    # If winner already calculated → return it
    if rooms[room_id]["result"]:
        result = rooms[room_id]["result"]
    else:
        # Calculate winner
        moves = rooms[room_id]["moves"]
        usernames = rooms[room_id]["usernames"]
        (p1, m1), (p2, m2) = list(moves.items())

        if m1 == m2:
            winner = "draw"
        elif (
            (m1 == "rock" and m2 == "scissors")
            or (m1 == "scissors" and m2 == "paper")
            or (m1 == "paper" and m2 == "rock")
        ):
            winner = usernames[p1]
        else:
            winner = usernames[p2]

        result = {
            "moves": {usernames[p1]: m1, usernames[p2]: m2},
            "winner": winner,
        }
        rooms[room_id]["result"] = result

    
    rooms[room_id]["seen"].add(user_id)

    # Reset when both have seen
    if len(rooms[room_id]["seen"]) == 2:
        rooms[room_id] = {"moves": {}, "usernames": {}, "result": None, "seen": set()}

    return result


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8002, reload=True)
