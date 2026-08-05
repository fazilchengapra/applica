#!/bin/sh

set -e

esc_jwt=$(printf '%s' "$KONG_JWT_SECRET" | sed 's/[&\\]/\\&/g')
esc_gw=$(printf '%s' "$GATEWAY_INTERNAL_SECRET" | sed 's/[&\\]/\\&/g')

cat /kong/declarative/kong.yml.template /kong/services/*.yml \
  | sed \
      -e "s|__KONG_JWT_SECRET__|$esc_jwt|g" \
      -e "s|__GATEWAY_INTERNAL_SECRET__|$esc_gw|g" \
  > /tmp/kong.yml

exec /docker-entrypoint.sh kong docker-start