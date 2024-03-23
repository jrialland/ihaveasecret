ihaveasecret
============

A simple web app that allow you to pass secret data to someone by giving him a temporary link.
Once the link is opened the secret message is deleted from the server.

The secrets are stored in redis, and are encrypted using the app's secret key

The application is intentinally as simple as possible in order to fulfill strong security requirements : almost no javascript, simple css, no fancy things.

It uses the following components:
 * [python](https://www.python.org/) 3.12
 * [flask](https://flask.palletsprojects.com/en/3.0.x/) ( and [waitress](https://github.com/Pylons/waitress) )
 * [pycryptodome](https://www.pycryptodome.org/)
 * [redis-py](https://github.com/redis/redis-py)
 * [bulma](https://bulma.io/)
 * [remixicon](https://remixicon.com/)

Configuration
-----

Configuration can be done either by providing docker secrets, environment variables, or a configuration file.
The resolution of configuration settings is done this way :

1. look for a file is /run/secrets with the same name. If this file exists, the value is the file's content.
2. check if an environment variable with that name exists.
3. look for the key in the configuration file "config.json"

This table explains how to configure the app :

| key | secret file | environment variable | definition | default value |
|---|---|---|---|---|
|app.secret_key|/run/secrets/app.secret_key|APP_SECRET_KEY|used for as flask unique key| none (mandatory)|
|app.url_prefix|/run/secrets/app.url_prefix|APP_URL_PREFIX|path to prepend to all uris| empty|
|secrets.max_length|/run/secrets/secrets.max_length|SECRETS_MAX_LENGTH|maximum allowed messages length|2048|
|redis.url|/run/secrets/redis.url|REDIS_URL|redis url|none, in-memory storage is used if missing|
|passwords.max_attempts|/run/secrets/password.max_attempts|PASSWORDS_MAX_ATTEMPTS|how many tries are allowed|3|

TODOs :
-------
 * Translations
 * <strike>Document configuration keys</strike>
 * javascript : hint on password strength (https://github.com/dropbox/zxcvbn ?)
 * javascript : message length

Development :
-----------
I use [podman-compose](https://github.com/containers/podman-compose) :

```
podman-compose up -d
```
Will start the application in debug (=flask auto-reload) mode along with a redis instance.

production :
------------

using docker or podman : `docker build -t ihaveasecret -f Containerfile`


Screenshots :
-------------

![Create a message](./docs/screenshot_create.png)
![Create a message, filled](./docs/screenshot_create_2.png)
![Message created](./docs/screenshot_created.png)
![Checking password](./docs/screenshot_check_password.png)
![Invalid password](./docs/screenshot_invalid_attempt.png)
![Read message](/docs/screenshot_read.png)