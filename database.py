
import json
from pathlib import Path
from typing import TypedDict, Optional, List, Union

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
    isToken: bool
    
all_cards = json.load(Path("assets/AtomicCardsGameplay.json").open())

comprehensive_rules = Path("assets/MagicCompRules.txt").read_text()

    
def get_card(name:str) -> CardInfo:
    return all_cards['data'][name]

def create_token_card_info(name:str, types:List[str], subtypes:list[str], power:Optional[int]=None, toughness:Optional[int]=None, text:str='') -> CardInfo:
    return {
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
    