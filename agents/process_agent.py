"""Process Agent - Prepares Cloudflare line art for print (A4 @ 300 DPI).

Default: soft contrast + sharpen + A4 resize (raw line art untouched).
Optional: clean_background=true (adaptive threshold) + dilate_lines=true.
"""
import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

from loguru import logger


class ProcessAgent:
    def __init__(self, config: dict):
        self.config = config
        self.proc_config = config["processing"]
        self.processed_dir = config["paths"]["output_processed"]
        self.dpi = config["book"]["dpi"]
        self.margin_mm = config["book"]["margin_mm"]
        # A4 at 300 DPI
        self.a4_width = int(210 * self.dpi / 25.4)
        self.a4_height = int(297 * self.dpi / 25.4)
        self.margin_px = int(self.margin_mm * self.dpi / 25.4)

    def _threshold(self, img_array):
        # Adaptive threshold handles uneven AI shading better than Otsu.
        # Block size / C config se aate hain (processing.threshold_*).
        block = int(self.proc_config.get("threshold_block_size", 71))
        if block % 2 == 0:
            block += 1
        c_val = int(self.proc_config.get("threshold_c", 10))
        return cv2.adaptiveThreshold(
            img_array, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block, c_val,
        )

    def _dilate_lines(self, img_array):
        if not self.proc_config["dilate_lines"]:
            return img_array
        kernel = np.ones(
            (self.proc_config["dilate_kernel_size"], self.proc_config["dilate_kernel_size"]),
            np.uint8,
        )
        inverted = cv2.bitwise_not(img_array)
        dilated = cv2.dilate(inverted, kernel, iterations=1)
        return cv2.bitwise_not(dilated)

    def _resize_to_a4(self, img):
        content_w = self.a4_width - (2 * self.margin_px)
        content_h = self.a4_height - (2 * self.margin_px)
        img.thumbnail((content_w, content_h), Image.LANCZOS)
        canvas = Image.new("L", (self.a4_width, self.a4_height), 255)
        x = (self.a4_width - img.width) // 2
        y = (self.a4_height - img.height) // 2
        canvas.paste(img, (x, y))
        return canvas


    def process_image(self, input_path, output_path):
        try:
            img = Image.open(input_path)
            if img.mode != "L":
                img = img.convert("L")
            img_array = np.array(img)
            cfg = self.proc_config

            if cfg.get("clean_background", False):
                processed = self._threshold(img_array)
                if cfg.get("dilate_lines", False):
                    processed = self._dilate_lines(processed)
                line_art = Image.fromarray(processed)
            else:
                line_art = Image.fromarray(img_array)

            if cfg.get("enhance_contrast", True):
                enhancer = ImageEnhance.Contrast(line_art)
                line_art = enhancer.enhance(cfg["contrast_factor"])

            if cfg.get("sharpen", True):
                line_art = line_art.filter(ImageFilter.SHARPEN)

            line_art = self._resize_to_a4(line_art)

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            line_art.save(output_path, "PNG", dpi=(self.dpi, self.dpi))
            return True
        except Exception as e:
            logger.error("Processing failed for {}: {}".format(input_path, e))
            return False

    def process_all(self, image_paths):
        Path(self.processed_dir).mkdir(parents=True, exist_ok=True)
        processed_paths = []
        for i, img_path in enumerate(image_paths):
            if img_path is None:
                processed_paths.append(None)
                continue
            filename = os.path.basename(img_path)
            output_path = os.path.join(self.processed_dir, filename)
            if self.process_image(img_path, output_path):
                processed_paths.append(output_path)
                logger.info("Processed {}/{}: {}".format(i + 1, len(image_paths), filename))
            else:
                processed_paths.append(None)
        success = sum(1 for p in processed_paths if p is not None)
        logger.success("Processed {}/{} images".format(success, len(image_paths)))
        return processed_paths
