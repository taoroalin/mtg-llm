import game_state
import prompts
import prompting
from pydantic import BaseModel, Field
from typing import Optional, Callable
import json
import io
from contextlib import redirect_stdout
from copy import deepcopy
import traceback
import log

class HistoryStep(BaseModel):
    visible_information: str
    available_actions: str
    action: str
    
class AgentInterface(BaseModel):

    def take_action(self, history:list["HistoryStep"], visible_information: str, available_actions:str, rules_violation_feedback:Optional[str]=None) -> str:
        pass
        return ""


class GameMaster(BaseModel):
    game_state: game_state.GameState
    agents: list["AgentInterface"]
    generation_settings: dict
    past_game_states: list[game_state.GameState] = Field(default_factory=list)
    player_observation_histories: list[list[HistoryStep]] = Field(default_factory=list)
    priority_player: int = Field(default=0)
    player_action:str = Field(default="")
    invalid_action_feedback: Optional[str] = Field(default=None)
    winner: Optional[int] = Field(default=None)
    priority_player_revealed_information: str = Field(default="")
    priority_player_available_actions: str = Field(default="")
        
    def game_loop(self):
        while self.winner is None:
            self.past_game_states.append(deepcopy(self.game_state))
            self.step(self.player_action)
            if self.winner is not None:
                return self.winner
            self.player_action = self.get_player_action(self.priority_player, self.priority_player_available_actions, self.priority_player_revealed_information,self.invalid_action_feedback)
            print(prompting.format_omniscient_view(self.game_state))
            print(f"Player {self.priority_player} action: {self.player_action}")
        return self.winner
            
    def get_player_action(self, player_index: int, available_actions: str, revealed_information: str, invalid_action_feedback: Optional[str]=None):
        if len(self.player_observation_histories) <= len(self.agents):
            self.player_observation_histories = [[] for _ in self.agents]
        player_view = prompting.format_player_view(self.game_state, player_index, revealed_information)
        player_action = self.agents[player_index].take_action(self.player_observation_histories[player_index],player_view, available_actions, invalid_action_feedback)
        self.player_observation_histories[player_index].append(HistoryStep(visible_information=player_view, action=player_action, available_actions=available_actions))
        return player_action
        
    def execute_action(self, action: str):
        execute_action_messages = self.get_base_messages()
        execute_action_messages.append({"role":"user", "content":f"Player validate whether the action player {self.priority_player} wants to take is valid. If it is, advance the game state according to the action.\nAction: {action}"})
        execute_action_tools = {"functions":[
            {
            "name": "advance_game_state",
            "description": "Advance the game state according to the rules of Magic: The Gathering. First validate that the last player action was legal. If it was, execute the action and update the game state. If it was not, return an explanation of why it was illegal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Reasoning about whether the last player action was valid according to game rules. Think about whether the action was legal, whether it was played correctly, whether the player had enough mana to pay for the action, etc."
                    },
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
                "required": ["reasoning", "is_action_valid", "python_code", "winner"]
            }
        }],
        "function_call":{"name": "advance_game_state"}}
        execution_success = False
        while True:
            response = log.llm_generate(
                messages=execute_action_messages,
                **self.generation_settings,
                **execute_action_tools
            )
            execute_action_messages.append(response.choices[0].message.model_dump(exclude_none=True))
            arguments = json.loads(response.choices[0].message.function_call.arguments)
            if not arguments["is_action_valid"]:
                return False, arguments["invalid_action_feedback"]
            execution_success, execution_output = self.execute_code_with_game_state(arguments["python_code"])
            if execution_success:
                return True, ""
            else:
                execute_action_messages.append({"role":"user", "content":f"The code to execute to advance the game state raised an exception. State was restored to before the action was executed. Please fix the code and try again.\nException: {execution_output}"})
                
    def advance_game_to_next_priority(self):
        advance_game_state_messages = self.get_base_messages()
    
        advance_state_tools = {"functions":[
                {
                "name": "advance_game_state",
                "description": "Advance the game state according to the rules of Magic: The Gathering to the next time a player will get priority and be able to take an action.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "Reasoning about when any player will next be able to take an action and what needs to be executed to advance the game state to that point."
                        },
                        "priority_player": {
                            "type": "integer",
                            "description": "Index of player who currently has priority"
                        },
                        "python_code": {
                            "type": "string",
                            "description": "Python code to execute to update game state. This code will execute in a context with `game_state` defined. This code should modify game_state in place. Before and after code is executed, game state is backed up. If code raises an exception, game state will be restored to its previous state. You will see the printed output of this code, which you can use to eg look at cards in players' libraries."
                        },
                    },
                    "required": ["reasoning", "priority_player", "python_code"]
                }
            }],
            "function_call":{"name": "advance_game_state"}}
        
        advance_game_state_messages.append({"role":"user", "content":"Please identify the next time an player will get priority and be able to take an action, and advance the game to that point. Advancing the game state involves setting the active_player and turn_step properties of game_state, as well as untapping permanents, drawing cards, clearing damage, resolving any triggered abilities that do not involve player choices, etc. Please skip over multiple steps if no players will have available actions, eg executing untap, upkeep, and draw steps and skipping to main phase if no player has instant speed actions available."})
        execution_success = False
        while True:
            response = log.llm_generate(
            messages=advance_game_state_messages,
            **self.generation_settings,
            **advance_state_tools
        )
            
            result = json.loads(response.choices[0].message.function_call.arguments)
            self.priority_player = result["priority_player"]
            execution_success, execution_output = self.execute_code_with_game_state(result["python_code"])
            if execution_success:
                break
            else:
                advance_game_state_messages.append({"role":"user", "content":f"The code to execute to advance the game state raised an exception. State was restored to before the action was executed. Please fix the code and try again.\nException: {execution_output}"})
        return result
        
    def analyze_state_at_priority(self):
        analyze_state_messages = self.get_base_messages()
        analyze_state_messages.append({"role":"user", "content":"Please analyze the current game state and describe what actions are available to the player who currently has priority."})
        
        analyze_state_tools = {"functions":[
                {
                "name": "extract_state_info",
                "description": "Extract key information about the current game state",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "Reasoning about the current game state. Think about who can legally take and pay for which actions, whether any win conditions are met, etc."
                        },
                        "priority_player": {
                            "type": "integer",
                            "description": "Index of player who currently has priority"
                        },
                        "priority_player_revealed_information": {
                            "type": "string",
                            "description": "Special available information revealed to priority player. For example, revealed cards from scrying or cards revealed during spell or ability resolution."
                        },
                        "priority_player_available_mana": {
                            "type": "string",
                            "description": "Mana available to priority player, including generic and colored mana."
                        },
                        "priority_player_available_actions": {
                            "type": "string",
                            "description": "List of legal actions available to priority player. Only include actions that the priority player can pay for."
                        },
                        "winner": {
                            "type": ["integer", "null"],
                            "description": "Index of winning player if game is over. None if game ongoing."
                        }
                    },
                    "required": ["reasoning", "priority_player", "priority_player_revealed_information", "priority_player_available_mana", "priority_player_available_actions", "winner"]
                }
            }],
            "function_call":{"name": "extract_state_info"}}
        response = log.llm_generate(
            messages=analyze_state_messages,
            **self.generation_settings,
            **analyze_state_tools
        )
        
        result = json.loads(response.choices[0].message.function_call.arguments)
        return result
        
    def step(self, action: str):
        if action != "":
            is_action_valid, invalid_action_feedback = self.execute_action(action)
            if not is_action_valid:
                self.invalid_action_feedback = invalid_action_feedback
        self.advance_game_to_next_priority()
        analyzed_state = self.analyze_state_at_priority()
        if analyzed_state.get("winner") is not None:
            self.winner = analyzed_state["winner"]
        self.priority_player = analyzed_state["priority_player"]
        self.priority_player_available_actions = analyzed_state["priority_player_available_actions"]
        self.priority_player_revealed_information = analyzed_state["priority_player_revealed_information"]
        
    def get_base_messages(self):
        omniscient_view = prompting.format_omniscient_view(self.game_state)
        game_state_code = open("game_state.py").read()
        messages = [{"role":"system", "content":"""You are an expert Magic: The Gathering judge. Your job is to enforce the rules of a Magic: The Gathering game played by two players who interact through natural language text. You track the state of the game using a Python API."""},{"role":"user", "content":f"""Game Phase reminder:
{prompts.game_phase_guide}"""},{"role":"user", "content":f"""
The current game state is stored in python objects. Here is a text summary of the current game state:

Here are the python classes that hold the game state:
{game_state_code}

Current Game State:
{omniscient_view}"""}]
        return messages
        
    def execute_code_with_game_state(self, code: str) -> tuple[bool, str]:

        f = io.StringIO()
        previous_game_state = deepcopy(self.game_state)
        local_vars = {"game_state": self.game_state}
        local_vars.update({name: getattr(game_state, name) for name in dir(game_state) if not name.startswith('_')})
        
        try:
            with redirect_stdout(f):
                exec(code, {}, local_vars)
            return True, f.getvalue()
        except Exception:
            self.game_state = previous_game_state
            return False, traceback.format_exc()