import json
import os
from pathlib import Path
    
os.makedirs("assets/example_decks", exist_ok=True)
def extract_gameplay_info(card):
    relevant_fields = [
        'name', 'manaCost', 'manaValue', 'colors', 'colorIdentity',
        'types', 'subtypes', 'supertypes',
        'power', 'toughness', 'loyalty', 'text', 'number'
    ]
    return {key: card[key] for key in relevant_fields if key in card}

atomic_cards_file = Path("assets/AtomicCards.json")
atomic_cards = json.load(atomic_cards_file.open())


print(next(iter(atomic_cards['data'].values()))[0].keys())
atomic_cards['data'] = {name: extract_gameplay_info(card[0]) for name,card in atomic_cards['data'].items()}

with open("assets/AtomicCardsGameplay.json", "w") as f:
    json.dump(atomic_cards, f, indent=4)

    
decks_dir = Path("assets/example_decks_raw")
for deck_file in os.listdir(decks_dir):
    if not deck_file.endswith("_FDN.json"):
        continue
    deck = json.load(open(decks_dir / deck_file))
    mainboard = {card['name']:card['count'] for card in deck['data'].get('mainBoard', [])}
    sideboard = {card['name']:card['count'] for card in deck['data'].get('sideBoard', [])}

    output = {
        "mainboard": mainboard,
        "sideboard": sideboard
    }
    output_file = Path("assets/example_decks") / deck_file.replace("_FDN", "")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=4)
    
