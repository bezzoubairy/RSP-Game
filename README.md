# Rock-Scissors-Paper (RSP) Game - Distributed System

This project is a distributed, two-person, turn-based Rock-Scissors-Paper game system. It is designed to demonstrate a microservices architecture, real-time communication using WebSockets, and the integration of multiple client applications.

## Architecture Overview

The system is built on a microservices architecture, with three backend services responsible for specific domains. These services communicate with each other via synchronous HTTP requests. The clients (CLI and Web) communicate with the backend services primarily through asynchronous WebSocket connections for real-time gameplay.

```
+-----------------+      +-----------------+
|   Web Client    |      |    CLI Client   |
| (HTML/CSS/JS)   |      |    (Python)     |
+-------+---------+      +--------+--------+
        |                           |
        +---------+     +-----------+
                  |     |
                  v     v
      +-----------[WebSocket & HTTP]------------+
      |                                         |
      |      Backend Microservices Layer        |
      |                                         |
      +-----------------------------------------+
      |           |           |                 |
      v           v           v                 v
+-----------+ +-----------+ +-----------+ +-----------+
| User Svc  | | Room Svc  | | Game Svc  | | CORS MW   |
| (p: 8000) | | (p: 8001) | | (p: 8002) | | (All Svcs)|
+-----------+ +-----------+ +-----------+ +-----------+
      ^           ^           ^
      |___________|___________| (HTTP)

```

## Technology Stack

| Component             | Technology                                       |
| --------------------- | ------------------------------------------------ |
| **Backend Language**    | Python 3.11+                                     |
| **Web Framework**       | FastAPI                                          |
| **ASGI Server**         | Uvicorn                                          |
| **Real-time Protocol**  | WebSockets                                       |
| **HTTP Client**         | `requests` (for service-to-service calls)        |
| **Web Client**          | HTML5, CSS3, Vanilla JavaScript                  |
| **CLI Client**          | Python (`websockets`, `requests`)                |
| **Data Storage**        | In-Memory (Python Dictionaries)                  |

## How to Run the Project

### Prerequisites

- Python 3.8 or newer
- `pip` for package management

### 1. Clone the Repository

```
git clone https://github.com/bezzoubairy/RSP-Game.git
cd RSP-Game
```

### 2. Set Up and Run Backend Services

For each service (`user-service`, `room-service`, `game-service`), you need to install dependencies. It is recommended to use a virtual environment.

Open **three separate terminals** for the backend services.

**Terminal 1: User Service**
```
cd user-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 8000 --reload
```

**Terminal 2: Room Service**
```
cd room-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

**Terminal 3: Game Service**
```
cd game-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 8002 --reload
```

### 3. Run a Client

You can run either the Web Client or the CLI Client.

**Option A: Run the Web Client (Recommended)**

Open a **fourth terminal**.

```
cd web-client
python -m http.server 8080
```

Now, open your web browser and navigate to `http://localhost:8080`. You can open two tabs to simulate two different players.

**Option B: Run the CLI Client**

Open a **fourth terminal**.

```
cd cli-client
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

To play a game, you will need to run two instances of the CLI client in two separate terminals.

## API Documentation

### Service-to-Service APIs (HTTP)

- **`GET /users/{userId}`** (Called by Room and Game Service)
  - **Service:** User Service
  - **Description:** Fetches the username for a given `userId`.
  - **Response:** `{"userId": "...", "username": "..."}`

### Client-to-Server APIs (HTTP)

- **`POST /login`**
  - **Service:** User Service
  - **Description:** Logs in or registers a new user.
  - **Request Body:** `{"username": "..."}`
  - **Response:** `{"userId": "...", "username": "..."}`

- **`POST /create-room`**
  - **Service:** Room Service
  - **Description:** Creates a new game room.
  - **Request Body:** `{"userId": "...", "roomName": "..."}`
  - **Response:** `{"roomId": "...", "roomName": "...", "players": [...]}`

- **`POST /join-room`**
  - **Service:** Room Service
  - **Description:** Joins an existing game room.
  - **Request Body:** `{"userId": "...", "roomId": "..."}`
  - **Response:** `{"roomId": "...", "roomName": "...", "players": [...]}`

### Real-time APIs (WebSocket)

- **Connection URL:** `ws://localhost:8002/ws/{roomId}/{userId}`
- **Service:** Game Service

#### Client-to-Server Messages

- **`submit_move`**
  - **Description:** Submits the player's move for the current round.
  - **Payload:** `{"type": "submit_move", "move": "rock" | "paper" | "scissors"}`

- **`ready_for_next_round`**
  - **Description:** Notifies the server that the client is ready to start the next round after viewing the results.
  - **Payload:** `{"type": "ready_for_next_round"}`

#### Server-to-Client Messages

- **`game_connected`**
  - **Description:** Confirms that the client has successfully connected to the game's WebSocket.
  - **Payload:** `{"type": "game_connected", "message": "..."}`

- **`move_received`**
  - **Description:** Informs clients that a player has submitted their move.
  - **Payload:** `{"type": "move_received", "message": "...", "moves_count": 1 | 2}`

- **`game_result`**
  - **Description:** Broadcasts the result of the round after both players have moved.
  - **Payload:** `{"type": "game_result", "result": {"moves": {"player1_name": "move1", "player2_name": "move2"}, "winner": "player_name" | "draw"}}`

- **`game_reset`**
  - **Description:** Informs clients that the game state has been reset and a new round can begin.
  - **Payload:** `{"type": "game_reset", "message": "..."}`

- **`player_disconnected`**
  - **Description:** Notifies clients that an opponent has disconnected from the game.
  - **Payload:** `{"type": "player_disconnected", "message": "..."}`
