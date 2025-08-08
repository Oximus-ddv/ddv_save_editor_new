"""
Augmentation helpers to safely add items (clothes, houses, NPC skins) to a DDV save dict
without overwriting unrelated data.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Set, Tuple


RE_CS_INT_ENTRY = re.compile(r"\{\s*(\d{5,9})\s*,\s*\".*?\"\s*\}")


def parse_ids_from_csharp_dict(cs_path: Path) -> Set[int]:
    text = cs_path.read_text(encoding="utf-8", errors="ignore")
    ids: Set[int] = set()
    for m in RE_CS_INT_ENTRY.finditer(text):
        try:
            ids.add(int(m.group(1)))
        except ValueError:
            continue
    return ids


def _get_inventory_dict(root: Dict[str, Any], inventory_id: str) -> Dict[str, Any]:
    player = root.setdefault("Player", {})
    list_inventories = player.setdefault("ListInventories", {})
    inv = list_inventories.setdefault(inventory_id, {})
    inventory = inv.setdefault("Inventory", {})
    return inventory


def add_items_to_inventory(
    inventory: Dict[str, Any],
    item_ids: Iterable[int],
    amount: int,
    mode: str,
) -> Tuple[int, int, int]:
    added = 0
    replaced = 0
    skipped = 0
    for item_id in item_ids:
        key = str(item_id)
        if key in inventory:
            if mode == "overwrite":
                old = inventory.get(key)
                new_val = {"Amount": amount}
                if old != new_val:
                    replaced += 1
                else:
                    skipped += 1
                inventory[key] = new_val
            else:
                skipped += 1
        else:
            inventory[key] = {"Amount": amount}
            added += 1
    return added, replaced, skipped


def augment_save_dict(
    save_dict: Dict[str, Any],
    *,
    add_clothes: bool,
    add_houses: bool,
    add_skins: bool,
    inventory_for_clothes: str = "1",
    inventory_for_houses: str = "5",
    inventory_for_skins: str = "7",
    amount: int = 1,
    mode: str = "missing-only",
    clothes_cs_path: Path | None = None,
    houses_cs_path: Path | None = None,
    skins_cs_path: Path | None = None,
) -> Dict[str, int]:
    """Augment a save dict in-place; returns counters per category and total."""

    summary = {
        "clothes_added": 0,
        "clothes_replaced": 0,
        "clothes_skipped": 0,
        "houses_added": 0,
        "houses_replaced": 0,
        "houses_skipped": 0,
        "skins_added": 0,
        "skins_replaced": 0,
        "skins_skipped": 0,
    }

    if add_clothes and clothes_cs_path and clothes_cs_path.exists():
        ids = parse_ids_from_csharp_dict(clothes_cs_path)
        inv = _get_inventory_dict(save_dict, inventory_for_clothes)
        a, r, s = add_items_to_inventory(inv, ids, amount, mode)
        summary["clothes_added"] = a
        summary["clothes_replaced"] = r
        summary["clothes_skipped"] = s

    if add_houses and houses_cs_path and houses_cs_path.exists():
        ids = parse_ids_from_csharp_dict(houses_cs_path)
        inv = _get_inventory_dict(save_dict, inventory_for_houses)
        a, r, s = add_items_to_inventory(inv, ids, amount, mode)
        summary["houses_added"] = a
        summary["houses_replaced"] = r
        summary["houses_skipped"] = s

    if add_skins and skins_cs_path and skins_cs_path.exists():
        ids = parse_ids_from_csharp_dict(skins_cs_path)
        inv = _get_inventory_dict(save_dict, inventory_for_skins)
        a, r, s = add_items_to_inventory(inv, ids, amount, mode)
        summary["skins_added"] = a
        summary["skins_replaced"] = r
        summary["skins_skipped"] = s

    return summary


