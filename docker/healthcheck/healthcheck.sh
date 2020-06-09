#!/bin/sh

starting=/healthcheck/web/starting
healthy=/healthcheck/web/healthy
unhealthy=/healthcheck/web/unhealthy

if [ -f "$healthy" ]; then
    exit 0
fi

if [ -f /healthcheck/hc ]; then
    mv "$starting" "$healthy"
else
    mv "$starting" "$unhealthy"
    exit 1
fi
