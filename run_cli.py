from game_state import GameState, DeckList
from agents import NaiveAgent
from game_master import GameMaster
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    generation_settings = {
        "model": "gpt-4o-2024-08-06",
        "temperature": 1
    }
    with open("assets/example_decks/Cats_Elves.json") as f:
        deck_1 = DeckList.model_validate_json(f.read())
    with open("assets/example_decks/Cats_Elves.json") as f:
        deck_2 = DeckList.model_validate_json(f.read())
    game_state = GameState.init_from_decklists([deck_1, deck_2])
    print(game_state.model_dump_json(indent=2))
    agents = [NaiveAgent(generation_settings=generation_settings), NaiveAgent(generation_settings=generation_settings)]
    game_master = GameMaster(game_state=game_state, agents=agents, generation_settings=generation_settings)
    winner = game_master.game_loop()
    print(f"Player {winner} wins!")