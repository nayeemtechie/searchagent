# src/output/pdf.py
import os
import textwrap
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Paths to TTFs you ship with the repo (recommended)
FONT_REG_PATH = "assets/fonts/DejaVuSans.ttf"
FONT_BOLD_PATH = "assets/fonts/DejaVuSans-Bold.ttf"



def _wrap_text(txt: str, width_chars: int = 100) -> str:
    # Wrap long lines, allow breaking long words/hyphens
    return "\n".join(textwrap.wrap(
        txt, width=width_chars, break_long_words=True, break_on_hyphens=True
    ))

def _qa_kv_lines(k, v):
    """Yield (label, line) tuples for flat and nested values."""
    if isinstance(v, dict):
        yield (str(k), "")  # header line for this dict
        for sk, sv in v.items():
            sval = _wrap_text(str(sv), 100)
            for line in sval.splitlines() or [""]:
                yield (f"  • {sk}", line)
    else:
        sval = _wrap_text(str(v), 100)
        for line in sval.splitlines() or [""]:
            yield (str(k), line)


class BrandPDF(FPDF):
    def __init__(self, title_text, accent_rgb):
        super().__init__()
        self.title_text = title_text
        self.accent_rgb = accent_rgb
        self._has_unicode_font = False

        # Try to register DejaVu fonts (Unicode)
        try:
            if os.path.exists(FONT_REG_PATH):
                self.add_font("DejaVu", "", FONT_REG_PATH, uni=True)
                if os.path.exists(FONT_BOLD_PATH):
                    self.add_font("DejaVu", "B", FONT_BOLD_PATH, uni=True)
                else:
                    # If bold TTF not present, at least regular is available
                    pass
                self._has_unicode_font = True
        except Exception as e:
            # Fallback to built-in fonts silently
            self._has_unicode_font = False

        self.set_auto_page_break(auto=True, margin=15)

    # ---- font helpers ----
    def _set_heading_font(self, bold=False, size=14):
        if self._has_unicode_font:
            self.set_font("DejaVu", "B" if bold else "", size)
        else:
            self.set_font("Helvetica", "B" if bold else "", size)

    def _set_body_font(self, size=11, bold=False, underline=False):
        style = ""
        if bold: style += "B"
        if underline: style += "U"
        if self._has_unicode_font:
            self.set_font("DejaVu", style, size)
        else:
            self.set_font("Helvetica", style, size)

    def header(self):
        # Title band
        self.set_fill_color(*self.accent_rgb)
        self.set_text_color(255, 255, 255)
        self._set_heading_font(bold=True, size=14)
        self.cell(0, 12, self.title_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C", fill=True)
        self.ln(5)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self._set_body_font(size=8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Curated by Nayeemuddin Mohammed | {self.title_text} | Page {self.page_no()}", 0, 0, "C")
        self.set_text_color(0, 0, 0)

def _section_bullet(pdf: BrandPDF, section_title: str) -> str:
    """Pick a bullet based on section + font availability."""
    if pdf._has_unicode_font:
        if "Executive" in section_title:
            return "⭐ "
        if "Consulting" in section_title:
            return "☑ "
        return "🚀 "
    # ASCII fallback if unicode font not loaded
    if "Executive" in section_title:
        return "* "
    if "Consulting" in section_title:
        return "- "
    return "> "

def make_pdf(path, title, accent, sections, qa=None):
    """
    path: output file
    title: document title (string)
    accent: (R,G,B) tuple
    sections: list of {title, paras: [..], links: [{title,url}]}
    qa: optional dict to append as a QA appendix page
    """
    pdf = BrandPDF(title, accent)
    pdf.add_page()
    pdf._set_body_font(size=12)

    usable_width = pdf.w - 2 * pdf.l_margin

    for sec in sections or []:
        # Section header
        pdf.set_fill_color(*accent)
        pdf.set_text_color(255, 255, 255)
        pdf._set_heading_font(bold=True, size=13)
        pdf.cell(0, 10, sec.get("title", ""), ln=True, fill=True)
        pdf.ln(2)
        pdf.set_text_color(0, 0, 0)
        pdf._set_body_font(size=11)

        bullet = _section_bullet(pdf, sec.get("title", ""))

        for para in sec.get("paras", []):
            # Prepend bullet
            pdf.multi_cell(usable_width, 6, f"{bullet}{para}")
            pdf.ln(1)

        links = sec.get("links", []) or []
        if links:
            pdf._set_body_font(size=11, bold=True)
            pdf.cell(0, 8, "Further reading:", ln=True)
            pdf._set_body_font(size=10)
            # Link color + underline
            for ln in links:
                url = (ln.get("url") or "").strip()
                if not url:
                    continue
                title_txt = (ln.get("title") or url).strip()
                # clickable
                pdf.set_text_color(0, 0, 255)
                pdf._set_body_font(size=10, underline=True)
                pdf.write(6, f"• {title_txt}", url)
                pdf.ln(6)
                pdf.set_text_color(0, 0, 0)
                pdf._set_body_font(size=10)

        pdf.ln(6)

    # QA appendix (optional)
    # QA appendix (optional)
    if qa:
        pdf.add_page()
        pdf._set_heading_font(bold=True, size=12)
        pdf.cell(0, 10, "Appendix — QA Meta", ln=True)
        pdf._set_body_font(size=10)

        usable_width = pdf.w - pdf.l_margin - pdf.r_margin

    for k, v in qa.items():
        for lbl, line in _qa_kv_lines(k, v):
            pdf.set_x(pdf.l_margin)  # ensure we start at left margin
            # Bold label on its own line if there is no value line
            if line == "":
                pdf._set_body_font(size=10, bold=True)
                pdf.multi_cell(usable_width, 6, f"{lbl}:")
                pdf._set_body_font(size=10, bold=False)
            else:
                # Label + value; keep label light and value wrapped
                pdf._set_body_font(size=10, bold=True)
                pdf.multi_cell(usable_width, 6, f"{lbl}:", align="L")
                pdf._set_body_font(size=10, bold=False)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(usable_width, 6, line, align="L")
        pdf.ln(2)


    pdf.output(path)
