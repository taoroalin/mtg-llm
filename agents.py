from typing import Optional
from pydantic import BaseModel, Field
import game_master
import log
agent_advice = """Remember that cost 2UU means 2 generic mana plus 2 blue mana, so 4 mana in total.
"""

class NaiveAgent(game_master.AgentInterface):
    generation_settings:dict

    async def take_action(self,history:list[game_master.HistoryStep],visible_information: str, available_actions:str, rules_violation_feedback:Optional[str]=None) -> str:
        messages = [{"role":"system", "content":"You are an expert Magic: The Gathering player. Your job is to win a game played over natural language with a text interface, talking to an expert judge who validates your actions and provides observations of the game state."},
        {"role":"user", "content":"Here are some of your notes to keep in mind:" + agent_advice},
                    {"role":"user", "content":f"""
Here is your history of past game states and actions:
{history}

Here is the current state of the game:
{visible_information}

Here is a summary of the actions available to you:
{available_actions}

Please think through your potential next actions and their consequences and then choose the best action.

Please describe your action precisely, including how you pay costs and what you choose during resolution of spells and abilities.
"""}]
        if rules_violation_feedback is not None:
            messages.append({"role":"user", "content":f"Your last action attempt was invalid. Please read this feedback and compose a legal action.\n{rules_violation_feedback}"})
        response = await log.llm_generate(
            **self.generation_settings,
                messages=messages,
        )
        action = response.choices[0].message.content
        return action
