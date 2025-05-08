from dataclasses import dataclass
from datetime import datetime
from base64 import b64encode, b64decode
import threading
import logging
from time import sleep
import json

from hashlib import sha256
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

from abc import ABC, abstractmethod
from typing import Tuple

from .util import random_string
from .configuration import configurationStore

import redis


@dataclass
class CipheredMessage:
    iv: bytes
    ciphertext: bytes

    def to_dict(self):
        return {
            "iv": b64encode(self.iv).decode(),
            "ciphertext": b64encode(self.ciphertext).decode(),
        }

    @staticmethod
    def from_dict(data) -> "CipheredMessage":
        return CipheredMessage(
            iv=b64decode(data["iv"]),
            ciphertext=b64decode(data["ciphertext"]),
        )

    @staticmethod
    def create_from_message(passphrase: str, message: str) -> "CipheredMessage":
        sha = sha256()
        sha.update(passphrase.encode())
        key = sha.digest()
        iv = get_random_bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(message.encode(), AES.block_size))
        return CipheredMessage(iv=iv, ciphertext=ciphertext)

    def decrypt(self, passphrase: str) -> str:
        sha = sha256()
        sha.update(passphrase.encode())
        key = sha.digest()
        cipher = AES.new(key, AES.MODE_CBC, self.iv)
        return unpad(cipher.decrypt(self.ciphertext), AES.block_size).decode()


@dataclass
class Secret:
    note: str
    message: CipheredMessage
    expires: datetime
    password_protected: bool = False
    password_hash: str = None
    password_attempts: int = 0

    def to_dict(self):
        return {
            "note": self.note,
            "message": self.message.to_dict(),
            "expires": self.expires.isoformat(),
            "password_protected": self.password_protected,
            "password_hash": self.password_hash,
            "password_attempts": self.password_attempts,
        }

    @staticmethod
    def from_dict(data):
        return Secret(
            note=data["note"],
            message=CipheredMessage.from_dict(data["message"]),
            expires=datetime.fromisoformat(data["expires"]),
            password_protected=data["password_protected"],
            password_hash=data["password_hash"],
            password_attempts=data["password_attempts"],
        )


class SecretStore(ABC):

    def __init__(self, default_password: str = None, max_attempts: int = 3):
        assert max_attempts > 0, "max_attempts must be greater than 0"
        self.default_password = default_password or random_string(64)
        self.max_attempts = max_attempts

    def save(
        self,
        key: str,
        note: str,
        message: str,
        expires: datetime,
        password: str | None = None,
    ) -> None:
        password_protected = password is not None and len(password) > 0
        if not password_protected:
            # use the default password if one is not provided
            password = self.default_password
        secret = Secret(
            note=note,
            message=CipheredMessage.create_from_message(password, message),
            expires=expires,
            password_protected=password_protected,
            password_hash=sha256(password.encode()).hexdigest(),
        )
        self._store(key, secret)

    def load(self, key: str, remove: bool = True) -> Secret | None:
        secret = self._load(key)
        if secret:
            if remove:
                self._remove(key)
            if secret.expires < datetime.now():
                return None
            return secret
        return None

    def get_message(self, key: str, password: str = None) -> str | None:
        secret = self.load(key, password=password)
        if secret:
            self._remove(key)
            return secret.message.decrypt(password or self.default_password)
        return None

    def is_password_protected(self, key: str) -> bool:
        secret = self._load(key)
        return secret and secret.password_protected

    def check_password(self, key: str, password: str) -> Tuple[str, bool, int]:
        """Check if the password is correct for a password-protected secret.
        return a tuple of (message note, is_correct, remaining_attempts)
        """
        secret = self._load(key)

        if not secret or not secret.password_protected:
            return None, False, 0

        if sha256(password.encode()).hexdigest() == secret.password_hash:
            return secret.note, True, 0
        else:
            secret.password_attempts += 1
            remaining_attempts = self.max_attempts - secret.password_attempts
            if remaining_attempts <= 0:
                self._remove(key)
            # update the secret in the store
            self._store(key, secret)
            return secret.note, False, remaining_attempts

    @abstractmethod
    def _store(self, key: str, secret: Secret) -> None:
        pass

    @abstractmethod
    def _load(self, key: str) -> Secret | None:
        pass

    @abstractmethod
    def _remove(self, key: str) -> None:
        pass


class InMemorySecretStore(SecretStore):

    def __init__(self, default_password: str = None, max_attempts: int = 3):
        super().__init__(default_password, max_attempts)
        self.logger = logging.getLogger(__name__)
        self.secrets = {}
        self.max_attempts = max_attempts
        self.cleanup_thread = threading.Thread(target=self._cleanup, daemon=True)
        self.cleanup_thread.start()

    def _cleanup(self):
        while self.cleanup_thread is not None:
            try:
                sleep(60)
                now = datetime.now()
                for key, secret in list(self.secrets.items()):
                    if secret.expires < now:
                        self._remove(key)
            except Exception as e:
                self.logger.error(f"Error in cleanup thread: {e}")

    def _store(self, key: str, secret: Secret) -> None:
        self.secrets[key] = secret

    def _load(self, key: str) -> Secret | None:
        return self.secrets.get(key)

    def _remove(self, key: str) -> None:
        self.secrets.pop(key, None)

    def __del__(self):
        t = self.cleanup_thread
        self.cleanup_thread = None
        t.join()


class RedisSecretStore(SecretStore):

    def __init__(
        self, redis_url: str, default_password: str = None, max_attempts: int = 3
    ):
        super().__init__(default_password, max_attempts)
        self.logger = logging.getLogger(__name__)
        self.redis = redis.Redis.from_url(redis_url)
        self.max_attempts = max_attempts

    def _store(self, key: str, secret: Secret) -> None:
        ex = int((secret.expires - datetime.now()).total_seconds())
        self.logger.debug(f"Storing secret {key} with expiration {secret.expires}")
        self.redis.set(f"ihaveasecret:{key}", json.dumps(secret.to_dict()), ex=ex)

    def _load(self, key: str) -> Secret | None:
        data = self.redis.get(f"ihaveasecret:{key}")
        if data:
            self.logger.debug(f"Loaded secret {key}")
            return Secret.from_dict(json.loads(data))
        else:
            self.logger.debug(f"Secret {key} not found")
            return None

    def _remove(self, key: str) -> None:
        self.logger.debug(f"Removing secret {key}")
        self.redis.delete(f"ihaveasecret:{key}")


redis_url = configurationStore.get("redis.url")
max_attempts = int(configurationStore.get("passwords.max_attempts", 3))
default_password = configurationStore.get("app.secret_key")

if not redis_url:
    logging.warning("Redis URL not set, using in-memory secret store")

secretStore = (
    InMemorySecretStore(default_password, max_attempts)
    if redis_url is None
    else RedisSecretStore(redis_url, default_password, max_attempts)
)
