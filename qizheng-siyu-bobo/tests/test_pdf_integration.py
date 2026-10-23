"""Optional real PDF extraction checks, using generated synthetic fixtures."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'qizheng-siyu-expert/skills/qz-reader/scripts/extract_pdf_text.py'


def synthetic_pdf(text):
    stream = ('BT /F1 12 Tf 30 100 Td (' + text + ') Tj ET').encode('ascii') if text else b''
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
        b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    content = b'%PDF-1.4\n'
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(content))
        content += f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(content)
    content += b'xref\n0 6\n0000000000 65535 f \n'
    content += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets)
    return content + f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()


@unittest.skipUnless(importlib.util.find_spec('pdfplumber') or importlib.util.find_spec('fitz'), 'PDF decoder not installed')
class RealPdfTests(unittest.TestCase):
    def test_real_text_and_blank_pdf_status(self):
        with tempfile.TemporaryDirectory(prefix='qz-generated-pdf-') as directory:
            root = Path(directory)
            for name, text in [('text', 'Fictional test only'), ('blank', '')]:
                with self.subTest(name=name):
                    pdf, output = root / (name + '.pdf'), root / name
                    pdf.write_bytes(synthetic_pdf(text))
                    result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--pdf', str(pdf), '--out', str(output)], capture_output=True, text=True)
                    if text:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn(text, (output / 'page_001.txt').read_text())
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn('empty', (output / 'index.json').read_text())


if __name__ == '__main__':
    unittest.main()
