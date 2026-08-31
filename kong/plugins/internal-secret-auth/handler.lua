local hmac = require "resty.hmac"
local kong = kong

local InternalSecretAuthHandler = {
  PRIORITY = 1000, -- run before header_injector (which should trust this has already validated)
  VERSION = "1.0.0",
}

local bit = require "bit"

local function secure_compare(a, b)
  if type(a) ~= "string" or type(b) ~= "string" then
    return false
  end
  if #a ~= #b then
    return false
  end
  local result = 0
  for i = 1, #a do
    result = bit.bor(result, bit.bxor(string.byte(a, i), string.byte(b, i)))
  end
  return result == 0
end

function InternalSecretAuthHandler:access(conf)
  local signature = kong.request.get_header(conf.secret_header)
  local timestamp = kong.request.get_header(conf.timestamp_header)

  if not signature or not timestamp then
    kong.log.warn("internal-secret-auth: missing signature or timestamp header")
    return kong.response.exit(401, { message = "Missing internal auth headers" })
  end

  -- Reject stale/replayed requests
  local ts_num = tonumber(timestamp)
  if not ts_num then
    return kong.response.exit(401, { message = "Invalid timestamp" })
  end

  local now = ngx.time()
  if math.abs(now - ts_num) > conf.max_clock_skew_seconds then
    kong.log.warn("internal-secret-auth: timestamp outside allowed skew")
    return kong.response.exit(401, { message = "Request expired" })
  end

  -- Read raw body for HMAC — must be done before any body transformation plugins run
  local raw_body = kong.request.get_raw_body() or ""

  -- Signed payload: method + path + timestamp + body (adjust to match sender's construction)
  local method = kong.request.get_method()
  local path = kong.request.get_path()
  local signing_string = method .. "\n" .. path .. "\n" .. timestamp .. "\n" .. raw_body

  local generator = hmac:new(conf.gateway_secret, hmac.ALGOS.SHA256)
  if not generator then
    kong.log.err("internal-secret-auth: failed to initialize HMAC generator")
    return kong.response.exit(500, { message = "Internal auth error" })
  end

  local ok = generator:update(signing_string)
  if not ok then
    kong.log.err("internal-secret-auth: failed to update HMAC digest")
    return kong.response.exit(500, { message = "Internal auth error" })
  end

  local computed_digest = generator:final(nil, true) -- hex output
  local expected_signature = computed_digest

  if not secure_compare(signature, expected_signature) then
    kong.log.warn("internal-secret-auth: signature mismatch")
    return kong.response.exit(401, { message = "Invalid internal signature" })
  end

  -- Signature valid — mark request as verified internal call
  kong.service.request.set_header(conf.injected_header_name, conf.injected_header_value)
end

return InternalSecretAuthHandler