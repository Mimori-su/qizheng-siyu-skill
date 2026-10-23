#!/usr/bin/env python3
from __future__ import annotations
import argparse, logging
from pathlib import Path

def parse_pages(spec: str, total: int) -> list[int]:
    if total < 1: raise ValueError('PDF contains no pages')
    if not spec.strip(): return list(range(1,total+1))
    pages=set()
    for part in spec.split(','):
        part=part.strip()
        if not part: raise ValueError('Empty page selection')
        if '-' in part:
            a,b=[int(x) for x in part.split('-',1)]
            if not 1 <= a <= b <= total: raise ValueError(f'Invalid page range: {part}')
            pages.update(range(a,b+1))
        else:
            page = int(part)
            if not 1 <= page <= total: raise ValueError(f'Page out of range: {page}')
            pages.add(page)
    return sorted(pages)

def main() -> int:
    p=argparse.ArgumentParser(description='Render PDF pages to PNG images.')
    p.add_argument('--pdf', required=True, type=Path); p.add_argument('--out', default=Path('build/page_images'), type=Path); p.add_argument('--pages', default=''); p.add_argument('--zoom', default=2.0, type=float)
    a=p.parse_args(); logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    if not a.pdf.exists(): logging.error('PDF not found: %s', a.pdf); return 2
    try: import fitz
    except Exception as exc: logging.error('PyMuPDF required: %s', exc); return 3
    doc = None
    try:
        doc=fitz.open(a.pdf)
        pages = parse_pages(a.pages, len(doc))
        a.out.mkdir(parents=True, exist_ok=True); matrix=fitz.Matrix(a.zoom,a.zoom)
        for pno in pages:
            pix=doc[pno-1].get_pixmap(matrix=matrix, alpha=False); target=a.out/f'page_{pno:03d}.png'; pix.save(target); logging.info('wrote %s', target)
        return 0
    except (ValueError, OSError) as exc:
        logging.error('Cannot render PDF: %s', exc)
        return 4
    finally:
        if doc is not None:
            doc.close()
if __name__ == '__main__': raise SystemExit(main())
