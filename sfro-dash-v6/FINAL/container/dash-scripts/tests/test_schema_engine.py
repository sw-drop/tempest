#!/usr/bin/env python3
import unittest
from unittest.mock import patch, mock_open
from datetime import datetime, timezone
import sys
import os

# Add parent dir to path to import schema_engine
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import schema_engine

class TestSchemaEngine(unittest.TestCase):

    def setUp(self):
        # Override paths for testing
        schema_engine.OVERRIDE_PATH = "/tmp/test_override.json"
        schema_engine.ROOF_PATH = "/tmp/test_roof.json"
        schema_engine.OUT_PATH = "/tmp/test_active_schema.json"

    @patch('schema_engine.datetime')
    @patch('schema_engine.get_actual_roof_state')
    @patch('schema_engine.get_forecast_roof_prospect')
    @patch('os.path.exists')
    def test_schema_matrix(self, mock_exists, mock_forecast_prospect, mock_roof_state, mock_datetime):
        # Disable override file
        mock_exists.return_value = False
        
        # Helper to run a test case
        def assert_schema(hour, roof_state, forecast_prospect, expected_schema):
            mock_datetime.now.return_value = datetime(2026, 7, 15, hour, 0, tzinfo=timezone.utc)
            mock_roof_state.return_value = roof_state
            mock_forecast_prospect.return_value = forecast_prospect
            result = schema_engine.evaluate_schema()
            self.assertEqual(result, expected_schema, f"Failed at hour {hour}, roof={roof_state}, forecast={forecast_prospect}")

        # --- 00:00 to 06:00 ---
        # RoofOpenNight1: roof open, or forecast to be open
        assert_schema(3, True, False, "RoofOpenNight1")
        assert_schema(3, False, True, "RoofOpenNight1")
        # RoofClosedNight1: roof closed AND forecast closed
        assert_schema(3, False, False, "RoofClosedNight1")

        # --- 06:00 to 09:00 ---
        assert_schema(7, True, False, "RoofOpenDawn1")
        assert_schema(7, False, False, "RoofClosedDawn1")

        # --- 09:00 to 12:00 ---
        assert_schema(10, False, True, "RoofOpenMorning1")
        assert_schema(10, False, False, "RoofClosedMorning1")

        # --- 12:00 to 15:00 ---
        assert_schema(13, True, True, "RoofOpenLunch1")
        assert_schema(13, False, False, "RoofClosedLunch1")

        # --- 15:00 to 18:00 ---
        # Afternoon1 ignores roof state/forecast
        assert_schema(16, True, True, "Afternoon1")
        assert_schema(16, False, False, "Afternoon1")

        # --- 18:00 to 21:00 ---
        # Supper1 ignores roof state/forecast
        assert_schema(19, True, True, "Supper1")
        assert_schema(19, False, False, "Supper1")

        # --- 21:00 to 23:59 ---
        assert_schema(22, True, False, "RoofOpenEvening1")
        assert_schema(22, False, True, "RoofOpenEvening1")
        assert_schema(22, False, False, "RoofClosedEvening1")

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"override": "Supper1"}')
    def test_override(self, mock_file, mock_exists):
        mock_exists.return_value = True
        self.assertEqual(schema_engine.evaluate_schema(), "Supper1")

if __name__ == '__main__':
    unittest.main()
