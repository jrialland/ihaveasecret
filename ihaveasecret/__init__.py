from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix
from .configuration import configurationStore
from .routes import create_routes
from .csrf_token import make_csrf_token
import logging
import os
from datetime import datetime
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


def get_locale():
    return request.accept_languages.best_match(app.config["LANGUAGES"].keys()) or "en"


app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = str(
    Path(__file__).parent.absolute() / "translations"
)
babel = Babel(app, locale_selector=get_locale)

# ------------------------------------------------------------------------------
# secret key configuration : required for session management
app_secret_key = configurationStore.get("app.secret_key")
if not app_secret_key:
    logging.warning("app.secret_key is not set, generating a random key")
    app_secret_key = os.urandom(24).hex()
app.secret_key = app_secret_key


# ------------------------------------------------------------------------------
# response headers configuration
@app.after_request
def add_security_headers(response):
    response.headers["Content-Security-Policy"] = "default-src 'self';"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# ------------------------------------------------------------------------------
# register variables in the Jinja context
url_prefix = configurationStore.get("app.url_prefix", "")
if url_prefix:
    assert url_prefix.startswith("/"), "app.url_prefix must start with /"
    assert not url_prefix.endswith("/"), "app.url_prefix must not end with /"


@app.context_processor
def inject_jinja_variables():
    return {
        "url_prefix": url_prefix,
        "max_message_length": int(configurationStore.get("secrets.max_length", 2048)),
        "locale": get_locale(),
        "make_csrf_token": make_csrf_token,
        "current_year": datetime.now().year,
    }


# ------------------------------------------------------------------------------
# register the routes
logging.info(f"Registering routes with url_prefix: {url_prefix}")
app.register_blueprint(create_routes(url_prefix), url_prefix=url_prefix)
