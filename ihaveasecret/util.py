import random
import string


def random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def build_url(*parts) -> str:
    return "/".join(part.strip("/") for part in parts if part.strip("/"))
