from game_state import GameState
from prompts import make_game_master_prompt, game_phase_guide
from prompting import format_omniscient_view
import openai
from pydantic import BaseModel
from typing import Optional, Callable
import json
import io
from contextlib import redirect_stdout
from copy import deepcopy

client = openai.Client()

class HistoryStep(BaseModel):
    visible_information: str
    rules_violation_feedback: Optional[str]
    action: str
    
class AgentInterface(BaseModel):
    def __init__(self, player_index: int):
        self.player_index = player_index

    def take_action(self, history:list["HistoryStep"], visible_information: str, rules_violation_feedback:Optional[str]=None) -> str:
        pass
        return ""


class GameMaster(BaseModel):
    game_state: GameState
    agents: list["AgentInterface"]
    past_game_states: list[GameState]
    generation_settings: dict
        
    def game_loop(self):
        while not self.game_state.is_game_over():
            self.past_game_states.append(deepcopy(self.game_state))
            priority_player, priority_player_available_actions, revealed_information, winner = self.step()
            if winner is not None:
                return winner
            priority_player.take_action(self.history, priority_player_available_actions)
        
    def advance_game_state(self, last_player_action: str):
        advance_game_state_messages = self.get_base_messages()
    
        gm_process_guide = """Please follow these steps to advance the game:
        1. Identify the current phase/step
        2. List what actions are available to each player given their cards in hand andthe current state of the game
        2. Execute any automatic game actions for this step (like untapping or drawing) that happen before players get priority
        3. Describe what actions are available to players
        4. Wait for player actions before proceeding
        5. Move to the next phase/step when all players pass priority with an empty stack"""
        
        advance_game_state_messages.append({"role":"user", "content":f"Please advance the game state according to the following guide using the advance_game_state tool:\n{gm_process_guide}"})

        advance_state_tools = {"functions":[
                {
                "name": "advance_game_state",
                "description": "Advance the game state according to the rules of Magic: The Gathering. First validate that the last player action was legal. If it was, execute the action and update the game state. If it was not, return an explanation of why it was illegal.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "is_action_valid": {
                            "type": "boolean",
                            "description": "Whether the last player action was valid according to game rules"
                        },
                        "invalid_action_feedback": {
                            "type": "string", 
                            "description": "If action was invalid, explanation of why"
                        },
                        "python_code": {
                            "type": "string",
                            "description": "Python code to execute to update game state. This code will execute in a context with `game_state` defined. This code should modify game_state in place. Before and after code is executed, game state is backed up. If code raises an exception, game state will be restored to its previous state. You will see the printed output of this code, which you can use to eg look at cards in players' libraries."
                        },
                    },
                    "required": ["is_action_valid", "python_code", "winner"]
                }
            }],
            "function_call":{"name": "advance_game_state"}}
            
        for i in range(5):
            response = client.chat.completions.create(
                messages=advance_game_state_messages,
                **self.generation_settings,
                **advance_state_tools
            )
            arguments = json.loads(response.choices[0].message.function_call.arguments)
            if not arguments["is_action_valid"]:
                return arguments["invalid_action_feedback"]
            if arguments["is_action_valid"]:
                self.execute_code_with_game_state(arguments["python_code"])
                break
            
        analyze_state_tools = {"functions":[
                {
                "name": "extract_state_info",
                "description": "Extract key information about the current game state",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "priority_player": {
                            "type": "integer",
                            "description": "Index of player who currently has priority"
                        },
                        "priority_player_revealed_information": {
                            "type": "string",
                            "description": "Special available information revealed to priority player. For example, revealed cards from scrying or cards revealed during spell or ability resolution."
                        },
                        "priority_player_available_actions": {
                            "type": "string",
                            "description": "List of legal actions available to priority player"
                        },
                        "winner": {
                            "type": "integer",
                            "description": "Index of winning player if game is over, -1 if game ongoing"
                        }
                    },
                    "required": ["priority_player", "priority_player_revealed_information", "priority_player_available_actions", "winner"]
                }
            }],
            "function_call":{"name": "extract_state_info"}}
        response = client.chat.completions.create(
            messages=messages,
            **self.generation_settings
        )
        
        result = json.loads(response.choices[0].message.function_call.arguments)
        return result
    
    def get_base_messages(self):
        omniscient_view = format_omniscient_view(self.game_state)
        game_state_code = open("game_state.py").read()
        messages = [{"role":"system", "content":"""You are an expert Magic: The Gathering judge. Your job is to enforce the rules of a Magic: The Gathering game played by two players with a Python API."""},{"role":"user", "content":f"""

Game Phase reminder:
{game_phase_guide}

The current game state is stored in python objects. Here is a text summary of the current game state:

Current Game State:
{omniscient_view}

Here are the python classes that hold the current game state:
{game_state_code}

"""}]
        return messages
        
    def execute_code_with_game_state(self, code: str) -> str:

        f = io.StringIO()
        previous_game_state = deepcopy(self.game_state)
        local_vars = {"game_state": self.game_state}
        
        try:
            with redirect_stdout(f):
                exec(code, {}, local_vars)
            return f.getvalue()
        except Exception as e:
            self.game_state = previous_game_state
            return str(e)