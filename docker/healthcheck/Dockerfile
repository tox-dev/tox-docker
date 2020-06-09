FROM python:3.8-alpine

# tests can cause the built-in healthcheck to fail by varying
# this envrionment variable; the healthcheck command cares about
# its presence (by default, it is present)
ENV HCFILE=hc

RUN mkdir -p /healthcheck/web
RUN touch /healthcheck/web/starting

COPY healthcheck.sh /
HEALTHCHECK CMD /healthcheck.sh

# so that tests can verify contents of the /healthcheck directory
EXPOSE 8000
CMD touch /healthcheck/$HCFILE && /usr/local/bin/python -m http.server 8000 -b 0.0.0.0 -d /healthcheck/web
