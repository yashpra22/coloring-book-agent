"""Style Review ROUND 2: pure line-art only. python scripts/style_review2.py"""
import os, sys, time, requests
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()
ACCOUNT = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
SUBJECT = "cute baby elephant playing with three big balloons, smiling, waving trunk"
PW, PH = 768, 1152
SW, SH = 1024, 1024
NEG = "color, colored, filled shapes, solid fill, solid black areas, black fill, grey fill, grey wash, shading, shadow, gradient, crosshatching, hatching, photorealistic, photo, 3d render, painting, watercolor, sketchy, messy lines, blurry, watermark, text, dark background, grey background"
FULL = "vertical portrait, fills entire page top to bottom edge to edge, full-bleed, pure white paper background, black outlines only"
EMPTY = "all shapes EMPTY WHITE INSIDE, white fill inside every shape, no fill, no solid black areas, no shading, no gradients, no grey tones, no colors"
STYLES = {
 "s1": "children coloring book line art, thick bold black outlines ONLY on pure white paper, single cute subject centered large, " + EMPTY + ", flat 2D cartoon outlines, clean minimal lines",
 "s2": "full-page children coloring book line art, thick black outlines ONLY on pure white paper, big central character plus hills clouds sun flowers butterflies, every element ONLY black outline, entire page filled edge to edge, " + EMPTY,
 "s3": "super simple toddler coloring page, ONE giant cute subject, extra thick black outlines on pure white paper, empty white background, huge empty white areas, ONLY black lines, " + EMPTY,
 "s4": "kids coloring page, clean medium black outlines on pure white paper, cute subject with stars dots background outlines, " + EMPTY + ", balanced open white spaces",
 "s5": "storybook coloring page, clear black line work ONLY on pure white paper, central animal with rectangular frame border, simple shapes " + EMPTY,
 "s6": "bold cartoon coloring page, EXTRA THICK uniform black outlines on pure white paper, very simple shapes, large empty white areas, only outlines, no solid blacks, " + EMPTY,
}
VARIANTS = [
 {"w": PW, "h": PH, "s": 8, "g": 3.5, "st": "s1", "nn": 1, "clean": "otsu"},
 {"w": PW, "h": PH, "s": 8, "g": 5.0, "st": "s1", "nn": 1, "clean": "otsu"},
 {"w": PW, "h": PH, "s": 8, "g": 7.0, "st": "s1", "nn": 1, "clean": "adapt71"},
 {"w": PW, "h": PH, "s": 8, "g": 3.5, "st": "s1", "nn": 1, "clean": "adapt71"},
 {"w": PW, "h": PH, "s": 8, "g": 5.0, "st": "s3", "nn": 1, "clean": "adapt71"},
 {"w": PW, "h": PH, "s": 8, "g": 5.0, "st": "s2", "nn": 1, "clean": "adapt71"},
 {"w": PW, "h": PH, "s": 8, "g": 5.0, "st": "s4", "nn": 1, "clean": "adapt51d"},
 {"w": PW, "h": PH, "s": 8, "g": 5.0, "st": "s5", "nn": 1, "clean": "adapt71"},
 {"w": PW, "h": PH, "s": 8, "g": 7.0, "st": "s6", "nn": 1, "clean": "otsud"},
 {"w": PW, "h": PH, "s": 8, "g": 3.5, "st": "s1", "nn": 1, "clean": "adapt101"},
]
MODEL = "@cf/bytedance/stable-diffusion-xl-lightning"
def cf_gen(prompt, w, h, steps, guidance, neg=None):
 url = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/{}".format(ACCOUNT, MODEL)
 hd = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}
 pl = {"prompt": prompt, "width": w, "height": h, "num_steps": steps, "guidance": guidance}
 if neg:
  pl["negative_prompt"] = neg
 try:
  r = requests.post(url, headers=hd, json=pl, timeout=180)
 except Exception as e:
  print("   req err:", e)
  return None
 if not r.ok:
  print("   CF HTTP {}: {}".format(r.status_code, r.text[:200]))
  return None
 ct = r.headers.get("content-type", "")
 if "image" not in ct and len(r.content) < 5000:
  print("   CF non-image:", r.text[:200])
  return None
 return r.content

def clean_bw(gray_arr, mode):
 if mode == "soft":
  return gray_arr
 if mode in ("otsu", "otsud"):
  _, bw = cv2.threshold(gray_arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
 else:
  block, c = {"adapt71": (71, 10), "adapt51d": (51, 7), "adapt101": (101, 15)}.get(mode, (71, 10))
  bw = cv2.adaptiveThreshold(gray_arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, c)
 if mode in ("adapt51d", "otsud"):
  inv = cv2.bitwise_not(bw)
  inv = cv2.dilate(inv, np.ones((2, 2), np.uint8), iterations=1)
  bw = cv2.bitwise_not(inv)
 return bw

def to_a4(raw, clean_mode):
 from io import BytesIO
 im = Image.open(BytesIO(raw))
 if im.mode != "L":
  im = im.convert("L")
 im = ImageEnhance.Contrast(im).enhance(1.2)
 im = im.filter(ImageFilter.SHARPEN)
 bw = clean_bw(np.array(im), clean_mode)
 im = Image.fromarray(bw)
 AW, AH = 1240, 1754
 ratio = AW / AH
 w, h = im.size
 if w / h > ratio:
  nw = int(h * ratio)
  x = (w - nw) // 2
  im = im.crop((x, 0, x + nw, h))
 else:
  nh = int(w / ratio)
  y = (h - nh) // 2
  im = im.crop((0, y, w, y + nh))
 return im.resize((AW, AH), Image.LANCZOS)

def main():
 if not ACCOUNT or not TOKEN:
  print("ERROR: CF creds missing in .env")
  sys.exit(1)
 out = Path(__file__).resolve().parents[1] / "output" / "review2"
 out.mkdir(parents=True, exist_ok=True)
 for i, v in enumerate(VARIANTS, start=1):
  tag = "V{:02d}".format(i)
  pr = "{}, {}, {}. Avoid: {}".format(SUBJECT, FULL, STYLES[v["st"]], NEG)
  print("[{}/10] {} {}x{} s={} g={} {} {} nn={}".format(i, tag, v["w"], v["h"], v["s"], v["g"], v["st"], v["clean"], v["nn"]), flush=True)
  b = cf_gen(pr, v["w"], v["h"], v["s"], v["g"], neg=NEG if v["nn"] else None)
  note = "{}x{}".format(v["w"], v["h"])
  if b is None:
   print("   portrait fail -> square retry")
   b = cf_gen(pr, SW, SH, v["s"], v["g"], neg=NEG if v["nn"] else None)
   note = "1024sq-fallback"
  if b is None:
   print("   {} FAILED".format(tag))
   continue
  a4 = to_a4(b, v["clean"])
  from PIL import ImageDraw
  d = ImageDraw.Draw(a4)
  d.rectangle([0, a4.height - 44, a4.width, a4.height], fill=255)
  d.text((20, a4.height - 32), "{} | {} | s={} g={} {} {}".format(tag, note, v["s"], v["g"], v["st"], v["clean"]), fill=0)
  a4.save(str(out / (tag.lower() + ".png")), dpi=(150, 150))
  print("   {} saved ({} KB)".format(tag, len(b) // 1024), flush=True)
  time.sleep(2)
 pngs = sorted(out.glob("v*.png"))
 if pngs:
  from fpdf import FPDF
  pdf = FPDF(orientation="P", unit="mm", format="A4")
  pdf.set_auto_page_break(auto=False)
  pdf.set_margins(0, 0, 0)
  pdf.set_title("Style Review R2 - pure line-art 10 variants")
  for p in pngs:
   pdf.add_page()
   pdf.image(str(p), x=0, y=0, w=210, h=297)
  pp = out / "review_styles_round2.pdf"
  pdf.output(str(pp))
  print("DONE: {} -> {}".format(len(pngs), pp))
 else:
  print("No images!")

if __name__ == "__main__":
 main()
