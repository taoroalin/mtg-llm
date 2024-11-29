from game_state import GameState, DeckList
from agents import NaiveAgent
from game_master import GameMaster

if __name__ == "__main__":
    generation_settings = {
        "model": "openai:gpt-4o-2024-08-06",
        "temperature": 0.75
    }
    deck_1 = DeckList.from_file("assets/example_decks/Cats_Elves.json")
    deck_2 = DeckList.from_file("assets/example_decks/Cats_Elves.json")
    game_state = GameState.init_from_decklists([deck_1, deck_2])
    print(game_state)
    agents = [NaiveAgent(0, generation_settings), NaiveAgent(1, generation_settings)]
    game_master = GameMaster(game_state, agents)
    winner = game_master.game_loop()
    print(f"Player {winner} wins!")