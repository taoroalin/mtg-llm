from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.responses import JSONResponse, Response, RedirectResponse
from typing import Set
import asyncio
from contextlib import asynccontextmanager
from game_master import GameMaster
import game_state
import agents
import image_generation
import random
import os
import uuid
from pathlib import Path
import json

app = FastAPI()

class GameStateWebSocket:
    def __init__(self, game_id: str):
        print("\n" + "="*50)
        print("       STARTING NEW MAGIC GAME")
        print("="*50 + "\n")
        self.active_connections: Set[WebSocket] = set()
        generation_settings = {
            "model": "gpt-4o-2024-08-06",
            "temperature": 1,
            "max_completion_tokens": 4000
        }
        deck_files = [f for f in os.listdir("assets/example_decks") if f.endswith(".json")]
        deck_files = ['Boros Energy.json']
        with open(f"assets/example_decks/{random.choice(deck_files)}") as f:
            deck_1 = game_state.DeckList.model_validate_json(f.read())
        with open(f"assets/example_decks/{random.choice(deck_files)}") as f:
            deck_2 = game_state.DeckList.model_validate_json(f.read())
        new_state = game_state.GameState.init_from_decklists([deck_1, deck_2],arena_hand_smoothing=True)
        print(new_state.model_dump_json(indent=2))
        new_agents = [agents.NaiveAgent(generation_settings=generation_settings), agents.NaiveAgent(generation_settings=generation_settings)]
        self.game_master = GameMaster(game_id=game_id, game_state=new_state, agents=new_agents, generation_settings=generation_settings)
        
        asyncio.create_task(self.game_loop())
        self.n_steps_since_last_broadcast = 0
        self.is_killed = False
        
    async def game_loop(self):
        while self.game_master.winner is None:
            if self.is_killed:
                return
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
            
        if self.is_abandoned():
            self.n_steps_since_last_broadcast += 1
            if self.n_steps_since_last_broadcast >= 3:
                del games[self.game_master.game_id]
                self.is_killed = True
                return
        else:
            self.n_steps_since_last_broadcast = 0
            
        state_json = self.game_master.truncated_json()
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(state_json)
            except:
                disconnected.add(connection)
        self.active_connections -= disconnected
        
    def is_abandoned(self) -> bool:
        return not self.active_connections

games:dict[str, GameStateWebSocket] = {}


def get_game_data(game_id: str):
    ongoing_path = Path("database/ongoing_games") / f"{game_id}.json"
    finished_path = Path("database/finished_games") / f"{game_id}.json"
    
    if ongoing_path.exists():
        return GameMaster.model_validate_json(ongoing_path.read_text())
    elif finished_path.exists():
        return GameMaster.model_validate_json(finished_path.read_text())

@app.get("/get_game/{game_id}")
async def get_game(game_id: str):
    result = get_game_data(game_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Game not found")
    response = JSONResponse(content=result.model_dump())
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response
    
@app.get("/games")
async def get_games():
    ongoing_games = [f.stem for f in Path("database/ongoing_games").glob("*.json")]
    finished_games = [f.stem for f in Path("database/finished_games").glob("*.json")]
    
    response = JSONResponse(content={
        "ongoing_games": ongoing_games,
        "finished_games": finished_games
    })
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response



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
@app.options("/create_game")
async def create_game(request: Request):
    if request.method == "OPTIONS":
        response = JSONResponse(content={})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
        
    game_id = str(uuid.uuid4())
    games[game_id] = GameStateWebSocket(game_id=game_id)
    response = JSONResponse(content={"game_id": game_id})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*" 
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@app.get("/playmat/{game_id}/{player_index}.png")
async def get_playmat(game_id: str, player_index: str):
    game = get_game_data(game_id)
    if game is None:
        game = games.get(game_id).game_master
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    decklist = game.game_state.player_decklists[int(player_index)]
    
    image_url = await image_generation.generate_playmat_for_deck(decklist)
    return RedirectResponse(url=image_url, status_code=303)
