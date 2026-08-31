from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from bms_milstd2525 import canonical_unit_kind, unit_glyph_primitives, validate_symbol_contract
from render_bms_enemy_air_threat_map import add_origin_bullseye_references, compact_label_text, is_airbase_origin, origin_name
from synthesize_bms_briefing import waypoint_summary


class MilStd2525ContractTests(unittest.TestCase):
    def test_mechanized_infantry_is_one_integrated_glyph(self) -> None:
        primitives = unit_glyph_primitives("Motor Rifle")
        self.assertEqual(canonical_unit_kind("Motor Rifle"), "mechanized")
        self.assertEqual([item.kind for item in primitives].count("ellipse"), 1)
        self.assertEqual([item.kind for item in primitives].count("line"), 2)
        self.assertEqual(validate_symbol_contract(), [])

    def test_headquarters_uses_frame_staff_not_hq_text(self) -> None:
        self.assertEqual(unit_glyph_primitives("HQ"), ())


class AirbaseIdentityTests(unittest.TestCase):
    def test_coordinate_aligned_airbase_wins_over_stale_target_id(self) -> None:
        flight = {
            "waypoints": [
                {
                    "index": 0,
                    "action_name": "WP_TAKEOFF",
                    "target_id": {"num": 924},
                    "grid_x": 421.0,
                    "grid_y": 313.0,
                    "grid_z": 0.0,
                    "arrive": 0,
                    "depart": 0,
                }
            ]
        }
        objectives = {
            921: {"camp_id": 921, "name": "Seosan AB (RKTP)"},
            924: {"camp_id": 924, "name": "Pyeongtaek AAF (RKSG)"},
        }
        airbases = [
            {"camp_id": 921, "name": "Seosan AB (RKTP)", "grid_x": 421.6, "grid_y": 313.4, "objective_class": "Airbase"},
            {"camp_id": 924, "name": "Pyeongtaek AAF (RKSG)", "grid_x": 470.3, "grid_y": 341.6, "objective_class": "Airbase"},
        ]
        result = waypoint_summary(
            flight,
            None,
            objectives,
            {},
            {},
            {"by_key": {}, "by_num": {}},
            airbases,
        )
        target = result[0]["target"]
        self.assertEqual(target["camp_id"], 921)
        self.assertEqual(target["name"], "Seosan AB (RKTP)")
        self.assertEqual(target["identity_conflict"]["target_id"], 924)
        self.assertEqual(target["identity_conflict"]["resolved_airbase_id"], 921)


class OffshoreOriginLabelTests(unittest.TestCase):
    def test_offshore_group_uses_bullseye_not_raw_grid(self) -> None:
        origin = {
            "name": origin_name(761.0, 190.0, None),
            "grid_x": 761.0,
            "grid_y": 190.0,
            "aircraft": ["Su-33", "Su-39"],
        }
        add_origin_bullseye_references(
            [origin],
            [{"bullseye": {"grid_x": 686.0, "grid_y": 234.0}}],
        )

        self.assertEqual(origin["name"], "Offshore group")
        self.assertEqual(origin["bullseye_ref"], "BE 120/47")
        self.assertEqual(compact_label_text(origin), "S33, S39 | BE 120/47")
        self.assertNotIn("761/190", compact_label_text(origin))
        origin["airbase_id"] = 8055
        self.assertFalse(is_airbase_origin(origin))


if __name__ == "__main__":
    unittest.main()
