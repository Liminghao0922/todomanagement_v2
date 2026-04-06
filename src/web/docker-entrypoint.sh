#!/bin/sh
set -eu

if [ -z "${API_PROXY_TARGET:-}" ]; then
  echo "API_PROXY_TARGET is required" >&2
  exit 1
fi

envsubst '${API_PROXY_TARGET}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'