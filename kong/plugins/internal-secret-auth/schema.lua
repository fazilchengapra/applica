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
        },
      },
    },
  },
}