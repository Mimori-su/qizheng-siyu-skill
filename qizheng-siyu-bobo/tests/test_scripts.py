"""Regression fixtures are entirely fictional; no client files are used."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1] / 'qizheng-siyu-expert' / 'skills'


def load(skill, name):
    return runpy.run_path(str(ROOT / skill / 'scripts' / name), run_name='test_import')


PARSER = load('qz-reader', 'parse_chart_text.py')
VALIDATOR = load('qz-reader', 'validate_structured_data.py')
CORE = load('qz-core', 'build_core_report.py')
EXTRACT = load('qz-reader', 'extract_pdf_text.py')
RENDER = load('qz-reader', 'render_pdf_pages.py')
ASSEMBLE = load('qz-report', 'assemble_report.py')
FICTIONAL_CHART = '''命宫：子宫
命度：角木1度
命度主：木
身宫：丑宫
身度：房日2度
身度主：日
日 子宫 角木1度
月 子宫 角木1度
金 子宫 角木1度
木 子宫 角木1度
水 子宫 角木1度
火 子宫 角木1度
土 子宫 角木1度
罗 子宫 角木1度
气 子宫 角木1度
计 子宫 角木1度
孛 子宫 角木1度
'''


def invoke(module, *arguments):
    with patch.object(sys, 'argv', ['test-script', *map(str, arguments)]):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return module['main']()


class ParserTests(unittest.TestCase):
    def test_natal_field_does_not_match_transit_label(self):
        self.assertEqual(PARSER['val']('流年命宫：丑宫\n命宫：子宫', '命宫'), '子宫')

    def test_empty_field_does_not_consume_following_line(self):
        self.assertEqual(PARSER['val']('命宫：\n命度：角木1度', '命宫'), '')

    def test_transit_section_does_not_supply_natal_field(self):
        text = '## 流年盘\n命宫：丑宫\n## 本命盘\n命宫：子宫'
        self.assertEqual(PARSER['val'](text, '命宫'), '子宫')

    def test_star_preserves_lodge_and_complete_degree(self):
        cells = PARSER['star_row']('日 子宫 角木 1度30分', '日', '七政').split('|')
        self.assertEqual(cells[5].strip(), '角木 1度30分')

    def test_transit_prefix_does_not_supply_natal_star(self):
        cells = PARSER['star_row']('流年日：丑宫 角木 2度\n日：子宫 角木 1度', '日', '七政').split('|')
        self.assertEqual(cells[4].strip(), '子宫')

    def test_transit_section_does_not_supply_natal_star(self):
        text = '## 本命星曜\n月 子宫 角木 1度\n## 流年星曜\n日 丑宫 角木 2度'
        cells = PARSER['star_row'](text, '日', '七政').split('|')
        self.assertEqual(cells[4].strip(), '')

    def test_conflicting_natal_values_remain_unknown(self):
        self.assertEqual(PARSER['val']('命宫：子宫\n命宫：丑宫', '命宫'), '')

    def test_export_star_aliases_keep_branch_lodge_and_original_name(self):
        fixtures = (
            ('日', '七政', '太阳', '太阳垣庙乐, 入午日福德宫13.25度, 张月3.75度', '午宫', '张月3.75度'),
            ('月', '七政', '月亮', '月亮喜, 入亥水兄弟宫8.25度, 室火2.25度', '亥宫', '室火2.25度'),
            ('金', '七政', '金星', '金星伏旺, 入酉金夫妻宫6.25度, 胃土1.25度', '酉宫', '胃土1.25度'),
            ('气', '四余', '紫炁', '紫炁, 入寅木官禄宫7.25度, 尾火4.25度', '寅宫', '尾火4.25度'),
            ('计', '四余', '计都', '计都, 入辰金田宅宫9.25度, 角木3.25度', '辰宫', '角木3.25度'),
            ('孛', '四余', '月孛', '月孛, 入丑土迁移宫4.25度, 斗木2.75度', '丑宫', '斗木2.75度'),
            ('罗', '四余', '罗喉', '罗喉, 入申水男女宫5.25度, 参水1.75度', '申宫', '参水1.75度'),
        )
        for canonical, kind, alias, text, palace, degree in fixtures:
            with self.subTest(alias=alias):
                cells = PARSER['star_row'](text, canonical, kind).split('|')
                self.assertEqual(cells[1].strip(), canonical)
                self.assertEqual(cells[4].strip(), palace)
                self.assertEqual(cells[5].strip(), degree)
                self.assertIn(alias, cells[7])
                self.assertEqual(cells[8].strip(), '输入文本')

    def test_summary_lines_are_not_star_position_records(self):
        for text in ('午宫内星：太阳、月亮', '太阳、月亮入午宫，张月3.75度',
                     '太阳宫内星汇总：入午宫，张月3.75度'):
            with self.subTest(text=text):
                cells = PARSER['star_row'](text, '日', '七政').split('|')
                self.assertEqual(cells[4].strip(), '')

    def test_transit_export_alias_is_not_used_as_natal_position(self):
        text = '## 流年星曜\n太阳垣, 入午日福德宫13.25度, 张月3.75度\n## 本命星曜\n太阳, 入子土命宫4.25度, 虚日1.25度'
        cells = PARSER['star_row'](text, '日', '七政').split('|')
        self.assertEqual(cells[4].strip(), '子宫')
        self.assertEqual(cells[5].strip(), '虚日1.25度')

    def test_compound_export_field_stops_before_next_label(self):
        self.assertEqual(PARSER['val']('命度:室火  难:水孛, 仇:金\n身度:角木', '命度'), '室火')


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='qz-fictional-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def test_empty_chart_is_not_validated(self):
        source = self.base / 'empty.md'
        source.write_text(PARSER['build'](''), encoding='utf-8')
        self.assertNotEqual(invoke(VALIDATOR, source), 0)

    def test_unknown_fields_are_not_validated(self):
        source = self.base / 'unknown.md'
        text = '\n'.join(k + '：未知' for k in ('命宫', '命度', '命度主', '身宫', '身度', '身度主'))
        source.write_text(PARSER['build'](text), encoding='utf-8')
        self.assertNotEqual(invoke(VALIDATOR, source), 0)

    def test_unknown_fields_do_not_authorize_core_analysis(self):
        source = self.base / 'unknown.md'
        source.write_text('\n'.join('| ' + k + ' | 未知 |' for k in ('命宫', '命度', '命度主', '身宫', '身度', '身度主')), encoding='utf-8')
        output = self.base / 'core.md'
        self.assertNotEqual(invoke(CORE, '--structured', source, '--out', output), 0)
        if output.exists():
            self.assertNotIn('可做初步核心分析', output.read_text(encoding='utf-8'))

    def test_transit_rows_cannot_fill_missing_natal_core_fields(self):
        source = self.base / 'transit-only.md'
        source.write_text('## 3. 太极与命身\n\n## 9. 运势资料\n' + '\n'.join(
            '| ' + k + ' | 虚构流年值 |' for k in ('命宫', '命度', '命度主', '身宫', '身度', '身度主')), encoding='utf-8')
        self.assertNotEqual(invoke(CORE, '--structured', source, '--out', self.base / 'core.md'), 0)

    def test_supplemental_star_table_is_not_a_duplicate_main_table(self):
        source = self.base / 'structured.md'
        supplemental = '\n### 本命逐星原始坐标补充表\n' + '\n'.join(
            '| ' + star + ' | 子 | 命宫 | 角木1度 | 木 | 虚构输入 | 低 |'
            for star in ('日', '月', '金', '木', '水', '火', '土', '罗', '气', '计', '孛'))
        source.write_text(PARSER['build'](FICTIONAL_CHART).replace(
            '## 5. 十二宫', supplemental + '\n\n## 5. 十二宫'), encoding='utf-8')
        self.assertEqual(invoke(VALIDATOR, source), 0)

    def test_complete_fictional_structure_can_produce_a_review_draft(self):
        source = self.base / 'structured.md'
        source.write_text(PARSER['build'](FICTIONAL_CHART), encoding='utf-8')
        self.assertEqual(invoke(VALIDATOR, source), 0)
        output = self.base / 'core.md'
        self.assertEqual(invoke(CORE, '--structured', source, '--out', output), 0)
        self.assertIn('待分析', output.read_text(encoding='utf-8'))

    def test_six_fields_alone_never_authorize_core_analysis(self):
        source, output = self.base / 'six-fields.md', self.base / 'core.md'
        source.write_text('## 3. 太极与命身\n' + '\n'.join(
            '| ' + key + ' | ' + value + ' |'
            for key, value in (('命宫', '子宫'), ('命度', '角木1度'), ('命度主', '木'),
                               ('身宫', '丑宫'), ('身度', '房日2度'), ('身度主', '日'))), encoding='utf-8')
        self.assertEqual(invoke(CORE, '--structured', source, '--out', output), 0)
        content = output.read_text(encoding='utf-8')
        self.assertNotIn('可做初步核心分析', content)
        self.assertIn('仅生成框架；仍须完整盘面与旺衰复核', content)

    def test_missing_topic_does_not_replace_existing_report(self):
        core, output = self.base / 'core.md', self.base / 'report.md'
        core.write_text('Fictional internal note', encoding='utf-8')
        output.write_text('Preserve existing output', encoding='utf-8')
        self.assertNotEqual(invoke(ASSEMBLE, '--core', core, '--topics', self.base / 'missing.md', '--out', output), 0)
        self.assertEqual(output.read_text(encoding='utf-8'), 'Preserve existing output')

    def test_missing_core_does_not_create_report(self):
        output = self.base / 'report.md'
        self.assertNotEqual(invoke(ASSEMBLE, '--core', self.base / 'missing.md', '--out', output), 0)
        self.assertFalse(output.exists())

    def test_existing_internal_inputs_can_be_assembled(self):
        core, topic, output = self.base / 'core.md', self.base / 'topic.md', self.base / 'report.md'
        core.write_text('Fictional core note', encoding='utf-8')
        topic.write_text('Fictional topic note', encoding='utf-8')
        self.assertEqual(invoke(ASSEMBLE, '--core', core, '--topics', topic, '--out', output), 0)
        content = output.read_text(encoding='utf-8')
        self.assertIn('Fictional core note', content)
        self.assertIn('Fictional topic note', content)

    def test_assembled_output_is_explicitly_an_internal_draft(self):
        source, output = self.base / 'core.md', self.base / 'report.md'
        source.write_text('Fictional internal note', encoding='utf-8')
        self.assertEqual(invoke(ASSEMBLE, '--core', source, '--out', output), 0)
        content = output.read_text(encoding='utf-8')
        self.assertEqual(content.splitlines()[0], '# 七政四余内部资料拼接草稿')

    def test_blank_core_does_not_create_report(self):
        source, output = self.base / 'blank.md', self.base / 'report.md'
        source.write_text(' \t\n', encoding='utf-8')
        self.assertNotEqual(invoke(ASSEMBLE, '--core', source, '--out', output), 0)
        self.assertFalse(output.exists())

    def test_blank_topic_does_not_replace_existing_report(self):
        source, topic, output = self.base / 'core.md', self.base / 'blank.md', self.base / 'report.md'
        source.write_text('Fictional internal note', encoding='utf-8')
        topic.write_text('\n \t', encoding='utf-8')
        output.write_text('Preserve existing output', encoding='utf-8')
        self.assertNotEqual(invoke(ASSEMBLE, '--core', source, '--topics', topic, '--out', output), 0)
        self.assertEqual(output.read_text(encoding='utf-8'), 'Preserve existing output')


class FakePage:
    """Only the unavailable PDF decoder is substituted, not file/status logic."""
    def __init__(self, text):
        self.text = text

    def get_text(self, kind):
        if isinstance(self.text, Exception):
            raise self.text
        return self.text

    def extract_text(self):
        return self.get_text('text')


class FakeDocument:
    def __init__(self, texts):
        self.pages = [FakePage(text) for text in texts]

    def __len__(self):
        return len(self.pages)

    def __iter__(self):
        return iter(self.pages)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def pdf_modules(texts):
    fitz, plumber = types.ModuleType('fitz'), types.ModuleType('pdfplumber')
    fitz.open = lambda path: FakeDocument(texts)
    fitz.Matrix = lambda x, y: (x, y)
    plumber.open = lambda path: FakeDocument(texts)
    return {'fitz': fitz, 'pdfplumber': plumber}


class PdfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='qz-fictional-pdf-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'fictional.pdf'
        self.source.write_bytes(b'%PDF synthetic decoder test')

    def test_empty_text_is_not_success(self):
        with patch.dict(sys.modules, pdf_modules([''])):
            status = invoke(EXTRACT, '--pdf', self.source, '--out', self.base / 'pages')
        self.assertNotEqual(status, 0)
        index = json.loads((self.base / 'pages/index.json').read_text(encoding='utf-8'))
        self.assertNotEqual(index['items'][0]['status'], 'ok')

    def test_all_page_failures_are_not_success(self):
        with patch.dict(sys.modules, pdf_modules([ValueError('fictional failure')])):
            self.assertNotEqual(invoke(EXTRACT, '--pdf', self.source, '--out', self.base / 'pages'), 0)

    def test_successful_text_extraction_remains_successful(self):
        with patch.dict(sys.modules, pdf_modules(['Fictional PDF text'])):
            self.assertEqual(invoke(EXTRACT, '--pdf', self.source, '--out', self.base / 'pages'), 0)
        self.assertIn('Fictional PDF text', (self.base / 'pages/page_001.txt').read_text(encoding='utf-8'))

    def test_invalid_pages_do_not_report_render_success(self):
        with patch.dict(sys.modules, pdf_modules(['first', 'second'])):
            self.assertNotEqual(invoke(RENDER, '--pdf', self.source, '--out', self.base / 'images', '--pages', '999'), 0)
        self.assertFalse((self.base / 'images').exists())

    def test_page_ranges_reject_out_of_range_or_reversed_parts(self):
        for spec in ('1,999', '2-1', '0', '1-999', ',,'):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                RENDER['parse_pages'](spec, 2)

    def test_valid_page_range_is_still_supported(self):
        self.assertEqual(RENDER['parse_pages']('2,1-2', 2), [1, 2])


if __name__ == '__main__':
    unittest.main()
