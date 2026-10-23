"""Top-star query behavior using anonymous, synthetic coordinates."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'qizheng-siyu-expert/skills/qz-reader/scripts/calculate_topstars.py'
AT = '2026-12-20T12:00:00+08:00'
STARS = list('日月金木水火土计罗炁孛')


def query(center=10.0, years=15.0, stars=None):
    return {
        'chart_version': 'anonymous-fixture-v1',
        'at': AT,
        'coordinate_system': '郑氏星案恒星制',
        'coordinate_profile': 'synthetic-common-origin',
        'center': {'longitude_deg': center, 'at': AT, 'source': 'synthetic current limit point'},
        'limit': {'years': years, 'source': 'synthetic selected limit segment'},
        'natal': {'source': 'synthetic natal coordinates', 'stars': stars or [
            {'name': '木', 'longitude_deg': 40.0}]},
    }


class TopstarTests(unittest.TestCase):
    def run_query(self, data, success=True):
        with tempfile.TemporaryDirectory() as workdir:
            p = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(data),
                               text=True, capture_output=True, cwd=workdir)
            self.assertEqual(list(Path(workdir).iterdir()), [], 'query must not create client files')
        if success:
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stderr, '')
            return json.loads(p.stdout)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertEqual(p.stdout, '')
        self.assertTrue(p.stderr.startswith('topstars: '), p.stderr)
        self.assertNotIn('Traceback', p.stderr)
        return p.stderr

    def test_modulo_thirty_and_natal_transit_are_separate(self):
        data = query()
        data['transit'] = {'at': AT, 'source': 'synthetic instant snapshot', 'stars': [
            {'name': '木', 'longitude_deg': 72.0}, {'name': '水', 'longitude_deg': 100.5}]}
        out = self.run_query(data)
        self.assertEqual(out['half_width_deg'], 1.0)
        self.assertEqual([x['name'] for x in out['natal']['hits']], ['木'])
        self.assertEqual([x['name'] for x in out['transit']['hits']], ['水'])
        self.assertEqual(out['meta']['scope'], 'instant_candidates')
        self.assertEqual(out['input'], data)

    def test_regular_window_is_closed_at_both_ends(self):
        out = self.run_query(query(stars=[{'name': '日', 'longitude_deg': 9},
                                         {'name': '月', 'longitude_deg': 41},
                                         {'name': '水', 'longitude_deg': 71.000001}]))
        self.assertEqual([x['name'] for x in out['natal']['hits']], ['日', '月'])
        self.assertEqual(out['natal']['hits'][1]['hit_reasons'], ['regular_window'])

    def test_decimal_endpoint_does_not_change_when_star_moves_thirty_degrees(self):
        for longitude in [11.1, 41.1, 71.1, 101.1]:
            with self.subTest(longitude=longitude):
                out = self.run_query(query(10.1, 15, [{'name': '木', 'longitude_deg': longitude}]))
                self.assertEqual(len(out['natal']['hits']), 1)
                self.assertEqual(out['natal']['hits'][0]['delta_deg'], 1.0)
        out = self.run_query(query(10.1, 15, [{'name': '木', 'longitude_deg': 41.1000000000001}]))
        self.assertEqual(out['natal']['hits'], [])

    def test_boundary_exception_independent_of_half_width(self):
        out = self.run_query(query(29.0, 60.0, [{'name': '炁', 'longitude_deg': 0.9999}]))
        hit = out['natal']['hits'][0]
        self.assertEqual(out['half_width_deg'], 0.25)
        self.assertEqual(hit['hit_reasons'], ['boundary_29_1'])
        self.assertTrue(hit['boundary_only'])

    def test_boundary_twenty_nine_is_included_one_is_excluded(self):
        cases = [(29.0, 0.9999, True), (0.9999, 29.0, True),
                 (29.0, 1.0, False), (1.0, 29.0, False),
                 (28.9999, 0.2, False), (0.2, 28.9999, False)]
        for center, candidate, expected in cases:
            with self.subTest(center=center, candidate=candidate):
                out = self.run_query(query(center, 60, [{'name': '炁', 'longitude_deg': candidate}]))
                self.assertEqual(bool(out['natal']['hits']), expected)

    def test_normalizes_angles_before_modulo_thirty(self):
        out = self.run_query(query(-350.0, stars=[{'name': '日', 'longitude_deg': 730.0}]))
        self.assertEqual(out['center_palace_degree'], 10.0)
        self.assertEqual(out['natal']['hits'][0]['longitude_deg'], 10.0)

    def test_coordinates_reproduce_two_routes(self):
        out = self.run_query(query(240.998, 10, [{'name': '木', 'longitude_deg': 1.618},
                                               {'name': '炁', 'longitude_deg': 179.766}]))
        self.assertEqual(out['natal']['hits'][0]['hit_reasons'], ['regular_window'])
        self.assertEqual(out['natal']['hits'][1]['hit_reasons'], ['boundary_29_1'])

    def test_partial_and_absent_star_sets_do_not_claim_complete_scan(self):
        out = self.run_query(query())
        self.assertEqual(out['natal']['status'], 'partial')
        self.assertEqual(out['transit']['status'], 'not_provided')
        self.assertEqual(out['natal']['missing_stars'], [s for s in STARS if s != '木'])
        self.assertEqual(out['transit']['missing_stars'], STARS)

    def test_complete_set_is_marked_complete_even_without_hits(self):
        out = self.run_query(query(stars=[{'name': s, 'longitude_deg': 20} for s in STARS]))
        self.assertEqual(out['natal']['status'], 'complete')
        self.assertEqual(out['natal']['hits'], [])

    def test_rejects_missing_center_and_year_start_substitution(self):
        data = query()
        del data['center']
        self.run_query(data, False)
        data = query()
        data['center']['at'] = '2026-01-01T00:00:00+08:00'
        self.run_query(data, False)

    def test_rejects_transit_at_wrong_instant_but_accepts_equivalent_zone(self):
        data = query()
        data['transit'] = {'at': '2026-12-20T04:00:00+00:00', 'source': 'snapshot',
                           'stars': [{'name': '日', 'longitude_deg': 10}]}
        self.assertEqual(len(self.run_query(data)['transit']['hits']), 1)
        data['transit']['at'] = '2026-12-21T04:00:00+00:00'
        self.run_query(data, False)

    def test_rejects_naive_time_and_wrong_coordinate_system(self):
        data = query()
        data['at'] = '2026-12-20T12:00:00'
        self.run_query(data, False)
        data = query()
        data['coordinate_system'] = 'tropical'
        self.run_query(data, False)

    def test_rejects_invalid_numbers_and_missing_sources(self):
        for value in [0, -10, float('nan'), float('inf'), True, '15']:
            with self.subTest(value=value):
                self.run_query(query(years=value), False)
        for path in [('center', 'longitude_deg'), ('natal', 'source'), ('limit', 'source')]:
            data = query()
            del data[path[0]][path[1]]
            self.run_query(data, False)

    def test_rejects_non_eleven_stars_and_duplicate_names(self):
        for name in ['天王', '斗', '罡', '流木']:
            self.run_query(query(stars=[{'name': name, 'longitude_deg': 10}]), False)
        data = query()
        data['natal']['stars'] *= 2
        self.run_query(data, False)

    def test_does_not_mutate_input_or_invent_missing_groups(self):
        data = query()
        before = copy.deepcopy(data)
        out = self.run_query(data)
        self.assertEqual(data, before)
        self.assertEqual(out['input'], before)
        self.assertEqual(out['transit']['checked'], [])


if __name__ == '__main__':
    unittest.main()
