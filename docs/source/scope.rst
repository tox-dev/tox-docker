===============
 Project Scope
===============

Tox-docker is meant to do just enough to support running tests in tox with
supporting services run in Docker. This page describes what that means, and
why some feature requests end up declined or solved some other way.

What tox-docker Is For
----------------------

Tox-docker was written for a common situation: your tests need a service,
like a database, and you don't want to encode details of your development or
CI environment into the tests. Tox-docker starts the database in a
container, tox runs the tests, and the tests find the service through
environment variables::

    tox
     |
     |  1. start containers, and wait for any health checks to pass
     +------------------------------------------> [docker:db] (postgres)
     |                                                    ^
     |  2. run commands, with DB_HOST and                 |
     |     DB_5432_TCP_PORT set in the environment        |
     +--> your tests -------------------------------------+
     |
     |  3. stop and remove the containers
     +------------------------------------------> [docker:db]

The tests still run directly through tox runs them (ie in a virtualenv).
Tox-docker does not run your tests inside a container; other tools exist
for that purpose.

What tox-docker Is Not
----------------------

Complex orchestration workflows of many services, dependencies, networks,
volumes, etc, are not the target use-case for tox-docker. Tox-docker is not
a replacement for `Docker Compose <https://docs.docker.com/compose/>`__ or
other more sophisticated tools. Tox-docker handles only a few things: run a
container, wait for it to become healthy, tell the tests how to reach it,
and clean it up afterward. It is not likely to grow much past that.

Customizing Containers
----------------------

Most requests for new configuration directives are really requests to
customize the container: run a different command, run as a different user,
add some files, change some settings. Docker already has a good way to do
all of these, the `Dockerfile
<https://docs.docker.com/reference/dockerfile/>`__. Tox-docker supports
building from a Dockerfile on demand, so we prefer to rely on that rather
than adding new ``tox.ini`` directives where possible::

    # docker/db/Dockerfile
    FROM postgres:16-alpine
    COPY schema.sql /docker-entrypoint-initdb.d/

    # tox.ini
    [docker:db]
    dockerfile = {toxinidir}/docker/db/Dockerfile

This keeps your ``tox.ini`` focused on what your tests need, and keeps the
container's setup in a format anyone who knows Docker can already read.

Things That Belong Elsewhere
----------------------------

Some setup is better handled outside of tox-docker:

* Logging in to a private registry or pulling images that need credentials
  is a job for your CI system before it runs tox. Once the image exists
  locally, tox-docker can use it as normal.
* Commands that need to run on the host before or after the tests can go in
  ``commands_pre`` and ``commands_post``, or in your CI configuration.

Configuration Should Be Explicit
--------------------------------

Where there's a choice between a little more typing in ``tox.ini`` and
tox-docker guessing what you meant, tox-docker asks you to type it. For
example, ``expose`` requires the protocol (``5432/tcp``) even though most
ports are TCP. This follows from the `Zen of Python
<https://peps.python.org/pep-0020/>`__.

Proposing New Features
----------------------

Use cases that tox-docker doesn't serve well are worth hearing about. Before
opening an issue or pull request for a new directive, consider:

* Can this be done in a Dockerfile?
* Can tox already do this, eg with ``commands_pre``, ``setenv``, or
  substitutions?
* Can your CI system do this before running tox?

If the answer to all of these is no, please open an issue that describes
what you're trying to do. Tox-docker aims to keep a small interface, so it
helps to understand the use case before settling on how (or whether)
tox-docker should support it.
