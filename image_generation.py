from game_state import DeckList, get_card_info
from log import llm_generate
import json
import os
import hashlib
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import trio
import asyncio

# Create cache directory for images
cache_images_dir = 'cache_images'
os.makedirs(cache_images_dir, exist_ok=True)

async def get_image_prompt(decklist: DeckList) -> str:
    # Get card info for all cards in mainboard
    cards_info = [get_card_info(card) for card in decklist.mainboard.keys()]
    
    # Generate prompt using Claude (keeping existing LLM for prompt generation)
    prompt_response = await llm_generate(
        model="claude-sonnet-4-20250514",
        messages=[
            {
                "role": "system",
                "content": "You are a creative director designing Magic: The Gathering playmats. Generate a detailed image prompt for Google's Imagen model based on the deck's cards and themes. Focus on visual elements, colors, atmosphere, and fantasy art style suitable for a playmat."
            },
            {
                "role": "user",
                "content": f"Create an image prompt for a Magic: The Gathering playmat based on these cards: {json.dumps(cards_info, indent=2)}. The prompt should describe a fantasy scene that captures the essence and theme of this deck."
            }
        ],
        temperature=0.7,
        no_cache=True
    )
    image_prompt = prompt_response.choices[0].message.content
    return image_prompt
    

async def generate_playmat_for_deck(decklist: DeckList) -> str:
    image_prompt = await get_image_prompt(decklist)
    
    # Create hash of the image prompt
    prompt_hash = hashlib.sha256(image_prompt.encode()).hexdigest()
    image_filename = f"{prompt_hash}.png"
    image_path = os.path.join(cache_images_dir, image_filename)
    
    # Check if image already exists in cache
    if os.path.exists(image_path):
        print(f"Using cached image for prompt hash {prompt_hash[:8]}...")
        return f"/cached-images/{image_filename}"
    
    # Generate new image
    client = genai.Client()
    response = client.models.generate_images(
        model='imagen-3.0-generate-002',
        prompt=image_prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="16:9",
        )
    )
    
    generated_image = response.generated_images[0]
    image = Image.open(BytesIO(generated_image.image.image_bytes))
    
    # Save image to cache
    image.save(image_path, 'PNG')
    print(f"Saved new image to cache: {image_filename}")
    
    # Return server URL path
    return f"/cached-images/{image_filename}"

async def main():
    decklist = DeckList.model_validate_json(open("assets/example_decks/Cats_elves.json").read())
    await generate_playmat_for_deck(decklist)

if __name__ == "__main__":
    asyncio.run(main())