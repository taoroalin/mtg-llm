import log
import game_state
import inspect
import json
import io
import contextlib
import trio
import os
import prompting
import anyio
from typing import Callable
from pydantic import BaseModel


def compute_decklist_stats(decklist: game_state.DeckList) -> dict:
    total_cards = sum(decklist.mainboard.values())
    total_mana_value = 0
    mana_value_histogram = {}
    color_sources = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0}
    color_pips = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0}
    type_counts = {}
    subtype_counts = {}
    for card_name, count in decklist.mainboard.items():
        card_info = game_state.get_card_info(card_name)
        mv = card_info['manaValue']
        total_mana_value += mv * count
        mana_value_histogram[mv] = mana_value_histogram.get(mv, 0) + count
        for color in card_info['colorIdentity']:
            color_sources[color] += count
        for symbol in card_info['manaCost']:
            if symbol in color_pips:
                color_pips[symbol] += count
        for type_ in card_info['types']:
            type_counts[type_] = type_counts.get(type_, 0) + count
        for subtype in card_info['subtypes']:
            subtype_counts[subtype] = subtype_counts.get(subtype, 0) + count
    average_mana_value = total_mana_value / total_cards if total_cards else 0
    return {
        'mainboard_count': total_cards,
        'sideboard_count': sum(decklist.sideboard.values()),
        'average_mana_value': average_mana_value,
        'mana_value_histogram': mana_value_histogram,
        'color_sources': color_sources,
        'color_pips': color_pips,
        'type_counts': type_counts,
        'subtype_counts': subtype_counts,
    }

async def generate_deck_from_request(request: str, review_rounds: int = 3) -> dict:
    """
    Generates a decklist based on a natural language request using an LLM.
    The LLM writes Python code defining a `deck` variable using `all_cards`.
    """
    decklist_code = inspect.getsource(game_state.DeckList)
    card_info_code = inspect.getsource(game_state.CardInfo)

    conversation = [
        {
            "role": "system",
            "content": (
                "You create Magic: The Gathering decks based on user requests."
                " You have access to `all_cards`, a dictionary of card names to card information."
                " and `decklist`, a `DeckList` object."
                " Iteratively update `decklist` to add cards to the deck."
                f" The DeckList class is defined as:\n{decklist_code}"
                f" Each card in all_cards follows this TypedDict definition:\n{card_info_code}"
                "Think about the deck's plan, how the deck will win games and what its opening turns will look like."
                "Start by filtering for relevant cards and reading their card information"
                "Building a deck requires many iterations of reading cards and updating the decklist."
                "Here are some things all decks need:"
                " Core cards needed to win. For creature decks, these are creatures that can attack for a lot of damage."
                " A strong mana base, including the best nonbasic lands legal in the format unless otherwise specified."
                " Cards that distrupt your opponent's game plan. These could be counterspells, removal, discard, etc. The most agressive decks don't need this."
                " A good mana curve / opening plan. You want to have good plays on early turns that set up your win condition."
                "If a format is specified, filter cards for legality in that format."
            ),
        },
        {
            "role": "user",
            "content": f"Create a deck according to: '{request}'",
        },
    ]
    
    build_deck_tools = {
        "tools": [{
            "name": "build_deck",
            "description": "Build a decklist according to the user's request.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Reasoning about how to build a decklist."
                    },
                    "is_finished": {
                        "type": "boolean",
                        "description": "Whether the decklist is already complete before running code."
                    },
                    "python_code": {
                        "type": "string",
                        "description": "Python code to build a decklist. This code will execute in a context with `all_cards`, a dict from card name to card info, and `decklist` defined. This code should modify `decklist` in place. Print information for new cards you are considering adding to the decklist. A function `query_cards_with_llm` is also available, which takes in a natural language query and a list of cards and returns a list of card names that match the query. The function uses a fast language model and is more efficient than reading cards manually. You often want to filter for all hard criteria like legality and cost, then use `query_cards_with_llm` to find cards that match a more qualitative query."
                    },
                },
                "required": ["reasoning", "is_finished", "python_code"]
            }
        }],
        "tool_choice": {"type": "tool", "name": "build_deck"}
    }
    decklist: game_state.DeckList = game_state.DeckList(mainboard={}, sideboard={})
    all_cards = game_state.card_database['data']
    review_round = 0
    while True:
        response = await log.llm_generate(
            model="claude-sonnet-4-20250514",
            messages=conversation,
            temperature=1,
            max_tokens=4000,
            **build_deck_tools
        )
        print(json.dumps(response.choices[0].message.__dict__, indent=2))
        conversation.append({
            "role": "assistant",
            "content": response.choices[0].message.content,
            "tool_uses": response.choices[0].message.tool_uses
        })
        arguments = response.choices[0].message.tool_uses[0].input
        if arguments["is_finished"]:
            review = await review_decklist(decklist, request)
            if review_round >= review_rounds:
                break
            conversation.append({"role": "user", "content": f"Please improve your decklist. Here's my review of the decklist:\n{review}"})
            review_round += 1

        local_vars = {'all_cards': all_cards, 'decklist': decklist, 'query_cards_with_llm': query_cards_with_llm_sync}
        try:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(arguments["python_code"], local_vars)
            code_output_string = output.getvalue()
            if code_output_string:
                code_output_string = truncate_string(code_output_string, 20_000)
                conversation.append({"role": "user", "content": f"Code output: {code_output_string}"})
            conversation.append({"role": "user", "content": f"Decklist: {decklist}\nDecklist Stats: {compute_decklist_stats(decklist)}"})
            card_details = "\n".join([prompting.format_card_full(card) for card in decklist.mainboard.keys()])
            conversation.append({"role": "user", "content": f"Card details: {card_details}"})
            print(f"Decklist: {decklist}\nDecklist Stats: {compute_decklist_stats(decklist)}")
        except Exception as e:
            error_msg = f"Error executing code: {e}"
            print(error_msg)
            conversation.append({"role": "user", "content": error_msg})
    return decklist
    
def truncate_string(s:str, max_length:int) -> str:
    return (s[:max_length//2-20]+"...output was over 20k characters, truncated..." + s[max_length//2-20:]) if len(s) > max_length else s

def get_all_cards_prompt():
    return "\n".join([prompting.format_card_full(card) for card in game_state.card_database['data'].keys()])
    

async def filter_cards_model(cards:list[str], query:str, model='claude-sonnet-4-20250514') -> list[str]:
    print("filtering cards with model", model, len(cards), "cards", query)
    cards_prompt = "\n\n".join(cards)
    conversation = [
        {"role": "user", "content": f"Filter the following cards to only include cards that match the query: {query}\n\n{cards_prompt}\n\nPlease respond in json like {{thinking:string, cards:[string]}}, step by step thoughts followed by a list of only card names that match the query in order shown. Respond only in json with no surrounding text."}
    ]
    print(conversation[0]['content'])
    response = await log.llm_generate(model=model, messages=conversation)
    print(response.choices[0].message.content)
    return json.loads(response.choices[0].message.content)['cards']

async def query_cards_with_llm(query:str, card_names:list[str])->list[str]:
    prompts = [prompting.format_card_full(card) for card in card_names]
    batch_size = 3 * 128000
    batches = []
    current_batch = []
    current_length = 0
    
    for prompt in prompts:
        prompt_length = len(prompt)
        if current_length + prompt_length > batch_size:
            batches.append(current_batch)
            current_batch = [prompt]
            current_length = prompt_length
        else:
            current_batch.append(prompt)
            current_length += prompt_length
            
    if current_batch:
        batches.append(current_batch)
    print("filtering cards in ", len(batches), " batches")
    
    results = []
    async with anyio.create_task_group() as task_group:
        async def collect_result(batch):
            result = await filter_cards_model(batch, query)
            results.append(result)
        
        for batch in batches:
            task_group.start_soon(collect_result, batch)
    
    return [item for batch in results for item in batch]

def query_cards_with_llm_sync(query:str, card_names:list[str])->list[str]:
    return anyio.run(query_cards_with_llm, query, card_names)
    
async def review_decklist(decklist: game_state.DeckList, request: str) -> str:
    card_details = "\n".join([prompting.format_card_full(card) for card in decklist.mainboard.keys()])
    deck_stats = compute_decklist_stats(decklist)
    conversation = [
        {
            "role": "user",
            "content": (
                """You are an expert Magic: The Gathering player.
Your job is to review a decklist according to a user's request.
Here are some properties of a good deck:
The deck can win or disrupt its opponent and secure an advantage in the right time frame for the given constructed format. Eg aggressive decks should win in:
3 turns in Modern
4 turns in Pioneer
4-5 turns in Standard
5-6 turns in Pauper
7 turns in Commander
3 turns in CEDH

The deck should be able to cast all its cards. Eg if a card has 20 white mana in card costs, it should have ~16+ white sources.
The deck should only use cards that are legal in the given format.
The deck should have a good mana curve.
The deck should either have very strong synergies or use the strongest cards in the format.
A deck should not use any suboptimal cards in the given format. For instance, the card Shock is suboptimal in Modern, because Lightning Bolt and numerous other cards are almost strictly better.
A good deck has enough support for its synergy cards. For instance, a deck with 8 cards that assist other Merfolk cards needs ~16 total Merfolk cards in order for the Merfolk synergy cards to be worthwhile. If a deck request requires a specific synergy, you may need to prioritize synergy over general card quality.

Brainstorm what decks this deck will likely play against, and consider whether it has the tools to win against them.

Note: only suggest specific cards if they are well known to be strong, otherwise let the user search for cards that meet your criteria.
"""
            )
        },
        {"role": "user", "content": f"The decklist is built according to the following request: {request}"},
        {
            "role": "user",
            "content": (
                f"Decklist:\n{decklist}\n"
                f"Card details:\n{card_details}\n"
                f"Deck stats:\n{json.dumps(deck_stats, indent=2)}\n"
            )
        },
    ]

    response = await log.llm_generate(
        model="claude-sonnet-4-20250514",
        messages=conversation,
    )
    print("Review Decklist Response:")
    print(response.choices[0].message.content)
    return response.choices[0].message.content

if __name__ == "__main__":
    # print(len(game_state.card_database['data']), len(get_all_cards_prompt())) # 30813 6200714
    # bear_filter = lambda card: 'Bear' in card['subtypes']
    # queried_names = trio.run(query_cards, "Find all cards that might be played in a power level 7 EDH deck", bear_filter)
    # for name in queried_names:
    #     print(prompting.format_card_full(name))
    # exit()

    decklist = anyio.run(generate_deck_from_request, "Please make a Standard legal izzet Otter themed deck for q4 2024")
    print(decklist) 
    print(compute_decklist_stats(decklist))
    os.makedirs("assets/built_decks", exist_ok=True)
    with open(f"assets/built_decks/izzet_otter_deck.json", "w") as f:
        json.dump(decklist.model_dump(), f, indent=4)
