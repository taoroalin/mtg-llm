from pydantic import BaseModel
from typing import Optional, Literal, Union
Card = str  # Type alias

CardOrToken = Card

class DeckList(BaseModel):
    library: list[Card]
    sideboard: list[Card]
    
class BattlefieldCard(BaseModel):
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
    library: list[Card]
    hand: list[Card]
    graveyard: list[Card]
    exile: list[Card]
    life: int
    counters: dict[str, int]
    battlefield: list[BattlefieldCard]
    
    def untap_all(self):
        for battlefield_card in self.battlefield:
            battlefield_card.tapped = False
    

class GameState(BaseModel):
    player_decklists: list[DeckList]
    player_boards: list[PlayerBoard]
    battlefield_ids: list[int]
    
    def cleanup_damage(self):
        for player_board in self.player_boards:
            for battlefield_card in player_board.battlefield:
                battlefield_card.marked_damage = 0
    