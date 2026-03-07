# Grimdark AI-GM Project

**You are the last crusader in a world the gods have already abandoned.**

The Veil thins. Veilspawn claw through the cracks. Faith is the only shield — and even faith decays.

You play **exclusively** as a male human Crusader Knight (Templar / Holy Judge / Cleric vocation only). No exceptions. Ever.

### PERMANENT CORE RULES (rules/core_rules.txt — immutable)
- Player = always male human Crusader Knight + vocation  
- Breath abilities = **strictly passive** (triggered only by high piety + fighting Veilspawn/major enemies)  
- **No active magic, no spells, no Divine Smite** for any male class — ever  
- Active magic = female-only (Veil Sorceress exclusive)

### Grimdark Lore Inspirations
- Berserk (lone knight vs endless demons)  
- Bloodborne / Dark Souls (thinning Veil + hollowing decay)  
- Darkest Dungeon (time + relationship erosion)  

The world does not want you to win. It wants to watch you break.

### Core Engine (now fully live)
- `scripts/ai_gm_engine.py` — mandatory time-passing, piety decay, relationship decay, Breath passive check
- `rules/master_system_prompt.txt` — AI-GM instructions (references core_rules.txt)
- `rules/organic_relationships.txt` — affinity/trust/intimacy/loyalty with natural time decay
- `rules/npc_memory.json` — persistent memory  

### How to Run (Console / API testing)
1. Open terminal in project root  
2. Run your console (`python gm_console.py` or `python main.py`)  
3. Chat with Elara Voss (clean wording only — no extra dots, exclamation marks, etc.)

*The Veil thins, Crusader… Play wisely. Or don’t. The world doesn’t care.*
