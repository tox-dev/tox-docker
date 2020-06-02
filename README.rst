============
 tox-docker
============

A `tox <https://tox.readthedocs.io/en/latest/>`__ plugin which runs one or
more `Docker <https://www.docker.com/>`__ containers during the test run.

.. image:: https://dev.azure.com/dcrosta/tox-docker/_apis/build/status/tox-dev.tox-docker?branchName=master
   :target: https://dev.azure.com/dcrosta/tox-docker/_build?definitionId=1&_a=summary
   :alt: Build Status

Usage and Installation
----------------------

tox loads all plugins automatically. It is recommended that you install the
tox-docker plugin into the same Python environment as you install tox into,
whether that's a virtualenv, etc.

You do not need to do anything special when running tox to invoke
tox-docker. You do need to configure your project to request docker
instances (see "Configuration" below).

Configuration
-------------

In the ``testenv`` section, list the Docker images you want to include in
the ``docker`` multi-line-list. Be sure to include the version tag.

You can include environment variables to be passed to the docker container
via the ``dockerenv`` multi-line list. These will also be made available to
your test suite as it runs, as ordinary environment variables::

    [testenv]
    docker =
        postgres:9-alpine
    dockerenv =
        POSTGRES_USER=username
        POSTGRES_DB=dbname

Host and Port Mapping
---------------------

By default, tox-docker runs the container with the "publish all ports" option.
You may also specify port publishing in ``tox.ini``, in a new section like::

    [docker:redis:5.0-alpine]
    ports = 5432:5432/tcp

The image name -- everything after the ``docker:`` in the section header --
must *exactly* match the image name used in your testenv's ``docker`` setting.
Published ports are separated by a newline and are in the format
``<HOST>:<CONTAINER>/<PROTOCOL>``.

Any port the container exposes will be made available to your test suite via
environment variables of the form
``<image-basename>_<exposed-port>_<protocol>_PORT``.  For instance, for the
PostgreSQL container, there will be an environment variable
``POSTGRES_5432_TCP_PORT`` whose value is the ephemeral port number that docker
has bound the container's port 5432 to.

Likewise, exposed UDP ports will have environment variables like
``TELEGRAF_8092_UDP_PORT`` Since it's not possible to check whether UDP port
is open it's just mapping to environment variable without any checks that
service up and running.

The host name for each service is also exposed via environment as
``<image-basename>_HOST``, which is ``POSTGRES_HOST`` and ``TELEGRAF_HOST`` for
the two examples above.

*Deprecation Note:* In older versions of tox-docker, the port was exposed as
``<image-basename>-<exposed-port>-<protocol>``. This additional environment
variable is deprecated, but will be supported until tox-docker 2.0.

Health Checking
---------------

As of version 1.4, tox-docker uses Docker's health checking to determine
when a container is fully running, before it begins your test. For Docker
images that contain a ``HEALTHCHECK`` command, tox-docker uses that.

You may also specify a custom health check in ``tox.ini``, in a new section
like::

    [docker:redis:5.0-alpine]
    healthcheck_cmd = redis-cli ping | grep -q PONG
    healthcheck_interval = 1
    healthcheck_timeout = 1
    healthcheck_retries = 30
    healthcheck_start_period = 0.5

The image name -- everything after the ``docker:`` in the section header --
must *exactly* match the image name used in your testenv's ``docker`` setting.

tox-docker will print a message for each container that it is waiting on a
health check from, whether via the container's built-in ``HEALTHCHECK`` or a
custom health check.

If you are running in a Docker-In-Docker environment, you can override the address
used for port checking using the environment variable ``TOX_DOCKER_GATEWAY``. This
variable should be the hostname or ip address used to connect to the container.

Container Linking
-----------------

Containers can be linked together using the `links` key.  The `links` configuration
should use the form `{IMAGE_NAME}` or `{IMAGE_NAME}:{ALIAS}`.  Multiple links may be
provided. If you do not provide an alias, the untagged image name will be used. The
default aliases in the contrived example below would be 'memcached', 'postgres', and
'elasticsearch'. No validation is performed on the alias. You are responsible for
providing a valid identifier. If the image name produces an auto-generated alias that
is invalid, you will need to provide a suitable alternative yourself using the form
`{IMAGE_NAME}:{ALIAS}` as documented above.

For example::

    docker = 
        memcached:alpine
        postgres:alpine
        elasticsearch:7.7.0
    dockerenv =
        POSTGRES_PASSWORD=password
        discovery.type=single-node
        ES_JAVA_OPTS=-Xms512m -Xmx512m
    [docker:postgres:alpine]
    links = memcached
    [docker:elasticsearch:7.7.0]
    links =
        memcached:cache
        postgres

Note: No dependency resolution is performed. You must define containers in proper
dependency order.  An error will be raised if a link references a container that has
not yet been processed.  Notice in the example above that `postgres` is listed after
`memcached`.  And `elasticsearch` is listed after both `memcached` and `postgres`.
It would be an error to list `postgres` before `memcached` and likewise for placing
`elasticsearch` before either `postgres` or `memcached`.
