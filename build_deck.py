import log
import game_state
import inspect
import json
import io
import contextlib
import asyncio
import os
import prompting

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
    
    build_deck_tools = {"functions":[
                {
                "name": "build_deck",
                "description": "Build a decklist according to the user's request.",
                "parameters": {
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
                            "description": "Python code to build a decklist. This code will execute in a context with `all_cards`, a dict from card name to card info, and `decklist` defined. This code should modify `decklist` in place. Print information for new cards you are considering adding to the decklist."
                        },
                    },
                    "required": ["reasoning", "is_finished", "python_code"]
                }
            }],
            "function_call":{"name": "build_deck"}}
    decklist: game_state.DeckList = game_state.DeckList(mainboard={}, sideboard={})
    all_cards = game_state.card_database['data']
    review_round = 0
    while True:
        response = await log.llm_generate(
            model="gpt-4o-2024-05-13",
            messages=conversation,
            temperature=1,
            max_tokens=4000,
            **build_deck_tools
        )
        print(json.dumps(response.choices[0].message.model_dump(exclude_none=True), indent=2))
        conversation.append(response.choices[0].message.model_dump(exclude_none=True))
        arguments = json.loads(response.choices[0].message.function_call.arguments)
        if arguments["is_finished"]:
            review = await review_decklist(decklist, request)
            if review_round >= review_rounds:
                break
            conversation.append({"role": "user", "content": f"Please improve your decklist. Here's my review of the decklist:\n{review}"})
            review_round += 1

        local_vars = {'all_cards': all_cards, 'decklist': decklist}
        try:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(arguments["python_code"], local_vars)
            if output.getvalue():
                conversation.append({"role": "user", "content": f"Code output: {output.getvalue()}"})
            conversation.append({"role": "user", "content": f"Decklist: {decklist}\nDecklist Stats: {compute_decklist_stats(decklist)}"})
            card_details = "\n".join([prompting.format_card_full(card) for card in decklist.mainboard.keys()])
            conversation.append({"role": "user", "content": f"Card details: {card_details}"})
            print(f"Decklist: {decklist}\nDecklist Stats: {compute_decklist_stats(decklist)}")
        except Exception as e:
            error_msg = f"Error executing code: {e}"
            print(error_msg)
            conversation.append({"role": "user", "content": error_msg})
    return decklist
    
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

Brainstorm what decks this deck will likely play against, and consider whether it has the tools to win against them.
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
        model="o1-preview",
        messages=conversation,
    )
    print("Review Decklist Response:")
    print(response.choices[0].message.content)
    return response.choices[0].message.content

if __name__ == "__main__":
    decklist = asyncio.run(generate_deck_from_request("Please make a pioneer legal Bird themed deck"))
    print(decklist)
    print(compute_decklist_stats(decklist))
    os.makedirs("assets/built_decks", exist_ok=True)
    with open(f"assets/built_decks/bird_deck.json", "w") as f:
        json.dump(decklist.model_dump(), f, indent=4)