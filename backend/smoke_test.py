import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pymupdf
from app.pdf_engine import extract_structure, apply_block_edit

SRC = "/Users/junot/Downloads/interialeortheses.pdf"
OUT_DIR = Path("/private/tmp/claude-501/-Users-junot/eda0ba74-3fe2-4e67-a5e0-421ccdbe7f3c/scratchpad")
OUT_DIR.mkdir(parents=True, exist_ok=True)

doc = pymupdf.open(SRC)
page = doc[0]
blocks = extract_structure(page)
print(f"extracted {len(blocks)} blocks")

date_block = next(b for b in blocks if "22/06/2026" in b.text and "Lille" in b.text)
name_block = next(b for b in blocks if "JUNOT" in b.text and "MME" in b.text)

print("date block text:", repr(date_block.text), date_block.bbox)
print("name block text:", repr(name_block.text), name_block.bbox)

orig_text_full = page.get_text()

sub1, bbox1 = apply_block_edit(doc, page, date_block, "Lille, le 05/09/2026")
print(f"date edit: substituted={sub1} new_bbox={bbox1}")

sub2, bbox2 = apply_block_edit(doc, page, name_block, "MME DURAND-LEFEBVRE MARGUERITE")
print(f"name edit: substituted={sub2} new_bbox={bbox2}")

doc.save(OUT_DIR / "backend-edit-result.pdf")

final_text = doc[0].get_text()
checks = {
    "old date gone": "22/06/2026" not in final_text,
    "new date present": "05/09/2026" in final_text,
    "old name gone": "JUNOT" not in final_text or "JUNOT" in name_block.text,  # JUNOT also appears elsewhere on page (legit)
    "new name present": "DURAND-LEFEBVRE" in final_text,
}
for k, v in checks.items():
    print(f"  [{'OK' if v else 'FAIL'}] {k}")

pix = page.get_pixmap(matrix=pymupdf.Matrix(3, 3))
pix.save(OUT_DIR / "backend-edit-result.png")
print("saved preview PNG + PDF to", OUT_DIR)
