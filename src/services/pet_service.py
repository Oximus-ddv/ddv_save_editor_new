"""
Pet service for handling pet-related logic
"""

LEVEL_TO_XP = {
    1: 0,
    2: 750,
    3: 2250,
    4: 4500,
    5: 7500
}

XP_TO_LEVEL = [
    (0, 749, 1),
    (750, 2249, 2),
    (2250, 4499, 3),
    (4500, 7499, 4),
    (7500, float('inf'), 5)
]

def get_xp_for_level(level: int) -> int:
    """Returns the minimum XP for a given level."""
    return LEVEL_TO_XP.get(level, 0)

def get_level_for_xp(xp: int) -> int:
    """Returns the level for a given XP value."""
    if xp >= 7500:
        return 5
    if xp >= 4500:
        return 4
    if xp >= 2250:
        return 3
    if xp >= 750:
        return 2
    return 1
