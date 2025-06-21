from typing import Optional
from pydantic import BaseModel, Field
import game_master
import log
agent_advice = """Remember that cost 2UU means 2 generic mana plus 2 blue mana, so 4 mana in total.

Action Format Examples:
- Play a land: "Play [Land Name]"
- Cast a spell: "Cast [Spell Name] targeting [target]" or "Cast [Spell Name]" if no target or "Cast [Spell Name] tapping [lands to tap] [other choices required to cast the spell]" you need to make choices about how to pay the costs or need to make additional choices when casting the spell
- Attack: "Attack with [Creature Name(s)]" or "Attack with battlefield ID [ID]"
- Activate ability: "Activate [ability description] on [card/battlefield ID]"
- Pass priority: "Pass" or "Do nothing"
- End turn: "End turn"

Always be specific about which cards you're referring to, especially when multiple copies exist.
"""

class NaiveAgent(game_master.AgentInterface):
    generation_settings: dict

    async def take_action(self,history:list[game_master.HistoryStep],visible_information: str, available_actions:str, rules_violation_feedback:Optional[str]=None) -> str:
        system ="You are an expert Magic: The Gathering player. Your job is to win a game played over natural language with a text interface, talking to an expert judge who validates your actions and provides observations of the game state.\nHere are some of your notes to keep in mind:" + agent_advice
        messages = [
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
            messages=messages,
            system=system,
            **self.generation_settings
        )
        action = response['content'][0]['text']
        return action
