"""The annual workflow must have an executable calculation entrypoint."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'qizheng-siyu-expert/skills/qz-reader/scripts/calculate_periods.py'


class EntrypointTests(unittest.TestCase):
    def test_month_anchor_and_reverse_count(self):
        self.assertTrue(SCRIPT.is_file(), '缺少年运三限计算入口')
        spec = importlib.util.spec_from_file_location('periods_entry_test', SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.yuexian_branch('辰', 7, 6), '巳')
        self.assertEqual(mod.yuexian_branch('辰', 7, 7), '辰')
        self.assertEqual(mod.xiaoxian_branch('酉', 1997, 2026), '辰')


if __name__ == '__main__':
    unittest.main()
