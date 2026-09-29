-- schema.lua
local typedefs = require "kong.db.schema.typedefs"

return {
  name = "internal-secret-auth",
  fields = {
    { consumer = typedefs.no_consumer },
    { protocols = typedefs.protocols_http },
    { config = {
        type = "record",
        fields = {
          { gateway_secret = { type = "string", required = true } },
          {
            internal_service = {
              type = "string",
              required = false,
              default = "notification-dispatcher",
              description = [[
Value stamped into the X-Internal-Service header that the upstream service
verifies. Defaults to the original notification-dispatcher value so existing
routes are unchanged; set it per route to identify a different caller.]],
            },
          },
        },
      },
    },
  },
}