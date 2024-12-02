from collections import defaultdict
from game_state import GameState, DeckList
from agents import NaiveAgent
from game_master import GameMaster
import asyncio
from dotenv import load_dotenv
import json
from pathlib import Path

import uuid
load_dotenv()

if __name__ == "__main__":
    n_runs = 20
    generation_settings = {
        "model": "gpt-4o-2024-08-06",
        "temperature": 1
    }
    generation_settings_4o_mini = {
        "model": "gpt-4o-mini",
        "temperature": 1
    }
    with open("assets/example_decks/Boros Energy.json") as f:
        boros_energy_deck = DeckList.model_validate_json(f.read())
    game_state = GameState.init_mirror(boros_energy_deck)
    agents = [NaiveAgent(generation_settings=generation_settings), NaiveAgent(generation_settings=generation_settings_4o_mini)]
    game_masters = [GameMaster(game_id=str(uuid.uuid4()), game_state=game_state, agents=agents, generation_settings=generation_settings) for _ in range(n_runs)]
    async def run_games():
        games = [game_master.game_loop() for game_master in game_masters]
        return await asyncio.gather(*games)
        
    # winners = asyncio.run(run_games())
    # print(f"Winners: {winners}")
    
    finished_games = Path("database/finished_games").glob("*.json")
    wins_by_model = defaultdict(int)
    wins_by_player_index = defaultdict(int)
    
    for game_file in finished_games:
        game_data = json.loads(game_file.read_text())
        winner = game_data["winner"]
        print("agents", game_data["agents"])
        winner_model = game_data["agents"][winner].get("generation_settings", {}).get("model", "unknown")
        wins_by_model[winner_model] += 1
        wins_by_player_index[winner] += 1

    print("\nWins by model:")
    for model, wins in wins_by_model.items():
        print(f"{model}: {wins}")
    print("\nWins by player index:")
    for player_index, wins in wins_by_player_index.items():
        print(f"Player {player_index}: {wins}")
