# Grimdark AI-GM Project

**You are the last crusader in a world the gods have already abandoned.**

The Veil thins. Veilspawn claw through the cracks. Faith is the only shield — and even faith decays.

You play **exclusively** as a male human Crusader Knight (Templar / Holy Judge / Cleric vocation only). No exceptions. Ever.

### PERMANENT CORE RULES (rules/core_rules.txt — immutable)
- Player = always male human Crusader Knight + vocation  
- Breath abilities = **strictly passive** (triggered only by high piety + fighting Veilspawn/major enemies)  
- **No active magic, no spells, no Divine Smite** for any male class — ever  
- Active magic = female-only (Veil Sorceress exclusive)  
- Templar Vocation fixed:  
  - Holy Fury (passive): Kill enemy of faith → +1 damage stack, +5% crit (max 5)  
  - Crusader Charge (12 stamina): Bonus damage + knockdown (physical only)

### Grimdark Lore Inspirations
- Warhammer Fantasy Sigmarite crusades  
- Berserk (lone knight vs endless demons)  
- Bloodborne / Dark Souls (thinning Veil + hollowing decay)  
- Darkest Dungeon (time + relationship erosion)  

The world does not want you to win. It wants to watch you break.

### Core Engine (now fully live)
- `scripts/ai_gm_engine.py` — mandatory time-passing, piety decay, Holy Fury stacks, relationship decay  
- `rules/master_system_prompt.txt` — AI-GM instructions (references core_rules.txt on every load)  
- `rules/organic_relationships.txt` — affinity/trust/intimacy/loyalty with natural time decay  
- `rules/npc_memory.json` — persistent memory  

### How to Run
1. Open terminal in project root  
2. Run your console (`python main.py` or `gm_console.py`)  
3. Type **`start session`**  
4. Game begins in strict 2nd-person narrative with header:  
   **[Day X | Hour XX | Piety XX | Holy Fury stacks XX]**

*The Veil thins, Crusader… Play wisely. Or don’t. The world doesn’t care.*
