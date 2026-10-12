"""Image Agent - Generates coloring book images using free APIs."""
import os
import time
import base64
import requests
from pathlib import Path

from loguru import logger
from .utils import sanitize_for_log


class ImageAgent:
    def __init__(self, config: dict, env: dict):
        self.config = config
        self.env = env
        self.providers = config["apis"]
        self.gen_config = config["generation"]
        self.raw_dir = config["paths"]["output_raw"]

    def _download(self, url, save_path, timeout=120):
        try:
            resp = requests.get(url, timeout=timeout, stream=True)
            if not resp.ok:
                logger.error("Download failed HTTP {}: {}".format(
                    resp.status_code,
                    sanitize_for_log(resp.text),
                ))
                return False
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return os.path.getsize(save_path) > 1000
        except Exception as e:
            logger.error("Download failed: {}".format(e))
            return False

    def _generate_nvidia(self, prompt, save_path):
        api_key = self.env.get("NVIDIA_API_KEY", "")
        if not api_key or api_key.startswith("nvapi-your"):
            logger.warning("NVIDIA_API_KEY is missing or still a placeholder")
            return False
        cfg = self.providers["nvidia"]
        headers = {
            "Authorization": "Bearer " + api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "text_prompts": [
                {"text": prompt, "weight": 1.0},
                {"text": self.config["prompts"]["negative_prompt"], "weight": -1.0},
            ],
            "cfg_scale": cfg["cfg_scale"],
            "height": cfg["height"],
            "width": cfg["width"],
            "sampler": cfg.get("sampler", "K_DPM_2_ANCESTRAL"),
            "steps": cfg["steps"],
            "samples": 1,
            "seed": int(time.time() * 1000) % 1000000,
            "style_preset": "none",
            "clip_guidance_preset": "NONE",
        }
        try:
            resp = requests.post(cfg["base_url"], headers=headers, json=payload, timeout=120)
            if not resp.ok:
                logger.warning("NVIDIA generation failed HTTP {}: {}".format(
                    resp.status_code,
                    sanitize_for_log(resp.text, [api_key]),
                ))
                return False
            data = resp.json()
            if "artifacts" in data and len(data["artifacts"]) > 0:
                img_b64 = data["artifacts"][0]["base64"]
                img_bytes = base64.b64decode(img_b64)
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(img_bytes)
                return os.path.getsize(save_path) > 1000
            logger.warning("NVIDIA response did not include image artifacts: {}".format(
                sanitize_for_log(data, [api_key]),
            ))
        except Exception as e:
            logger.warning("NVIDIA generation failed: {}".format(
                sanitize_for_log(e, [api_key]),
            ))
        return False

    def _generate_huggingface(self, prompt, save_path):
        token = self.env.get("HF_TOKEN", "")
        if not token or token.startswith("hf_your"):
            logger.warning("HF_TOKEN is missing or still a placeholder")
            return False
        cfg = self.providers["huggingface"]
        model = cfg.get("model", "stabilityai/stable-diffusion-xl-base-1.0")
        provider = cfg.get("provider", "auto")
        negative_prompt = self.config["prompts"]["negative_prompt"]
        try:
            from huggingface_hub import InferenceClient

            try:
                client = InferenceClient(token=token, provider=provider)
            except TypeError:
                client = InferenceClient(token=token)
            image = client.text_to_image(
                prompt,
                negative_prompt=negative_prompt,
                height=cfg.get("height"),
                width=cfg.get("width"),
                num_inference_steps=cfg.get("steps"),
                guidance_scale=cfg.get("guidance_scale"),
                model=model,
            )
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            image.save(save_path)
            return os.path.getsize(save_path) > 1000
        except ImportError:
            logger.warning("HuggingFace client not installed - falling back to direct HTTP")
        except Exception as e:
            logger.warning("HuggingFace client generation failed: {}".format(
                sanitize_for_log(e, [token]),
            ))

        headers = {"Authorization": "Bearer " + token}
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": negative_prompt,
                "height": cfg.get("height"),
                "width": cfg.get("width"),
                "num_inference_steps": cfg.get("steps"),
                "guidance_scale": cfg.get("guidance_scale"),
            },
        }
        try:
            resp = requests.post(cfg["base_url"], headers=headers, json=payload, timeout=120)
            if not resp.ok:
                logger.warning("HuggingFace direct HTTP failed HTTP {}: {}".format(
                    resp.status_code,
                    sanitize_for_log(resp.text, [token]),
                ))
                return False
            if resp.headers.get("content-type", "").startswith("image"):
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return os.path.getsize(save_path) > 1000
            logger.warning("HuggingFace direct HTTP returned non-image content: {}".format(
                sanitize_for_log(resp.text, [token]),
            ))
        except Exception as e:
            logger.warning("HuggingFace generation failed: {}".format(
                sanitize_for_log(e, [token]),
            ))
        return False

    def _generate_cloudflare(self, prompt, save_path):
        """Generate image via Cloudflare Workers AI (free tier: 10k neurons/day)."""
        account_id = self.env.get("CLOUDFLARE_ACCOUNT_ID", "")
        api_token = self.env.get("CLOUDFLARE_API_TOKEN", "")
        if not account_id or not api_token:
            logger.warning("CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN missing")
            return False
        cfg = self.providers["cloudflare"]
        model = cfg.get("model", "@cf/bytedance/stable-diffusion-xl-lightning")
        url = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/{}".format(account_id, model)
        headers = {
            "Authorization": "Bearer " + api_token,
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "negative_prompt": self.config["prompts"]["negative_prompt"],
            "height": cfg.get("height", 1024),
            "width": cfg.get("width", 1024),
            "num_steps": cfg.get("num_steps", 8),
            "guidance": cfg.get("guidance", 7.5),
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            if not resp.ok:
                logger.warning("Cloudflare generation failed HTTP {}: {}".format(
                    resp.status_code, sanitize_for_log(resp.text, [api_token])))
                return False
            # Cloudflare SDXL returns raw image bytes (Content-Type: image/*)
            ct = resp.headers.get("content-type", "")
            if ct.startswith("image"):
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return os.path.getsize(save_path) > 1000
            # Otherwise expect JSON with base64 image
            data = resp.json()
            img_b64 = None
            if isinstance(data.get("result"), dict):
                img_b64 = data["result"].get("image")
            elif isinstance(data.get("result"), str):
                img_b64 = data["result"]
            if img_b64:
                if img_b64.startswith("data:"):
                    img_b64 = img_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(img_b64)
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(img_bytes)
                return os.path.getsize(save_path) > 1000
            logger.warning("Cloudflare response missing image: {}".format(
                sanitize_for_log(data, [api_token])))
        except Exception as e:
            logger.warning("Cloudflare generation failed: {}".format(
                sanitize_for_log(e, [api_token])))
        return False

    def _generate_pollinations(self, prompt, save_path):
        """Generate image via Pollinations.ai (FREE, no key needed)."""
        import urllib.parse
        cfg = self.providers.get("pollinations", {})
        model = cfg.get("model", "flux")
        width = cfg.get("width", 1024)
        height = cfg.get("height", 1024)
        seed = int(time.time() * 1000) % 1000000
        encoded = urllib.parse.quote(prompt[:1500])
        url = "https://image.pollinations.ai/prompt/{}?width={}&height={}&seed={}&nologo=true&model={}".format(
            encoded, width, height, seed, model)
        try:
            resp = requests.get(url, timeout=180)
            if not resp.ok:
                logger.warning("Pollinations failed HTTP {}: {}".format(
                    resp.status_code, sanitize_for_log(resp.text[:500])))
                return False
            ct = resp.headers.get("content-type", "")
            if "image" not in ct and len(resp.content) < 1000:
                logger.warning("Pollinations returned non-image: {}".format(
                    sanitize_for_log(resp.text[:500])))
                return False
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return os.path.getsize(save_path) > 1000
        except Exception as e:
            logger.warning("Pollinations generation failed: {}".format(e))
            return False

    def _get_provider_func(self, name):
        return {
            "pollinations": self._generate_pollinations,
            "cloudflare": self._generate_cloudflare,
            "nvidia": self._generate_nvidia,
            "huggingface": self._generate_huggingface,
        }.get(name)

    def generate_single(self, prompt, save_path, index=0, total=0):
        providers = self.gen_config["provider_priority"]
        max_retries = self.gen_config["max_retries"]
        for attempt in range(max_retries):
            for provider_name in providers:
                func = self._get_provider_func(provider_name)
                if not func:
                    continue
                logger.debug("[{}/{}] Trying {} (attempt {})".format(index, total, provider_name, attempt + 1))
                if func(prompt, save_path):
                    logger.success("[{}/{}] Image saved via {}".format(index, total, provider_name))
                    return True
            if attempt < max_retries - 1:
                delay = self.gen_config["retry_delay"]
                logger.warning("[{}/{}] Retrying in {}s".format(index, total, delay))
                time.sleep(delay)
        logger.error("[{}/{}] Failed after {} attempts".format(index, total, max_retries))
        return False

    def generate_all(self, prompts):
        total = len(prompts["pages"]) + 1
        saved_paths = []
        Path(self.raw_dir).mkdir(parents=True, exist_ok=True)

        cover = prompts["cover"]
        cover_path = os.path.join(self.raw_dir, "cover.png")
        logger.info("Generating cover image...")
        if self.generate_single(cover["image_prompt"], cover_path, 1, total):
            saved_paths.append(cover_path)
        else:
            logger.error("Failed to generate cover image")
            return []

        for i, page in enumerate(prompts["pages"]):
            page_num = page["page_number"]
            page_path = os.path.join(self.raw_dir, "page_{:03d}.png".format(page_num))
            logger.info("Generating page {}/{}".format(page_num, len(prompts["pages"])))
            if self.generate_single(page["image_prompt"], page_path, i + 2, total):
                saved_paths.append(page_path)
            else:
                logger.warning("Skipping page {} - generation failed".format(page_num))
                saved_paths.append(None)

        success_count = sum(1 for p in saved_paths if p is not None)
        logger.success("Generated {}/{} images successfully".format(success_count, total))
        return saved_paths

