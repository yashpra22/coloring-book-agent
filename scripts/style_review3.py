"""Style Review ROUND 3: creative STORY scenes. python scripts/style_review3.py"""
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
NEG = "color, colored, filled shapes, solid fill, solid black areas, black fill, grey fill, grey wash, shading, shadow, gradient, crosshatching, hatching, photorealistic, photo, 3d render, painting, watercolor, sketchy, messy lines, blurry, watermark, text, dark background, grey background"
FULL = "vertical portrait, fills entire page top to bottom edge to edge, full-bleed, pure white paper background, black outlines only"
EMPTY = "all shapes EMPTY WHITE INSIDE, white fill inside every shape, no fill, no solid black areas, no shading, no gradients, no grey tones, no colors"
CORE = "children coloring book page, kawaii storybook, chubby cute baby animals with big round dot eyes happy smiles, FULL-PAGE dense story scene top to bottom edge to edge, 3-4 characters interacting doing activity, MANY simple props filling all space, thick bold black outlines ONLY on pure white paper"
VARIANTS = [
 {"g": 3.5, "clean": "adapt71"},
 {"g": 3.5, "clean": "adapt71"},
 {"g": 3.5, "clean": "adapt71"},
 {"g": 4.0, "clean": "adapt71"},
 {"g": 4.0, "clean": "adapt101"},
 {"g": 4.0, "clean": "adapt71"},
 {"g": 3.5, "clean": "adapt101"},
 {"g": 4.0, "clean": "adapt71"},
 {"g": 3.5, "clean": "adapt71"},
 {"g": 4.0, "clean": "adapt101"},
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
 out = Path(__file__).resolve().parents[1] / "output" / "review3"
 out.mkdir(parents=True, exist_ok=True)
 for i, v in enumerate(VARIANTS, start=1):
  tag = "V{:02d}".format(i)
  subj = SUBJECTS[i - 1]
  label = LABELS[i - 1]
  pr = "{}, {}, {}, {}. Avoid: {}".format(subj, FULL, CORE, EMPTY, NEG)
  print("[{}/10] {} ({}) g={} {}".format(i, tag, label, v["g"], v["clean"]), flush=True)
  b = cf_gen(pr, PW, PH, 8, v["g"], neg=NEG)
  note = "{}x{}".format(PW, PH)
  if b is None:
   print("   portrait fail -> square retry")
   b = cf_gen(pr, SW, SH, 8, v["g"], neg=NEG)
   note = "1024sq-fallback"
  if b is None:
   print("   {} FAILED".format(tag))
   continue
  a4 = to_a4(b, v["clean"])
  from PIL import ImageDraw
  d = ImageDraw.Draw(a4)
  d.rectangle([0, a4.height - 44, a4.width, a4.height], fill=255)
  d.text((20, a4.height - 32), "{} | {} | g={} {} ({})".format(tag, note, v["g"], v["clean"], label), fill=0)
  a4.save(str(out / (tag.lower() + ".png")), dpi=(150, 150))
  print("   {} saved ({} KB)".format(tag, len(b) // 1024), flush=True)
  time.sleep(2)
 pngs = sorted(out.glob("v*.png"))
 if pngs:
  from fpdf import FPDF
  pdf = FPDF(orientation="P", unit="mm", format="A4")
  pdf.set_auto_page_break(auto=False)
  pdf.set_margins(0, 0, 0)
  pdf.set_title("Style Review R3 - creative story scenes")
  for p in pngs:
   pdf.add_page()
   pdf.image(str(p), x=0, y=0, w=210, h=297)
  pp = out / "review_styles_round3.pdf"
  pdf.output(str(pp))
  print("DONE: {} -> {}".format(len(pngs), pp))
 else:
  print("No images!")

if __name__ == "__main__":
 main()
