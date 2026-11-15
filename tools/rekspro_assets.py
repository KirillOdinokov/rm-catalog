#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""rekspro_assets.py — скачивание фото и PDF с reks.pro + извлечение текста PDF.

Читает data\rekspro\pages.jsonl, качает:
  data\rekspro\img\<slug>.webp   фото товаров (на заводском сайте уже WebP)
  E:\Оптимизация\Knowledge\reks.pro\pdf\<file>.pdf   паспорта/ТУ/сертификаты
  data\rekspro\docs.jsonl        распознанный текст PDF (PyMuPDF), флаг scan для OCR
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "rekspro")
IMG = os.path.join(OUT, "img")
# сами PDF живут в общей базе знаний, рядом с распознанным текстом
PDF = r"E:\Оптимизация\Knowledge\reks.pro\pdf"

HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "image/webp,image/*,application/pdf,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
}


def slugify(u):
    name = urllib.parse.unquote(os.path.basename(urllib.parse.urlparse(u).path))
    name = re.sub(r"\.(webp|jpg|jpeg|png|pdf)$", "", name, flags=re.I)
    name = re.sub(r"[^0-9A-Za-z._-]+", "-", name).strip("-").lower()
    return name or "file"


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            if i == tries - 1:
                sys.stderr.write("FAIL %s %s\n" % (url, e))
                return b""
            time.sleep(1 + i)
    return b""


def load_pages():
    p = os.path.join(OUT, "pages.jsonl")
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def download_images(pages):
    os.makedirs(IMG, exist_ok=True)
    index_p = os.path.join(OUT, "images.jsonl")
    done = set()
    if os.path.exists(index_p):
        with open(index_p, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["url"])
                except Exception:
                    pass
    n = 0
    with open(index_p, "a", encoding="utf-8") as fo:
        for pg in pages:
            for u in pg.get("img", []):
                if u in done:
                    continue
                ext = os.path.splitext(urllib.parse.urlparse(u).path)[1].lower() or ".webp"
                name = slugify(u) + ext
                path = os.path.join(IMG, name)
                if not os.path.exists(path):
                    data = get(u)
                    if not data or len(data) < 500:
                        continue
                    with open(path, "wb") as f:
                        f.write(data)
                    time.sleep(0.15)
                fo.write(json.dumps({"url": u, "file": name, "page": pg["url"],
                                     "name": pg.get("name", ""), "kind": pg.get("kind", "")},
                                    ensure_ascii=False) + "\n")
                fo.flush()
                done.add(u)
                n += 1
    print("images:", n)


def download_pdfs(pages):
    os.makedirs(PDF, exist_ok=True)
    index_p = os.path.join(OUT, "pdf_index.jsonl")
    done = set()
    if os.path.exists(index_p):
        with open(index_p, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["url"])
                except Exception:
                    pass
    n = 0
    with open(index_p, "a", encoding="utf-8") as fo:
        for pg in pages:
            for d in pg.get("pdf", []):
                u = d["url"]
                if u in done:
                    continue
                name = slugify(u) + ".pdf"
                path = os.path.join(PDF, name)
                if not os.path.exists(path):
                    data = get(u)
                    if not data or len(data) < 1000 or data[:4] != b"%PDF":
                        sys.stderr.write("NOT PDF %s\n" % u)
                        continue
                    with open(path, "wb") as f:
                        f.write(data)
                    time.sleep(0.2)
                fo.write(json.dumps({"url": u, "file": name, "label": d.get("label", ""),
                                     "page": pg["url"], "name": pg.get("name", ""),
                                     "kind": pg.get("kind", "")}, ensure_ascii=False) + "\n")
                fo.flush()
                done.add(u)
                n += 1
    print("pdf:", n)


def ocr_page(pix, lang="rus+eng"):
    """OCR страницы через tesseract.exe, если он есть в системе."""
    import subprocess
    import tempfile
    exe = None
    for c in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if os.path.exists(c):
            exe = c
            break
    if not exe:
        return ""
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, "p.png")
        pix.save(png)
        out = os.path.join(td, "o")
        try:
            subprocess.run([exe, png, out, "-l", lang, "--psm", "3"],
                           check=True, capture_output=True, timeout=180)
        except Exception:
            return ""
        txt = out + ".txt"
        if os.path.exists(txt):
            with open(txt, encoding="utf-8", errors="replace") as f:
                return f.read()
    return ""


def page_text(page):
    """Текст страницы с учётом двухколоночной вёрстки паспортов."""
    W = page.rect.width
    blocks = [b for b in page.get_text("blocks") if b[4].strip()]
    if not blocks:
        return ""
    # колонка: 0 — левая половина, 1 — правая
    def col(b):
        return 1 if (b[0] + b[2]) / 2 > W * 0.55 else 0
    cols = sorted({col(b) for b in blocks})
    if len(cols) <= 1:
        blocks.sort(key=lambda b: (round(b[1]), b[0]))
        return "\n".join(b[4].strip() for b in blocks)
    out = []
    for c in cols:
        part = sorted([b for b in blocks if col(b) == c], key=lambda b: (round(b[1]), b[0]))
        out.append("\n".join(b[4].strip() for b in part))
    return "\n".join(out)


def extract_pdfs():
    try:
        import fitz  # PyMuPDF
    except Exception:
        print("PyMuPDF нет — пропускаю разбор PDF")
        return
    idx = os.path.join(OUT, "pdf_index.jsonl")
    if not os.path.exists(idx):
        return
    rows = []
    with open(idx, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    out_p = os.path.join(OUT, "docs.jsonl")
    done = set()
    if os.path.exists(out_p):
        with open(out_p, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["file"])
                except Exception:
                    pass
    with open(out_p, "a", encoding="utf-8") as fo:
        for r in rows:
            if r["file"] in done:
                continue
            path = os.path.join(PDF, r["file"])
            if not os.path.exists(path):
                continue
            try:
                doc = fitz.open(path)
            except Exception as e:
                sys.stderr.write("Open %s %s\n" % (r["file"], e))
                continue
            parts, scanned = [], 0
            for pi, page in enumerate(doc):
                t = page_text(page)
                if len((t or "").strip()) < 40:
                    t2 = page.get_text("text") or ""
                    if len(t2.strip()) >= 40:
                        t = t2
                    else:
                        pix = page.get_pixmap(dpi=300)
                        t2 = ocr_page(pix)
                        if t2.strip():
                            t = t2
                        else:
                            scanned += 1
                            t = t or ""
                parts.append("[[стр. %d]]\n%s" % (pi + 1, (t or "").strip()))
            text = "\n\n".join(parts)
            rec = dict(r)
            rec["pages"] = doc.page_count
            rec["chars"] = len(text)
            rec["scanned"] = scanned
            rec["text"] = text
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fo.flush()
            print("  pdf", r["file"], doc.page_count, "p", len(text), "chars", "scan", scanned)
    print("docs ok")


def main():
    pages = load_pages()
    print("pages:", len(pages))
    if "--pdf-only" not in sys.argv:
        download_images(pages)
    download_pdfs(pages)
    extract_pdfs()


if __name__ == "__main__":
    main()
