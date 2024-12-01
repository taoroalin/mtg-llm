from pydantic import BaseModel, Field
from typing import Optional, Literal, Union, TypedDict, List
import random
from enum import Enum, auto
import json
from pathlib import Path

Card = str  # Type alias

CardOrToken = Card

class Format(Enum):
    COMMANDER = "COMMANDER"
    MODERN = "MODERN"
    STANDARD = "STANDARD"
    PAUPER = "PAUPER"
    PIONEER = "PIONEER"

class CardInfo(TypedDict, total=False):
    name: str
    manaCost: str 
    manaValue: int
    
    colors: List[str]
    colorIdentity: List[str]
    types: List[str]
    subtypes: List[str]
    supertypes: List[str]
    # power and toughness are sometimes strings
    power: Optional[Union[int, str]]
    toughness: Optional[Union[int, str]]
    loyalty: Optional[Union[int, str]]
    
    text: str
    
    number: str
    legalities:Optional[list[Format]]
    isToken: bool
    
def card_fill_missing_fields(card_info:CardInfo):
    if not card_info.get('manaValue'):
        card_info['manaValue'] = 0
    if not card_info.get('manaCost'):
        card_info['manaCost'] = ""
    if not card_info.get('text'):
        card_info['text'] = ""
    return card_info

def get_card_info(name:str) -> CardInfo:
    return card_fill_missing_fields(card_database['data'][name])

card_database = json.load(Path("assets/AtomicCardsGameplay.json").open())

def create_token_card_info(name:str, types:List[str], subtypes:list[str], power:Optional[int]=None, toughness:Optional[int]=None, text:str='') -> CardInfo:
    """Token names don't contain 'Token', eg name is 'Goblin' not 'Goblin Token'. Token-ness is indicated by isToken=True."""
    assert name not in card_database['data'], f"Card {name} already exists"
    new_card_info: CardInfo = {
        "name": name,
        "manaCost": "",
        "manaValue": 0,
        "types": types,
        "subtypes": subtypes,
        "power": power,
        "toughness": toughness,
        "text": text,
        "isToken": True
    }
    card_database['data'][name] = new_card_info
    return new_card_info


class TurnStep(Enum):
    UNTAP = "UNTAP"
    UPKEEP = "UPKEEP"
    DRAW = "DRAW" 
    MAIN_1 = "MAIN_1"
    BEGIN_COMBAT = "BEGIN_COMBAT"
    DECLARE_ATTACKERS = "DECLARE_ATTACKERS"
    DECLARE_BLOCKERS = "DECLARE_BLOCKERS"
    FIRST_STRIKE_DAMAGE = "FIRST_STRIKE_DAMAGE"
    COMBAT_DAMAGE = "COMBAT_DAMAGE"
    END_COMBAT = "END_COMBAT"
    MAIN_2 = "MAIN_2"
    END = "END"
    CLEANUP = "CLEANUP"

class DeckList(BaseModel):
    "Decklist for a player at the beginning of the game"
    mainboard: dict[Card, int]
    sideboard: dict[Card, int]
    
class BattlefieldCard(BaseModel):
    "A card on the battlefield. Has an ID which other cards can reference."
    battlefield_id: int
    card: CardOrToken
    owner: int
    counters: dict[str, int]
    tapped: bool
    effects:list[str]
    attached_to: Optional[int]
    marked_damage: int
    
    @classmethod
    def from_card(cls, card: CardOrToken, owner: int, battlefield_id: int) -> "BattlefieldCard":
        return cls(
            battlefield_id=battlefield_id,
            card=card,
            owner=owner,
            counters={},
            tapped=False,
            effects=[],
            attached_to=None,
            marked_damage=0
        )
    

class PlayerBoard(BaseModel):
    "The entire state of a player, including their hand, battlefield, counters and tokens, graveyard, etc."
    library: list[Card]
    hand: list[Card] = Field(default_factory=list, description="Cards in hand. Note that cards are displayed in mana value order but stored unsorted.")
    
    def get_hand_sorted(self) -> list[Card]:
        return sorted(self.hand, key=lambda card: get_card_info(card)["manaValue"])
        
    graveyard: list[Card] = Field(default_factory=list)
    exile: list[Card] = Field(default_factory=list)
    life: int = Field(default=20)
    counters: dict[str, int] = Field(default_factory=dict)
    battlefield: dict[int, BattlefieldCard] = Field(default_factory=dict)
    
    def untap_all(self):
        for battlefield_card in self.battlefield.values():
            battlefield_card.tapped = False
            
    def battlefield_to_graveyard(self, battlefield_ids: list[int]):
        for battlefield_id in battlefield_ids:
            battlefield_card = self.battlefield[battlefield_id]
            self.graveyard.append(battlefield_card.card)
            del self.battlefield[battlefield_id]
    
    def battlefield_to_exile(self, battlefield_ids: list[int]):
        for battlefield_id in battlefield_ids:
            battlefield_card = self.battlefield[battlefield_id]
            self.exile.append(battlefield_card.card)
            del self.battlefield[battlefield_id]
            
    def tap_permanents(self, battlefield_ids: list[int]):
        for battlefield_id in battlefield_ids:
            self.battlefield[battlefield_id].tapped = True
            
    def cleanup_damage(self):
        for battlefield_card in self.battlefield.values():
            battlefield_card.marked_damage = 0
                    
    @classmethod
    def init_from_decklist(cls, decklist: DeckList):
        initial_library = [card for card,count in decklist.mainboard.items() for _ in range(count)]
        random.shuffle(initial_library)
        initial_library, initial_hand = initial_library[7:], initial_library[:7]
        self = cls(library=initial_library, hand=initial_hand)
        return self
        
    @property
    def battlefield_sorted(self) -> list[BattlefieldCard]:
        return sorted(self.battlefield.values(), key=lambda card: get_card_info(card.card)["manaValue"])
        
class GameState(BaseModel):
    player_decklists: list[DeckList]
    player_boards: list[PlayerBoard]
    battlefield_ids: list[int] = Field(default_factory=list)
    stack: list[CardOrToken] = Field(default_factory=list)
    next_battlefield_id: int = Field(default=0)
    active_player_index: int = Field(default=0)
    turn_step: TurnStep = Field(default=TurnStep.UNTAP)
    turn_number: int = Field(default=1, description="The number of the current turn, starting from 1. Each player taking a turn is 1 turn.")
    starting_player_index: int = Field(default=0)
    
    def cleanup_damage(self):
        for player_board in self.player_boards:
            player_board.cleanup_damage()
    
    def shuffle_library(self, player_index: int):
        random.shuffle(self.player_boards[player_index].library)
    
    def draw_cards(self, player_index: int, number_of_cards: int=1):
        for _ in range(number_of_cards):
            self.player_boards[player_index].hand.append(self.player_boards[player_index].library.pop())
            
    def add_card_to_battlefield(self,player_index: int, card: CardOrToken):
        battlefield_card = BattlefieldCard.from_card(card, player_index, self.next_battlefield_id)
        self.player_boards[player_index].battlefield[self.next_battlefield_id] = battlefield_card
        self.next_battlefield_id += 1

    def deal_damage(self, player_index: int, battlefield_ids: list[int], damage: int):
        for battlefield_id in battlefield_ids:
            battlefield_card = self.player_boards[player_index].battlefield[battlefield_id]
            battlefield_card.marked_damage += damage
            if battlefield_card.marked_damage >= battlefield_card.toughness:
                self.player_boards[player_index].battlefield_to_graveyard([battlefield_id])
                    
    @classmethod
    def init_from_decklists(cls, decklists: list[DeckList]):
        self = cls(player_decklists=decklists, player_boards=[PlayerBoard.init_from_decklist(decklist) for decklist in decklists])
        return self
