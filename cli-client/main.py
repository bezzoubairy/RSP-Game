import requests
import asyncio
import websockets
import json
import threading
import time
from typing import Optional

USER_SERVICE_URL = "http://localhost:8000"
ROOM_SERVICE_URL = "http://localhost:8001"
GAME_SERVICE_URL = "http://localhost:8002"

class GameClient:
    def __init__(self):
        self.user_id: Optional[str] = None
        self.username: Optional[str] = None
        self.room_id: Optional[str] = None
        self.game_websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.room_websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.game_active = False
        self.waiting_for_result = False
        self.current_result = None

    def login(self):
        """Login or register a user"""
        username = input("Enter username: ")
        try:
            response = requests.post(f"{USER_SERVICE_URL}/login", json={"username": username})
            if response.status_code == 200:
                data = response.json()
                self.user_id = data["userId"]
                self.username = data.get("username", username)
                print(f"✅ Logged in as {self.username} (ID: {self.user_id[:8]}...)")
                return True
            else:
                print(f"❌ Login failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    def create_or_join_room(self):
        """Create or join a game room"""
        choice = input("Create or join room? (c/j): ").lower()
        
        try:
            if choice == "c":
                room_name = input("Enter a name for the room: ")
                response = requests.post(
                    f"{ROOM_SERVICE_URL}/create-room",
                    json={"userId": self.user_id, "roomName": room_name}
                )
                if response.status_code == 200:
                    data = response.json()
                    self.room_id = data["roomId"]
                    print(f"✅ Room '{room_name}' created with ID: {self.room_id}")
                    return True
                else:
                    print(f"❌ Room creation failed: {response.text}")
                    return False
            else:
                room_id = input("Enter room ID to join: ")
                response = requests.post(
                    f"{ROOM_SERVICE_URL}/join-room", 
                    json={"roomId": room_id, "userId": self.user_id}
                )
                if response.status_code == 200:
                    data = response.json()
                    self.room_id = room_id
                    room_name = data.get("roomName", room_id)
                    players = data.get("players", [])
                    print(f"✅ Joined room '{room_name}' with {len(players)} players")
                    return True
                else:
                    print(f"❌ Failed to join room: {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Room operation error: {e}")
            return False

    async def handle_game_messages(self, websocket):
        """Handle incoming WebSocket messages from game service"""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "")
                    
                    if msg_type == "game_connected":
                        print(f"🎮 {data.get('message', 'Connected to game')}")
                        game_status = data.get("game_status", {})
                        if game_status.get("has_result"):
                            print("📊 Previous game result available")
                        
                    elif msg_type == "move_received":
                        moves_count = data.get("moves_count", 0)
                        if moves_count == 1:
                            print("⏳ Waiting for opponent's move...")
                        elif moves_count == 2:
                            print("🎯 Both moves received! Calculating result...")
                        
                    elif msg_type == "game_result":
                        result = data.get("result", {})
                        print("\n" + "="*50)
                        print("🏆 GAME RESULT 🏆")
                        print("="*50)
                        print("Moves revealed:")
                        for player, move in result.get("moves", {}).items():
                            print(f"  {player}: {move}")
                        winner = result.get("winner", "Unknown")
                        if winner == "draw":
                            print("🤝 Result: It's a draw!")
                        else:
                            print(f"🏆 Winner: {winner}")
                        print("="*50)
                        
                        self.current_result = result
                        self.waiting_for_result = False
                        
                        # Ask if user wants to play again
                        play_again = input("\nPlay another round? (y/n): ").lower()
                        if play_again == 'y':
                            await websocket.send(json.dumps({
                                "type": "ready_for_next_round"
                            }))
                        else:
                            self.game_active = False
                            print("Thanks for playing! 👋")
                        
                    elif msg_type == "game_reset":
                        print("\n🔄 " + data.get("message", "Game reset"))
                        print("Ready for next round!")
                        
                    elif msg_type == "player_disconnected":
                        print(f"⚠️  {data.get('message', 'Player disconnected')}")
                        
                    elif msg_type == "error":
                        print(f"❌ Error: {data.get('message', 'Unknown error')}")
                        
                except json.JSONDecodeError:
                    print(f"⚠️  Received invalid message: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Game connection closed")
        except Exception as e:
            print(f"❌ Game message handler error: {e}")

    async def connect_to_game(self):
        """Connect to game service via WebSocket"""
        try:
            game_ws_url = f"ws://localhost:8002/ws/{self.room_id}/{self.user_id}"
            print(f"🔌 Connecting to game service...")
            
            async with websockets.connect(game_ws_url) as websocket:
                self.game_websocket = websocket
                print("✅ Connected to game service")
                
                # Start message handler
                message_task = asyncio.create_task(self.handle_game_messages(websocket))
                
                # Game loop
                self.game_active = True
                while self.game_active:
                    try:
                        if not self.waiting_for_result:
                            print("\n🎮 Make your move!")
                            move = input("Enter your move (rock/paper/scissors): ").lower().strip()
                            
                            if move in ["rock", "paper", "scissors"]:
                                self.waiting_for_result = True
                                await websocket.send(json.dumps({
                                    "type": "submit_move",
                                    "move": move
                                }))
                                print(f"✅ Move '{move}' submitted!")
                            else:
                                print("❌ Invalid move! Please enter: rock, paper, or scissors")
                        else:
                            # Wait before checking again
                            await asyncio.sleep(0.5)
                            
                    except KeyboardInterrupt:
                        print("\n👋 Exiting game...")
                        self.game_active = False
                        break
                    except Exception as e:
                        print(f"❌ Game loop error: {e}")
                        break
                
                
                message_task.cancel()
                
        except Exception as e:
            print(f"❌ Failed to connect to game service: {e}")

    async def play_game_websocket(self):
        """Play the game using WebSocket communication"""
        print("\n🎮 Starting game with WebSocket communication...")
        print("Game Rules: Rock beats Scissors, Scissors beats Paper, Paper beats Rock")
        print("Both players need to make their moves, then results will be revealed!")
        
        await self.connect_to_game()

    def play_game_http_fallback(self):
        """Fallback to HTTP polling if WebSocket fails"""
        print("\n🔄 Falling back to HTTP polling...")
        print("Game start! Only 2 players allowed.")
        move = input("Enter your move (rock/paper/scissors): ").lower()

        try:
            # Submit the move
            requests.post(
                f"{GAME_SERVICE_URL}/play",
                json={"roomId": self.room_id, "userId": self.user_id, "username": self.username, "move": move}
            )

            # Poll for result
            print("⏳ Waiting for result...")
            while True:
                response = requests.get(f"{GAME_SERVICE_URL}/state/{self.room_id}/{self.user_id}")
                data = response.json()

                if "moves" not in data:
                    print(f"Status: {data.get('status', 'waiting...')}")
                    time.sleep(2)
                else:
                    print("✅ Round finished!")
                    print("Moves revealed:")
                    for player, m in data["moves"].items():
                        print(f"  {player}: {m}")
                    print(f"🏆 Winner: {data['winner']}")
                    break
        except Exception as e:
            print(f"❌ HTTP game error: {e}")

    async def main_async(self):
        """Main async function"""
        print("🎮 Welcome to Rock Paper Scissors!")
        print("=" * 40)
        
        # Login
        if not self.login():
            return
        
        # Create or join room
        if not self.create_or_join_room():
            return
        
        # Try WebSocket game first, fallback to HTTP if needed
        try:
            await self.play_game_websocket()
        except Exception as e:
            print(f"⚠️  WebSocket game failed: {e}")
            print("🔄 Trying HTTP fallback...")
            self.play_game_http_fallback()

def main():
    """Main entry point"""
    client = GameClient()
    try:
        asyncio.run(client.main_async())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Application error: {e}")

if __name__ == "__main__":
    main()
