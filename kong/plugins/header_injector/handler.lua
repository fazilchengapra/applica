local cjson = require "cjson.safe"

local HeaderInjector = {
    PRIORITY = 950,
    VERSION = "1.0.0",
}

function HeaderInjector:access(conf)

    local ok, err = pcall(function()

        local jwt_cookie = ngx.var.cookie_access_token

        if jwt_cookie then

            local payload_b64 = jwt_cookie:match("^[^.]+%.([^.]+)%.")

            if payload_b64 then

                payload_b64 = payload_b64
                    :gsub("%-", "+")
                    :gsub("_", "/")

                local pad = #payload_b64 % 4

                if pad > 0 then
                    payload_b64 = payload_b64 ..
                        string.rep("=", 4 - pad)
                end

                local decoded = ngx.decode_base64(payload_b64)

                if decoded then

                    -- Convert JSON string → Lua table
                    local claims, json_err =
                        cjson.decode(decoded)

                    if claims then

                        -- Share JWT claims with other plugins
                        kong.ctx.shared.jwt_claims = claims

                        kong.log.notice(
                            "JWT CLAIMS: ",
                            cjson.encode(claims)
                        )

                        -- Get user ID
                        local user_id = claims.sub

                        if user_id then
                            kong.service.request.set_header(
                                "X-User-Id",
                                tostring(user_id)
                            )
                        end

                    else
                        kong.log.err(
                            "Failed to decode JWT JSON: ",
                            json_err
                        )
                    end
                end
            end
        end

        kong.service.request.set_header(
            "X-Gateway-Secret",
            conf.gateway_secret
        )

    end)

    if not ok then
        kong.log.err(err)
    end
end

return HeaderInjector