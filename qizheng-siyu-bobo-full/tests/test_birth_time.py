"""Historical clock/DST checks; fixtures are public clock transitions, not charts."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'qizheng-siyu-expert/skills/qz-reader/scripts/check_birth_time.py'


class BirthTimeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'Birth-time DST checker is not implemented')
        spec = importlib.util.spec_from_file_location('birth_time', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def check(self, local, zone='Asia/Shanghai', basis='civil'):
        return self.module.check_birth_time({'local_time': local, 'timezone': zone, 'time_basis': basis})

    def test_whole_summer_period_prompts_not_only_transition_day(self):
        r = self.check('1988-07-01T12:00:00')
        self.assertEqual(r['status'], 'unique')
        self.assertTrue(r['confirmation_required'])
        self.assertEqual(r['candidates'][0]['utc'], '1988-07-01T03:00:00+00:00')
        self.assertEqual(r['candidates'][0]['dst_seconds'], 3600)

    def test_historical_date_is_not_replaced_by_current_dst_policy(self):
        for stamp in ['1988-01-01T12:00:00', '2026-07-01T12:00:00']:
            with self.subTest(stamp=stamp):
                r = self.check(stamp)
                self.assertEqual(r['status'], 'unique')
                self.assertFalse(r['confirmation_required'])

    def test_repeated_clock_time_keeps_two_utc_candidates(self):
        r = self.check('2024-11-03T01:30:00', 'America/New_York')
        self.assertEqual(r['status'], 'ambiguous')
        self.assertTrue(r['confirmation_required'])
        self.assertEqual([x['utc'] for x in r['candidates']], ['2024-11-03T05:30:00+00:00', '2024-11-03T06:30:00+00:00'])

    def test_nonexistent_clock_time_is_not_silently_shifted(self):
        r = self.check('2024-03-10T02:30:00', 'America/New_York')
        self.assertEqual(r['status'], 'nonexistent')
        self.assertTrue(r['confirmation_required'])
        self.assertEqual(r['candidates'], [])
        self.assertEqual(r['local_time'], '2024-03-10T02:30:00')

    def test_dst_adjustment_is_not_assumed_one_hour(self):
        r = self.check('2024-12-01T12:00:00', 'Australia/Lord_Howe')
        self.assertEqual(r['candidates'][0]['dst_seconds'], 1800)
        self.assertTrue(r['confirmation_required'])

    def test_converted_times_are_not_reinterpreted_as_civil(self):
        for basis in ['standard', 'mean_solar', 'apparent_solar']:
            with self.subTest(basis=basis):
                r = self.check('1988-07-01T12:00:00', basis=basis)
                self.assertEqual(r['status'], 'basis_requires_review')
                self.assertEqual(r['candidates'], [])
                self.assertTrue(r['confirmation_required'])

    def test_unknown_timezone_does_not_mean_no_dst(self):
        r = self.check('1988-07-01T12:00:00', 'Invalid/Nowhere')
        self.assertEqual(r['status'], 'timezone_unknown')
        self.assertIsNone(r['dst_active'])
        self.assertTrue(r['confirmation_required'])

    def test_unknown_time_basis_requires_confirmation_even_outside_dst(self):
        r = self.check('2026-07-01T12:00:00', basis='unknown')
        self.assertTrue(r['confirmation_required'])
        self.assertIsNotNone(r['prompt'])
        self.assertFalse(r['dst_active'])

    def test_explicit_offset_and_date_only_are_rejected(self):
        for local in ['1988-07-01', '1988-07-01T12:00:00+08:00']:
            with self.subTest(local=local):
                with self.assertRaises(ValueError):
                    self.check(local)

    def test_cli_uses_stdin_stdout_without_writing_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-B', str(SCRIPT)], input=json.dumps({'local_time': '1988-07-01T12:00:00', 'timezone': 'Asia/Shanghai', 'time_basis': 'civil'}), text=True, capture_output=True, cwd=directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['confirmation_required'])
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
