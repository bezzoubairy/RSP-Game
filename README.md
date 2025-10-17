# Rock Paper Scissors (Version 1)

This project implements a basic two-person, turn-based rock-paper-scissors game using a distributed microservices architecture. This is the initial version of the project, primarily demonstrating HTTP-based communication between services and a command-line interface (CLI) client that uses HTTP polling for game state updates.

## 1. Technology Summary

The project is built with the following technologies:

| Component      | Technology                                      |
|----------------|-------------------------------------------------|
| **Backend**    | Python 3, FastAPI, Uvicorn                      |
| **CLI Client** | Python 3, `requests`                            |

### Microservices

- **User Service**: Manages user identification and registration.
- **Room Service**: Handles game room creation, player management, and room status.
- **Game Service**: Implements the core game logic, including move validation and winner determination.

## 2. Architecture Overview

The system follows a microservices architecture where each service is responsible for a specific domain. Services communicate with each other via HTTP REST calls. 
The CLI client also communicates with the backend services using HTTP requests, employing a polling mechanism to check for game state updates.


## 3. API Documentation

### Service-to-Service and Client-Service APIs (HTTP)

#### User Service (`http://localhost:8000`)

- **`POST /login`**: Logs in a user or creates a new one if they don\"t exist.
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

- **`GET /rooms/{roomId}/players`**: Retrieves room status and player list.
  - **Response**: `{"roomName": "string", "players": ["string"]}`

#### Game Service (`http://localhost:8002`)

- **`POST /play`**: Submits a player\"s move for the current round.
  - **Request Body**: `{"roomId": "string", "userId": "string", "username": "string", "move": "string"}`
  - **Response**: `{"status": "move received"}`

- **`GET /state/{room_id}/{user_id}`**: Polls for the current game state and result.
  - **Response (waiting)**: `{"status": "waiting"}`
  - **Response (result)**: `{"moves": {"player1_name": "move", "player2_name": "move"}, "winner": "player_name"}`

## 4. Setup and Running Instructions /////////////////////////////

To get the Rock Paper Scissors game up and running, follow these step-by-step instructions carefully.

### Prerequisites

*   **Python 3.7+**: Download and install from [python.org](https://www.python.org/downloads/).
*   **`pip`**: Python's package installer, usually included with Python installations.

### Installation

1.  **Clone the repository** :
    ```
    git clone [REPOSITORY_URL]
    cd...

2.  **Set up virtual environments and install dependencies** in seperate terminal for each service :
    ```
     # For user-service
    cd user-service
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000
    
    # For room-service
    cd room-service
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8001
    
   
    # For game-service
    cd game-service
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8002
    

    # For cli-client
    cd cli-client
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python main.py
    
    ```









