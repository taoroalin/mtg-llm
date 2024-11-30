from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
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
        generation_settings = {
            "model": "gpt-4o-2024-08-06",
            "temperature": 1
        }
        with open("assets/example_decks/Cats_Elves.json") as f:
            deck_1 = game_state.DeckList.model_validate_json(f.read())
        with open("assets/example_decks/Cats_Elves.json") as f:
            deck_2 = game_state.DeckList.model_validate_json(f.read())
        new_state = game_state.GameState.init_from_decklists([deck_1, deck_2])
        print(new_state.model_dump_json(indent=2))
        new_agents = [agents.NaiveAgent(generation_settings=generation_settings), agents.NaiveAgent(generation_settings=generation_settings)]
        self.game_master = GameMaster(game_state=new_state, agents=new_agents, generation_settings=generation_settings)
        
        asyncio.create_task(self.game_loop())
        
    async def game_loop(self):
        while self.game_master.winner is None:
            await self.broadcast_state()
            await self.game_master.step()
        return self.game_master.winner
    
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



@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    game = games[game_id]
    await game.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        await game.disconnect(websocket)
        
        
@app.post("/create_game")
# @app.options("/create_game")
async def create_game(request: Request):
    if request.method == "OPTIONS":
        response = JSONResponse(content={})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
        
    game_id = str(len(games))
    games[game_id] = GameStateWebSocket()
    response = JSONResponse(content={"game_id": game_id})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*" 
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

