"""
Pet service for handling pet-related logic
"""

LEVEL_TO_XP = {
    1: 0,
    2: 750,
    3: 2250,
    4: 4500,
    5: 7500,
    6: 11250,
    7: 15000,
    8: 22500,
    9: 30000,
    10: 45000
}

FRIENDSHIP_LEVEL_TO_XP = {
    1: 0,
    2: 100,
    3: 250,
    4: 500,
    5: 1000,
    6: 1500,
    7: 2000,
    8: 2500,
    9: 3000,
    10: 5000
}

def get_xp_for_level(level: int) -> int:
    """Returns the minimum XP for a given level."""
    return LEVEL_TO_XP.get(level, 0)

def get_level_for_xp(xp: int) -> int:
    """Returns the level for a given XP value."""
    if xp >= 45000:
        return 10
    if xp >= 30000:
        return 9
    if xp >= 22500:
        return 8
    if xp >= 15000:
        return 7
    if xp >= 11250:
        return 6
    if xp >= 7500:
        return 5
    if xp >= 4500:
        return 4
    if xp >= 2250:
        return 3
    if xp >= 750:
        return 2
    return 1

def get_xp_for_friendship_level(level: int) -> int:
    """Returns the minimum XP for a given friendship level."""
    return FRIENDSHIP_LEVEL_TO_XP.get(level, 0)

def get_friendship_level_for_xp(xp: int) -> int:
    """Returns the friendship level for a given XP value."""
    if xp >= 5000:
        return 10
    if xp >= 3000:
        return 9
    if xp >= 2500:
        return 8
    if xp >= 2000:
        return 7
    if xp >= 1500:
        return 6
    if xp >= 1000:
        return 5
    if xp >= 500:
        return 4
    if xp >= 250:
        return 3
    if xp >= 100:
        return 2
    return 1
