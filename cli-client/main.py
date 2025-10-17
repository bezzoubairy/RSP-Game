import requests
import time

USER_SERVICE_URL = "http://localhost:8000"
ROOM_SERVICE_URL = "http://localhost:8001"
GAME_SERVICE_URL = "http://localhost:8002"


def login():
    username = input("Enter username: ")
    r = requests.post(f"{USER_SERVICE_URL}/login", json={"username": username})
    return r.json()["userId"], username


def create_or_join_room(user_id, username):
    choice = input("Create or join room? (c/j): ").lower()
    if choice == "c":
        room_name = input("Enter a name for the room: ")
        r = requests.post(
            f"{ROOM_SERVICE_URL}/create-room",
            json={"userId": user_id, "roomName": room_name},
        )
        data = r.json()
        room_id = data["roomId"]
        print(f"Room '{room_name}' created with ID: {room_id}")
    else:
        room_id = input("Enter room ID to join: ")
        r = requests.post(f"{ROOM_SERVICE_URL}/join-room", json={"roomId": room_id, "userId": user_id})
        data = r.json()
        room_name = data.get("roomName", room_id)
        players = data.get("players", [])
        print(f"Joined room '{room_name}' with players: {players}")

    return room_id


def play_game(user_id, username, room_id):
    print("Game start! Only 2 players allowed.")
    move = input("Enter your move (rock/paper/scissors): ").lower()

    # Submit the move
    requests.post(
        f"{GAME_SERVICE_URL}/play",
        json={"roomId": room_id, "userId": user_id, "username": username, "move": move}
    )

    # Poll for result
    while True:
        r = requests.get(f"{GAME_SERVICE_URL}/state/{room_id}/{user_id}")
        data = r.json()

        if "moves" not in data:
            print(data.get("status", "waiting..."))
            time.sleep(2)
        else:
            print("✅ Round finished!")
            print("Moves revealed:")
            for player, m in data["moves"].items():
                print(f"{player}: {m}")
            print(f"🏆 Winner: {data['winner']}")
            break


def main():
    user_id, username = login()
    room_id = create_or_join_room(user_id, username)
    play_game(user_id, username, room_id)


if __name__ == "__main__":
    main()
