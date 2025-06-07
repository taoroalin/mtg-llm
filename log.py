import anthropic
import os
import json
from datetime import datetime

logging_dir = 'logs'
os.makedirs(logging_dir, exist_ok=True)
os.makedirs(f"{logging_dir}/generations", exist_ok=True)
os.makedirs(f"{logging_dir}/games", exist_ok=True)

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
    
    if "claude" in model:
        # Handle system message
        messages = kwargs.get("messages", [])
        system_message = next((msg["content"] for msg in messages if msg["role"] == "system"), None)
        if system_message:
            kwargs['system'] = system_message
        
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
    
    # Return a response object that mimics the original structure but with actual ToolUseBlock objects
    class Response:
        def __init__(self, data, original_response):
            # Store the original tool use blocks for access
            original_tool_uses = []
            for content_block in original_response.content:
                if content_block.type == "tool_use":
                    original_tool_uses.append(content_block)
            
            self.choices = [type('Choice', (), {
                'message': type('Message', (), {
                    'content': data['choices'][0]['message']['content'],
                    'tool_uses': original_tool_uses
                })()
            })()]
            self.usage = type('Usage', (), usage)()
    
    return Response(response_data, response)

def save_game(id:str, game_state):
    with open(f"database/ongoing_games/{id}.json", "w") as f:
        json.dump(game_state.model_dump(), f)

def finish_game(id:str):
    src_path = f"database/ongoing_games/{id}.json"
    dst_path = f"database/finished_games/{id}.json"
    os.rename(src_path, dst_path)