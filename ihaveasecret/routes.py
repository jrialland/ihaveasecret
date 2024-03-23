from flask import (
    Blueprint,
    request,
    session,
    render_template,
    send_from_directory,
    redirect,
    url_for,
)
from datetime import datetime, timedelta
from .configuration import configurationStore
from .secretstore import secretStore
from .util import random_string, build_url
from pathlib import Path
from flask_babel import gettext, ngettext

possible_ttls = [
    ("1 hour", gettext('1 hour'), timedelta(hours=1)),
    ("1 day", gettext('1 day'), timedelta(days=1)),
    ("1 week", gettext('1 week'), timedelta(weeks=1)),
]

possible_ttls_keys = [ttl[0] for ttl in possible_ttls]
timedeltas = {ttl[0]: ttl[2] for ttl in possible_ttls}

def check_csrf_token():
    if request.method == "POST":
        csrf_token = request.form.get("csrf_token")
        assert csrf_token, "Missing CSRF token"
        assert csrf_token == session.get("csrf_token"), "Invalid CSRF token"


def create_routes(url_prefix: str) -> Blueprint:

    bp = Blueprint("ihaveasecret", __name__)

    staticdir = (Path(__file__).parent / "static").as_posix()

    max_message_length = int(configurationStore.get("secrets.max_length", 2048))

    @bp.route("/static/<path:path>")
    def send_static(path: str):
        return send_from_directory(staticdir, path)

    @bp.route("/create", methods=["GET"])
    def display_create_page():
        csrf_token = session["csrf_token"] = random_string(32)
        return render_template(
            "create.html", possible_ttls=possible_ttls, csrf_token=csrf_token
        )

    @bp.route("/create", methods=["POST"])
    def create():
        check_csrf_token()
        message = request.form.get("message")
        ttl = request.form["ttl"]
        password = request.form.get("password")
        assert ttl in possible_ttls_keys, f"Invalid TTL: {ttl}"

        if not message:
            csrf_token = session["csrf_token"] = random_string(32)
            return render_template(
                "create.html",
                possible_ttls=possible_ttls,
                error="Message is required",
                csrf_token=csrf_token,
            )

        if len(message) > max_message_length:
            csrf_token = session["csrf_token"] = random_string(32)
            return render_template(
                "create.html",
                possible_ttls=possible_ttls,
                error=ngettext("Message is too long (max %(max_message_length)s characters)", max_message_length),
                message=message,
                csrf_token=csrf_token,
            )

        key = random_string(32)
        secretStore.save(
            key, message, datetime.now() + timedeltas[ttl], password=password
        )
        return render_template(
            "created.html",
            message_url=build_url(request.url_root, url_prefix, "secret", key),
        )

    def reveal_secret(message_key: str, password: str = None):
        secret_text = secretStore.get_message(message_key, password=password)
        if secret_text is not None:
            return render_template("reveal.html", secret_text=secret_text)
        else:
            return (
                render_template(
                    "error.html",
                    level="danger",
                    message=gettext("Sorry, that secret has already been seen or does not exist."),
                ),
                404,
            )

    @bp.route("/secret/<string:message_key>", methods=["GET"])
    def open_secret(message_key: str):
        is_password_protected = secretStore.is_password_protected(message_key)
        if is_password_protected:
            csrf_token = session["csrf_token"] = random_string(32)
            return render_template(
                "check_password.html", message_key=message_key, csrf_token=csrf_token
            )
        else:
            return render_template(
                "confirm_reveal.html",
                reveal_url=build_url(
                    request.url_root, url_prefix, "reveal", message_key
                ),
            )

    @bp.route("/reveal/<string:message_key>", methods=["GET"])
    def reveal(message_key: str):
        return reveal_secret(message_key)

    @bp.route("/check_password/<string:message_key>", methods=["POST"])
    def check_password(message_key: str):
        check_csrf_token()
        password = request.form["password"]
        success, remaining_attempts = secretStore.check_password(message_key, password)
        if success:
            return reveal_secret(message_key, password=password)
        elif remaining_attempts > 0:
            csrf_token = session["csrf_token"] = random_string(32)
            return render_template(
                "check_password.html",
                message_key=message_key,
                remaining_attempts=remaining_attempts,
                error=gettext("Incorrect password. Please try again."),
                csrf_token=csrf_token,
            )
        else:
            # burn the secret by fetching it
            secretStore.load(message_key)
            return (
                render_template(
                    "error.html",
                    level="danger",
                    message=gettext("The secret has been deleted because of too many incorrect password attempts."),
                ),
                404,
            )

    @bp.route("/", methods=["GET"])
    def index():
        return redirect(url_for("ihaveasecret.display_create_page"))

    return bp
