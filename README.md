# Rock Paper Scissors - Distributed Game System

This project is a simple, two-person, turn-based rock-paper-scissors game implemented with a distributed microservices architecture.

## 1. Technology Summary

The project is built with the following technologies:

| Component      | Technology                                      |
|----------------|-------------------------------------------------|
| **Backend**    | Python 3, FastAPI, Uvicorn                      |
| **CLI Client** | Python 3, `websockets`, `requests`, `asyncio`   |

### Microservices

- **User Service**: Manages user identification and registration.
- **Room Service**: Handles game room creation, player management, and room status.
- **Game Service**: Implements the core game logic, including move validation and winner determination.

## 2. Architecture Overview

The system follows a microservices architecture where each service is responsible for a specific domain. The services communicate with each other via synchronous HTTP REST calls, while clients connect to the services using WebSocket for real-time, bidirectional communication.


![alt text](image.png)

## 3. API Documentation

### Service-to-Service APIs (HTTP)

#### User Service (`http://localhost:8000`)

- **`POST /login`**: Logs in a user or creates a new one if they don\'t exist.
  - **Request Body**: `{"username": "string"}`
  - **Response**: `{"userId": "string", "username": "string"}`

- **`GET /users/{userId}`**: Retrieves user information by their ID.
  - **Response**: `{"userId": "string", "username": "string"}`

#### Room Service (`http://localhost:8001`)

- **`POST /create-room`**: Creates a new game room.
  - **Request Body**: `{"userId": "string", "roomName": "string"}`
  - **Response**: `{"roomId": "string", "roomName": "string", "players": ["string"]}`

- **`POST /join-room`**: Allows a user to join an existing room.
  - **Request Body**: `{"roomId": "string", "userId": "string"}`
  - **Response**: `{"roomId": "string", "roomName": "string", "players": ["string"]}`

### Client-Server APIs (WebSocket)

#### Game Service (`ws://localhost:8002/ws/{roomId}/{userId}`)

**Client to Server Messages:**

- **Submit Move**: Submits a player's move for the current round.
  ```json
  {
    "type": "submit_move",
    "move": "rock" // "rock", "paper", or "scissors"
  }
  ```

- **Ready for Next Round**: Indicates the client is ready for the next round after seeing the results.
  ```json
  {
    "type": "ready_for_next_round"
  }
  ```

**Server to Client Messages:**

- **Game Connected**: Sent upon successful WebSocket connection.
- **Move Received**: Notifies clients that a player has made a move.
- **Game Result**: Broadcasts the game result, including moves and the winner.
- **Game Reset**: Notifies clients that the game has been reset for a new round.
- **Player Disconnected**: Informs clients that an opponent has disconnected.

## 4. Setup and Running Instructions

### Prerequisites

- Python 3.7+
- `pip` for package installation

### Installation

1.  **Clone the repository.**

2.  **Install dependencies for each service and the client:**

    ```
    # For each service (user-service, room-service, game-service)
    cd <service-directory>
    pip install -r requirements.txt

    # For the CLI client
    cd cli-client
    pip install -r requirements.txt
    ```

### Running the System

1.  **Start each microservice in a separate terminal:**

    ```
    # Terminal 1: User Service
    cd user-service
    python main.py

    # Terminal 2: Room Service
    cd room-service
    python main.py

    # Terminal 3: Game Service
    cd game-service
    python main.py
    ```

2.  **Run the CLI client in a new terminal:**

    ```
    cd cli-client
    python main.py
    ```

3.  **Follow the on-screen prompts** to log in, create or join a room, and play the game. You can run two instances of the client to play against yourself.

