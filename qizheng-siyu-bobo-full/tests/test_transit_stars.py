"""Anonymous regression fixtures: sky snapshots and synthetic palace mappings only."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'qizheng-siyu-expert/skills/qz-reader/scripts/calculate_transits.py'
spec = importlib.util.spec_from_file_location('transit_stars', SCRIPT)
transits = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transits)

BRANCHES = list('子丑寅卯辰巳午未申酉戌亥')
PALACES = ['命宫', '财帛', '兄弟', '田宅', '男女', '奴仆', '夫妻', '疾厄', '迁移', '官禄', '福德', '相貌']
AT = '2026-10-09T01:16:00+08:00'


def natal_mapping():
    # Deliberately synthetic: not a client's natal chart.
    return {'palaces': {b: {'name': p} for b, p in zip(BRANCHES, PALACES)}}


class TransitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = transits.calculate_snapshot(AT, mansion_profile='xhcl_original')

    def test_exactly_eleven_stars_and_no_extra_fields(self):
        self.assertEqual([s['name'] for s in self.snapshot['stars']], list('日月金木水火土计罗炁孛'))
        data = json.dumps(self.snapshot, ensure_ascii=False)
        for forbidden in ['xingguan', '星官', 'uranus', 'neptune', 'pluto']:
            self.assertNotIn(forbidden, data)
        self.assertEqual(self.snapshot['meta']['system'], '郑氏星案恒星制')
        self.assertEqual(self.snapshot['meta']['scope'], 'instant_snapshot')

    def test_independent_sky_fixture(self):
        # Supplied minute snapshot, rounded to 0.01 degree; no client identifiers.
        expected = {
            '日': ('辰', 1.30, '轸水', 10.30), '月': ('巳', 7.56, '翼火', 5.56),
            '金': ('辰', 23.77, '亢金', 3.77), '木': ('午', 6.79, '柳土', 10.79),
            '水': ('辰', 26.06, '亢金', 6.06), '火': ('未', 21.99, '井木', 30.99),
            '土': ('亥', 26.83, '壁水', 6.83), '计': ('子', 14.93, '虚日', 5.93),
            '罗': ('午', 14.93, '星日', 5.93), '炁': ('巳', 9.43, '翼火', 7.43),
            '孛': ('寅', 18.54, '箕水', 2.54),
        }
        for star in self.snapshot['stars']:
            with self.subTest(star=star['name']):
                branch, degree, mansion, within = expected[star['name']]
                self.assertEqual(star['branch'], branch)
                self.assertAlmostEqual(star['palace_degree'], degree, delta=0.02)
                self.assertEqual(star['mansion'], mansion)
                self.assertAlmostEqual(star['mansion_degree'], within, delta=0.02)

    def test_explicit_mansion_profiles_do_not_change_longitude(self):
        default = transits.calculate_snapshot(AT, mansion_profile='moira_sidereal')
        for original, other in zip(self.snapshot['stars'], default['stars']):
            self.assertEqual(original['sidereal_longitude'], other['sidereal_longitude'])
        self.assertAlmostEqual(default['stars'][0]['mansion_degree'] - self.snapshot['stars'][0]['mansion_degree'], 0.9)
        self.assertAlmostEqual(default['stars'][1]['mansion_degree'] - self.snapshot['stars'][1]['mansion_degree'], 0.6)

    def test_palace_boundaries_are_not_rounded_before_lookup(self):
        for angle, branch, within in [(0, '戌', 0), (29.9999999, '戌', 29.9999999),
                                      (30, '酉', 0), (359.9999999, '亥', 29.9999999),
                                      (360, '戌', 0), (-0.1, '亥', 29.9)]:
            with self.subTest(angle=angle):
                actual = transits.palace_position(angle)
                self.assertEqual(actual['branch'], branch)
                self.assertAlmostEqual(actual['palace_degree'], within)
        for invalid in [float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                transits.palace_position(invalid)

    def test_explicit_timezone_same_instant_and_seconds_preserved(self):
        utc = transits.calculate_snapshot('2026-10-08T17:16:00Z', mansion_profile='xhcl_original')
        self.assertEqual(utc['stars'], self.snapshot['stars'])
        one_second = transits.calculate_snapshot('2026-10-09T01:16:01+08:00')
        self.assertAlmostEqual((one_second['meta']['jd_ut'] - self.snapshot['meta']['jd_ut']) * 86400, 1, delta=0.0001)
        self.assertNotEqual(one_second['stars'][1]['sidereal_longitude'], self.snapshot['stars'][1]['sidereal_longitude'])

    def test_natal_mapping_is_an_overlay_and_keeps_unknown_distinct(self):
        natal = natal_mapping()
        natal['palaces']['辰']['natal_stars'] = ['月']
        natal['palaces']['巳']['natal_stars'] = []
        before = copy.deepcopy(natal)
        result = transits.calculate_snapshot(AT, natal=natal, focus=['辰', '奴仆'], mansion_profile='xhcl_original')
        self.assertEqual(natal, before)
        self.assertEqual(len(result['stars']), 11)
        self.assertEqual(result['palaces']['辰']['name'], '男女')
        self.assertEqual(result['palaces']['辰']['natal_stars'], ['月'])
        self.assertEqual(result['palaces']['辰']['transit_stars'], ['日', '金', '水'])
        self.assertEqual(result['palaces']['巳']['natal_stars'], [])
        self.assertIsNone(result['palaces']['未']['natal_stars'])
        self.assertEqual(result['focus_branches'], ['辰', '巳'])
        self.assertEqual(result['stars'][0]['natal_palace'], '男女')
        self.assertEqual(result['stars'][0]['sidereal_longitude'], self.snapshot['stars'][0]['sidereal_longitude'])

    def test_invalid_inputs_are_not_silently_repaired(self):
        for at in ['2026', '2026-10-09', '2026-10-09T01:16:00', '2026-02-30T01:00+08:00',
                   '2026-10-09T01+08:00', '9999-12-31T23:59:59-01:00', '0001-01-01T00:00:00+01:00']:
            with self.subTest(at=at), self.assertRaises(ValueError):
                transits.calculate_snapshot(at)
        with self.assertRaises(ValueError):
            transits.calculate_snapshot(AT, mansion_profile='unknown')
        with self.assertRaises(ValueError):
            transits.calculate_snapshot(AT, focus=['官禄'])
        for edit in ['partial', 'duplicate_names', 'duplicate_stars', 'invalid_star']:
            natal = natal_mapping()
            if edit == 'partial':
                del natal['palaces']['子']
            elif edit == 'duplicate_names':
                natal['palaces']['丑']['name'] = '命宫'
            elif edit == 'duplicate_stars':
                natal['palaces']['子']['natal_stars'] = ['月']
                natal['palaces']['丑']['natal_stars'] = ['月']
            else:
                natal['palaces']['子']['natal_stars'] = ['冥']
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                transits.calculate_snapshot(AT, natal=natal)

    def test_second_independent_snapshot(self):
        result = transits.calculate_snapshot('2027-10-09T01:16:00+08:00', mansion_profile='xhcl_original')
        expected = [('辰', 1.05, '轸水', 10.05), ('丑', 14.42, '斗木', 18.42),
                    ('辰', 16.53, '角木', 8.53), ('巳', 1.70, '张月', 15.70),
                    ('辰', 20.70, '亢金', 0.70), ('卯', 10.72, '氐土', 11.72),
                    ('戌', 10.99, '奎木', 11.99), ('丑', 25.08, '牛金', 4.08),
                    ('未', 25.08, '鬼金', 3.08), ('巳', 22.27, '轸水', 1.27),
                    ('丑', 29.06, '女土', 1.06)]
        for star, (branch, degree, mansion, within) in zip(result['stars'], expected):
            with self.subTest(star=star['name']):
                self.assertEqual(star['branch'], branch)
                self.assertEqual(star['mansion'], mansion)
                self.assertAlmostEqual(star['palace_degree'], degree, delta=0.02)
                self.assertAlmostEqual(star['mansion_degree'], within, delta=0.02)

    def test_true_apogee_and_boundary_profiles(self):
        true = transits.calculate_snapshot(AT, apogee='true')
        mean = transits.calculate_snapshot(AT, apogee='mean')
        self.assertNotEqual(true['stars'][-1]['sidereal_longitude'], mean['stars'][-1]['sidereal_longitude'])
        self.assertNotEqual(true['stars'][-1]['speed_deg_per_day'], mean['stars'][-1]['speed_deg_per_day'])
        self.assertEqual(true['stars'][:-1], mean['stars'][:-1])
        engine = transits.load_engine()
        for name, (constant, _) in transits.PROFILES.items():
            boundaries = getattr(engine, constant)
            chart = engine.ZhengCaseSidereal(boundaries=boundaries)
            for index, boundary in enumerate(boundaries):
                with self.subTest(profile=name, boundary=boundary):
                    self.assertEqual(chart.get_mansion_index(boundary), index)
                    self.assertEqual(chart.degree_within_mansion(boundary), 0)

    def test_motion_is_current_and_nodes_are_not_hardcoded_direct(self):
        stars = {s['name']: s for s in self.snapshot['stars']}
        self.assertLess(stars['土']['speed_deg_per_day'], 0)
        self.assertTrue(stars['土']['is_retrograde'])
        self.assertLess(stars['计']['speed_deg_per_day'], 0)
        self.assertTrue(stars['计']['is_retrograde'])
        self.assertFalse(stars['日']['is_retrograde'])
        self.assertNotIn('natal_strength', stars['日'])
        self.assertNotIn('蚀', transits.to_markdown(self.snapshot))

    def test_markdown_groups_natal_and_transit_separately(self):
        natal = natal_mapping()
        natal['palaces']['辰']['natal_stars'] = ['月']
        result = transits.calculate_snapshot(AT, natal=natal, focus=['辰'], mansion_profile='xhcl_original')
        md = transits.to_markdown(result)
        self.assertIn('郑氏星案恒星制', md)
        self.assertIn('本命宫内星', md)
        self.assertIn('流曜', md)
        self.assertIn('| 辰 | 男女 | 月 | 日、金、水 |', md)
        self.assertNotIn('星官', md)

    def test_cli_stdout_and_stdin_do_not_write_case_files(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--at', AT, '--natal', '-',
                                     '--mansion-profile', 'xhcl_original'], input=json.dumps(natal_mapping()),
                                    text=True, capture_output=True, cwd=directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)['stars']), 11)
            self.assertEqual(list(Path(directory).iterdir()), [])
        invalid = subprocess.run([sys.executable, '-B', str(SCRIPT), '--at', '2026'], text=True, capture_output=True)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertEqual(invalid.stdout, '')
        self.assertNotIn('Traceback', invalid.stderr)


if __name__ == '__main__':
    unittest.main()
