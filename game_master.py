import game_state
import prompts
import prompting
from pydantic import BaseModel, Field
from typing import Optional, Callable, Any
import json
import io
from contextlib import redirect_stdout
from copy import deepcopy
import traceback
import log
import trio
import uuid

class HistoryStep(BaseModel):
    visible_information: str
    available_actions: str
    action: str
    
class AgentInterface(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True,
        "ignore_bound_methods": True,
        "json_schema_extra": {
            "exclude": {"take_action"}
        }
    }
    
    async def take_action(self, history:list["HistoryStep"], visible_information: str, available_actions:str, rules_violation_feedback:Optional[str]=None) -> str:
        pass
        return ""
        
def game_state_consistency(game_states: list[game_state.GameState]) -> tuple[Any, int]:
    jsons = [state.model_dump_json() for state in game_states]
    state_counts = {}
    for state_json in jsons:
        state_counts[state_json] = state_counts.get(state_json, 0) + 1
    max_value = max(state_counts.items(), key=lambda x: x[1])[0]
    return game_states[jsons.index(max_value)], jsons.index(max_value)
    
def consistency(objects: list)->tuple[Any, int]:
    counts = {}
    for obj in objects:
        counts[obj] = counts.get(obj, 0) + 1
    max_value =  max(counts.items(), key=lambda x: x[1])[0]
    return max_value, objects.index(max_value)
    
python_tool_description = """Python code to execute to update game state. This code will execute in a context with variable `game_state` defined and game_state.py imported. This code should modify game_state in place. Before and after code is executed, game state is backed up. If code raises an exception, game state will be restored to its previous state. This code will only be executed once on the exact game state you can see, so you only need to check conditions in complex situations or when you need to read information that's hidden by default like players' libraries. You will see the printed output of this code, which you can use to eg look at cards in players' libraries."""


class GameMaster(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True,
        "ignore_bound_methods": True,
    }

    game_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    game_state: game_state.GameState
    agents: list["AgentInterface"] = Field(default_factory=list)
    generation_settings: dict
    past_game_states: list[game_state.GameState] = Field(default_factory=list)
    player_observation_histories: list[list[HistoryStep]] = Field(default_factory=list)
    
    priority_player: int = Field(default=0)
    player_action:str = Field(default="")
    invalid_action_feedback: Optional[str] = Field(default=None)
    winner: Optional[int] = Field(default=None)
    priority_player_revealed_information: str = Field(default="")
    priority_player_available_actions: str = Field(default="")
    
    used_python_code: list[str] = Field(default_factory=list)
    error_messages: list[str] = Field(default_factory=list)
    global_action_history: list[dict[str, int | str]] = Field(default_factory=list)
    code_local_vars: dict[str, Any] = Field(default_factory=dict)
    
    metadata: dict = Field(default_factory=dict)
    n_retries: int = Field(default=5)
    max_turns: int = Field(default=15)
    max_errors: int = Field(default=10)
    max_steps: int = Field(default=40)
    
    def model_post_init(self, *args, **kwargs):
        self.player_observation_histories = [[] for _ in self.agents]
        
    def truncated_json(self, **kwargs) -> str:
        game_master_copy = deepcopy(self)
        game_master_copy.past_game_states = game_master_copy.past_game_states[-5:]
        for history in game_master_copy.player_observation_histories:
            history[:] = history[-5:]
        return game_master_copy.model_dump_json(**kwargs)
        
    async def step(self):
        self.past_game_states.append(deepcopy(self.game_state))
        await self.game_master_step(self.player_action)
        try:
            log.save_game(self.game_id, self)
        except Exception:
            print("Failed to save game")
        if self.winner is not None:
            log.finish_game(self.game_id)
            return self.winner
        self.player_action = await self.get_player_action(self.priority_player, self.priority_player_available_actions, self.priority_player_revealed_information,self.invalid_action_feedback)
        print(prompting.format_omniscient_view(self.game_state))
        print(f"Player {self.priority_player} action: {self.player_action}")
        
    async def game_loop(self):
        while self.winner is None:
            await self.step()
            if self.game_state.turn_number > self.max_turns:
                print(f"Game timed out after {self.max_turns} turns")
                break    
            if len(self.error_messages) > self.max_errors:
                print(f"Game ended with too many errors: {len(self.error_messages)}")
                break
            if len(self.global_action_history) > self.max_steps:
                print(f"Game timed out after {len(self.global_action_history)} steps")
                break
        return self.winner
            
    async def get_player_action(self, player_index: int, available_actions: str, revealed_information: str, invalid_action_feedback: Optional[str]=None):
        player_view = prompting.format_player_view(self.game_state, player_index, revealed_information)
        player_action = await self.agents[player_index].take_action(self.player_observation_histories[player_index],player_view, available_actions, invalid_action_feedback)
        self.player_observation_histories[player_index].append(HistoryStep(visible_information=player_view, action=player_action, available_actions=available_actions))
        return player_action
        
    async def execute_action(self, action: str, consistency_n = 8):
        execute_action_messages, system_content = self.get_base_messages()
        execute_action_messages.insert(0, {"role": "system", "content": system_content})
        execute_action_messages.append({"role":"user", "content":f"Player validate whether the action player {self.priority_player} wants to take is valid. If it is, advance the game state according to the action.\nAction: {action}"})
        execute_action_tools = {
            "tools": [{
                "name": "advance_game_state",
                "description": "Advance the game state according to the rules of Magic: The Gathering. First validate that the last player action was legal. If it was, execute the action and update the game state. If it was not, return an explanation of why it was illegal.",
                "input_schema": {
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
                            "description": python_tool_description
                        },
                    },
                    "required": ["reasoning", "is_action_valid", "python_code"]
                }
            }],
            "tool_choice": {"type": "tool", "name": "advance_game_state"}
        }
        for _ in range(self.n_retries):
            response = await log.llm_generate(
                messages=execute_action_messages,
                **self.generation_settings,
                **execute_action_tools
            )
            choice_jsons = [tool_use.input for tool_use in response.choices[0].message.tool_uses]
            majority_valid = consistency([choice["is_action_valid"] for choice in choice_jsons])[0]
            if not majority_valid:
                return False, next(c["invalid_action_feedback"] for c in choice_jsons if c["invalid_action_feedback"])
            valid_codes = [choice["python_code"] for choice in choice_jsons if choice["is_action_valid"]]
            evaluation_results = [await self.execute_code_with_game_state(code, apply_changes=False) for code in valid_codes]
            if not any([result[0] for result in evaluation_results]):
                execute_action_messages.append({"role":"user", "content":f"The code to execute to advance the game state raised an exception. State was restored to before the action was executed. Please fix the code and try again.\nException: {evaluation_results[0][1]}"})
                continue
            
            valid_states = [x[2] for x in evaluation_results if x[0]]
            valid_state_codes = [choice_jsons[i]["python_code"] for i, x in enumerate(evaluation_results) if x[0]]
            chosen_state, chosen_index = game_state_consistency(valid_states)
            self.game_state = chosen_state
            self.used_python_code.append(valid_state_codes[chosen_index])
            return True, ""
                
    async def advance_game_to_next_priority(self, consistency_n = 8):
        advance_game_state_messages, system_content = self.get_base_messages()
        advance_game_state_messages.insert(0, {"role": "system", "content": system_content})
    
        advance_state_tools = {
            "tools": [{
                "name": "advance_game_state",
                "description": "Advance the game state according to the rules of Magic: The Gathering to the next time a player will get priority and be able to take an action.",
                "input_schema": {
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
            "tool_choice": {"type": "tool", "name": "advance_game_state"}
        }
        
        advance_game_state_messages.append({"role":"user", "content":"Please identify the next time an player will get priority and be able to take an action, and advance the game to that point. Advancing the game state involves setting the active_player and turn_step properties of game_state, as well as untapping permanents, drawing cards, clearing damage, resolving any triggered abilities that do not involve player choices, etc. Please skip over multiple steps if no players will have available actions, eg executing untap, upkeep, and draw steps and skipping to main phase if no player has instant speed actions available."})
        for _ in range(self.n_retries):
            response = await log.llm_generate(
                messages=advance_game_state_messages,
                **self.generation_settings,
                **advance_state_tools
            )
            
            choice_jsons = [tool_use.input for tool_use in response.choices[0].message.tool_uses]
                
            evaluation_results = [await self.execute_code_with_game_state(choice["python_code"], apply_changes=False) for choice in choice_jsons]
            if not any([result[0] for result in evaluation_results]):
                advance_game_state_messages.append({"role":"user", "content":f"The code to execute to advance the game state raised an exception. State was restored to before the action was executed. Please fix the code and try again.\nException: {evaluation_results[0][1]}"})
                continue
            
            valid_states = [x[2] for x in evaluation_results if x[0]]
            valid_state_codes = [choice_jsons[i]["python_code"] for i, x in enumerate(evaluation_results) if x[0]]
            chosen_state, chosen_index = game_state_consistency(valid_states)
            self.game_state = chosen_state
            self.used_python_code.append(valid_state_codes[chosen_index])
            self.priority_player = choice_jsons[chosen_index]["priority_player"]
            return
        
    async def analyze_state_at_priority(self):
        analyze_state_messages, system_content = self.get_base_messages()
        analyze_state_messages.insert(0, {"role": "system", "content": system_content})
        analyze_state_messages.append({"role":"user", "content":"Please analyze the current game state and describe what actions are available to the player who currently has priority."})

        analyze_state_tools = {
            "tools": [{
                "name": "extract_state_info",
                "description": "Extract key information about the current game state",
                "input_schema": {
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
            "tool_choice": {"type": "tool", "name": "extract_state_info"}
        }
        for _ in range(self.n_retries):
            response = await log.llm_generate(
                messages=analyze_state_messages,
                **self.generation_settings,
                **analyze_state_tools
            )
            
            result = response.choices[0].message.tool_uses[0].input
            required_fields = ["reasoning", "priority_player", "priority_player_revealed_information", "priority_player_available_mana", "priority_player_available_actions", "winner"]
            if not all(field in result for field in required_fields):
                analyze_state_messages.append({"role":"user", "content":f"The response is missing required fields. Please include all of: {required_fields}"})
                continue
            return result
        
    async def game_master_step(self, action: str):
        if action != "":
            is_action_valid, invalid_action_feedback = await self.execute_action(action)
            if not is_action_valid:
                self.invalid_action_feedback = invalid_action_feedback
                self.error_messages.append(f"Player {self.priority_player} action was invalid: \n\n{action} \n\nInvalid reason: {invalid_action_feedback}")
                return
            self.global_action_history.append(
                {
                    "player_index": self.priority_player,
                    "action": action
                }
            )
        await self.advance_game_to_next_priority()
        analyzed_state = await self.analyze_state_at_priority()
        if analyzed_state.get("winner") is not None:
            self.winner = analyzed_state["winner"]
        self.priority_player = analyzed_state["priority_player"]
        self.priority_player_available_actions = analyzed_state["priority_player_available_actions"]
        self.priority_player_revealed_information = analyzed_state["priority_player_revealed_information"]
        
    def get_base_messages(self):
        omniscient_view = prompting.format_omniscient_view(self.game_state)
        game_state_code = open("game_state.py").read()
        global_action_history = "\n".join([f"Player {action['player_index']}: {action['action']}" for action in self.global_action_history])
        used_python_code = "\n".join(self.used_python_code)
        
        system_content = f"""You are an expert Magic: The Gathering judge. Your job is to enforce the rules of a Magic: The Gathering game played by two players who interact through natural language text. You track the state of the game using a Python API.

Game Phase reminder:
{prompts.game_phase_guide}

Here are the python classes that hold the game state:
{game_state_code}"""
        
        messages = [
            {"role":"user", "content":f"""
Current Game State:
{omniscient_view}"""},
            {"role":"user", "content":f"""
Here are all the actions agents have taken in this game:
{global_action_history}
"""},
            {"role":"user", "content":f"""
Here is all the python code that you have used to execute actions and advance game state so far:
{used_python_code}
"""},
        ]
        return messages, system_content

    async def execute_code_with_game_state(self, code: str, apply_changes: bool = True) -> tuple[bool, str, game_state.GameState]:

        f = io.StringIO()
        new_game_state = deepcopy(self.game_state)
        global_vars = {name: getattr(game_state, name) for name in dir(game_state) if not name.startswith('_')}
        self.code_local_vars['game_state'] = new_game_state
        
        try:
            with redirect_stdout(f):
                exec(code, global_vars, self.code_local_vars)
            if apply_changes:
                self.used_python_code.append(code)
                self.game_state = new_game_state
            return True, f.getvalue(), new_game_state
        except Exception:
            error_trace = traceback.format_exc()
            self.error_messages.append(f"Code execution failed\nCode:\n{code}\n\nError:\n{error_trace}")
            return False, error_trace, new_game_state