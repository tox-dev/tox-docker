# healthcheck

A Docker image to test tox-docker's health checking abilities.

The container exposes a simple HTTP server on port 8000 which lists a
directory, the files in which indicate the healthcheck status: `starting`,
`healthy`, or `unhealthy`. The built-in health check script will indicate
its output for inspection in this way.

By default the image's health check will succeed when first run. To test
cases where the health check fails, set environment variable `HCFILE` to
anything other than "hc".
