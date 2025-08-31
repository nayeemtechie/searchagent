import os, smtplib, ssl, mimetypes
from email.message import EmailMessage
def send_email(subject, body_text, to_addrs, attachments=None):
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.office365.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USERNAME')
    smtp_pass = os.getenv('SMTP_APP_PASSWORD') or os.getenv('SMTP_PASSWORD')
    from_addr = os.getenv('EMAIL_FROM', smtp_user)
    if not (smtp_user and smtp_pass and from_addr):
        raise RuntimeError('SMTP credentials not set. Fill .env with Outlook/Gmail App Password.')
    msg = EmailMessage()
    msg['Subject'] = subject; msg['From'] = from_addr
    if isinstance(to_addrs, str): to_addrs = [to_addrs]
    msg['To'] = ', '.join(to_addrs)
    msg.set_content(body_text)
    for path in attachments or []:
        import os as _os, mimetypes as _mt
        ctype, _ = _mt.guess_type(path)
        maintype, subtype = (ctype or 'application/octet-stream').split('/', 1)
        with open(path, 'rb') as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=_os.path.basename(path))
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls(context=context)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
