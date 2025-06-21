from game_state import GameState, DeckList
from agents import NaiveAgent
from game_master import GameMaster
import trio
import anyio
from dotenv import load_dotenv
import uuid
load_dotenv()

if __name__ == "__main__":
    generation_settings = {
        "model": "claude-sonnet-4-20250514",
        "temperature": 1
    }
    with open("assets/example_decks/Cats_Elves.json") as f:
        deck_1 = DeckList.model_validate_json(f.read())
    with open("assets/example_decks/Cats_Elves.json") as f:
        deck_2 = DeckList.model_validate_json(f.read())
    game_state = GameState.init_from_decklists([deck_1, deck_2])
    print(game_state.model_dump_json(indent=2))
    agents = [
        NaiveAgent(generation_settings=generation_settings), 
        NaiveAgent(generation_settings=generation_settings)
    ]
    game_id = str(uuid.uuid4())
    game_master = GameMaster(game_id=game_id, game_state=game_state, agents=agents, generation_settings=generation_settings)
    winner = anyio.run(game_master.game_loop)
    print(f"Player {winner} wins!")