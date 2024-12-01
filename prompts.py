game_phase_guide = """# Magic: The Gathering Turn Structure

## Beginning Phase

### 1. Untap Step
- Untap all tapped permanents you control
- No player can cast spells or activate abilities during this step
- Special abilities that trigger during untap step go on the stack at the beginning of upkeep

### 2. Upkeep Step
- Beginning of upkeep triggered abilities trigger
- Players can cast instants and activate abilities
- Many cumulative upkeep and other upkeep-triggered effects occur here

### 3. Draw Step
- Active player draws a card (except for the first turn of the game for the player who goes first)
- Players can cast instants and activate abilities after the draw

## Main Phase 1 (Pre-Combat Main Phase)
- Can play lands (one per turn unless modified by effects)
- Can cast spells of any type (creatures, sorceries, enchantments, artifacts, planeswalkers)
- Can activate abilities
- Can attach equipment or fortifications
- Combat hasn't occurred yet, so summoning creatures now allows them to attack this turn

## Combat Phase

### 1. Beginning of Combat Step
- Last chance to cast spells or activate abilities before attackers are declared
- "At beginning of combat" triggers occur

### 2. Declare Attackers Step
- Active player decides which creatures will attack and which player or planeswalker each will attack
- Creatures must be untapped to attack
- Tapping attacking creatures happens simultaneously
- After declarations, players can cast spells and activate abilities

### 3. Declare Blockers Step
- Defending player(s) declare which creatures will block and which attacking creatures they block
- Multiple blockers can be assigned to a single attacker
- After declarations, players can cast spells and activate abilities

### 4. First Strike Damage Step
- Skip this step if no creatures with first strike or double strike are attacking or blocking
- First strike damage is assigned and dealt (if applicable)
- All combat damage happens simultaneously within each damage step
- After damage is dealt, players can cast spells and activate abilities

### 4. Combat Damage Step
- Regular combat damage is assigned and dealt
- All combat damage happens simultaneously within each damage step
- After damage is dealt, players can cast spells and activate abilities

### 5. End of Combat Step
- Last chance to cast spells and activate abilities before combat ends
- "At end of combat" triggers occur
- Creatures remain "attacking" or "blocking" until this step ends

## Main Phase 2 (Post-Combat Main Phase)
- Second chance to play lands if you haven't played one yet
- Can cast spells of any type
- Can activate abilities
- Good time to play creatures you don't want to attack with
- Good time to play sorcery-speed effects after seeing how combat played out

## Ending Phase

### 1. End Step
- "At end of turn" or "at beginning of end step" triggers occur
- Last chance to cast spells and activate abilities before cleanup

### 2. Cleanup Step
- Active player discards down to maximum hand size (usually seven)
- All damage on creatures is removed
- "Until end of turn" and "this turn" effects end
- No player receives priority during this step unless a triggered ability goes on the stack
- If triggers occur, players get priority to respond, then another cleanup step begins

## Important Notes
- Priority passes between players in each step/phase (except Untap and most Cleanup steps)
- Each time a player would receive priority, state-based actions are checked first
- The active player receives priority first in each step/phase
- Players must pass priority in succession (with the stack empty) for a phase or step to end
- Some steps may be skipped if nothing happens during them (like combat steps if no creatures attack)

## Common Shortcuts in Practice
- Most players shortcut through unused steps/phases
- Common to combine untap/upkeep/draw unless there are relevant triggers
- Combat phase often shortened if there are no attacks
- Make sure to announce important phase changes to avoid confusion
"""

TURN_GUIDE = """
Beginning Phase:
1. Untap - Untap all permanents, no priority
2. Upkeep - Upkeep triggers, players get priority  
3. Draw - Active player draws, players get priority

Main Phase 1:
- Play lands (one per turn)
- Cast spells
- Activate abilities

Combat Phase:
1. Beginning of Combat - Declare intent to attack
2. Declare Attackers - Choose attackers
3. Declare Blockers - Assign blocks
4. Combat Damage - First strike then regular damage
5. End of Combat - Final combat effects resolve

Main Phase 2:
- Second chance to play lands
- Cast spells
- Activate abilities

Ending Phase:
1. End Step - End of turn triggers
2. Cleanup - Active player discards down to 7 cards in hand of their choice, remove damage, end turn effects
"""
comprehensive_rules = open("assets/MagicCompRules.txt").read()
