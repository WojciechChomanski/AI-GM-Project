# Grimdark AI-GM Project

**Strict, lore-heavy, time-aware AI Game Master for a grimdark fantasy world.**

You play **exclusively** as a male human Crusader Knight (Templar / Holy Judge / Cleric vocation only).

### PERMANENT CORE RULES (never break)
See `rules/core_rules.txt`

- Player = always male human Crusader Knight + vocation  
- Breath abilities = **strictly passive** (high piety + fighting Veilspawn/major enemies only)  
- **No active magic, no spells, no Divine Smite** for any male class — ever  
- Active magic = female-only (Veil Sorceress exclusive)  
- Templar Vocation fixed: Holy Fury (passive stacks on faith-kills, max 5) + Crusader Charge (physical only)  

### Core Engine
- `scripts/ai_gm_engine.py` → Mandatory time-passing, piety decay, Holy Fury passive stacks, relationship decay  
- `rules/master_system_prompt.txt` → AI-GM instructions (references core_rules.txt every response)  
- `rules/organic_relationships.txt` → NPC affinity/trust/intimacy/loyalty with natural time decay  
- `rules/npc_memory.json` → Persistent memory  

### How to Run
1. `cd` into the project folder  
2. Run your console (`python main.py` or `gm_console.py`)  
3. Type **`start session`**  
4. Game begins in strict 2nd-person with header:  
   **[Day X | Hour XX | Piety XX | Holy Fury stacks XX]**

*The Veil thins, Crusader… Play smart or face consequences.*
