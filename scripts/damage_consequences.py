import random

class DamageConsequences:
    def __init__(self):
        self.consequences = {
            "slashing": {
                (1, 20): {
                    "effect": "Minor Laceration",
                    "description": "A shallow slash tears the skin, blood trickling down in thin rivulets.",
                    "pain": 3, "stress": 5, "bleeding": 0.3
                },
                (21, 40): {
                    "effect": "Deep Cut",
                    "description": "The blade carves a deep gash, exposing raw muscle as blood spurts with each heartbeat.",
                    "pain": 6, "stress": 10, "bleeding": 0.6
                },
                (41, 60): {
                    "effect": "Severed Muscle",
                    "description": "A brutal swing severs muscle fibers, leaving the limb twitching and useless, blood pooling beneath.",
                    "pain": 9, "stress": 15, "bleeding": 1.2, "mobility_penalty": 10
                },
                (61, 80): {
                    "effect": "Artery Slashed",
                    "description": "The blade slices an artery, unleashing a crimson fountain that sprays across the battlefield.",
                    "pain": 12, "stress": 20, "bleeding": 2.4
                },
                (81, 100): {
                    "effect": "Limb Severed",
                    "description": "With a sickening crunch, the blade cleaves through bone, sending the severed limb spinning away in a spray of gore.",
                    "pain": 15, "stress": 25, "bleeding": 3.6, "mobility_penalty": 25
                }
            },
            "piercing": {
                (1, 20): {
                    "effect": "Puncture Wound",
                    "description": "The point pierces flesh, leaving a neat hole that weeps blood slowly.",
                    "pain": 3, "stress": 5, "bleeding": 0.3
                },
                (21, 40): {
                    "effect": "Deep Stab",
                    "description": "The weapon plunges deep, blood bubbling around the embedded blade as it’s wrenched free.",
                    "pain": 6, "stress": 10, "bleeding": 0.6
                },
                (41, 60): {
                    "effect": "Organ Puncture",
                    "description": "A precise thrust skewers an organ, blood and bile mixing in a gruesome torrent.",
                    "pain": 9, "stress": 15, "bleeding": 1.2
                },
                (61, 80): {
                    "effect": "Internal Bleeding",
                    "description": "The stab tears internal vessels, blood pooling invisibly, each breath a labored gasp.",
                    "pain": 12, "stress": 20, "bleeding": 2.4
                },
                (81, 100): {
                    "effect": "Critical Organ Hit",
                    "description": "The blade impales a vital organ, blood gushing as the victim collapses, life fading fast.",
                    "pain": 15, "stress": 25, "bleeding": 3.6, "collapse": True
                }
            },
            "blunt": {
                (1, 20): {
                    "effect": "Bruise",
                    "description": "A heavy blow leaves a purpling bruise, tender and throbbing with each movement.",
                    "pain": 3, "stress": 5
                },
                (21, 40): {
                    "effect": "Fractured Bone",
                    "description": "The impact cracks bone, sending sharp pain lancing through with every step.",
                    "pain": 6, "stress": 10, "mobility_penalty": 10
                },
                (41, 60): {
                    "effect": "Broken Bone",
                    "description": "A sickening snap echoes as bone shatters, the limb dangling uselessly.",
                    "pain": 9, "stress": 15, "mobility_penalty": 20
                },
                (61, 80): {
                    "effect": "Crushed Tissue",
                    "description": "The blow pulverizes flesh, leaving a mangled, swollen mass of ruined tissue.",
                    "pain": 12, "stress": 20, "mobility_penalty": 25
                },
                (81, 100): {
                    "effect": "Shattered Bone",
                    "description": "The weapon crushes bone to splinters, the limb collapsing in a grotesque ruin.",
                    "pain": 15, "stress": 25, "mobility_penalty": 30, "collapse": True
                }
            }
        }

    def apply_consequence(self, character, body_part, damage_type, excess_damage):
        if damage_type not in self.consequences:
            print(f"⚠️ Unknown damage type: {damage_type}")
            return
        roll = random.randint(1, 100) + excess_damage
        roll = min(100, max(1, roll))
        for (low, high), effect in self.consequences[damage_type].items():
            if low <= roll <= high:
                print(f"💥 {character.name}'s {body_part} suffers: {effect['effect']}!")
                print(f"🩸 {effect['description']}")
                character.pain_penalty += effect.get("pain", 0)
                character.stress_level += effect.get("stress", 0)
                character.bleeding += effect.get("bleeding", 0)
                if "mobility_penalty" in effect:
                    character.mobility_penalty += effect["mobility_penalty"]
                if effect.get("collapse", False):
                    character.exhausted = True
                    character.last_action = True
                    character.in_combat = False
                    print(f"💀 {character.name} collapses from injury!")
                if body_part in ["head", "throat"] and effect["effect"] in ["Limb Severed", "Artery Slashed", "Critical Organ Hit", "Shattered Bone"]:
                    character.alive = False
                    character.in_combat = False
                    print(f"💀 {character.name} is killed instantly by a catastrophic {body_part} injury!")
                break