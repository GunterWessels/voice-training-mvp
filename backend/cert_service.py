import os
import logging
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ASSETS = Path(__file__).parent / "assets"

_fonts_registered = False


def _register_fonts() -> tuple[str, str]:
    """Register brand fonts if available; return (heading_font, body_font) names."""
    global _fonts_registered
    oswald_path = ASSETS / "fonts/Oswald-Bold.ttf"
    manrope_path = ASSETS / "fonts/Manrope-Regular.ttf"
    if not _fonts_registered and oswald_path.exists() and manrope_path.exists():
        try:
            pdfmetrics.registerFont(TTFont("Oswald-Bold", str(oswald_path)))
            pdfmetrics.registerFont(TTFont("Manrope", str(manrope_path)))
            _fonts_registered = True
        except Exception as e:
            logging.warning("cert_service: font registration failed: %s", e)
    if _fonts_registered:
        return ("Oswald-Bold", "Manrope")
    return ("Helvetica-Bold", "Helvetica")


def should_issue_cert(cof_clinical: bool, cof_operational: bool, cof_financial: bool,
                       arc_stage: int, preset: str) -> bool:
    return (cof_clinical and cof_operational and cof_financial
            and arc_stage >= 5
            and preset in ("full_practice", "cert_run"))


def generate_cert_pdf(data: dict, output_path: str) -> str:
    heading_font, body_font = _register_fonts()
    c = canvas.Canvas(output_path, pagesize=letter)
    w, h = letter

    # Navy header bar
    c.setFillColor(colors.HexColor("#1B2B5B"))
    c.rect(0, h - 1.5 * inch, w, 1.5 * inch, fill=1, stroke=0)

    # Logo (optional)
    logo = ASSETS / "ls_logo.png"
    if logo.exists():
        c.drawImage(str(logo), 0.5 * inch, h - 1.3 * inch, width=2 * inch, preserveAspectRatio=True)

    # Title
    c.setFillColor(colors.white)
    c.setFont(heading_font, 24)
    c.drawCentredString(w / 2, h - 0.9 * inch, "Certificate of Completion")

    # Body
    c.setFillColor(colors.HexColor("#1B2B5B"))
    c.setFont(body_font, 14)
    c.drawCentredString(w / 2, h - 2.5 * inch, "This certifies that")
    c.setFont(heading_font, 20)
    c.drawCentredString(w / 2, h - 3.0 * inch, data["rep_name"])
    c.setFont(body_font, 13)
    c.drawCentredString(w / 2, h - 3.5 * inch, "has successfully completed")
    c.setFont(heading_font, 16)
    c.drawCentredString(w / 2, h - 4.0 * inch, data["scenario_name"])

    # COF gates
    c.setFont(body_font, 11)
    gates = [
        ("Clinical", data["cof_clinical"]),
        ("Operational", data["cof_operational"]),
        ("Financial", data["cof_financial"]),
    ]
    y = h - 5.0 * inch
    for name, passed in gates:
        mark = "+" if passed else "o"  # ASCII-safe instead of unicode checkmark
        c.drawString(2.5 * inch, y, f"{mark}  {name} Domain")
        y -= 0.3 * inch

    # Score + date
    c.setFont(body_font, 12)
    c.drawCentredString(w / 2, h - 6.2 * inch, f"Score: {data['score']}   |   {data['completed_at']}")

    # Signature (optional)
    sig = ASSETS / "signature.png"
    if sig.exists():
        c.drawImage(str(sig), w / 2 - 1 * inch, h - 7.5 * inch, width=2 * inch, preserveAspectRatio=True)
    c.setFont(body_font, 10)
    c.drawCentredString(w / 2, h - 8.0 * inch, "Dr. Gunter Wessels, Ph.D., M.B.A.")
    c.drawCentredString(w / 2, h - 8.3 * inch, "LiquidSMARTS\u2122")

    # Footer
    c.setFont(body_font, 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(w / 2, 0.5 * inch, f"Completion ID: {data['completion_id']}")

    c.save()
    return output_path


async def upload_and_email_cert(completion_data: dict, user_email: str) -> str:
    """Generate PDF, upload to Supabase Storage, email to rep. Returns public URL."""
    import tempfile
    import resend
    from supabase import create_client

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "certificates")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        generate_cert_pdf(completion_data, f.name)
        pdf_bytes = Path(f.name).read_bytes()

    path = f"{completion_data['user_id']}/{completion_data['completion_id']}.pdf"
    supabase.storage.from_(bucket).upload(path, pdf_bytes, {"content-type": "application/pdf"})
    public_url = supabase.storage.from_(bucket).get_public_url(path)

    resend.api_key = os.environ["RESEND_API_KEY"]
    resend.Emails.send({
        "from": "training@liquidsmarts.com",
        "to": user_email,
        "subject": f"Your LiquidSMARTS\u2122 Certificate -- {completion_data['scenario_name']}",
        "text": f"Congratulations {completion_data['rep_name']}!\n\nYour certificate is attached.\n\nCompletion ID: {completion_data['completion_id']}",
        "attachments": [{"filename": "certificate.pdf", "content": list(pdf_bytes)}],
    })
    return public_url
