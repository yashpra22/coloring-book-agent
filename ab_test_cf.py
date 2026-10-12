"""Quick A/B: same coloring prompt, 3 Cloudflare models. Saves raw PNGs."""
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
ACC = os.environ['CLOUDFLARE_ACCOUNT_ID']
TOK = os.environ['CLOUDFLARE_API_TOKEN']

PROMPT = ('cute baby elephant playing with balloons, kids coloring book page, '
          'clean bold black outlines only, thick lines, pure white background, '
          'simple cartoon shapes, large open areas to color, no shading, '
          'no grey, no color, flat line drawing')
NEG = ('color, shading, gradient, shadow, photorealistic, 3d render, '
       'blurry, watermark, text, grey fill')

MODELS = [
    ('lightning', '@cf/bytedance/stable-diffusion-xl-lightning', 8, 2.0),
    ('sdxl-base', '@cf/stabilityai/stable-diffusion-xl-base-1.0', 20, 7.5),
    ('dreamshaper', '@cf/lykon/dreamshaper-8-lcm', 20, 7.5),
]

out = Path('ab_test')
out.mkdir(exist_ok=True)
for name, model, steps, guidance in MODELS:
    url = 'https://api.cloudflare.com/client/v4/accounts/{}/ai/run/{}'.format(ACC, model)
    print('Trying {} ...'.format(name), flush=True)
    r = requests.post(url, headers={'Authorization': 'Bearer ' + TOK,
                                     'Content-Type': 'application/json'},
                      json={'prompt': PROMPT, 'negative_prompt': NEG,
                            'height': 1024, 'width': 1024,
                            'num_steps': steps, 'guidance': guidance},
                      timeout=180)
    print('  HTTP', r.status_code, '| content-type:', r.headers.get('content-type'), flush=True)
    if r.ok and r.headers.get('content-type', '').startswith('image'):
        (out / (name + '.png')).write_bytes(r.content)
        print('  saved {}.png ({} bytes)'.format(name, len(r.content)), flush=True)
    else:
        print('  FAIL:', r.text[:300], flush=True)
print('DONE -> open ab_test/ folder and compare the 3 images')
