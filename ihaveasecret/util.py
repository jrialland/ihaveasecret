import random
import string
from pathlib import Path
import re


def random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def build_url(*parts) -> str:
    return "/".join(part.strip("/") for part in parts if part.strip("/"))


def to_data_uri(resource: str):
    """
    Transform a resouce from the static folder into a data URI.
    """
    from base64 import b64encode

    staticfolder = Path(__file__).parent / "static"
    resource_path = staticfolder / resource
    if not resource_path.exists():
        raise FileNotFoundError(f"Resource {resource} not found in static folder")
    with open(resource_path, "rb") as f:
        data = f.read()
    mime_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "svg": "image/svg+xml",
    }
    mime_type = mime_types.get(resource_path.suffix[1:], "application/octet-stream")
    return f"data:{mime_type};base64,{b64encode(data).decode('utf-8')}"


email_regex = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")


def is_valid_email(email: str) -> bool:
    """
    Check if the email is valid.
    """

    return bool(email_regex.match(email))
