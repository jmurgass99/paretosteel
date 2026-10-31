"""Tests for consolidated profile reuse matching in ParetoSteel."""
import pytest
from paretosteel.reuse import DemandItem, InventoryItem, match_reuse


def test_greedy_reuse_matching_exact():
    demands = [DemandItem(id="D1", required=100.0), DemandItem(id="D2", required=150.0)]
    inventory = [
        InventoryItem(id="INV1", capacity=110.0, embodied_carbon_saved=25.0),
        InventoryItem(id="INV2", capacity=180.0, embodied_carbon_saved=40.0),
        InventoryItem(id="INV3", capacity=90.0, embodied_carbon_saved=20.0),
    ]
    res = match_reuse(demands, inventory)
    assert res.matched_demands == 2
    assert res.unmatched_demands == 0
    assert res.reuse_ratio == 1.0
    assert res.total_embodied_carbon_saved == 65.0
    assert res.assignments[0].inventory_id == "INV1"
    assert res.assignments[1].inventory_id == "INV2"
