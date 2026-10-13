"""PDF Agent - Assembles processed line art into a final A4 PDF."""
import os
from pathlib import Path
from loguru import logger
from fpdf import FPDF


class PDFAgent:
    def __init__(self, config):
        self.config = config
        self.books_dir = config["paths"]["output_books"]
        self.meta = config["metadata"]

    def _add_page_number(self, pdf, page_num, total):
        pdf.set_y(-15)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, "Page {} of {}".format(page_num, total), align="C")

    def build_pdf(self, processed_paths, cover_title, date_str, color_cover_path=None):
        valid_paths = [p for p in processed_paths if p is not None]
        if not valid_paths:
            logger.error("No valid images to build PDF")
            return None

        # Color cover available ho to wo PDF ka page-1 banta hai aur line-art
        # cover bonus coloring page ke roop me andar rehta hai.
        if color_cover_path and os.path.exists(color_cover_path):
            cover_path = color_cover_path
            page_paths = valid_paths
        else:
            cover_path = valid_paths[0]
            page_paths = valid_paths[1:]
        total_pages = len(page_paths) + 1

        logger.info("Building PDF with {} pages...".format(total_pages))

        a4_w = 210
        a4_h = 297

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=False)
        pdf.set_margins(0, 0, 0)
        pdf.set_title("{} - {}".format(cover_title, date_str))
        pdf.set_author(self.meta.get("author", "AI Coloring Book"))
        pdf.set_creator("Daily Coloring Book Agent")
        pdf.set_keywords("coloring book, kids, printable, AI generated, line art")

        # Cover page
        pdf.add_page()
        if os.path.exists(cover_path):
            pdf.image(cover_path, x=0, y=0, w=a4_w, h=a4_h)

        # Coloring pages
        for i, page_path in enumerate(page_paths):
            pdf.add_page()
            if os.path.exists(page_path):
                pdf.image(page_path, x=0, y=0, w=a4_w, h=a4_h)
            self._add_page_number(pdf, i + 2, total_pages)

        # Save
        Path(self.books_dir).mkdir(parents=True, exist_ok=True)
        safe_title = "".join(c for c in cover_title if c.isalnum() or c in " -_").strip()
        filename = "coloring_book_{}_{}.pdf".format(date_str, safe_title.replace(" ", "_")[:30])
        output_path = os.path.join(self.books_dir, filename)
        pdf.output(output_path)

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.success("PDF saved: {} ({:.1f} MB, {} pages)".format(output_path, file_size_mb, total_pages))
        return output_path
