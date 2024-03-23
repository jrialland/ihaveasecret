from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix
from .configuration import configurationStore
from .routes import create_routes
import logging
import os
from pathlib import Path
from flask_babel import Babel

# ------------------------------------------------------------------------------
# force logging to be enabled in development
if os.environ.get("FLASK_ENV") == "development":
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Development mode enabled")

# ------------------------------------------------------------------------------
# create the Flask app, and wrap it in a ProxyFix to handle X-Forwarded-For
app = Flask(__name__)

if bool(configurationStore.get("app.proxy_fix", False)):
    logging.info("Enabling ProxyFix")
    app.wsgi_app = ProxyFix(app.wsgi_app)

# ------------------------------------------------------------------------------
# i18n configuration
app.config["LANGUAGES"] = {
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
}

app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = str(Path(__file__).parent.absolute() / "translations")
babel = Babel(app, locale_selector=lambda: (request.accept_languages.best_match(app.config["LANGUAGES"].keys()) or "en"))

# ------------------------------------------------------------------------------
# secret key configuration : required for session management
app_secret_key = configurationStore.get("app.secret_key")
if not app_secret_key:
    logging.warning("app.secret_key is not set, generating a random key")
    app_secret_key = os.urandom(24).hex()
app.secret_key = app_secret_key

# ------------------------------------------------------------------------------
# register the routes
url_prefix = configurationStore.get("app.url_prefix", "")
if url_prefix:
    assert url_prefix.startswith("/"), "app.url_prefix must start with /"
    assert not url_prefix.endswith("/"), "app.url_prefix must not end with /"

logging.info(f"Registering routes with url_prefix: {url_prefix}")
app.register_blueprint(create_routes(url_prefix), url_prefix=url_prefix)
