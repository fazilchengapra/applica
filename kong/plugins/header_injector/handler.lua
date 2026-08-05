local HeaderInjector = {
    PRIORITY = 900,
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

                local ok2, decoded =
                    pcall(ngx.decode_base64, payload_b64)

                if ok2 and decoded then

                    local user_id =
                        decoded:match('"user_id"%s*:%s*"?([%w%-_]+)"?')

                    if user_id then
                        kong.service.request.set_header(
                            "X-User-Id",
                            user_id
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