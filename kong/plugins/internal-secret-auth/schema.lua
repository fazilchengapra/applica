local typedefs = require "kong.db.schema.typedefs"

local PLUGIN_NAME = "internal-secret-auth"

local schema = {
  name = PLUGIN_NAME,
  fields = {
    { consumer = typedefs.no_consumer },
    { protocols = typedefs.protocols_http },
    { config = {
        type = "record",
        fields = {
          { secret_header = { type = "string", default = "X-Internal-Signature", required = true } },
          { timestamp_header = { type = "string", default = "X-Internal-Timestamp", required = true } },
          { gateway_secret = { type = "string", required = true } }, -- drop `encrypted = true` unless Kong Enterprise keyring is set up
          { injected_header_name = { type = "string", default = "X-Internal-Service", required = true } },
          { injected_header_value = { type = "string", default = "notification-dispatcher", required = true } },
          { max_clock_skew_seconds = { type = "number", default = 300, required = true } },
        },
      },
    },
  },
}

return schema