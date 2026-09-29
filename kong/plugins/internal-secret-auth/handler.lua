-- handler.lua
local kong = kong

local InternalSecretAuthHandler = {
  PRIORITY = 1000,
  VERSION = "1.0.0",
}

function InternalSecretAuthHandler:access(conf)
  local provided_secret = kong.request.get_header("X-Internal-Secret")

  if provided_secret ~= conf.gateway_secret then
    return kong.response.exit(401, { message = "Invalid internal secret" })
  end

  -- secret matched, safe to pass through. The caller identity is stamped
  -- rather than the secret so the backend can trust the request came through
  -- the gateway without the secret being re-read here.
  kong.service.request.set_header(
    "X-Internal-Service",
    conf.internal_service or "notification-dispatcher"
  )
end

return InternalSecretAuthHandler