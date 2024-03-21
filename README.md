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

TODOs :
-------
 * Translations
 * Document configuration keys
 * javascript : hint on password strength (https://github.com/dropbox/zxcvbn ?)
 * javascript : message length

Development :
-----------
I use podman & podman compose :

```
podman-compose up -d
```
Will start the application in debug (=flask auto-reload) mode along with a redis instance.

Deployment :
------------

WIP



Screenshots :
-------------

![Create a message](./docs/screenshot_create.png)
![Create a message, filled](./docs/screenshot_create_2.png)
![Message created](./docs/screenshot_created.png)
![Checking password](./docs/screenshot_check_password.png)
![Invalid password](./docs/screenshot_invalid_attempt.png)
![Read message](/docs/screenshot_read.png)