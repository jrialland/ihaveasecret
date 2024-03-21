from flask import Flask, redirect, url_for
from .config import configurationStore
from .routes import create_routes
import logging
import os

if os.environ.get("FLASK_ENV") == "development":
    logging.basicConfig(level=logging.DEBUG)


app = Flask(__name__)

app_secret_key = configurationStore.get("app.secret_key")
assert app_secret_key, "app.secret_key is required"
app.secret_key = app_secret_key

url_prefix = configurationStore.get("app.url_prefix", "")
if url_prefix:
    assert url_prefix.startswith("/"), "app.url_prefix must start with /"
    assert not url_prefix.endswith("/"), "app.url_prefix must not end with /"

app.register_blueprint(create_routes(), url_prefix=url_prefix)


@app.route(url_prefix + "/")
def home():
    return redirect(url_for("ihaveasecret.display_create_page"))
