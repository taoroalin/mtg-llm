import anthropic
import os
import json
from datetime import datetime
import trio
import random
import hashlib
import anyio

logging_dir = 'logs'
cache_dir = 'cache'
os.makedirs(logging_dir, exist_ok=True)
os.makedirs(f"{logging_dir}/generations", exist_ok=True)
os.makedirs(f"{logging_dir}/games", exist_ok=True)
os.makedirs(cache_dir, exist_ok=True)

os.makedirs("database", exist_ok=True)
os.makedirs("database/finished_games", exist_ok=True)
os.makedirs("database/ongoing_games", exist_ok=True)

anthropic_client = anthropic.AsyncAnthropic(max_retries=5)

prices = {
    "claude-sonnet-4-20250514": {"input": 3/1_000_000, "output": 15/1_000_000},
    "claude-opus-4-20250514": {"input": 15/1_000_000, "output": 75/1_000_000}
}

total_input_tokens = 0
total_output_tokens = 0

async def llm_generate(**kwargs):
    global total_input_tokens, total_output_tokens
    model = kwargs["model"]
    no_cache = kwargs.pop("no_cache", False)
    # Check cache first
    cache_key = _get_cache_key(kwargs)
    if not no_cache:
        cached_response = _load_from_cache(cache_key)
        if cached_response:
            print(f"Cache hit for request {cache_key[:8]}...")
            return cached_response
    
    if "claude" in model:
        if 'max_tokens' not in kwargs:
            kwargs['max_tokens'] = 8192

        response = await anthropic_client.messages.create(**kwargs)
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens
        }
        response_data = response.model_dump()
    else:
        raise ValueError(f"Unsupported model: {model}")

    # Save to cache
    _save_to_cache(cache_key, response_data)

    # Success - log and return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_data = {
        "request": kwargs,
        "response": response_data
    }
    
    with open(f"{logging_dir}/generations/{timestamp}.json", "w") as f:
        json.dump(log_data, f, indent=4)

    total_input_tokens += usage["prompt_tokens"]
    total_output_tokens += usage["completion_tokens"]
    
    usage_path = f"{logging_dir}/total_usage.json"
    try:
        with open(usage_path) as f:
            usage_data = json.load(f)
    except FileNotFoundError:
        usage_data = {"input": 0, "output": 0, "total": 0, "cost": 0}
        
    usage_data["input"] += usage["prompt_tokens"]
    usage_data["output"] += usage["completion_tokens"]
    usage_data["total"] = usage_data["input"] + usage_data["output"]
    usage_data["cost"] += usage["prompt_tokens"] * prices[model]["input"] + usage["completion_tokens"] * prices[model]["output"]
    
    with open(usage_path, "w") as f:
        json.dump(usage_data, f)
    
    return response_data

def _get_cache_key(kwargs):
    """Generate a cache key from the request parameters."""
    # Create a deterministic hash of the request
    cache_data = {
        'model': kwargs.get('model'),
        'messages': kwargs.get('messages'),
        'temperature': kwargs.get('temperature'),
        'max_tokens': kwargs.get('max_tokens'),
        'system': kwargs.get('system'),
        'tools': kwargs.get('tools'),
        'tool_choice': kwargs.get('tool_choice')
    }
    cache_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.sha256(cache_str.encode()).hexdigest()

def _load_from_cache(cache_key):
    """Load response from disk cache if it exists."""
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None

def _save_to_cache(cache_key, response_data):
    """Save response to disk cache."""
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump(response_data, f, indent=2)
    except IOError:
        pass  # Silently fail if we can't write to cache

def save_game(id:str, game_state):
    with open(f"database/ongoing_games/{id}.json", "w") as f:
        json.dump(game_state.model_dump(), f)

def finish_game(id:str):
    src_path = f"database/ongoing_games/{id}.json"
    dst_path = f"database/finished_games/{id}.json"
    os.rename(src_path, dst_path)