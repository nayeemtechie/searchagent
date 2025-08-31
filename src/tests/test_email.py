"""Email test (Outlook/Gmail). Usage: python -m src.tests.test_email"""
import os, tempfile
from dotenv import load_dotenv
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from src.emailer.smtp import send_email

def _tmp_pdf(path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    # Use ASCII hyphen (-) and the new_x/new_y args (no more ln=)
    pdf.cell(0, 10, 'Search Intel - Email Test PDF', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.output(path)

def main():
    load_dotenv()
    to = os.getenv('EMAIL_TO') or os.getenv('SMTP_USERNAME')
    if not to: raise SystemExit('Set EMAIL_TO (or SMTP_USERNAME) in .env')
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    _tmp_pdf(tmp.name)
    send_email('[TEST] Search Intel — SMTP works',
               'This is a test email with a PDF attachment.',
               to_addrs=to, attachments=[tmp.name])
    print('✅ Email sent to', to)
    print('Attachment path:', tmp.name)

if __name__ == '__main__':
    main()
