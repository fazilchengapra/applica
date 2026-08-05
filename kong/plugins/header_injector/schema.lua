local typedefs = require "kong.db.schema.typedefs"

return {
  name = "header_injector",
  fields = {
    {
      config = {
        type = "record",
        fields = {
          {
            gateway_secret = {
              type = "string",
              required = true,
            },
          },
        },
      },
    },
  },
}