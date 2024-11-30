from fastapi import FastAPI, WebSocket
from typing import Set
import asyncio
from contextlib import asynccontextmanager
from game_master import GameMaster

app = FastAPI()

class GameStateWebSocket:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.game_master: GameMaster | None = None
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        if self.game_master:
            await websocket.send_text(self.game_master.truncated_json())
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast_state(self):
        if not self.game_master:
            return
        state_json = self.game_master.truncated_json()
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(state_json)
            except:
                disconnected.add(connection)
        self.active_connections -= disconnected

game_ws = GameStateWebSocket()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await game_ws.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        await game_ws.disconnect(websocket)