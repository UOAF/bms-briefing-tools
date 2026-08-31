from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from prepare_bms_community_publish import (
    discord_post,
    discover_mission_files,
    load_signup_packages,
    parse_hhmm,
)


class MissionFileInventoryTests(unittest.TestCase):
    def test_inventory_is_prefix_scoped_and_requires_ini(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            campaign_dir = Path(raw_dir)
            (campaign_dir / "744pre.cam").write_bytes(b"cam")
            (campaign_dir / "744pre.cam.backup-1").write_bytes(b"backup")
            (campaign_dir / "744pre.ini").write_text("ini", encoding="utf-8")
            (campaign_dir / "744prelude.txt").write_text("wrong", encoding="utf-8")
            (campaign_dir / "743pre.ini").write_text("wrong", encoding="utf-8")

            result = discover_mission_files(campaign_dir, "744pre")

        self.assertEqual([row["name"] for row in result], [
            "744pre.cam",
            "744pre.cam.backup-1",
            "744pre.ini",
        ])
        self.assertEqual(sum(bool(row["is_ini"]) for row in result), 1)
        self.assertTrue(all(len(row["sha256"]) == 64 for row in result))


class SignupPackageTests(unittest.TestCase):
    def test_extracts_requested_package_and_flight_rows(self) -> None:
        synthesis = {
            "focus_package_id": 6939,
            "packages": [{
                "package_id": 6939,
                "mission": "SEAD",
                "flights": [{
                    "callsign": "Plasma 3",
                    "mission": "DEAD",
                    "aircraft_type": "F-16CM-50",
                    "aircraft_count": 4,
                    "takeoff_hhmm": "1757Z",
                    "tot_hhmm": "1815Z",
                }],
            }],
        }
        with tempfile.TemporaryDirectory() as raw_dir:
            path = Path(raw_dir) / "briefing_synthesis.json"
            path.write_text(json.dumps(synthesis), encoding="utf-8")
            result = load_signup_packages([path], [6939])

        self.assertEqual(result[0]["seat_count"], 4)
        self.assertEqual(result[0]["flights"][0]["callsign"], "Plasma 3")


class DiscordPostTests(unittest.TestCase):
    def test_uses_actual_utc_event_datetime(self) -> None:
        post, timestamp, ready = discord_post(
            event_number="744",
            operation_name="Broken Quiver",
            event_date=date(2026, 9, 5),
            briefing_time=parse_hhmm("1800"),
            theater="KTO",
            bms_version="4.38.1",
            objectives="Suppress the corridor.",
            marshal_time=parse_hhmm("1745"),
            signup_url="https://docs.google.com/spreadsheets/d/example/edit",
        )
        self.assertEqual(timestamp, 1788631200)
        self.assertTrue(ready)
        self.assertIn("Saturday, 5 September 2026, <t:1788631200:t>", post)
        self.assertIn("Marshal: 1745z. Briefing: 1800z.", post)


if __name__ == "__main__":
    unittest.main()
