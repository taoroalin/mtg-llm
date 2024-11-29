from typing import Optional
from pydantic import BaseModel, Field
import game_master
import openai
client = openai.Client()



class NaiveAgent(game_master.AgentInterface):
    generation_settings:dict
    def __init__(self, player_index: int, generation_settings:dict):
        self.player_index = player_index
        self.generation_settings = generation_settings

    def take_action(self,history:list["HistoryStep"], visible_information: str, rules_violation_feedback:Optional[str]=None) -> str:
        messages = [{"role":"system", "content":"You are an expert Magic: The Gathering player. Your job is to win a game played over text."},
                    {"role":"user", "content":f"""
Here is your history of past game states and actions:
{self.history}

Here is the current state of the game:
{visible_information}

Please think through your potential next actions and their consequences and then choose the best action.

Please describe your action precisely, including how you pay costs and what you choose during resolution of spells and abilities.
"""}]
        response = client.chat.completions.create(
            **self.generation_settings,
            messages=messages,
        )
        action = response.choices[0].message.content
        return action
