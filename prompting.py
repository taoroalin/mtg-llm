import game_state
import prompts
import re

def simplify_mana_cost_fn(mana_cost:str):
    return re.sub(r'[{}]', '', mana_cost)

def format_card_full(card_name:game_state.Card, simplify_basic_lands:bool=False, simplify_mana_cost:bool=True, omit_all_reminder_text:bool=True):
    card = game_state.get_card_info(card_name)
    parts = []
    parts.append(f"Name: {card['name']}")
    if simplify_basic_lands and 'supertypes' in card and 'Basic' in card['supertypes']:
        return "\n".join(parts)
    
    if 'manaCost' in card:
        if simplify_mana_cost:
            mana_cost = simplify_mana_cost_fn(card['manaCost'])
        else:
            mana_cost = card['manaCost']
        parts.append(f"Cost: {mana_cost}")
    
    type_line = []
    if 'supertypes' in card and card['supertypes']:
        type_line.extend(card['supertypes'])
    if 'types' in card:
        type_line.extend(card['types']) 
    if 'subtypes' in card and card['subtypes']:
        type_line.extend(['-'] + card['subtypes'])
    parts.append(f"Type: {' '.join(type_line)}")
    
    if 'text' in card:
        text = card['text']
        if omit_all_reminder_text:
            text = re.sub(r'\([^)]*\)', '', text)
        parts.append(f"Text: {text}")
        
    stats = []
    if 'power' in card and 'toughness' in card:
        stats.append(f"{card['power']}/{card['toughness']}")
    if 'loyalty' in card:
        stats.append(f"Loyalty: {card['loyalty']}")
    if stats:
        parts.append(f"Stats: {' '.join(stats)}")
        
    return '\n'.join(parts)
    
def format_battlefield_card(card:game_state.BattlefieldCard, simplify_basic_lands:bool=False):
    physical_card_formatted = format_card_full(card.card, simplify_basic_lands)
    
    battlefield_parts = []
    if card.marked_damage > 0:
        battlefield_parts.append(f"Damage: {card.marked_damage}")
    counters = []
    for name, count in card.counters.items():
        counters.append(f"{name}: {count}")
    if counters:
        battlefield_parts.append(f"Counters: {', '.join(counters)}")
    if card.tapped:
        battlefield_parts.append("Card is tapped")
    if 'Creature' in game_state.get_card_info(card.card).get('types', []) and card.entered_battlefield_this_turn:
        battlefield_parts.append("Entered battlefield this turn")
    return f"Battlefield ID: {card.battlefield_id}\n" + physical_card_formatted + '\n' + '\n'.join(battlefield_parts)


def format_omniscient_view(game_state:game_state.GameState, simplify_basic_lands:bool=True):
    parts = []
    parts.append(f"Turn Number: {game_state.turn_number}")
    parts.append(f"Player {game_state.active_player_index}'s turn")
    parts.append(f"Turn Step: {game_state.turn_step.name}")
    for i, player_board in enumerate(game_state.player_boards):
        parts.append(f"Player {i}:")
        parts.append(f"Life: {player_board.life}")
        counters = [f"{name}: {count}" for name, count in player_board.counters.items()]
        if counters:
            parts.append(f"Player Counters: {', '.join(counters)}")
        hand = player_board.get_hand_sorted()
        parts.append(f"Hand hand has {len(hand)} cards:")
        for card in hand:
            parts.append(format_card_full(card, simplify_basic_lands))
            parts.append("")
        parts.append(f"Battlefield ({len(player_board.battlefield)}) cards:" if player_board.battlefield else "Battlefield empty")
        for battlefield_card in player_board.battlefield_sorted:
            parts.append(format_battlefield_card(battlefield_card, simplify_basic_lands))
            parts.append("")
        parts.append(f"Library has {len(player_board.library)} cards")
        parts.append(f"Graveyard ({len(player_board.graveyard)}) cards: {', '.join(player_board.graveyard)}")
        if player_board.exile:
            parts.append(f"Exile ({len(player_board.exile)}) cards: {', '.join(player_board.exile)}")
    parts.append(f"Starting player: {game_state.starting_player_index}")
    return '\n'.join(parts)
    
def format_player_view(game_state:game_state.GameState, player_index:int, revealed_information:str, simplify_basic_lands:bool=True):
    parts = []
    parts.append(f"Turn Number: {game_state.turn_number}")
    parts.append(f"You are player {player_index}")
    parts.append(f"Opponent {game_state.active_player_index}'s turn" if player_index != game_state.active_player_index else "It's your turn")
    parts.append(f"Turn Step: {game_state.turn_step.name}")
    for index, player_board in enumerate(game_state.player_boards):
        parts.append(f"Opponent {index}'s board state:" if player_index != index else "Your board state:")
        parts.append(f"Life: {player_board.life}")
        counters = [f"{name}: {count}" for name, count in player_board.counters.items()]
        if counters:
            parts.append(f"Player Counters: {', '.join(counters)}")
        hand = player_board.get_hand_sorted()
        if player_index == index:
            parts.append(f"Hand has {len(hand)} cards:")
            for card in hand:
                parts.append(format_card_full(card, simplify_basic_lands))
                parts.append("")
        else:
            parts.append(f"Player has ({len(player_board.hand)}) cards in hand")
        parts.append(f"Battlefield ({len(player_board.battlefield)}) cards:" if player_board.battlefield else "Battlefield empty")
        for battlefield_card in player_board.battlefield_sorted:
            parts.append(format_battlefield_card(battlefield_card, simplify_basic_lands))
            parts.append("")
        parts.append(f"Library has {len(player_board.library)} cards")
        parts.append(f"Graveyard ({len(player_board.graveyard)}) cards: {', '.join(player_board.graveyard)}")
        if player_board.exile:
            parts.append(f"Exile ({len(player_board.exile)}) cards: {', '.join(player_board.exile)}")
        parts.append(f"Current revealed information (eg scrying): {revealed_information}")
    parts.append(f"Starting player: {game_state.starting_player_index}")
    return '\n'.join(parts)
    
