"""Temporary: render sample pages from the reference PDF for visual comparison."""
import io
import os

import pymupdf  # type: ignore

SRC = r"c:\Users\titangrey\Desktop\Image generator\Teddy & Cats — 100 Cute Adventures Coloring Book.pdf"
OUT = r"c:\Users\titangrey\Desktop\Image generator\coloring-book-agent\output\ref_sample"
os.makedirs(OUT, exist_ok=True)

doc = pymupdf.open(SRC)
n = doc.page_count
print("pages:", n)
print("page size (pts):", doc[0].rect)
print("metadata:", {k: v for k, v in doc.metadata.items() if v})

# Render: cover + a spread of interior pages
picks = [0, 1, 3, 5, 10, 20, 50, 99]
picks = [p for p in picks if p < n]
for p in picks:
    pix = doc[p].get_pixmap(dpi=100)
    path = os.path.join(OUT, "ref_p{:03d}.png".format(p + 1))
    pix.save(path)
    print("saved", path, pix.width, "x", pix.height)
doc.close()
