export interface CardInfo {
  name: string;
  manaCost?: string;
  manaValue?: number;
  power?: number | string;
  toughness?: number | string;
  text?: string;
  types?: string[];
}


export interface HistoryStep {
  visible_information: string;
  available_actions: string;
  action: string;
}

export interface DeckList {
  mainboard: Record<string, number>;
  sideboard: Record<string, number>;
}

export interface BattlefieldCard {
  battlefield_id: number;
  card: string;
  owner: number;
  counters: Record<string, number>;
  tapped: boolean;
  effects: string[];
  attached_to: number | null;
  marked_damage: number;
}

export interface PlayerBoard {
  library: string[];
  hand: string[];
  graveyard: string[];
  exile: string[];
  life: number;
  counters: Record<string, number>;
  battlefield: Record<number, BattlefieldCard>;
}

export enum TurnStep {
  UNTAP = "UNTAP",
  UPKEEP = "UPKEEP",
  DRAW = "DRAW",
  MAIN_1 = "MAIN_1",
  BEGIN_COMBAT = "BEGIN_COMBAT",
  DECLARE_ATTACKERS = "DECLARE_ATTACKERS",
  DECLARE_BLOCKERS = "DECLARE_BLOCKERS",
  FIRST_STRIKE_DAMAGE = "FIRST_STRIKE_DAMAGE",
  COMBAT_DAMAGE = "COMBAT_DAMAGE",
  END_COMBAT = "END_COMBAT",
  MAIN_2 = "MAIN_2",
  END = "END",
  CLEANUP = "CLEANUP"
}

export interface GameState {
  player_decklists: DeckList[];
  player_boards: PlayerBoard[];
  battlefield_ids: number[];
  stack: string[];
  next_battlefield_id: number;
  active_player_index: number;
  turn_step: TurnStep;
  turn_number: number;
}

export interface GameMaster {
  game_state: GameState;
  agents: AgentInterface[];
  generation_settings: Record<string, any>;
  step_callback?: () => void;
  past_game_states: GameState[];
  player_observation_histories: HistoryStep[][];
  priority_player: number;
  player_action: string;
  invalid_action_feedback: string | null;
  winner: number | null;
  priority_player_revealed_information: string;
  priority_player_available_actions: string;
}

export interface AgentInterface {
  take_action: (
    history: HistoryStep[],
    visible_information: string,
    available_actions: string,
    rules_violation_feedback?: string
  ) => Promise<string>;
}