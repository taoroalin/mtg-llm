import openai
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

openai_client = openai.AsyncOpenAI()
anthropic_client = anthropic.AsyncAnthropic()

prices = {
    "o3-mini": {"input": 0.2/1_000_000, "output": 0.6/1_000_000},  # $0.0002/1K input tokens, $0.0006/1K output tokens
    "gpt-4o-2024-08-06": {"input": 2.5/1_000_000, "output": 10/1_000_000}, 
    "gpt-4o-2024-05-13": {"input": 5/1_000_000, "output": 10/1_000_000}, 
    "gpt-4o": {"input": 5/1_000_000, "output": 10/1_000_000}, 
    "o1-preview": {"input": 15/1_000_000, "output": 60/1_000_000}, 
    "gpt-4o-mini": {"input": 0.15/1_000_000, "output": 0.6/1_000_000},
    "claude-3-opus-20240229": {"input": 15/1_000_000, "output": 75/1_000_000},
    "claude-3-sonnet-20240229": {"input": 3/1_000_000, "output": 15/1_000_000},
    "claude-3-5-sonnet-20241022": {"input": 3/1_000_000, "output": 15/1_000_000}
}

total_input_tokens = 0
total_output_tokens = 0

async def llm_generate(**kwargs):
    global total_input_tokens, total_output_tokens
    model = kwargs["model"]
    
    if "claude" in model:
        # Convert OpenAI format to Anthropic format
        n = kwargs.pop("n", 1)
        messages = kwargs.get("messages", [])
        system_message = next((msg["content"] for msg in messages if msg["role"] == "system"), None)
        if system_message:
            kwargs['system'] = system_message
        # Build the messages for Anthropic
        anthropic_messages = []
        messages = [x for x in messages if x["role"] != "system"]
        kwargs['messages'] = messages
        if 'tool_choice' in kwargs:
            tool_choice = kwargs.pop('tool_choice')
            kwargs['tool_choice'] = {'type':'tool', 'name': tool_choice['function']['name']}
        kwargs['max_tokens'] = kwargs.pop("max_completion_tokens", 4096)
        if 'tools' in kwargs:
            tools = kwargs.pop('tools')
            kwargs['tools'] = [{'name': tool['function']['name'], 'description': tool['function']['description'], 'input_schema': tool['function']['parameters']} for tool in tools]

        response = await anthropic_client.messages.create(
            **kwargs
        )
        
        # Convert Anthropic response to OpenAI format for consistent logging
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens
        }
        tool_calls = [x for x in response.content if x.type == "tool_use"]
        response_data = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": response.content[0].text if response.content[0].type == "text" else ""
                },
                "tool_calls": tool_calls
            }],
            "usage": usage
        }
    else:
        response = await openai_client.chat.completions.create(**kwargs)
        response_data = response.model_dump(exclude_none=True)
        usage = response.usage

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_data = {
        "request": kwargs,
        "response": response_data
    }
    
    with open(f"{logging_dir}/generations/{timestamp}.json", "w") as f:
        json.dump(log_data, f, indent=4)

    total_input_tokens += usage.prompt_tokens
    total_output_tokens += usage.completion_tokens
    
    usage_path = f"{logging_dir}/total_usage.json"
    try:
        with open(usage_path) as f:
            usage_data = json.load(f)
    except FileNotFoundError:
        usage_data = {"input": 0, "output": 0, "total": 0, "cost": 0}
        
    usage_data["input"] += usage.prompt_tokens
    usage_data["output"] += usage.completion_tokens
    usage_data["total"] = usage_data["input"] + usage_data["output"]
    usage_data["cost"] += usage.prompt_tokens * prices[model]["input"] + usage.completion_tokens * prices[model]["output"]
    
    with open(usage_path, "w") as f:
        json.dump(usage_data, f)
    
    return response if "claude" not in model.lower() else type('Response', (), {'model_dump': lambda *args, **kwargs: response_data})()

def save_game(id:str, game_state):
    with open(f"database/ongoing_games/{id}.json", "w") as f:
        json.dump(game_state.model_dump(), f)

def finish_game(id:str):
    src_path = f"database/ongoing_games/{id}.json"
    dst_path = f"database/finished_games/{id}.json"
    os.rename(src_path, dst_path)