"""Style Review: 10 A4 full-page variants, 1 subject. python scripts/style_review.py"""
import os, sys, time, requests
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()
ACCOUNT = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
SUBJECT = "cute baby elephant playing with three big balloons, smiling, waving trunk"
PW, PH = 768, 1152
SW, SH = 1024, 1024
NEG = "color, shading, gradient, shadow, photorealistic, 3d render, painting, sketchy, messy lines, thin lines, complex background, blurry, watermark, text, grey fill, dark background"
FULL = "vertical portrait composition, subject fills entire page top to bottom edge to edge, full-bleed, no margins"
STYLES = {
 "s1": "coloring book page, bold black line art on white, thick outlines, single centered subject, large open areas, flat 2D, no shading, no grey, no color",
 "s2": "full-page coloring scene, bold outlines, big central character plus hills clouds sun flowers butterflies background, every area outlined, busy cheerful, flat 2D, no shading, no grey, no color",
 "s3": "outline drawing, one big cute subject centered, extra thick outlines, empty white background, huge areas to color, very simple, flat 2D, no shading",
 "s4": "coloring page, medium clean outlines, cute detailed subject with stars dots background pattern, balanced open areas, flat 2D, no shading, no grey",
 "s5": "storybook coloring page, clear black line work, central animal with decorative frame border and corner ornaments, simple shapes, large open areas, no shading",
}
VARIANTS = [
 {"w": PW, "h": PH, "s": 8, "g": 3.5, "st": "s1", "nn": 0},
 {"w": PW, "h": PH, "s": 8, "g": 2.0, "st": "s1", "nn": 0},
 {"w": PW, "h": PH, "s": 8, "g": 7.0, "st": "s1", "nn": 0},
 {"w": PW, "h": PH, "s": 8, "g": 5.0, "st": "s1", "nn": 0},
 {"w": PW, "h": PH, "s": 8, "g": 3.5, "st": "s1", "nn": 1},
 {"w": PW, "h": PH, "s": 8, "g": 3.5, "st": "s2", "nn": 0},
 {"w": PW, "h": PH, "s": 8, "g": 3.5, "st": "s3", "nn": 0},
 {"w": PW, "h": PH, "s": 8, "g": 5.0, "st": "s4", "nn": 0},
 {"w": PW, "h": PH, "s": 8, "g": 5.0, "st": "s5", "nn": 0},
 {"w": PW, "h": PH, "s": 8, "g": 7.0, "st": "s2", "nn": 1},
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
def to_a4(raw):
 from io import BytesIO
 im = Image.open(BytesIO(raw))
 if im.mode != "L":
  im = im.convert("L")
 im = ImageEnhance.Contrast(im).enhance(1.2)
 im = im.filter(ImageFilter.SHARPEN)
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
 out = Path(__file__).resolve().parents[1] / "output" / "review"
 out.mkdir(parents=True, exist_ok=True)
 for i, v in enumerate(VARIANTS, start=1):
  tag = "V{:02d}".format(i)
  pr = "{}, {}, {}. Avoid: {}".format(SUBJECT, FULL, STYLES[v["st"]], NEG)
  print("[{}/10] {} {}x{} s={} g={} {} nn={}".format(i, tag, v["w"], v["h"], v["s"], v["g"], v["st"], v["nn"]))
  b = cf_gen(pr, v["w"], v["h"], v["s"], v["g"], neg=NEG if v["nn"] else None)
  note = "{}x{}".format(v["w"], v["h"])
  if b is None:
   print("   portrait fail -> square retry")
   b = cf_gen(pr, SW, SH, v["s"], v["g"], neg=NEG if v["nn"] else None)
   note = "1024sq-fallback"
  if b is None:
   print("   {} FAILED".format(tag))
   continue
  a4 = to_a4(b)
  from PIL import ImageDraw
  d = ImageDraw.Draw(a4)
  d.rectangle([0, a4.height - 44, a4.width, a4.height], fill=255)
  d.text((20, a4.height - 32), "{} | {} | s={} g={} {}".format(tag, note, v["s"], v["g"], v["st"]), fill=0)
  a4.save(str(out / (tag.lower() + ".png")), dpi=(150, 150))
  print("   {} saved ({} KB)".format(tag, len(b) // 1024))
  time.sleep(2)
 pngs = sorted(out.glob("v*.png"))
 if pngs:
  from fpdf import FPDF
  pdf = FPDF(orientation="P", unit="mm", format="A4")
  pdf.set_auto_page_break(auto=False)
  pdf.set_margins(0, 0, 0)
  pdf.set_title("Style Review - 10 A4 variants")
  for p in pngs:
   pdf.add_page()
   pdf.image(str(p), x=0, y=0, w=210, h=297)
  pp = out / "review_styles.pdf"
  pdf.output(str(pp))
  print("DONE: {} -> {}".format(len(pngs), pp))
 else:
  print("No images!")
if __name__ == "__main__":
 main()
