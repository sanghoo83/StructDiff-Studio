"""
StructDiff Studio
Author: Noah Nam
Contact: n83.noah@gmail.com
Version: 0.5.0
Purpose: Regression tests for file pairing logic.
"""

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from structdiff.app import StructDiffStudioApp


class PairingModeTests(unittest.TestCase):
    def setUp(self):
        self.app = StructDiffStudioApp.__new__(StructDiffStudioApp)

    def test_exact_pairing_uses_same_document_id(self):
        left_files = [
            "ADELsbcOverlayDriftControl_ec4b4164-888f-496a-8b9b-5c3f4707bed1.xml",
            "ADELsbcOverlayDriftControl_a4db0d6c-f675-40b1-9946-f83de8a456dd.xml",
        ]
        right_files = [
            "ADELsbcOverlayDriftControl_8968eca6-eb71-4dd3-97d6-df1e12071443.xml",
            "ADELsbcOverlayDriftControl_a4db0d6c-f675-40b1-9946-f83de8a456dd.xml",
        ]

        pairs, unmatched_left, unmatched_right = self.app._build_exact_file_pairs(left_files, right_files)

        self.assertEqual(
            pairs,
            [
                (
                    "ADELsbcOverlayDriftControl_a4db0d6c-f675-40b1-9946-f83de8a456dd.xml",
                    "ADELsbcOverlayDriftControl_a4db0d6c-f675-40b1-9946-f83de8a456dd.xml",
                )
            ],
        )
        self.assertEqual(unmatched_left, ["ADELsbcOverlayDriftControl_ec4b4164-888f-496a-8b9b-5c3f4707bed1.xml"])
        self.assertEqual(unmatched_right, ["ADELsbcOverlayDriftControl_8968eca6-eb71-4dd3-97d6-df1e12071443.xml"])

    def test_candidate_pairing_compares_every_unmatched_combination(self):
        unmatched_left = [
            "ADELsbcOverlayDriftControl_ec4b4164-888f-496a-8b9b-5c3f4707bed1.xml",
            "ADELsbcOverlayDriftControl_a4db0d6c-f675-40b1-9946-f83de8a456dd.xml",
        ]
        unmatched_right = [
            "ADELsbcOverlayDriftControl_8968eca6-eb71-4dd3-97d6-df1e12071443.xml",
            "ADELsbcOverlayDriftControl_bbbbbbbb-eb71-4dd3-97d6-df1e12071443.xml",
        ]

        candidate_pairs = self.app._build_review_pairs(unmatched_left, unmatched_right)

        self.assertEqual(len(candidate_pairs), 4)
        self.assertEqual(
            candidate_pairs,
            [
                (
                    "ADELsbcOverlayDriftControl_a4db0d6c-f675-40b1-9946-f83de8a456dd.xml",
                    "ADELsbcOverlayDriftControl_8968eca6-eb71-4dd3-97d6-df1e12071443.xml",
                ),
                (
                    "ADELsbcOverlayDriftControl_a4db0d6c-f675-40b1-9946-f83de8a456dd.xml",
                    "ADELsbcOverlayDriftControl_bbbbbbbb-eb71-4dd3-97d6-df1e12071443.xml",
                ),
                (
                    "ADELsbcOverlayDriftControl_ec4b4164-888f-496a-8b9b-5c3f4707bed1.xml",
                    "ADELsbcOverlayDriftControl_8968eca6-eb71-4dd3-97d6-df1e12071443.xml",
                ),
                (
                    "ADELsbcOverlayDriftControl_ec4b4164-888f-496a-8b9b-5c3f4707bed1.xml",
                    "ADELsbcOverlayDriftControl_bbbbbbbb-eb71-4dd3-97d6-df1e12071443.xml",
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
