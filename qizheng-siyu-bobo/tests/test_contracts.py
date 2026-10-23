"""Static contract checks; no client charts or interpretive claims are tested."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'qizheng-siyu-expert/skills'


class ContractTests(unittest.TestCase):
    def test_active_entry_inventory_excludes_retired_lawsuit(self):
        entries = [ROOT / 'SKILL.md', *SKILLS.glob('*/SKILL.md')]
        self.assertEqual(len(entries), 14)
        self.assertFalse((SKILLS / 'qz-lawsuit').exists())

    def test_health_is_enabled_without_silently_enabling_other_modules(self):
        self.assertNotIn('disable: true', (SKILLS / 'qz-health/SKILL.md').read_text())
        for name in ('qz-study', 'qz-election', 'qz-rectifier'):
            self.assertIn('disable: true', (SKILLS / name / 'SKILL.md').read_text())

    def test_source_contract_retains_raw_aspects_and_identities(self):
        contract = (SKILLS / 'qz-reader/resources/data_contract.md').read_text()
        for field in ('原始相位表', '45°刑', '135°对刑', '逐星身份表', '化曜身份原文', '管库／职衔', '未提供'):
            self.assertIn(field, contract)

    def test_data_contract_keeps_ten_sections(self):
        contract = (SKILLS / 'qz-reader/resources/data_contract.md').read_text()
        headers = [line for line in contract.splitlines() if line.startswith('## ')]
        self.assertEqual(len(headers), 10)
        self.assertTrue(headers[4].startswith('## 5. 十二宫'))

    def test_missing_gender_does_not_block_shared_natal_analysis(self):
        rules = (SKILLS / 'qz-reader/resources/missing_data_rules.md').read_text()
        blocking = rules.split('## 必须暂停的缺失', 1)[1].split('## 可以继续', 1)[0]
        self.assertNotIn('缺性别', blocking)
        self.assertIn('不阻断共同原局分析', rules)

    def test_no_archive_handoff_is_explicit(self):
        for name in ('qz-reader', 'qz-core', 'qz-love', 'qz-children', 'qz-election'):
            text = (SKILLS / name / 'SKILL.md').read_text()
            self.assertIn('不存档', text)
            self.assertIn('内存', text)

    def test_active_runtime_identifiers_are_unchanged(self):
        self.assertIn('name: qizheng-siyu-full\n', (ROOT / 'SKILL.md').read_text())
        for path in SKILLS.glob('*/SKILL.md'):
            self.assertIn('name: ' + path.parent.name + '\n', path.read_text())

    def test_plugin_json_is_parseable_and_has_no_lawsuit_route(self):
        text = (ROOT / 'qizheng-siyu-expert/.codebuddy-plugin/plugin.json').read_text()
        json.loads(text)
        self.assertNotIn('qz-lawsuit', text)


if __name__ == '__main__':
    unittest.main()
