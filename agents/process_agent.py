"""Process Agent - Prepares Cloudflare line art for print (A4 @ 300 DPI).

Default: soft contrast + sharpen + A4 resize (raw line art untouched).
Optional: clean_background=true (adaptive threshold) + dilate_lines=true.
"""
import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from loguru import logger


class ProcessAgent:
    def __init__(self, config: dict):
        self.config = config
        self.proc_config = config["processing"]
        self.cover_cfg = config.get("cover", {})
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

    def _threshold_global(self, img_array):
        """Single global binary threshold — the Round-4 recipe.

        Everything lighter than `threshold_value` becomes pure white, so the
        soft grey wash / shading FLUX leaves behind disappears instead of being
        preserved the way adaptive threshold does.
        """
        value = int(self.proc_config.get("threshold_value", 200))
        _, bw = cv2.threshold(img_array, value, 255, cv2.THRESH_BINARY)
        return bw

    def _remove_speckles(self, img_array):
        """Delete tiny isolated black blobs (stipple dots, dither noise).

        Thresholding turns scattered grey pixels into 1-2px black islands that
        print as dirt. Any connected black component smaller than
        `speckle_min_area` is filled back to white. Real outlines are always
        much larger, so line detail survives.
        """
        min_area = int(self.proc_config.get("speckle_min_area", 12))
        if min_area <= 0:
            return img_array
        black = (img_array == 0).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(black, connectivity=8)
        out = img_array.copy()
        for label in range(1, count):
            if stats[label, cv2.CC_STAT_AREA] < min_area:
                out[labels == label] = 255
        return out

    def _clean(self, img_array):
        """Apply whichever threshold mode the config selects, then de-speckle."""
        mode = self.proc_config.get("threshold_mode", "global")
        if mode == "adaptive":
            processed = self._threshold(img_array)
        else:
            processed = self._threshold_global(img_array)
        if self.proc_config.get("speckle_removal", True):
            processed = self._remove_speckles(processed)
        return processed

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
        # FULL-BLEED A4: cover-fit crop (no letterbox bars) so the image
        # covers the whole page edge-to-edge, exactly like the PDF prints it.
        target_ratio = self.a4_width / self.a4_height
        w, h = img.size
        src_ratio = w / h
        if src_ratio > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))
        img = img.resize((self.a4_width, self.a4_height), Image.LANCZOS)
        return img


    def process_image(self, input_path, output_path):
        try:
            img = Image.open(input_path)
            if img.mode != "L":
                img = img.convert("L")
            img_array = np.array(img)
            cfg = self.proc_config

            if cfg.get("clean_background", False):
                processed = self._clean(img_array)
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
            # cover_color.png line-art pipeline se SKIP hota hai —
            # usko process_cover() alag se handle karta hai (RGB + title).
            if os.path.basename(img_path) == "cover_color.png":
                processed_paths.append(img_path)
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

    # ── Color Cover (ChatGPT-reference look) ────────────────
    def _fit_title_lines(self, draw, text, font_path, max_w, start_size, min_size):
        """Wrap title into <=3 lines, shrinking font until every line fits."""
        size = start_size
        while size >= min_size:
            font = ImageFont.truetype(font_path, size)
            words = text.split()
            lines, current = [], ""
            ok = True
            for word in words:
                candidate = (current + " " + word).strip()
                if draw.textlength(candidate, font=font) <= max_w:
                    current = candidate
                elif current:
                    lines.append(current)
                    current = word
                else:
                    ok = False  # single word wider than page
                    break
            if current:
                lines.append(current)
            if ok and len(lines) <= 3 and all(
                draw.textlength(ln, font=font) <= max_w for ln in lines
            ):
                return lines, font
            size -= 8
        font = ImageFont.truetype(font_path, min_size)
        return [text], font

    def process_cover(self, input_path, output_path, title, subtitle=None):
        """Full-color cover: RGB polish + A4 full-bleed + PIL title overlay.

        Title text yahan draw hota hai (FLUX text render nahi kar sakta) —
        reference jaisa warm-orange fill + white outline + drop shadow,
        neeche subtitle ribbon.
        """
        try:
            img = Image.open(input_path).convert("RGB")
            cfg = self.cover_cfg

            img = ImageEnhance.Color(img).enhance(float(cfg.get("saturation", 1.15)))
            img = ImageEnhance.Contrast(img).enhance(float(cfg.get("contrast", 1.05)))
            img = self._resize_to_a4(img)

            draw = ImageDraw.Draw(img)
            w, h = img.size
            margin = int(w * 0.06)
            max_text_w = w - 2 * margin

            title_font_path = cfg.get("title_font", "C:/Windows/Fonts/comicbd.ttf")
            subtitle_font_path = cfg.get("subtitle_font", "C:/Windows/Fonts/arialbd.ttf")
            title_fill = tuple(cfg.get("title_fill", [255, 140, 30]))
            title_stroke = tuple(cfg.get("title_stroke", [255, 255, 255]))
            subtitle_fill = tuple(cfg.get("subtitle_fill", [255, 255, 255]))
            subtitle_bg = tuple(cfg.get("subtitle_bg", [66, 133, 244]))
            band_h = int(h * float(cfg.get("title_band_ratio", 0.24)))

            # -- Title (top band, centered, drop shadow + white outline) --
            lines, title_font = self._fit_title_lines(
                draw, title.upper(), title_font_path,
                max_text_w, start_size=int(w * 0.17), min_size=60,
            )
            line_h = title_font.size + int(title_font.size * 0.18)
            block_h = line_h * len(lines)
            y = max(int(band_h * 0.12), (band_h - block_h) // 2)
            stroke_w = max(4, title_font.size // 11)
            shadow_off = max(3, title_font.size // 22)
            for line in lines:
                tw = draw.textlength(line, font=title_font)
                x = (w - tw) // 2
                draw.text((x + shadow_off, y + shadow_off), line, font=title_font,
                          fill=(60, 40, 10))  # soft shadow
                draw.text((x, y), line, font=title_font,
                          fill=title_fill, stroke_width=stroke_w, stroke_fill=title_stroke)
                y += line_h

            # -- Subtitle ribbon (centered pill below the title) --
            subtitle = subtitle if subtitle is not None else cfg.get("subtitle", "")
            if subtitle:
                sub_size = max(36, int(w * 0.035))
                sub_font = ImageFont.truetype(subtitle_font_path, sub_size)
                pad_x = int(sub_size * 0.9)
                pad_y = int(sub_size * 0.45)
                tw = draw.textlength(subtitle.upper(), font=sub_font)
                box_w = tw + 2 * pad_x
                box_h = sub_size + 2 * pad_y
                bx = (w - box_w) // 2
                by = y + int(sub_size * 0.4)
                draw.rounded_rectangle(
                    [bx, by, bx + box_w, by + box_h],
                    radius=box_h // 2, fill=subtitle_bg,
                    outline=(255, 255, 255), width=max(3, sub_size // 12),
                )
                draw.text(
                    (bx + pad_x, by + pad_y - sub_size * 0.08),
                    subtitle.upper(), font=sub_font, fill=subtitle_fill,
                )

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "PNG", dpi=(self.dpi, self.dpi))
            logger.success("Color cover ready: {}".format(output_path))
            return True
        except Exception as e:
            logger.error("Color cover processing failed for {}: {}".format(input_path, e))
            return False
