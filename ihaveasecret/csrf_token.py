from flask import request, session, abort
import os
import datetime

def make_csrf_token():
    session["csrf_token"] = token = os.urandom(32).hex()
    session["csrf_token_created_at"] = datetime.datetime.now().isoformat()
    return token


def check_csrf_token(param="csrf_token"):
    token = session.pop("csrf_token", None)
    if request.method in ["POST", "PATCH", "PUT", "DELETE"]:

        if not token:
            abort(403, "Missing CSRF token")

        if datetime.datetime.fromisoformat(session.pop("csrf_token_created_at")) < datetime.datetime.now() - datetime.timedelta(hours=1):
            abort(403, "CSRF token has expired")

        if token != request.form.get(param):
            abort(403, "Invalid CSRF token")
