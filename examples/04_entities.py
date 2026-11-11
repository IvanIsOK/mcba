"""Entities, equipment, containers, spawners, and dropped items.

Targets Java 1.21.1 item/entity NBT (data version 3955):
- mobs still use HandItems / ArmorItems
- items inside those lists use id / count / components (1.20.5+ format)

Run directly:      python examples/04_entities.py
Through the CLI:   python -m mcba run examples/04_entities.py --out entities.litematic
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcba import Build, nbt

b = Build("entity_showcase", author="mcba", description="entities and items")

# Floor and a back wall
b.fill(0, 0, 0, 12, 0, 6, "smooth_stone")
b.walls(0, 1, 0, 12, 4, 6, "stone_bricks")
b.gable_roof(0, 0, 12, 6, 5, "spruce_planks")
b.door(6, 1, 0, "oak", facing="south")

# Fully equipped armor stand
b.add_entity("minecraft:armor_stand", 2.5, 1.0, 3.5, {
    "ShowArms": True,
    "NoBasePlate": True,
    "Pose": {
        "RightArm": [nbt.F(-80), nbt.F(0), nbt.F(0)],
        "LeftArm": [nbt.F(-80), nbt.F(0), nbt.F(0)],
    },
    "HandItems": [
        {
            "id": "minecraft:diamond_sword",
            "count": 1,
            "components": {
                "minecraft:custom_name": '{"text":"Guard Sword","italic":false}',
                "minecraft:enchantments": {
                    "levels": {"minecraft:sharpness": 5}
                },
                "minecraft:unbreakable": {},
            },
        },
        {},
    ],
    "ArmorItems": [
        {"id": "minecraft:diamond_boots", "count": 1},
        {"id": "minecraft:diamond_leggings", "count": 1},
        {"id": "minecraft:diamond_chestplate", "count": 1},
        {"id": "minecraft:diamond_helmet", "count": 1},
    ],
})

# A chest with custom components
b.chest_with_items(4, 1, 5, [
    {
        "slot": 0,
        "id": "minecraft:golden_apple",
        "count": 4,
        "components": {
            "minecraft:custom_name": '{"text":"Healing Fruit","italic":false}',
            "minecraft:lore": ['{"text":"Restores health","color":"gray"}'],
        },
    },
    {
        "slot": 1,
        "id": "minecraft:enchanted_book",
        "count": 1,
        "components": {
            "minecraft:stored_enchantments": {
                "levels": {"minecraft:mending": 1}
            },
        },
    },
])

# Mob spawner (only runs when a player is near and conditions are met)
b.spawner(8, 1, 5, "minecraft:zombie", spawn_data={
    "IsBaby": False,
    "CanBreakDoors": True,
}, count=2, min_delay=100, max_delay=400, required_player_range=16)

# A named villager with a profession
b.add_entity("minecraft:villager", 10.5, 1.0, 3.5, {
    "CustomName": '{"text":"Trader","italic":false}',
    "CustomNameVisible": True,
    "VillagerData": {
        "type": "minecraft:plains",
        "profession": "minecraft:librarian",
        "level": 3,
    },
    "PersistenceRequired": True,
})

# Dropped item entity (1.20.5+ item stack format)
b.add_entity("minecraft:item", 6.5, 1.2, 2.5, {
    "Item": {"id": "minecraft:diamond", "count": 3},
    "Age": nbt.S(0),
    "PickupDelay": nbt.S(10),
    "NoGravity": True,
})

# Chest minecart with items
b.add_entity("minecraft:chest_minecart", 1.5, 1.0, 1.5, {
    "Items": [
        {"Slot": nbt.B(0), "id": "minecraft:iron_ingot", "count": 16},
        {"Slot": nbt.B(1), "id": "minecraft:coal", "count": 32},
    ],
})

# Labels on the back wall
b.sign_text(2, 2, 5, ["Equipment"], facing="north")
b.sign_text(4, 2, 5, ["Chest"], facing="north")
b.sign_text(8, 2, 5, ["Spawner"], facing="north")
b.sign_text(10, 2, 5, ["Villager"], facing="north")

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "out")
    os.makedirs(out, exist_ok=True)
    b.save(os.path.join(out, "entity_showcase.litematic"))
    b.save(os.path.join(out, "entity_showcase.schem"))
    print(b.describe())
