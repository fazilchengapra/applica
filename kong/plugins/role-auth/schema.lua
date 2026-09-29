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
                            required = false,
                            default = {},
                            elements = {
                                type = "string",
                            },
                            description = [[
Roles allowed to access this route. Leave empty for pass-through mode:
any authenticated caller is allowed (treated as the default "user" role) and
no X-Admin-Authorized header is injected. The plugin always strips a
client-supplied X-Admin-Authorized header, so attaching it to a shared route
cannot be used to spoof admin access.
                            ]],
                        },
                    },
                },
            },
        },
    },
}
