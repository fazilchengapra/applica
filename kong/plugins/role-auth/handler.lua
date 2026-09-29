local cjson = require "cjson.safe"

local RoleAuthHandler = {
    PRIORITY = 900,
    VERSION = "1.1.0",
}


-- Only this plugin may grant admin access to downstream services.
local ADMIN_HEADER = "X-Admin-Authorized"

-- Role assumed when the JWT carries no roles claim, so plain authenticated
-- callers are never mistaken for admins.
local DEFAULT_ROLE = "user"


-- Check if a role exists in a table
local function has_role(roles, required_role)
    for _, role in ipairs(roles) do

        if role == required_role then
            return true
        end

    end

    return false
end


-- Check whether the user has at least one allowed role
local function has_allowed_role(user_roles, allowed_roles)
    for _, allowed_role in ipairs(allowed_roles) do

        if has_role(user_roles, allowed_role) then
            return true
        end

    end

    return false
end


-- Pass-through mode when no roles are configured for the route
local function is_open_to_all_users(conf)
    local allowed_roles = conf.allowed_roles

    return type(allowed_roles) ~= "table" or #allowed_roles == 0
end


function RoleAuthHandler:access(conf)

    -- Get JWT claims
    local claims = kong.ctx.shared.jwt_claims

    kong.log.notice(
        "JWT CLAIMS: ",
        cjson.encode(claims or {})
    )

    -- JWT claims not available
    if not claims then

        return kong.response.exit(
            401,
            {
                message = "Authentication required"
            }
        )

    end


    -- Drop any client-supplied admin header on every route this plugin is
    -- attached to. It is only ever set below, after a successful role check.
    kong.service.request.clear_header(ADMIN_HEADER)


    -- No allowed_roles configured: the route serves ordinary users as well.
    -- Authenticated callers pass through and no admin header is injected.
    if is_open_to_all_users(conf) then

        return

    end


    -- Get roles from JWT, defaulting to a plain user
    local user_roles = x.roles

    if type(user_roles) ~= "table" or #user_roles == 0 then

        user_roles = { DEFAULT_ROLE }

    end


    kong.log.notice("user roles: ", cjson.encode(user_roles))


    -- Get allowed roles from Kong configuration
    local allowed_roles = conf.allowed_roles


    -- Check authorization
    if not has_allowed_role(user_roles, allowed_roles) then

        return kong.response.exit(
            403,
            {
                message = "You do not have permission to access this resource"
            }
        )

    end

    -- Authorized: mark the request as admin for downstream services
    kong.service.request.set_header(ADMIN_HEADER, "true")

end


return RoleAuthHandler
