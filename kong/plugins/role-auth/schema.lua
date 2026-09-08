local typedefs = require "kong.db.schema.typedefs"

return {
    name = "role-auth",

    fields = {
        {
            config = {
                type = "record",
                fields = {
                    {
                        allowed_roles = {
                            type = "array",
                            required = true,
                            elements = {
                                type = "string",
                            },
                            description = "Roles allowed to access this route",
                        },
                    },
                },
            },
        },
    },
}