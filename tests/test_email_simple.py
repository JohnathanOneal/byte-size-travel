import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content
from pathlib import Path
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / '.env'
load_dotenv(ENV_PATH)


def test_single_send():
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))

    from_email = Email(os.environ.get("EMAIL_FROM_ADDRESS"), os.environ.get("EMAIL_FROM_SENDER"))
    to_email = os.environ.get("TEST_SINGLE_EMAIL")
    subject = "Sending with SendGrid is Fun"
    content = Content("text/plain", "and easy to do anywhere, even with Python")
    mail = Mail(from_email, to_email, subject, content)

    # Get a JSON-ready representation of the Mail object
    mail_json = mail.get()

    # Send an HTTP POST request to /mail/send
    response = sg.client.mail.send.post(request_body=mail_json)
    print(response.status_code)
    print(response.headers)


def test_list_send():
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))

    message = Mail(
        from_email=Email(
            email=os.environ.get("EMAIL_FROM_ADDRESS"),
            name=os.environ.get("EMAIL_FROM_SENDER")
        ),
        subject="Check out today's NCAA basketball odds and predictions!"
    )

    personalization = Personalization()
    personalization.add_to(To(email="placeholder@example.com"))  # Required but will be overridden by list
    message.add_personalization(personalization)

    html_content = Content(
        "text/html",
        '<a href="https://johnathanoneal.github.io/categories/sports/basketball/2024/12/5/">Check Out NCAA Basketball Odds & Predictions</a>'
    )
    message.content = html_content

    # Add list ID without conversion
    message.custom_args = {"list": os.environ.get("BYTESIZE_SUBSCRIBERS_LIST_ID")}

    response = sg.send(message)
    print(f"Status code: {response.status_code}")


if __name__ == '__main__':
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))

    id = "f9d3a412-0e48-4a8f-970a-2b28ce59bab0"

    response = sg.client.marketing.lists._(id).get()

    print(response.status_code)
    print(response.body)
    print(response.headers)
    # test_single_send()
    # test_list_send()