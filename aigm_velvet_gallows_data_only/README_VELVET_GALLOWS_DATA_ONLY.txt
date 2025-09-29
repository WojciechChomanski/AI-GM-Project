AI_GM_Project — Velvet Gallows Encounter Pack (DATA ONLY)

This pack DOES NOT change your code. It only adds JSON files so your existing system
has a ready-made scene and NPCs to use. You can delete these files any time.

It adds:
1) rules/encounters/velvet_gallows.json  -> scene, participants, simple social checks
2) rules/characters/bandit.json          -> basic bandit
3) rules/characters/bandit_leader.json   -> tougher bandit leader

How to install:
1) Unzip this pack into your project folder: H:\Code\AI_GM_Project
   (It will create /rules/encounters/ if missing and add the character files if missing.
    Existing files with the same name are left unchanged to avoid overwriting your work.)
2) You're done. No scripts were modified.

How to use (manual approach until we wire a runner):
- You can temporarily swap 'gorthak.json' with 'bandit_leader.json' to test your current battle_simulation.
- Or just keep these NPCs for upcoming steps where we add a small "runner" script to load this encounter
  without altering your engine.

Safe by design:
- This pack NEVER overwrites existing files. If a file exists, it is left untouched.
