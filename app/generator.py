from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)

MARGIN_OUTER = 25
MARGIN_INNER = 31

COLOR_PRIMARY = colors.HexColor("#1A365D")
COLOR_SECONDARY = colors.HexColor("#2B6CB0")
COLOR_ACCENT = colors.HexColor("#D69E2E")
COLOR_TEXT = colors.HexColor("#4A5568")
COLOR_MUTED = colors.HexColor("#718096")

FONT_TITLE = "Helvetica-Bold"
FONT_HEADER = "Times-Bold"
FONT_BODY = "Times-Roman"
FONT_MUTED = "Helvetica"

TITLE_Y = PAGE_HEIGHT - 100
SUBTITLE_Y = PAGE_HEIGHT - 145
NAME_Y = PAGE_HEIGHT - 195
BODY_Y = PAGE_HEIGHT - 245
COURSE_Y = PAGE_HEIGHT - 285
DETAILS_Y = 125
SIGNATURE_LINE_Y = 100
CODE_Y = 55
VERIFY_Y = 40

MAX_TEXT_WIDTH = PAGE_WIDTH - 120


def draw_auto_shrunk_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    initial_font_size: float,
    font_name: str,
    color: colors.Color,
) -> None:
    font_size = initial_font_size
    min_font_size = 10.0
    while font_size > min_font_size:
        if c.stringWidth(text, font_name, font_size) <= max_width:
            break
        font_size -= 1.0

    c.setFont(font_name, font_size)
    c.setFillColor(color)
    c.drawCentredString(x, y, text)


def generate_certificate_pdf(cert, job, output_path: str | Path) -> str:
    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    recipient_name = str(getattr(cert, "recipient_name", "") or "").strip()
    course_name = str(getattr(job, "course_name", "") or "").strip()
    completion_date = str(getattr(job, "completion_date", "") or "").strip()
    issuer_name = str(getattr(job, "issuer", "") or "").strip()
    cert_code = str(getattr(cert, "code", "") or "").strip()

    try:
        c = canvas.Canvas(str(out_path), pagesize=landscape(A4))

        c.setStrokeColor(COLOR_PRIMARY)
        c.setLineWidth(3)
        c.rect(MARGIN_OUTER, MARGIN_OUTER, PAGE_WIDTH - (MARGIN_OUTER * 2), PAGE_HEIGHT - (MARGIN_OUTER * 2))

        c.setStrokeColor(COLOR_ACCENT)
        c.setLineWidth(1)
        c.rect(MARGIN_INNER, MARGIN_INNER, PAGE_WIDTH - (MARGIN_INNER * 2), PAGE_HEIGHT - (MARGIN_INNER * 2))

        c.setFillColor(COLOR_PRIMARY)
        c.setFont(FONT_HEADER, 28)
        c.drawCentredString(PAGE_WIDTH / 2.0, TITLE_Y, "CERTIFICATE OF COMPLETION")

        c.setFillColor(COLOR_TEXT)
        c.setFont(FONT_BODY, 15)
        c.drawCentredString(PAGE_WIDTH / 2.0, SUBTITLE_Y, "This is to certify that")

        draw_auto_shrunk_text(
            c=c,
            text=recipient_name,
            x=PAGE_WIDTH / 2.0,
            y=NAME_Y,
            max_width=MAX_TEXT_WIDTH,
            initial_font_size=26.0,
            font_name=FONT_TITLE,
            color=COLOR_SECONDARY,
        )

        c.setFillColor(COLOR_TEXT)
        c.setFont(FONT_BODY, 15)
        c.drawCentredString(PAGE_WIDTH / 2.0, BODY_Y, "has successfully completed the course")

        draw_auto_shrunk_text(
            c=c,
            text=course_name,
            x=PAGE_WIDTH / 2.0,
            y=COURSE_Y,
            max_width=MAX_TEXT_WIDTH,
            initial_font_size=20.0,
            font_name=FONT_TITLE,
            color=COLOR_PRIMARY,
        )

        c.setFont(FONT_MUTED, 11)
        c.setFillColor(COLOR_TEXT)
        c.drawString(80, DETAILS_Y, f"Date: {completion_date}")

        c.drawString(PAGE_WIDTH - 240, DETAILS_Y, f"Issuer: {issuer_name}")
        c.setStrokeColor(COLOR_MUTED)
        c.setLineWidth(0.75)
        c.line(PAGE_WIDTH - 240, SIGNATURE_LINE_Y, PAGE_WIDTH - 80, SIGNATURE_LINE_Y)
        c.setFont(FONT_MUTED, 9)
        c.drawString(PAGE_WIDTH - 240, SIGNATURE_LINE_Y - 12, "Authorized Signature")

        c.setFont(FONT_MUTED, 10)
        c.setFillColor(COLOR_MUTED)
        c.drawCentredString(PAGE_WIDTH / 2.0, CODE_Y, f"Certificate Code: {cert_code}")
        c.setFont(FONT_MUTED, 8)
        c.drawCentredString(PAGE_WIDTH / 2.0, VERIFY_Y, f"Verify at /api/v1/verify/{cert_code}")

        c.save()
        return str(out_path)
    except Exception as e:
        raise ValueError(f"Failed to render certificate PDF: {e}") from e
