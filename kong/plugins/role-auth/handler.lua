local RoleAuthHandler = {
    PRIORITY = 900,
    VERSION = "1.0.0",
}


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


function RoleAuthHandler:access(conf)

    -- Get JWT claims
    local claims = kong.ctx.shared.jwt_claims

    kong.log.notice(
        "JWT CLAIMS: ",
        require("cjson").encode(claims or {})
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


    -- Get roles from JWT
    local user_roles = claims.roles or {}


    -- Get allowed roles from Kong configuration
    local allowed_roles = conf.allowed_roles or {}


    -- Check authorization
    if not has_allowed_role(user_roles, allowed_roles) then

        return kong.response.exit(
            403,
            {
                message = "You do not have permission to access this resource"
            }
        )

    end

end


return RoleAuthHandler