"""Style Review ROUND 4: FLUX + light cleaning. python scripts/style_review4.py"""
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
SUBJECTS = [
 "chubby baby bear wearing garden hat planting flower with shovel, two happy kittens helping, watering can, pots, seed packets, gloves, big flowers, butterfly",
 "chubby baby bear teacher pointing at big blank whiteboard, three cute kittens at school desks with open books, backpack, globe, pencils, classroom",
 "chubby baby bear and three kittens camping around campfire roasting marshmallows, tent, pine trees, moon stars, backpack, lantern, sleeping bag",
 "chubby baby bear chef baking cookies with two kittens in cozy kitchen, mixing bowl, cookies tray, cupcakes, milk bottle, jars, oven",
 "chubby baby bear picnic with two kittens on checkered blanket, picnic basket, apples, watermelon, juice, sandwiches, flowers, butterflies, park",
 "chubby baby bear building sandcastle with two kittens on beach, bucket spade, beach ball, crab, starfish, shells, palm tree, sailboat, sun, waves",
 "chubby baby bear birthday party with two kittens in party hats, big birthday cake candles, balloons, gifts, bunting flags, confetti, treats table",
 "chubby baby bear doctor checking kitten patient with stethoscope, two kittens waiting, bed, medicine kit, bandage, clipboard, hearts",
 "chubby baby bear painting rainbow on easel with two kittens painting, paint pots, brushes, palette, crayons, pictures on wall, sun clouds",
 "chubby baby bear astronaut with two kittens in space helmets in cute rocket, planets, moon, stars, alien friend, saturn, comet",
]
LABELS = ["gardening", "classroom", "camping", "baking", "picnic", "beach", "birthday", "doctor", "painting", "space"]
PW, PH = 768, 1152
SW, SH = 1024, 1024
NEG = "color, shading, shadow, gradient, stipple dots, noise, texture, fur detail, crosshatching, hatching, heavy black fills, photorealistic, photo, 3d render, painting, watercolor, sketchy, messy, blurry, watermark, text, letters"
FULL = "vertical portrait, fills entire page top to bottom edge to edge, full-bleed, pure white paper background, black outlines only"
EMPTY = "all shapes EMPTY WHITE INSIDE, white fill inside every shape, no fill, no solid black areas, no shading, no gradients, no grey tones, no colors"
CORE = "professional children coloring book illustration, kawaii style, smooth clean thick black outlines, simple flat shapes, NO texture NO fur NO stippling, chubby cute baby animals with solid black dot eyes and happy smiles, FULL-PAGE story scene edge to edge, 3-4 characters interacting, MANY simple colorable props, pure white paper background"
VARIANTS = [
 {"g": None, "clean": "light200"},
 {"g": None, "clean": "light200"},
 {"g": None, "clean": "light210"},
 {"g": None, "clean": "none"},
 {"g": None, "clean": "light200"},
 {"g": None, "clean": "light210"},
 {"g": None, "clean": "none"},
 {"g": None, "clean": "light200"},
 {"g": None, "clean": "light210"},
 {"g": None, "clean": "none"},
]
MODEL = "@cf/black-forest-labs/flux-1-schnell"
def cf_gen(prompt, w, h, steps, guidance, neg=None, seed=0):
 url = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/{}".format(ACCOUNT, MODEL)
 hd = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}
 pl = {"prompt": prompt, "steps": 4}
 try:
  r = requests.post(url, headers=hd, json=pl, timeout=300)
 except Exception as e:
  print("   req err:", e)
  return None
 if not r.ok:
  print("   CF HTTP {}: {}".format(r.status_code, r.text[:300]))
  return None
 ct = r.headers.get("content-type", "")
 if "image" in ct:
  return r.content
 try:
  data = r.json()
  res = data.get("result", data)
  img_b64 = res.get("image", "")
  if img_b64:
   import base64 as _b64
   return _b64.b64decode(img_b64)
  print("   CF non-image JSON:", str(data)[:300])
  return None
 except Exception as e:
  print("   parse err:", e)
  return None
 return None

def clean_bw(gray_arr, mode):
 if mode == "none":
  return gray_arr
 thresh = {"light200": 200, "light210": 210, "light190": 190}.get(mode, 200)
 _, bw = cv2.threshold(gray_arr, thresh, 255, cv2.THRESH_BINARY)
 nb, labels, stats, _c = cv2.connectedComponentsWithStats((bw == 0).astype(np.uint8), connectivity=8)
 out = bw.copy()
 for lbl in range(1, nb):
  if stats[lbl, cv2.CC_STAT_AREA] < 12:
   out[labels == lbl] = 255
 return out

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
 out = Path(__file__).resolve().parents[1] / "output" / "review4"
 out.mkdir(parents=True, exist_ok=True)
 for i, v in enumerate(VARIANTS, start=1):
  tag = "V{:02d}".format(i)
  subj = SUBJECTS[i - 1]
  label = LABELS[i - 1]
  pr = "{}, {}, {}, {}. Avoid: {}".format(subj, FULL, CORE, EMPTY, NEG)
  print("[{}/10] {} ({}) {} seed={}".format(i, tag, label, v["clean"], 100 + i), flush=True)
  b = cf_gen(pr, PW, PH, 4, None, seed=100 + i)
  note = "{}x{}".format(PW, PH)
  if b is None:
   print("   portrait fail -> square retry")
   b = cf_gen(pr, SW, SH, 4, None, seed=200 + i)
   note = "1024sq-fallback"
  if b is None:
   print("   {} FAILED".format(tag))
   continue
  a4 = to_a4(b, v["clean"])
  from PIL import ImageDraw
  d = ImageDraw.Draw(a4)
  d.rectangle([0, a4.height - 44, a4.width, a4.height], fill=255)
  d.text((20, a4.height - 32), "{} | {} | {} ({})".format(tag, note, v["clean"], label), fill=0)
  a4.save(str(out / (tag.lower() + ".png")), dpi=(150, 150))
  print("   {} saved ({} KB)".format(tag, len(b) // 1024), flush=True)
  time.sleep(2)
 pngs = sorted(out.glob("v*.png"))
 if pngs:
  from fpdf import FPDF
  pdf = FPDF(orientation="P", unit="mm", format="A4")
  pdf.set_auto_page_break(auto=False)
  pdf.set_margins(0, 0, 0)
  pdf.set_title("Style Review R4 - FLUX smooth line art")
  for p in pngs:
   pdf.add_page()
   pdf.image(str(p), x=0, y=0, w=210, h=297)
  pp = out / "review_styles_round4.pdf"
  pdf.output(str(pp))
  print("DONE: {} -> {}".format(len(pngs), pp))
 else:
  print("No images!")

if __name__ == "__main__":
 main()
