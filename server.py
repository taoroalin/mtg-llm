from fastapi import FastAPI, WebSocket
from typing import Set
import asyncio
from contextlib import asynccontextmanager
from game_master import GameMaster
import game_state
import agents

app = FastAPI()

class GameStateWebSocket:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.game_master: GameMaster | None = None    
        with open("assets/example_decks/Cats_Elves.json") as f:
            deck_1 = game_state.DeckList.model_validate_json(f.read())
        with open("assets/example_decks/Cats_Elves.json") as f:
            deck_2 = game_state.DeckList.model_validate_json(f.read())
        game_state = game_state.GameState.init_from_decklists([deck_1, deck_2])
        print(game_state.model_dump_json(indent=2))
        agents = [agents.NaiveAgent(generation_settings=generation_settings), agents.NaiveAgent(generation_settings=generation_settings)]
        game_master = GameMaster(game_state=game_state, agents=agents, generation_settings=generation_settings)
        winner = game_master.game_loop()
        
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

games:dict[str, GameStateWebSocket] = {}



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await game_ws.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        await game_ws.disconnect(websocket)
        
        
@app.post("/create_game")
async def create_game():
    game_id = str(len(games))
    games[game_id] = GameStateWebSocket()
    return {"game_id": game_id}

