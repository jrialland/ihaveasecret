from pathlib import Path
import os
import json
import logging


class ConfigurationStore:

    def __init__(self, config_file: str = None):
        self.logger = logging.getLogger(__name__)
        self._config = {}
        if config_file:
            p = Path(config_file)
            if p.is_file():
                with p.open() as f:
                    self._config = json.load(f)
            else:
                self.logger.warning(f"Configuration file {config_file} not found")

    def _get_from_secrets(self, key):
        """
        get a configuration value from docker secrets
        """
        secret_path = Path("/run/secrets") / key
        if secret_path.exists():
            return secret_path.read_text()
        else:
            return None

    def _get_from_env(self, key):
        envvar = key.upper().replace(".", "_")
        return os.environ.get(envvar)

    def _get_from_file(self, key):
        return self._config.get(key)

    def get(self, key, default=None):
        """
        get a configuration value by reading, in order of precedence:
            - docker secrets
            - environment variables
            - configuration file
            - default value
        """
        return (
            self._get_from_secrets(key)
            or self._get_from_env(key)
            or self._get_from_file(key)
            or default
        )


configurationStore = ConfigurationStore(
    (Path(__file__).parent / "config.json").as_posix()
)
