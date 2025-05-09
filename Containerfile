FROM python:3.12-alpine as builder
ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VENV="/app/.venv"

RUN pip install --root-user-action=ignore --upgrade pip
RUN pip install --root-user-action=ignore poetry

ADD poetry.lock pyproject.toml /app/

WORKDIR /app
RUN poetry lock
RUN poetry install --no-root --only main

# ------------------------------------------------------------------------------
FROM python:3.12-alpine as runtime
COPY --from=builder /app /app
ADD ihaveasecret /app/ihaveasecret

# add the executables brought from imported modules into the PATH
ENV PATH="/app/.venv/bin:${PATH}"

# compile the translations
RUN cd /app/ihaveasecret && pybabel compile -d translations

# ------------------------------------------------------------------------------
WORKDIR /app
EXPOSE 5000
CMD ["waitress-serve", "--port=5000", "ihaveasecret:app"]