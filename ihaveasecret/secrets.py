from dataclasses import dataclass
from datetime import datetime
import logging
import redis
import json
import re
from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Hash import HMAC, SHA256
from Crypto.Random import get_random_bytes

from .config import configurationStore
from typing import Tuple


def encode_message(passphrase: str, message: str) -> str:
    key = get_random_bytes(32)
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(message.encode(), AES.block_size))
    return json.dumps(
        {
            "key": b64encode(key).decode(),
            "iv": b64encode(iv).decode(),
            "ciphertext": b64encode(ciphertext).decode(),
        }
    )


def decode_message(passphrase: str, encoded_message: str) -> str:
    data = json.loads(encoded_message)
    key = b64decode(data["key"])
    iv = b64decode(data["iv"])
    ciphertext = b64decode(data["ciphertext"])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size).decode()


@dataclass
class Secret:
    key: str
    message: str
    expires: datetime
    password_protected: bool = False
    password_hash: str = None


class SecretStore:
    """A store for secrets that expire after a certain time or after being read.
    The secrets are stored in a Redis database.
    """

    def __init__(
        self, secret_key: str = None, max_attempts: int = 3, redis_url: str = None
    ):
        self.logger = logging.getLogger(__name__)
        if redis_url is None:
            redis_url = configurationStore.get("redis.url", "redis://localhost:6379/0")
        self.redis = redis.Redis.from_url(redis_url)
        self.max_attempts = int(
            configurationStore.get("ihaveasecret.max_attempts", max_attempts)
        )

    def save(self, secret: Secret, password: str = None):
        ex = secret.expires - datetime.now()
        if password:
            secret.message = encode_message(password, secret.message)
            secret.password_protected = True
            secret.password_hash = HMAC.new(
                password.encode(), digestmod=SHA256
            ).hexdigest()
            self.redis.set(f"{secret.key}:password_protected", 1, ex=ex)
        payload = json.dumps(
            {
                "message": secret.message,
                "expires": secret.expires.isoformat(),
                "password_protected": secret.password_protected,
                "password_hash": secret.password_hash,
            }
        )
        self.redis.set(secret.key, payload, ex=ex)

    def is_password_protected(self, key: str) -> bool:
        return self.redis.exists(f"{key}:password_protected")

    def check_password(self, key: str, password: str) -> Tuple[bool, int]:

        secret = self.load(key, remove=False)

        if not secret:
            self.logger.warning(f"Secret {key} not found")
            return False, 0

        if not secret.password_protected:
            self.logger.warning(f"Secret {key} is not password protected")
            return True, 0

        if (
            secret.password_hash
            != HMAC.new(password.encode(), digestmod=SHA256).hexdigest()
        ):
            attempts_key = f"{key}:attempts"
            attempts = self.redis.incr(attempts_key)
            self.redis.expire(attempts_key, secret.expires - datetime.now())
            remaining_attempts = max(0, self.max_attempts - attempts)
            self.logger.debug(f"Remaining attempts: {remaining_attempts}")
            return False, remaining_attempts
        else:
            self.redis.delete(f"{key}:password_protected")
            self.redis.delete(f"{key}:attempts")
            return True, 0

    def load(
        self, key: str, password: str = None, remove: bool = True
    ) -> Secret | None:
        payload = self.redis.get(key)
        if not payload:
            return None
        payload = json.loads(payload.decode())
        payload["key"] = key
        payload["expires"] = datetime.fromisoformat(payload["expires"])
        secret = Secret(**payload)
        self.logger.debug(password)
        self.logger.debug(secret.message)
        if secret.password_protected and password:
            if not self.check_password(key, password)[0]:
                return None
            secret.message = decode_message(password, secret.message)

        if remove:
            self.redis.delete(key)
        return secret


secretStore = SecretStore()
