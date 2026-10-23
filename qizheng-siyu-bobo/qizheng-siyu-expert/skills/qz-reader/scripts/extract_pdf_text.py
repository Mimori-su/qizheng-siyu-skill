#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, logging
from pathlib import Path

def extract_with_fitz(pdf: Path, out: Path) -> dict:
    import fitz
    doc = fitz.open(pdf); items=[]
    for i,page in enumerate(doc,1):
        target=out/f'page_{i:03d}.txt'
        try:
            text=page.get_text('text') or ''
            target.write_text(f'<!-- PDF page {i} -->\n\n{text}', encoding='utf-8')
            items.append({'page':i,'file':target.name,'chars':len(text),'status':'ok' if text.strip() else 'empty'})
        except Exception as exc:
            logging.exception('page %s failed', i)
            target.write_text(f'<!-- PDF page {i} extraction failed: {exc} -->\n', encoding='utf-8')
            items.append({'page':i,'file':target.name,'status':'failed','error':str(exc)})
    result = {'engine':'fitz','pages':len(doc),'items':items}
    doc.close()
    return result

def extract_with_pdfplumber(pdf: Path, out: Path) -> dict:
    import pdfplumber
    items=[]
    with pdfplumber.open(str(pdf)) as doc:
        for i,page in enumerate(doc.pages,1):
            target=out/f'page_{i:03d}.txt'
            try:
                text=page.extract_text() or ''
                target.write_text(f'<!-- PDF page {i} -->\n\n{text}', encoding='utf-8')
                items.append({'page':i,'file':target.name,'chars':len(text),'status':'ok' if text.strip() else 'empty'})
            except Exception as exc:
                logging.exception('page %s failed', i)
                target.write_text(f'<!-- PDF page {i} extraction failed: {exc} -->\n', encoding='utf-8')
                items.append({'page':i,'file':target.name,'status':'failed','error':str(exc)})
        return {'engine':'pdfplumber','pages':len(doc.pages),'items':items}

def main() -> int:
    p=argparse.ArgumentParser(description='Extract PDF text page by page.')
    p.add_argument('--pdf', required=True, type=Path); p.add_argument('--out', required=True, type=Path); p.add_argument('--verbose', action='store_true')
    a=p.parse_args(); logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format='%(levelname)s: %(message)s')
    if not a.pdf.exists(): logging.error('PDF not found: %s', a.pdf); return 2
    a.out.mkdir(parents=True, exist_ok=True); errors=[]; result=None
    try: result=extract_with_fitz(a.pdf,a.out)
    except Exception as exc: errors.append(f'fitz: {exc}'); logging.warning('PyMuPDF failed: %s', exc)
    if result is None or (result['items'] and all(item['status'] == 'failed' for item in result['items'])):
        if result is not None:
            errors.append('fitz: all pages failed; trying pdfplumber')
        try: result=extract_with_pdfplumber(a.pdf,a.out)
        except Exception as exc:
            errors.append(f'pdfplumber: {exc}'); logging.error('Install PyMuPDF or pdfplumber. Last error: %s', exc); return 3
    result['source']=str(a.pdf); result['errors']=errors
    (a.out/'index.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if not result['items'] or any(item['status'] != 'ok' for item in result['items']):
        logging.error('Extraction incomplete: inspect index.json; empty pages may require OCR or visual review.')
        return 4
    logging.info('extracted %s pages with %s to %s', result.get('pages'), result.get('engine'), a.out)
    return 0
if __name__ == '__main__': raise SystemExit(main())
