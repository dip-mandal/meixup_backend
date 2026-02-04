from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from common.config import settings
from pathlib import Path

# 1. Dynamically find the absolute path to the project root
# This ensures that no matter where you run uvicorn from, the folder is found.
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "email_templates"

# 2. Configuration for FastAPI-Mail
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,  # Using settings for flexibility
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER=TEMPLATE_DIR
)

async def send_professional_email(
    email_to: str, 
    subject: str, 
    template_name: str, 
    context: dict
):
    """
    Sends a professional HTML email using the Jinja2 templates 
    located in the email_templates folder.
    """
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        template_body=context,
        subtype=MessageType.html
    )
    
    fm = FastMail(conf)
    
    # This will look for the .html file inside TEMPLATE_DIR
    await fm.send_message(message, template_name=template_name)