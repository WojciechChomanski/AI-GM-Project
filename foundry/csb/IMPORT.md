# How to drop these onto the general sheet

Foundry cannot invent a CSB item template id for you. Do this once.

1. In your Breath world, create an Item of type Equippable Item Template.
2. Name it exactly Breath Class.
3. Add Number / Text fields whose keys match the contract (class_id, class_strength, show_veil_block, and the rest).
4. Open each JSON in this folder, create an Equippable Item from that template, tick Make item unique, set Unique Id to breath_class.
5. Paste the system.props values from the JSON into that item.
6. Drag one Class item onto a blank Breath actor.

Until the slim actor template exists, the numbers will sit on the item even if the actor face is still empty. That is expected.

Do not import Divine Smite or Divine_Surge as clickable actions on the Knight.
