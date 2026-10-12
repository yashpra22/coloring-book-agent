"""Prompt Agent — Generates creative, diverse coloring book prompts using free LLMs."""
import json
import random
import time
import requests
from typing import List, Dict, Optional

from loguru import logger
from .utils import prompt_hash, sanitize_for_log


class PromptAgent:
    def __init__(self, config: dict, themes: dict, env: dict):
        self.config = config
        self.themes = themes
        self.env = env
        self.api_key = env.get("OPENROUTER_API_KEY", "")
        self.base_url = config["apis"]["openrouter"]["base_url"]
        self.model = config["apis"]["openrouter"]["model"]
        self.fallback_models = config["apis"]["openrouter"]["fallback_models"]
        self.max_tokens = config["apis"]["openrouter"]["max_tokens"]
        self.temperature = config["apis"]["openrouter"]["temperature"]

    def _call_llm(self, messages, model=None):
        model = model or self.model
        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        try:
            url = self.base_url.rstrip("/") + "/chat/completions"
            resp = requests.post(
                url,
                headers=headers, json=payload, timeout=60,
            )
            if not resp.ok:
                logger.warning(
                    "LLM call failed ({}) HTTP {}: {}".format(
                        model,
                        resp.status_code,
                        sanitize_for_log(resp.text, [self.api_key]),
                    )
                )
                return None
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("LLM call failed ({}): {}".format(
                model,
                sanitize_for_log(e, [self.api_key]),
            ))
            return None

    def _parse_json(self, text):
        try:
            text = text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
        except Exception:
            return None

    def _parse_json_list(self, text, expected):
        try:
            text = text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            data = json.loads(text.strip())
            if isinstance(data, list) and len(data) >= expected * 0.5:
                while len(data) < expected:
                    data.append(data[len(data) % len(data)])
                return data[:expected]
            return None
        except Exception:
            return None

    def _generate_with_llm(self, num_pages):
        if not self.api_key:
            logger.info("No OpenRouter API key - using template generation")
            return None

        system_prompt = (
            "You are a creative children's coloring book designer. "
            "You generate unique, diverse, kid-friendly coloring page descriptions. "
            "Each description should be a vivid scene for a black-and-white line art coloring page."
        )

        cover_themes = ", ".join(random.sample(
            self.themes["cover_themes"],
            k=min(3, len(self.themes["cover_themes"]))
        ))
        cover_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                "Generate ONE creative cover page description for a kids coloring book. "
                "The cover should feature: " + cover_themes + ". "
                'Return ONLY a JSON object: {"title": "catchy book title", '
                '"scene": "detailed cover scene under 50 words"}'
            )},
        ]

        all_subjects = []
        for category, subjects in self.themes["categories"].items():
            all_subjects.extend(subjects)
        random.shuffle(all_subjects)

        subject_list = chr(10).join(all_subjects[:30])
        page_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                "Generate exactly {} unique coloring page descriptions for kids. ".format(num_pages) +
                "Mix of animals, vehicles, fantasy, nature, space, food, daily life, seasonal. " +
                "Each vivid and detailed (20-40 words). No repetition. " +
                "Inspiration: " + subject_list + " " +
                "Return ONLY a JSON array of strings. Exactly {} items.".format(num_pages)
            )},
        ]

        models_to_try = [self.model] + self.fallback_models
        cover_result = None
        pages_result = None

        for model in models_to_try:
            if cover_result is None:
                logger.info("Generating cover prompt with {}...".format(model))
                cover_raw = self._call_llm(cover_messages, model)
                if cover_raw:
                    cover_result = self._parse_json(cover_raw)
                    if cover_result:
                        logger.success("Cover prompt generated with " + model)

            if pages_result is None:
                logger.info("Generating page prompts with {}...".format(model))
                pages_raw = self._call_llm(page_messages, model)
                if pages_raw:
                    pages_result = self._parse_json_list(pages_raw, num_pages)
                    if pages_result:
                        logger.success("Page prompts generated with " + model)

            if cover_result and pages_result:
                break
            time.sleep(1)

        if not pages_result:
            logger.warning("LLM generation failed - falling back to templates")
            return None

        return {"cover": cover_result or self._template_cover(), "pages": pages_result}

    def _template_cover(self):
        title = random.choice(self.themes["cover_titles"])
        theme = random.choice(self.themes["cover_themes"])
        return {
            "title": title,
            "scene": "A magical coloring book cover featuring " + theme + ", with decorative border elements",
        }

    def _generate_with_templates(self, num_pages):
        logger.info("Generating prompts from templates...")
        all_subjects = []
        for category, subjects in self.themes["categories"].items():
            all_subjects.extend(subjects)
        random.shuffle(all_subjects)

        pages = []
        for i in range(num_pages):
            if i < len(all_subjects):
                pages.append(all_subjects[i])
            else:
                base = all_subjects[i % len(all_subjects)]
                variation = random.choice([
                    "with a rainbow in the background",
                    "in a magical forest setting",
                    "surrounded by flowers and butterflies",
                    "under a starry night sky",
                    "near a sparkling waterfall",
                    "in a cozy meadow",
                    "with friends around",
                    "on a sunny day",
                ])
                pages.append(base + ", " + variation)

        return {"cover": self._template_cover(), "pages": pages}

    def _build_page_prompt(self, description):
        style = self.config["prompts"]["page_style_suffix"]
        negative = self.config["prompts"]["negative_prompt"]
        return description + ", " + style + ". Avoid: " + negative

    def _build_cover_prompt(self, title, scene):
        style = self.config["prompts"]["cover_style_suffix"]
        return scene + ', with the title "' + title + '" in bold decorative letters at the top, ' + style

    def generate(self):
        num_pages = self.config["book"]["pages"]
        logger.info("Generating prompts for {} pages + 1 cover...".format(num_pages))

        result = self._generate_with_llm(num_pages)
        if not result:
            result = self._generate_with_templates(num_pages)

        cover = result["cover"]
        final_prompts = {
            "cover": {
                "title": cover.get("title", "My Coloring Book"),
                "scene": cover.get("scene", "A magical coloring scene"),
                "image_prompt": self._build_cover_prompt(
                    cover.get("title", "My Coloring Book"),
                    cover.get("scene", "A magical coloring scene"),
                ),
                "hash": prompt_hash(cover.get("scene", "")),
            },
            "pages": [],
        }

        for i, desc in enumerate(result["pages"]):
            final_prompts["pages"].append({
                "page_number": i + 1,
                "description": desc,
                "image_prompt": self._build_page_prompt(desc),
                "hash": prompt_hash(desc),
            })

        logger.success("Generated {} page prompts + 1 cover prompt".format(len(final_prompts["pages"])))
        return final_prompts

