"""Anonymous, executable contracts for annual/monthly timing calculations."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "qizheng-siyu-expert/skills/qz-reader/scripts/calculate_periods.py"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
PALACE_NAMES = ["命宫", "财帛", "兄弟", "田宅", "男女", "奴仆", "夫妻", "疾厄", "迁移", "官禄", "福德", "相貌"]


def synthetic_chart():
    """Synthetic occupants, not a saved client chart."""
    occupants = {"辰": ["日"], "酉": ["月"], "申": ["金"], "未": ["木"], "午": ["水"],
                 "巳": ["火"], "卯": ["土"], "寅": ["计"], "丑": ["罗"], "子": ["炁"],
                 "亥": ["孛"], "戌": []}
    palaces = {BRANCHES[(9 - i) % 12]: {"name": name, "natal_stars": occupants[BRANCHES[(9 - i) % 12]]}
               for i, name in enumerate(PALACE_NAMES)}
    return {"birth_at": "1997-08-20T12:00:00+08:00", "palaces": palaces,
            "palace_limits": [{"start": "2018-09-17T01:00:00+08:00", "branch": "亥"}]}


class TimingPeriodsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert SCRIPT.exists(), "Timing feature is not implemented: calculate_periods.py is missing"
        spec = importlib.util.spec_from_file_location("qz_calculate_periods_under_test", SCRIPT)
        cls.api = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.api
        sys.path.insert(0, str(SCRIPT.parent))
        spec.loader.exec_module(cls.api)

    def test_xiaoxian_starts_at_birth_and_repeats_after_twelve_years(self):
        cases = [(1997, "酉"), (1998, "申"), (2008, "戌"), (2009, "酉"), (2026, "辰")]
        for year, want in cases:
            with self.subTest(year=year):
                self.assertEqual(self.api.xiaoxian_branch("酉", 1997, year), want)

    def test_yuexian_birth_month_anchor_and_reverse_direction(self):
        for month, want in [(1, "戌"), (6, "巳"), (7, "辰"), (8, "卯"), (12, "亥")]:
            with self.subTest(month=month):
                self.assertEqual(self.api.yuexian_branch("辰", 7, month), want)

    def test_invalid_formula_inputs_are_rejected(self):
        for month in [0, 13, -1, 1.5, True]:
            with self.subTest(month=month), self.assertRaises((ValueError, TypeError)):
                self.api.yuexian_branch("辰", 7, month)
        with self.assertRaises(ValueError):
            self.api.xiaoxian_branch("酉", 1997, 1996)
        with self.assertRaises(ValueError):
            self.api.feixian_branch("子", 0)
        with self.assertRaises(ValueError):
            self.api.xiaoxian_branch("未知", 1997, 2026)

    def test_feixian_yang_yin_and_six_year_repeat(self):
        cases = {"子": "子子午午辰申子子午午辰申子", "丑": "丑丑未未酉巳丑丑未未酉巳丑"}
        for base, want in cases.items():
            for year, branch in enumerate(want, 1):
                with self.subTest(base=base, year=year):
                    self.assertEqual(self.api.feixian_branch(base, year), branch)

    def test_solar_month_is_jie_month_not_calendar_or_lunar_month(self):
        cases = [("2026-01-20T12:00:00+08:00", 2025, 12, "丑"),
                 ("2026-07-12T12:00:00+08:00", 2026, 6, "未"),
                 ("2026-08-12T12:00:00+08:00", 2026, 7, "申")]
        for at, year, number, branch in cases:
            with self.subTest(at=at):
                result = self.api.solar_month(at)
                self.assertEqual((result["solar_year"], result["month_number"], result["month_branch"]),
                                 (year, number, branch))
                self.assertLessEqual(datetime.fromisoformat(result["start"]), datetime.fromisoformat(at))
                self.assertLess(datetime.fromisoformat(at), datetime.fromisoformat(result["end"]))
                self.assertTrue(result["start"].endswith("+08:00"))
                self.assertTrue(result["end"].endswith("+08:00"))

    def test_month_changes_at_exact_returned_jie_time(self):
        august = self.api.solar_month("2026-08-12T12:00:00+08:00")
        boundary = datetime.fromisoformat(august["start"])
        self.assertEqual(august["start_term"], "立秋")
        self.assertEqual(august["end_term"], "白露")
        self.assertEqual(boundary.month, 8)
        self.assertIn(boundary.day, [7, 8])
        before = self.api.solar_month((boundary - timedelta(seconds=1)).isoformat())
        at = self.api.solar_month(boundary.isoformat())
        self.assertEqual(before["month_number"], 6)
        self.assertEqual(at["month_number"], 7)

    def test_xiaoxian_changes_at_lichun_not_january_first(self):
        chart = synthetic_chart()
        feb = self.api.solar_month("2026-02-10T12:00:00+08:00")
        boundary = datetime.fromisoformat(feb["start"])
        before = self.api.calculate_at((boundary - timedelta(seconds=1)).isoformat(), chart)
        after = self.api.calculate_at(boundary.isoformat(), chart)
        self.assertEqual(before["xiaoxian"]["branch"], "巳")
        self.assertEqual(after["xiaoxian"]["branch"], "辰")

    def test_birth_before_lichun_belongs_to_previous_solar_year(self):
        chart = synthetic_chart()
        chart["birth_at"] = "1998-01-20T12:00:00+08:00"
        result = self.api.calculate_at("2026-08-12T12:00:00+08:00", chart)
        self.assertEqual(result["xiaoxian"]["branch"], "辰")
        self.assertEqual(result["yuexian"]["branch"], "酉")

    def test_confirmed_summer_dates_and_natal_occupants(self):
        july = self.api.calculate_at("2026-07-12T12:00:00+08:00", synthetic_chart())
        august = self.api.calculate_at("2026-08-12T12:00:00+08:00", synthetic_chart())
        self.assertEqual(july["xiaoxian"]["branch"], "辰")
        self.assertEqual(july["xiaoxian"]["name"], "奴仆")
        self.assertEqual(july["xiaoxian"]["natal_stars"], ["日"])
        self.assertEqual(july["yuexian"]["branch"], "巳")
        self.assertEqual(july["yuexian"]["name"], "男女")
        self.assertEqual(july["yuexian"]["natal_stars"], ["火"])
        self.assertEqual(august["yuexian"]["branch"], "辰")

    def test_feixian_year_counts_solar_year_not_anniversary(self):
        chart = synthetic_chart()
        chart["palace_limits"] = [{"start": "2025-07-01T10:00:00+08:00", "branch": "子"}]
        first = self.api.calculate_at("2025-07-02T12:00:00+08:00", chart)
        second = self.api.calculate_at("2026-02-10T12:00:00+08:00", chart)
        self.assertEqual(first["feixian"]["year_number"], 1)
        self.assertEqual(second["feixian"]["year_number"], 2)
        self.assertEqual(second["feixian"]["branch"], "子")

    def test_feixian_has_no_lord_and_cycle_year_is_explicit(self):
        result = self.api.calculate_at("2026-08-12T12:00:00+08:00", synthetic_chart())
        flight = result["feixian"]
        self.assertEqual((flight["year_number"], flight["cycle_year"], flight["branch"]), (9, 3, "巳"))
        self.assertNotIn("lord", flight)
        self.assertEqual(flight["natal_stars"], ["火"])

    def test_missing_palace_limit_does_not_invent_feixian(self):
        chart = synthetic_chart()
        chart.pop("palace_limits")
        result = self.api.calculate_at("2026-08-12T12:00:00+08:00", chart)
        self.assertIsNone(result["feixian"])
        self.assertIsNone(result["palace_limit"])
        self.assertEqual(result["xiaoxian"]["branch"], "辰")

    def test_unknown_and_known_empty_natal_occupants_stay_distinct(self):
        chart = synthetic_chart()
        chart["palaces"]["辰"]["natal_stars"] = None
        result = self.api.calculate_at("2026-08-12T12:00:00+08:00", chart)
        self.assertIsNone(result["xiaoxian"]["natal_stars"])
        january = self.api.calculate_at("2026-02-20T12:00:00+08:00", chart)
        self.assertEqual(january["yuexian"]["natal_stars"], [])

    def test_birth_future_target_and_incoherent_palaces_are_rejected(self):
        with self.assertRaises(ValueError):
            self.api.calculate_at("1997-08-19T12:00:00+08:00", synthetic_chart())
        chart = synthetic_chart()
        chart["birth_at"] = "1997-08-20"
        with self.assertRaises(ValueError):
            self.api.calculate_at("2026-08-12T12:00:00+08:00", chart)
        chart = synthetic_chart()
        chart["palaces"]["辰"]["name"], chart["palaces"]["卯"]["name"] = "夫妻", "奴仆"
        with self.assertRaises(ValueError):
            self.api.calculate_at("2026-08-12T12:00:00+08:00", chart)

    def test_year_segments_cover_solar_year_without_gaps(self):
        result = self.api.calculate_year(2026, synthetic_chart())
        segments = result["segments"]
        self.assertEqual(len(segments), 12)
        self.assertEqual([s["solar_month"]["month_number"] for s in segments], list(range(1, 13)))
        self.assertEqual(segments[0]["solar_month"]["start_term"], "立春")
        self.assertEqual(segments[-1]["solar_month"]["end_term"], "立春")
        for left, right in zip(segments, segments[1:]):
            self.assertEqual(left["end"], right["start"])
        self.assertEqual(result["snapshots"], [])
        self.assertTrue(all(s["transit_snapshot"] is None for s in segments))

    def test_year_splits_at_actual_palace_and_degree_changes(self):
        chart = synthetic_chart()
        chart["palace_limits"].append({"start": "2026-07-01T10:00:00+08:00", "branch": "子"})
        chart["degree_limits"] = [{"start": "2020-07-01T10:00:00+08:00", "mansion": "斗"},
                                  {"start": "2026-08-20T15:00:00+08:00", "mansion": "女"}]
        result = self.api.calculate_year(2026, chart)
        segments = result["segments"]
        self.assertEqual(len(segments), 14)
        switch = next(s for s in segments if s["start"] == "2026-07-01T10:00:00+08:00")
        self.assertEqual(switch["palace_limit"]["branch"], "子")
        self.assertEqual(switch["feixian"]["year_number"], 1)
        degree = next(s for s in segments if s["start"] == "2026-08-20T15:00:00+08:00")
        self.assertEqual(degree["degree_limit"]["mansion"], "女")
        for left, right in zip(segments, segments[1:]):
            self.assertEqual(left["end"], right["start"])

    def test_transits_remain_separate_from_natal_occupants(self):
        chart = synthetic_chart()
        untouched = copy.deepcopy(chart)
        result = self.api.calculate_at("2026-08-12T12:00:00+08:00", chart, include_transits=True)
        self.assertEqual(chart, untouched)
        self.assertEqual(result["xiaoxian"]["natal_stars"], ["日"])
        self.assertEqual(len(result["transit_snapshot"]["stars"]), 11)
        self.assertNotIn("lord", result["feixian"])
        self.assertEqual(result["transit_snapshot"]["palaces"]["辰"]["natal_stars"], ["日"])

    def test_year_samples_are_instant_snapshots_not_year_long_transits(self):
        result = self.api.calculate_year(2026, synthetic_chart(), sample_times=["2026-08-12T12:00:00+08:00"])
        self.assertEqual(len(result["snapshots"]), 1)
        self.assertEqual(len(result["snapshots"][0]["transit_snapshot"]["stars"]), 11)
        self.assertTrue(all(s["transit_snapshot"] is None for s in result["segments"]))

    def test_cli_reads_private_input_from_stdin_without_creating_files(self):
        with tempfile.TemporaryDirectory(prefix="qz-timing-test-") as directory:
            proc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--at", "2026-08-12T12:00:00+08:00",
                                   "--input", "-", "--format", "json"], input=json.dumps(synthetic_chart()),
                                  text=True, capture_output=True, cwd=directory)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(result["yuexian"]["branch"], "辰")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_supplied_birth_month_must_agree_with_solar_terms(self):
        chart = synthetic_chart()
        chart["birth_month_branch"] = "未"
        with self.assertRaises(ValueError):
            self.api.calculate_at("2026-08-12T12:00:00+08:00", chart)
        chart["birth_month_branch"] = "申"
        result = self.api.calculate_at("2026-08-12T12:00:00+08:00", chart)
        self.assertEqual(result["yuexian"]["branch"], "辰")

    def test_limit_rows_cannot_be_reordered_or_duplicated_silently(self):
        for key, value_key, first, second in [("palace_limits", "branch", "亥", "子"),
                                              ("degree_limits", "mansion", "斗", "女")]:
            for bad_start in ["2018-09-17T01:00:00+08:00", "2018-09-16T01:00:00+08:00"]:
                chart = synthetic_chart()
                chart[key] = [{"start": "2018-09-17T01:00:00+08:00", value_key: first},
                              {"start": bad_start, value_key: second}]
                with self.subTest(key=key, start=bad_start), self.assertRaises(ValueError):
                    self.api.calculate_at("2026-08-12T12:00:00+08:00", chart)

    def test_expired_limit_schedule_preserves_xiaoxian_and_yuexian(self):
        chart = synthetic_chart()
        chart["degree_limits"] = [{"start": "2020-07-01T10:00:00+08:00", "mansion": "斗木"}]
        chart["limits_valid_until"] = "2026-08-12T12:00:00+08:00"
        before = self.api.calculate_at("2026-08-12T11:59:59+08:00", chart)
        expired = self.api.calculate_at("2026-08-12T12:00:00+08:00", chart)
        self.assertIsNotNone(before["feixian"])
        self.assertIsNotNone(before["palace_limit"])
        self.assertIsNotNone(before["degree_limit"])
        self.assertIsNone(expired["feixian"])
        self.assertIsNone(expired["palace_limit"])
        self.assertIsNone(expired["degree_limit"])
        self.assertEqual(expired["xiaoxian"]["branch"], "辰")
        self.assertEqual(expired["yuexian"]["branch"], "辰")
        yearly = self.api.calculate_year(2026, chart)
        boundary = next(s for s in yearly["segments"] if s["start"] == chart["limits_valid_until"])
        self.assertIsNone(boundary["feixian"])

    def test_birth_year_segments_are_clipped_to_birth_instant(self):
        chart = synthetic_chart()
        result = self.api.calculate_year(1997, chart)
        self.assertEqual(result["meta"]["start"], chart["birth_at"])
        self.assertEqual(result["segments"][0]["start"], chart["birth_at"])
        self.assertEqual(result["segments"][0]["solar_month"]["month_number"], 7)
        self.assertEqual(len(result["segments"]), 6)
        self.assertEqual(result["segments"][0]["xiaoxian"]["branch"], "酉")
        with self.assertRaises(ValueError):
            self.api.calculate_year(1996, chart)

    def test_year_samples_reject_outside_solar_year_and_before_birth(self):
        for sample in ["2026-01-20T12:00:00+08:00", "2027-02-10T12:00:00+08:00"]:
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                self.api.calculate_year(2026, synthetic_chart(), sample_times=[sample])
        with self.assertRaises(ValueError):
            self.api.calculate_year(1997, synthetic_chart(), sample_times=["1997-08-19T12:00:00+08:00"])
        following_january = self.api.calculate_year(2026, synthetic_chart(),
                                                   sample_times=["2027-01-20T12:00:00+08:00"])
        self.assertEqual(following_january["snapshots"][0]["solar_month"]["month_number"], 12)

    def test_source_shensha_and_star_details_are_preserved_without_aliasing(self):
        chart = synthetic_chart()
        chart["palaces"]["辰"].update({"shensha": ["文昌", "天贵"],
                                        "annual_shensha": {"2025": ["天喜"], "2026": ["驿马"]},
                                        "source": {"label": "synthetic fixture"}})
        chart["natal_star_details"] = {"日": {"mansion": "张", "mansion_degree": 3.5,
                                               "roles": ["官禄主"], "source": {"line": 1}}}
        original = copy.deepcopy(chart)
        result = self.api.calculate_at("2026-08-12T12:00:00+08:00", chart)
        self.assertEqual(chart, original)
        self.assertEqual(result["xiaoxian"]["shensha"], ["文昌", "天贵"])
        self.assertEqual(result["xiaoxian"]["annual_shensha"], ["驿马"])
        self.assertEqual(result["xiaoxian"]["source"], {"label": "synthetic fixture"})
        self.assertEqual(result["natal_star_details"], original["natal_star_details"])
        result["xiaoxian"]["shensha"].append("changed")
        result["natal_star_details"]["日"]["roles"].append("changed")
        self.assertEqual(chart, original)
        self.assertEqual(result["yuexian"]["shensha"], ["文昌", "天贵"])

    def test_markdown_formats_real_single_and_year_results(self):
        at = "2026-08-12T12:00:00+08:00"
        point = self.api.calculate_at(at, synthetic_chart(), include_transits=True)
        point_md = self.api.to_markdown(point)
        self.assertIn(at, point_md)
        self.assertIn("辰·奴仆", point_md)
        self.assertIn("巳·男女", point_md)
        self.assertIn(point["solar_month"]["start"], point_md)
        year = self.api.calculate_year(2026, synthetic_chart(), sample_times=[at])
        year_md = self.api.to_markdown(year)
        self.assertIn(at, year_md)
        for segment in year["segments"]:
            self.assertIn(segment["start"], year_md)
            self.assertIn(segment["end"], year_md)

    def test_cli_rejects_incompatible_time_and_snapshot_options(self):
        incompatible = [["--at", "2026-08-12T12:00:00+08:00", "--year", "2026"],
                        ["--year", "2026", "--transits"],
                        ["--at", "2026-08-12T12:00:00+08:00", "--sample", "2026-08-12T12:00:00+08:00"]]
        for arguments in incompatible:
            with self.subTest(arguments=arguments):
                proc = subprocess.run([sys.executable, "-B", str(SCRIPT), *arguments, "--input", "-"],
                                      input=json.dumps(synthetic_chart()), text=True, capture_output=True)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")
                self.assertIn("error", proc.stderr)

    def test_cli_markdown_year_and_instant_are_usable_outputs(self):
        for arguments in [["--at", "2026-08-12T12:00:00+08:00", "--transits"],
                          ["--year", "2026", "--sample", "2026-08-12T12:00:00+08:00"]]:
            with self.subTest(arguments=arguments):
                proc = subprocess.run([sys.executable, "-B", str(SCRIPT), *arguments, "--input", "-", "--format", "md"],
                                      input=json.dumps(synthetic_chart()), text=True, capture_output=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("2026-08-12T12:00:00+08:00", proc.stdout)
                self.assertIn("辰·奴仆", proc.stdout)

    def test_hour_precision_first_birth_limit_is_normalized_only_with_explicit_provenance(self):
        chart = synthetic_chart()
        chart["birth_at"] = "1997-08-20T12:30:45+08:00"
        source_start = "1997-08-20T12:00:00+08:00"
        chart["palace_limits"] = [{"start": source_start, "branch": "酉", "start_precision": "hour"}]
        untouched = copy.deepcopy(chart)
        try:
            result = self.api.calculate_at(chart["birth_at"], chart)
        except ValueError as error:
            self.fail(f"An explicitly hour-precision first ming limit must be accepted: {error}")
        self.assertEqual(result["palace_limit"]["start"], chart["birth_at"])
        self.assertEqual(result["palace_limit"]["source_start"], source_start)
        self.assertEqual(result["feixian"]["year_number"], 1)
        self.assertEqual(result["feixian"]["branch"], "酉")
        self.assertEqual(chart, untouched)

        variants = []
        missing_precision = copy.deepcopy(chart)
        missing_precision["palace_limits"][0].pop("start_precision")
        variants.append(("unmarked earlier time", missing_precision))
        wrong_palace = copy.deepcopy(chart)
        wrong_palace["palace_limits"][0]["branch"] = "申"
        variants.append(("not natal ming palace", wrong_palace))
        later_row = copy.deepcopy(chart)
        later_row["palace_limits"].insert(0, {"start": chart["birth_at"], "branch": "酉"})
        variants.append(("not first row", later_row))
        for label, earlier in [("different hour", "1997-08-20T11:00:00+08:00"),
                               ("different day", "1997-08-19T12:00:00+08:00")]:
            invalid = copy.deepcopy(chart)
            invalid["palace_limits"][0]["start"] = earlier
            variants.append((label, invalid))
        for label, invalid in variants:
            with self.subTest(case=label), self.assertRaises(ValueError):
                self.api.calculate_at(invalid["birth_at"], invalid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
