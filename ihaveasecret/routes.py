from flask import (
    Blueprint,
    request,
    session,
    render_template,
    send_from_directory,
    redirect,
    url_for,
)
import logging
from datetime import datetime, timedelta
from .configuration import configurationStore
from .secretstore import secretStore
from .send_email import send_message_created_email
from .util import random_string, build_url, is_valid_email
from pathlib import Path
from flask_babel import gettext, ngettext
from .csrf_token import check_csrf_token

possible_ttls = [
    ("1 hour", gettext("1 hour"), timedelta(hours=1)),
    ("1 day", gettext("1 day"), timedelta(days=1)),
    ("1 week", gettext("1 week"), timedelta(weeks=1)),
]

possible_ttls_keys = [ttl[0] for ttl in possible_ttls]
timedeltas = {ttl[0]: ttl[2] for ttl in possible_ttls}


def create_routes(url_prefix: str) -> Blueprint:

    bp = Blueprint("ihaveasecret", __name__)

    staticdir = (Path(__file__).parent / "static").as_posix()

    max_message_length = int(configurationStore.get("secrets.max_length", 2048))

    @bp.route("/static/<path:path>")
    def send_static(path: str):
        return send_from_directory(staticdir, path)

    @bp.route("/robots.txt")
    def send_robots_txt():
        return send_from_directory(staticdir, "robots.txt")
    
    @bp.route("/favicon.ico")
    def send_favicon():
        return send_from_directory(staticdir, "favicon.ico")
    
    @bp.route("ads.txt")
    def send_ads_txt():
        return send_from_directory(staticdir, "ads.txt")

    @bp.route("/create", methods=["GET"])
    def display_create_page():
        check_csrf_token()
        return render_template("create.html", possible_ttls=possible_ttls)

    # / is the same as /create
    @bp.route("/", methods=["GET"])
    def display_create_page_redirect():
        check_csrf_token()
        return render_template("create.html", possible_ttls=possible_ttls)

    @bp.route("/create", methods=["POST"])
    def create():
        check_csrf_token()
        note = request.form.get("note", "")
        message = request.form.get("message")
        email = request.form.get("email")
        ttl = request.form["ttl"]
        password = request.form.get("password")
        assert ttl in possible_ttls_keys, f"Invalid TTL: {ttl}"

        if len(note) > max_message_length:
            return render_template(
                "create.html",
                possible_ttls=possible_ttls,
                error=ngettext(
                    "Note is too long (max %(max_message_length)s characters)",
                    max_message_length,
                ),
                note=note,
                message=message,
                email=email,
                ttl=ttl,
            )

        if len(message) > max_message_length:
            return render_template(
                "create.html",
                possible_ttls=possible_ttls,
                error=ngettext(
                    "Message is too long (max %(max_message_length)s characters)",
                    max_message_length,
                ),
                note=note,
                message=message,
                email=email,
                ttl=ttl,
            )
        if not message:
            return render_template(
                "create.html", possible_ttls=possible_ttls, error="Message is required",
                note=note,
                message=message,
                email=email,
                ttl=ttl,
            )

        if len(message) > max_message_length:
            return render_template(
                "create.html",
                possible_ttls=possible_ttls,
                error=ngettext(
                    "Message is too long (max %(max_message_length)s characters)",
                    max_message_length,
                ),
                note=note,
                message=message,
                email=email,
                ttl=ttl,
            )

        # check email
        if email and email.strip() != "":
            if not is_valid_email(email):
                return render_template(
                    "create.html",
                    possible_ttls=possible_ttls,
                    error=gettext("Invalid email address"),
                    note=note,
                    message=message,
                    email=email,
                    ttl=ttl,
                )

        key = random_string(32)

        # save the secret
        secretStore.save(
            key, note, message, datetime.now() + timedeltas[ttl], password=password
        )

        message_url = build_url(request.url_root, url_prefix, "secret", key)

        # send email if configured
        email_status = "not_sent"
        if email and not bool(configurationStore.get("app.disable_email", False)):
            try:
                send_message_created_email(email, message_url=message_url, note=note, ttl=ttl)
                email_status = "sent"
            except Exception as e:
                email_status = "error"
                logging.exception("Failed to send email")

        return render_template(
            "created.html",
            message_url=message_url,
            email_status=email_status,
        )

    def reveal_secret(message_key: str, password: str = None):
        secret = secretStore.load(message_key, remove=True)
        if secret is None:
            return (
                render_template(
                    "error.html",
                    level="danger",
                    message=gettext(
                        "Sorry, that secret has already been seen or does not exist."
                    ),
                ),
                404,
            )
        secret_text = secret.message.decrypt(password or secretStore.default_password)
        if secret_text is not None:
            return render_template(
                "reveal.html", note=secret.note, secret_text=secret_text
            )
        else:
            return (
                render_template(
                    "error.html",
                    level="danger",
                    message=gettext(
                        "Sorry, that secret has already been seen or does not exist."
                    ),
                ),
                404,
            )

    @bp.route("/secret/<string:message_key>", methods=["GET"])
    def open_secret(message_key: str):
        secret = secretStore.load(message_key, remove=False)
        if secret is None:
            return (
                render_template(
                    "error.html",
                    level="danger",
                    message=gettext(
                        "Sorry, that secret has already been seen or does not exist."
                    ),
                ),
                404,
            )
        if secret.expires < datetime.now():
            return (
                render_template(
                    "error.html",
                    level="danger",
                    message=gettext("Sorry, that secret has expired."),
                ),
                404,
            )
        if secret.password_protected:
            return render_template(
                "check_password.html",
                message_key=message_key,
                note=secret.note,
                remaining_attempts=secret.password_attempts,
            )
        else:
            return render_template(
                "confirm_reveal.html",
                note=secret.note,
                reveal_url=build_url(
                    request.url_root, url_prefix, "reveal", message_key
                ),
            )

    @bp.route("/reveal/<string:message_key>", methods=["GET"])
    def reveal(message_key: str):
        return reveal_secret(message_key)

    @bp.route("/check_password/<string:message_key>", methods=["GET"])
    def check_password_get(message_key: str):
        # redirect to the /secret/<message_key> route
        return redirect(url_for("ihaveasecret.open_secret", message_key=message_key))

    @bp.route("/check_password/<string:message_key>", methods=["POST"])
    def check_password(message_key: str):
        check_csrf_token()
        password = request.form["password"]
        note, success, remaining_attempts = secretStore.check_password(
            message_key, password
        )
        if success:
            return reveal_secret(message_key, password=password)
        elif remaining_attempts > 0:
            return render_template(
                "check_password.html",
                note=note,
                message_key=message_key,
                remaining_attempts=remaining_attempts,
                error=gettext("Incorrect password. Please try again."),
            )
        else:
            # burn the secret by fetching it
            secretStore.load(message_key)
            return (
                render_template(
                    "error.html",
                    level="danger",
                    note=note,
                    message=gettext(
                        "The secret has been deleted because of too many incorrect password attempts."
                    ),
                ),
                404,
            )

    @bp.route("/", methods=["GET"])
    def index():
        return redirect(url_for("ihaveasecret.display_create_page"))

    return bp
