from .configuration import configurationStore
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from jinja2 import Environment, PackageLoader
from bs4 import BeautifulSoup
from .util import to_data_uri


template_env = Environment(
    loader=PackageLoader("ihaveasecret", "templates"), autoescape=True
)


def send_message_created_email(recipient: str, message_url: str, note: str = None, ttl: str = None):
    """
    Send an email to the recipient with the message created.
    """

    # prepare the email content
    template = template_env.get_template("created_email.html")
    msg_html = template.render(
        to_data_uri=to_data_uri,
        recipient=recipient,
        message_url=message_url,
        note=note,
        ttl=ttl,
    )

    # compute alternative text using bs4
    soup = BeautifulSoup(msg_html, "html.parser")
    msg_text = soup.get_text()

    # create a multipart email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Secret Created"
    msg["From"] = configurationStore.get("smtp.sender_email", "noreply@ihaveasecret.cloud")
    msg["To"] = recipient
    msg.attach(MIMEText(msg_text, "plain"))
    msg.attach(MIMEText(msg_html, "html"))

    # get smtp configuration
    smtp_server = configurationStore.get("smtp.server", "localhost")
    smtp_port = int(configurationStore.get("smtp.port", 587))
    smtp_user = configurationStore.get("smtp.user")
    smtp_password = configurationStore.get("smtp.password")

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        else:
            logging.warning("SMTP user and password not set, using anonymous login")
        server.sendmail(msg["From"], recipient, msg.as_string())
        logging.info(f"Email sent to {recipient}")
