import openai
import os
logging_dir = 'logs'
os.makedirs(logging_dir, exist_ok=True)
os.makedirs(f"{logging_dir}/generations", exist_ok=True)

client = openai.Client()

prices = {"gpt-4o-2024-08-06": {"input": 2.5/1_000_000, "output": 10/1_000_000}}

total_input_tokens = 0
total_output_tokens = 0
def llm_generate( **kwargs):
    global total_input_tokens, total_output_tokens
    response = client.chat.completions.create(**kwargs)
    import json
    import os
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    os.makedirs(logging_dir, exist_ok=True)
    
    log_data = {
        "request": kwargs,
        "response": response.model_dump(exclude_none=True)
    }
    
    with open(f"{logging_dir}/generations/{timestamp}.json", "w") as f:
        json.dump(log_data, f, indent=4)
    total_input_tokens += response.usage.prompt_tokens
    total_output_tokens += response.usage.completion_tokens
    import json
    usage_path = f"{logging_dir}/total_usage.json"
    try:
        with open(usage_path) as f:
            usage = json.load(f)
    except FileNotFoundError:
        usage = {"input": 0, "output": 0, "total": 0, "cost": 0}
        
    usage["input"] += response.usage.prompt_tokens
    usage["output"] += response.usage.completion_tokens
    usage["total"] = usage["input"] + usage["output"]
    usage["cost"] += response.usage.prompt_tokens * prices[kwargs["model"]]["input"] + response.usage.completion_tokens * prices[kwargs["model"]]["output"]
    with open(usage_path, "w") as f:
        json.dump(usage, f)
    return response
