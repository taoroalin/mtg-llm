from game_state import DeckList, get_card_info
from log import llm_generate
import json
from pathlib import Path
from typing import List
import base64
import openai
openai = openai.AsyncOpenAI()

async def generate_playmat_for_deck(decklist: DeckList) -> bytes:
    # Get card info for all cards in mainboard
    cards_info = [get_card_info(card) for card in decklist.mainboard.keys()]
    
    # Generate prompt using GPT-4
    prompt_response = await llm_generate(
        model="o3-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a creative director designing Magic: The Gathering playmats. Generate an image prompt for DALL-E based on the deck's cards and themes."
            },
            {
                "role": "user",
                "content": f"Make a prompt for the image generation model Dalle 3 to generate a playmat image based on these cards: {json.dumps(cards_info, indent=2)}"
            }
        ],
        temperature=0.7
    )
    print("playmat prompt is", prompt_response.choices[0].message.content)
    dalle_prompt = prompt_response.choices[0].message.content

    # Generate image using DALL-E 3
    image_response = await openai.images.generate(
        prompt=dalle_prompt,
        model="dall-e-3",
        size="1792x1024",
        quality="standard",
    )
    print("got image response")
    
    return image_response.data[0].url