import json
import os
from pathlib import Path
import re

    
os.makedirs("assets/example_decks", exist_ok=True)
os.makedirs("assets/example_half_decks", exist_ok=True)
def extract_gameplay_info(card):
    relevant_fields = [
        'name', 'manaCost', 'manaValue', 'colors', 'colorIdentity',
        'types', 'subtypes', 'supertypes',
        'power', 'toughness', 'loyalty', 'text', 'number', 'legalities'
    ]
    legalities_to_keep = ['commander', 'modern', 'standard', 'pauper', 'pioneer']
    if card['legalities']:
        card['legalities'] = [key for key in legalities_to_keep if key in card['legalities'] and card['legalities'][key] == 'Legal']
    return {key: card[key] for key in relevant_fields if key in card}

atomic_cards_file = Path("assets/AtomicCards.json")
atomic_cards = json.load(atomic_cards_file.open())


print(next(iter(atomic_cards['data'].values()))[0].keys())
atomic_cards['data'] = {name: extract_gameplay_info(card[0]) for name,card in atomic_cards['data'].items() if not card[0].get('isFunny')}
print(len(atomic_cards['data']))
standard_legal = sum(1 for card in atomic_cards['data'].values() if 'standard' in card.get('legalities', []))
pioneer_legal = sum(1 for card in atomic_cards['data'].values() if 'pioneer' in card.get('legalities', []))
print(f"Standard legal cards: {standard_legal}")
print(f"Pioneer legal cards: {pioneer_legal}")

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
    output_file = Path("assets/example_half_decks") / deck_file.replace("_FDN", "")
    with open(output_file, 'w') as f:
            json.dump(output, f, indent=4)

# Combine each pair of decks into a new deck file
deck_files = [f for f in os.listdir("assets/example_half_decks")]
for i, deck1 in enumerate(deck_files):
    for deck2 in deck_files[i+1:]:
        deck1_name = deck1.replace(".json", "")
        deck2_name = deck2.replace(".json", "")
        combined_name = f"{deck1_name}_{deck2_name}.json"
        
        deck1_data = json.load(open(Path("assets/example_half_decks") / deck1))
        deck2_data = json.load(open(Path("assets/example_half_decks") / deck2))
        
        combined = {
            "mainboard": {
                card: deck1_data["mainboard"].get(card, 0) + deck2_data["mainboard"].get(card, 0)
                for card in set(deck1_data["mainboard"]) | set(deck2_data["mainboard"])
            },
            "sideboard": {
                card: deck1_data["sideboard"].get(card, 0) + deck2_data["sideboard"].get(card, 0)
                for card in set(deck1_data["sideboard"]) | set(deck2_data["sideboard"])
            }
        }
        
        with open(Path("assets/example_decks") / combined_name, "w") as f:
            json.dump(combined, f, indent=4)

def parse_deck_text(deck_text: str) -> dict:
    mainboard = {}
    sideboard = {}
    current_section = mainboard
    
    for line in deck_text.splitlines():
        line = line.strip()
        if not line or line.lower() == "sideboard":
            current_section = sideboard
            continue
            
        try:
            count, *card_parts = line.split(" ")
            count = int(count)
            card_name = " ".join(card_parts)
            current_section[card_name] = count
        except ValueError:
            continue
            
    return {
        "mainboard": mainboard,
        "sideboard": sideboard
    }
    

# Convert downloaded text decks to json format
txt_deck_dir = Path("assets/downloaded_txt_decks")
for deck_file in txt_deck_dir.glob("*.txt"):
    deck_name = deck_file.stem + ".json"
    deck_text = deck_file.read_text()
    deck_data = parse_deck_text(deck_text)
    
    with open(Path("assets/example_decks") / deck_name, "w") as f:
        json.dump(deck_data, f, indent=4)

def moxfield_to_name_to_printings(filename:str):
    preferred_art_file = Path(filename)
    card_printings = {}
    with preferred_art_file.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = re.match(r'\d+\s+(.+?)\s+\((\w+)\)\s+(\S+)(?:\s+(.*))?', line)
            if match:
                card_name = match.group(1)
                set_code = match.group(2)
                card_number = match.group(3)
                annotations = match.group(4) or ''
                printing = {'set': set_code, 'number': card_number}
                if annotations:
                    printing['annotations'] = annotations.strip()
                card_printings.setdefault(card_name, []).append(printing)
            else:
                print(f"Line didn't match pattern: {line}")
    return card_printings

printings = moxfield_to_name_to_printings("assets/tao_preferred_art.txt")
print("preferred art printings:")
print(printings)
with open("assets/tao_preferred_art_printings.json", "w") as f:
    json.dump(printings, f, indent=4)
with open("mtg-llm-web/src/tao_preferred_art_printings.json", "w") as f:
    json.dump(printings, f, indent=4)