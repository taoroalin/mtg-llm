import game_state
import database

def format_card_full(card_name:game_state.Card):
    card = database.get_card(card_name)
    parts = []
    parts.append(f"Name: {card['name']}")
    
    if 'manaCost' in card:
        parts.append(f"Cost: {card['manaCost']}")
    
    type_line = []
    if 'supertypes' in card:
        type_line.extend(card['supertypes'])
    if 'types' in card:
        type_line.extend(card['types']) 
    if 'subtypes' in card:
        type_line.extend(['-'] + card['subtypes'])
    parts.append(f"Type: {' '.join(type_line)}")
    
    if 'text' in card:
        parts.append(f"Rules Text: {card['text']}")
        
    stats = []
    if 'power' in card and 'toughness' in card:
        stats.append(f"{card['power']}/{card['toughness']}")
    if 'loyalty' in card:
        stats.append(f"Loyalty: {card['loyalty']}")
    if stats:
        parts.append(f"Stats: {' '.join(stats)}")
        
    return '\n'.join(parts)
    
def format_battlefield_card(card:game_state.BattlefieldCard):
    physical_card_formatted = format_card_full(card.card)
    
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
    return physical_card_formatted + '\n' + '\n'.join(battlefield_parts)


def format_omniscient_view(game_state:game_state.GameState):
    parts = []
    for player_board in game_state.player_boards:
        parts.append(f"Player {player_board.index}:")
        parts.append(f"Life: {player_board.life}")
        counters = [f"{name}: {count}" for name, count in player_board.counters.items()]
        if counters:
            parts.append(f"Player Counters: {', '.join(counters)}")
        parts.append(f"Number of cards in library: {len(player_board.library)}")
        
        parts.append(f"Hand ({len(player_board.hand)}) cards: {', '.join(player_board.hand)}")
        parts.append("Hand cards full info:")
        for card in player_board.hand:
            parts.append(format_card_full(card))
        parts.append(f"Graveyard ({len(player_board.graveyard)}) cards: {', '.join(player_board.graveyard)}")
        parts.append(f"Battlefield ({len(player_board.battlefield)}) cards:")
        for battlefield_card in player_board.battlefield:
            parts.append(format_battlefield_card(battlefield_card))
    return '\n'.join(parts)
    
