import anthropic
import os
import json
from datetime import datetime
import asyncio
import random
import hashlib

logging_dir = 'logs'
cache_dir = 'cache'
os.makedirs(logging_dir, exist_ok=True)
os.makedirs(f"{logging_dir}/generations", exist_ok=True)
os.makedirs(f"{logging_dir}/games", exist_ok=True)
os.makedirs(cache_dir, exist_ok=True)

os.makedirs("database", exist_ok=True)
os.makedirs("database/finished_games", exist_ok=True)
os.makedirs("database/ongoing_games", exist_ok=True)

anthropic_client = anthropic.AsyncAnthropic()

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
            return _create_response_object(cached_response)
    
    max_retries = 5
    base_delay = 1.0
    
    for attempt in range(max_retries + 1):
        try:
            if "claude" in model:
                # Handle system message
                messages = kwargs.get("messages", [])
                
                # Remove thinking_limit parameter as it's not supported in current API
                kwargs.pop("thinking_limit", None)
                
                # Filter out system messages from messages list
                kwargs['messages'] = [x for x in messages if x["role"] != "system"]
                
                # Convert max_tokens parameter
                if 'max_completion_tokens' in kwargs:
                    kwargs['max_tokens'] = kwargs.pop('max_completion_tokens')
                elif 'max_tokens' not in kwargs:
                    kwargs['max_tokens'] = 4096

                response = await anthropic_client.messages.create(**kwargs)
                
                # Convert response to consistent format
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens
                }
                
                # Handle tool use content blocks (Anthropic native format)
                tool_uses = []
                content = ""
                for content_block in response.content:
                    if content_block.type == "text":
                        content = content_block.text
                    elif content_block.type == "tool_use":
                        # Convert to serializable format for logging
                        tool_uses.append({
                            "id": content_block.id,
                            "name": content_block.name,
                            "input": content_block.input
                        })
                
                response_data = {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": content,
                            "tool_uses": tool_uses if tool_uses else None
                        }
                    }],
                    "usage": usage
                }
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
            
            return _create_response_object(response_data)
            
        except Exception as e:
            # Check if it's a rate limit error
            is_rate_limit = (
                hasattr(e, 'status_code') and e.status_code == 429 or
                'rate limit' in str(e).lower() or
                'too many requests' in str(e).lower()
            )
            
            if is_rate_limit and attempt < max_retries:
                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limit hit, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})")
                await asyncio.sleep(delay)
                continue
            else:
                # Re-raise the exception if it's not a rate limit or we've exhausted retries
                raise

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

def _create_response_object(response_data):
    """Create a response object from response data (for both cached and fresh responses)."""
    class Response:
        def __init__(self, data):
            # For cached responses, we don't have original tool use blocks
            # so we create mock objects with the same interface
            tool_uses = data['choices'][0]['message'].get('tool_uses', [])
            mock_tool_uses = []
            if tool_uses:
                for tool_use in tool_uses:
                    mock_tool_use = type('ToolUse', (), {
                        'id': tool_use['id'],
                        'name': tool_use['name'],
                        'input': tool_use['input']
                    })()
                    mock_tool_uses.append(mock_tool_use)
            
            self.choices = [type('Choice', (), {
                'message': type('Message', (), {
                    'content': data['choices'][0]['message']['content'],
                    'tool_uses': mock_tool_uses
                })()
            })()]
            self.usage = type('Usage', (), data['usage'])()
    
    return Response(response_data)

def save_game(id:str, game_state):
    with open(f"database/ongoing_games/{id}.json", "w") as f:
        json.dump(game_state.model_dump(), f)

def finish_game(id:str):
    src_path = f"database/ongoing_games/{id}.json"
    dst_path = f"database/finished_games/{id}.json"
    os.rename(src_path, dst_path)