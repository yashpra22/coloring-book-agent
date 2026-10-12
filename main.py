"""
Daily Coloring Book Agent — Main Orchestrator

Pipeline:
1. Generate creative prompts (LLM or template)
2. Generate images (Pollinations → NVIDIA → HuggingFace)
3. Process to line art (OpenCV + PIL)
4. Assemble A4 PDF

Usage:
    python main.py                  # Generate today's book
    python main.py --pages 50       # Custom page count
    python main.py --dry-run        # Generate prompts only, no images
"""
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from agents.utils import (
    setup_logging, load_config, load_themes, load_env,
    ensure_dirs, get_date_str, save_json,
)
from agents.prompt_agent import PromptAgent
from agents.image_agent import ImageAgent
from agents.process_agent import ProcessAgent
from agents.pdf_agent import PDFAgent


def main():
    parser = argparse.ArgumentParser(description="Daily Kids Coloring Book Agent")
    parser.add_argument("--pages", type=int, default=None, help="Number of pages (default: from config)")
    parser.add_argument("--dry-run", action="store_true", help="Generate prompts only")
    parser.add_argument("--config", default="config/settings.yaml", help="Config file path")
    parser.add_argument("--themes", default="config/themes.yaml", help="Themes file path")
    args = parser.parse_args()

    # ── Setup ──
    setup_logging()
    load_dotenv()

    config = load_config(args.config)
    themes = load_themes(args.themes)
    env = load_env()

    if args.pages:
        config["book"]["pages"] = args.pages

    ensure_dirs(config)
    date_str = get_date_str()

    logger.info("=" * 60)
    logger.info(f"  Daily Coloring Book Agent — {date_str}")
    logger.info(f"  Pages: {config['book']['pages']} + 1 cover")
    logger.info(f"  Size: A4 @ {config['book']['dpi']} DPI")
    logger.info("=" * 60)

    # ── Phase 1: Generate Prompts ──
    logger.info("─── Phase 1: Generating Prompts ───")
    prompt_agent = PromptAgent(config, themes, env)
    prompts = prompt_agent.generate()

    # Save prompts for reference
    save_json(prompts, os.path.join(config["paths"]["output_prompts"], f"prompts_{date_str}.json"))

    if args.dry_run:
        logger.success("Dry run complete — prompts saved. No images generated.")
        logger.info(f"Cover title: {prompts['cover']['title']}")
        logger.info(f"First 5 pages: {[p['description'][:50] for p in prompts['pages'][:5]]}")
        return

    # ── Phase 2: Generate Images ──
    logger.info("─── Phase 2: Generating Images ───")
    image_agent = ImageAgent(config, env)
    raw_paths = image_agent.generate_all(prompts)

    success_raw = sum(1 for p in raw_paths if p is not None)
    if success_raw == 0:
        logger.error("No images generated. Aborting.")
        sys.exit(1)

    # ── Phase 3: Process Line Art ──
    logger.info("─── Phase 3: Processing Line Art ───")
    process_agent = ProcessAgent(config)
    processed_paths = process_agent.process_all(raw_paths)

    success_processed = sum(1 for p in processed_paths if p is not None)
    if success_processed == 0:
        logger.error("No images processed. Aborting.")
        sys.exit(1)

    # ── Phase 4: Build PDF ──
    logger.info("─── Phase 4: Building PDF ───")
    pdf_agent = PDFAgent(config)
    pdf_path = pdf_agent.build_pdf(
        processed_paths,
        prompts["cover"]["title"],
        date_str,
    )

    # ── Summary ──
    logger.info("=" * 60)
    logger.info("  GENERATION COMPLETE")
    logger.info(f"  Cover: {prompts['cover']['title']}")
    logger.info(f"  Images generated: {success_raw}/{len(raw_paths)}")
    logger.info(f"  Images processed: {success_processed}/{len(processed_paths)}")
    logger.info(f"  PDF: {pdf_path}")
    logger.info(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
