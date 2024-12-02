from pydantic import BaseModel, Field
from typing import Optional, Literal, Union, TypedDict, List
import random
from enum import Enum, auto
import json
from pathlib import Path
import copy

Card = str  # Type alias

CardOrToken = Card

class CardInfo(TypedDict, total=False):
    "All gameplay relevant information on a card."
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
    legalities:Optional[list[str]] # list of lowercase format names
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

card_database: dict[str, CardInfo] = json.load(Path("assets/AtomicCardsGameplay.json").open())

def create_token_card_info(name:str, types:List[str], subtypes:list[str], power:Optional[int]=None, toughness:Optional[int]=None, text:str='') -> CardInfo:
    """Token names don't contain 'Token', eg name is 'Goblin' not 'Goblin Token'"""
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


class TurnStep(str, Enum):
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
    "Decklist for a player at the beginning of the game. Mapping from card name to count."
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
        assert card in card_database['data'], f"Card {card} not found in card database. Use create_token_card_info to create a new token."
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
            
    def draw_cards(self, number_of_cards: int=1):
        for _ in range(number_of_cards):
            self.hand.append(self.library.pop())
                    
    @classmethod
    def init_from_decklist(cls, decklist: DeckList, arena_hand_smoothing:bool=False):
        initial_library = [card for card,count in decklist.mainboard.items() for _ in range(count)]
        random.shuffle(initial_library)
        if arena_hand_smoothing:
            initial_library, initial_hand = cls.arena_hand_smoothing(initial_library)
        else:
            initial_library, initial_hand = initial_library[7:], initial_library[:7]
        self = cls(library=initial_library, hand=initial_hand)
        return self
        
    @classmethod
    def arena_hand_smoothing(cls, library:list[Card])->tuple[list[Card], list[Card]]:
        """implement approximate MTG Arena augmented hand drawing algorithm:
        resample any hands that have an unusual number of lands for the deck
        This is not for competitive play, only for training and demonstration"""
        land_count = sum(1 for card in library if "Land" in get_card_info(card)["types"])
        expected_land_count = land_count / len(library) * 7
        while True:
            random.shuffle(library)
            hand, remaining_library = library[:7], library[7:]
            hand_land_count = sum(1 for card in hand if "Land" in get_card_info(card)["types"])
            if abs(hand_land_count - expected_land_count) <=1:
                return remaining_library, hand
        
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
    def init_from_decklists(cls, decklists: list[DeckList], arena_hand_smoothing:bool=False):
        self = cls(player_decklists=decklists, player_boards=[PlayerBoard.init_from_decklist(decklist, arena_hand_smoothing) for decklist in decklists])
        return self
        
    @classmethod
    def init_mirror(cls, decklist: DeckList):
        "init with identical shuffles to reduce variance in initial game state"
        randomized_player_board = PlayerBoard.init_from_decklist(decklist, arena_hand_smoothing=True)
        player_boards = [copy.deepcopy(randomized_player_board) for _ in range(2)]
        
        self = cls(player_decklists=[decklist]*2, player_boards=player_boards)
        return self

    def advance_to_step_simple(self, step: TurnStep):
        "Advance to next step assuming no other effects. Handles untap, draw, and cleaning up damage.If there are other effects, use this function multiple times with other code in between to handle them, eg advance to upkeep, run code to handle specific upkeep effects, then advance to draw"
        while True:
            if self.turn_step == step:
                return
            current_step_index = list(TurnStep).index(self.turn_step)
            next_step_index = (current_step_index + 1)
            if next_step_index >= len(TurnStep):
                next_step_index = 0
                self.active_player_index = (self.active_player_index + 1) % len(self.player_boards)
                print(f"advance_to_step_simple set active player to {self.active_player_index}")
                if self.active_player_index == self.starting_player_index:
                    self.turn_number += 1
            self.turn_step = list(TurnStep)[next_step_index]
            if self.turn_step == TurnStep.UNTAP:
                self.player_boards[self.active_player_index].untap_all()
            elif self.turn_step == TurnStep.DRAW:
                self.draw_cards(self.active_player_index)
            elif self.turn_step == TurnStep.CLEANUP:
                self.cleanup_damage()
                if len(self.player_boards[self.active_player_index].hand)>7:
                    print(f"WARNING: Aborted at cleanup step for player {self.active_player_index}. Player has {len(self.player_boards[self.active_player_index].hand)}>7 cards in hand. Please manually handle discarding to hand size if applicable then continue.")
                    return