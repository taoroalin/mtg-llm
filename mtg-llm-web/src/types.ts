export interface CardInfo {
  name: string;
  manaCost?: string;
  manaValue?: number;
  power?: number | string;
  toughness?: number | string;
  text?: string;
  types?: string[];
}

export interface BattlefieldCard {
  battlefield_id: number;
  card: string;
  owner: number;
  tapped: boolean;
  marked_damage: number;
}

export interface PlayerBoard {
  life: number;
  hand: string[];
  battlefield: Record<number, BattlefieldCard>;
  graveyard: string[];
  exile: string[];
}

export interface GameState {
  player_boards: PlayerBoard[];
  active_player_index: number;
  turn_step: string;
}