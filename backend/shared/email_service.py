import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(to_email: str, subject: str, body: str):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    sender = os.getenv("EMAIL_FROM", username)

    if not all([host, username, password]):
        raise ValueError("SMTP configuration missing")

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(username, password)
        server.sendmail(sender, to_email, msg.as_string())


def send_applicant_confirmed_email(caretaker_email: str, booking_details: dict):
    subject = "Congratulations! You've been selected for a pet care job"
    body = f"""Dear Caretaker,

Congratulations! You've been selected for the following pet care job:

Pet: {booking_details['pet_name']}
Dates: {booking_details['start_date']} to {booking_details['end_date']}
Description: {booking_details['description']}

Please contact the pet owner to arrange details.

Best regards,
CarePets Team
"""
    send_email(caretaker_email, subject, body)


def send_applicant_rejected_email(caretaker_email: str, booking_details: dict):
    subject = "Update on your application for a pet care job"
    body = f"""Dear Caretaker,

Thank you for your interest in the following pet care job:

Pet: {booking_details['pet_name']}
Dates: {booking_details['start_date']} to {booking_details['end_date']}

Unfortunately, another caretaker was selected. We appreciate your application and hope to work with you on future opportunities.

Best regards,
CarePets Team
"""
    send_email(caretaker_email, subject, body)
