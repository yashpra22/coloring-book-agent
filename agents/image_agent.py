"""Image Agent - Generates coloring book images using free APIs."""
import os
import time
import base64
import requests
from pathlib import Path
from urllib.parse import quote

from loguru import logger


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
            resp.raise_for_status()
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return os.path.getsize(save_path) > 1000
        except Exception as e:
            logger.error("Download failed: {}".format(e))
            return False

    def _generate_pollinations(self, prompt, save_path):
        cfg = self.providers["pollinations"]
        encoded_prompt = quote(prompt)
        params = "?width={}&height={}&model={}&nologo={}&seed={}".format(
            cfg["width"], cfg["height"], cfg["model"],
            str(cfg["nologo"]).lower(), int(time.time()),
        )
        url = "{}/{}{}".format(cfg["base_url"], encoded_prompt, params)
        logger.debug("Pollinations URL: " + url[:100])
        return self._download(url, save_path, timeout=cfg["timeout"])

    def _generate_nvidia(self, prompt, save_path):
        api_key = self.env.get("NVIDIA_API_KEY", "")
        if not api_key:
            return False
        cfg = self.providers["nvidia"]
        headers = {
            "Authorization": "Bearer " + api_key,
            "Accept": "application/json",
        }
        payload = {
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": cfg["cfg_scale"],
            "height": cfg["height"],
            "width": cfg["width"],
            "sampler": "K_DPMPP_2M",
            "steps": cfg["steps"],
        }
        try:
            resp = requests.post(cfg["base_url"], headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            if "artifacts" in data and len(data["artifacts"]) > 0:
                img_b64 = data["artifacts"][0]["base64"]
                img_bytes = base64.b64decode(img_b64)
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(img_bytes)
                return os.path.getsize(save_path) > 1000
        except Exception as e:
            logger.warning("NVIDIA generation failed: {}".format(e))
        return False

    def _generate_huggingface(self, prompt, save_path):
        token = self.env.get("HF_TOKEN", "")
        if not token:
            return False
        cfg = self.providers["huggingface"]
        headers = {"Authorization": "Bearer " + token}
        payload = {"inputs": prompt}
        try:
            resp = requests.post(cfg["base_url"], headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            if resp.headers.get("content-type", "").startswith("image"):
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return os.path.getsize(save_path) > 1000
        except Exception as e:
            logger.warning("HuggingFace generation failed: {}".format(e))
        return False

    def _get_provider_func(self, name):
        return {
            "pollinations": self._generate_pollinations,
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

