from pydantic import BaseModel, Field
from typing import Optional, Literal, Union
import random
from enum import Enum, auto

Card = str  # Type alias

CardOrToken = Card

class TurnStep(Enum):
    UNTAP = auto()
    UPKEEP = auto() 
    DRAW = auto()
    MAIN_1 = auto()
    BEGIN_COMBAT = auto()
    DECLARE_ATTACKERS = auto()
    DECLARE_BLOCKERS = auto()
    FIRST_STRIKE_DAMAGE = auto()
    COMBAT_DAMAGE = auto()
    END_COMBAT = auto()
    MAIN_2 = auto()
    END = auto()
    CLEANUP = auto()

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
    hand: list[Card]
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
            
    @classmethod
    def init_from_decklist(cls, decklist: DeckList):
        initial_library = [card for card,count in decklist.mainboard.items() for _ in range(count)]
        random.shuffle(initial_library)
        initial_library, initial_hand = initial_library[:7], initial_library[7:]
        self = cls(library=initial_library, hand=initial_hand)
        return self

class GameState(BaseModel):
    player_decklists: list[DeckList]
    player_boards: list[PlayerBoard]
    battlefield_ids: list[int] = Field(default_factory=list)
    stack: list[CardOrToken] = Field(default_factory=list)
    next_battlefield_id: int = Field(default=0)
    active_player_index: int = Field(default=0)
    turn_step: TurnStep = Field(default=TurnStep.UNTAP)
    
    def cleanup_damage(self):
        for player_board in self.player_boards:
            for battlefield_card in player_board.battlefield.values():
                battlefield_card.marked_damage = 0
    
    def shuffle_library(self, player_index: int):
        random.shuffle(self.player_boards[player_index].library)
    
    def draw_cards(self, player_index: int, number_of_cards: int=1):
        for _ in range(number_of_cards):
            self.player_boards[player_index].hand.append(self.player_boards[player_index].library.pop())
            
    def add_card_to_battlefield(self,player_index: int, card: CardOrToken):
        battlefield_card = BattlefieldCard.from_card(card, player_index, self.last_battlefield_id)
        self.player_boards[player_index].battlefield[self.next_battlefield_id] = battlefield_card
        self.next_battlefield_id += 1
            
    def tap_permanents(self, player_index: int, battlefield_ids: list[int]):
        for battlefield_id in battlefield_ids:
            self.player_boards[player_index].battlefield[battlefield_id].tapped = True

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