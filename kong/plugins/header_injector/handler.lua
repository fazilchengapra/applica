local HeaderInjector = {
    PRIORITY = 900,
    VERSION = "1.0.0",
}

function HeaderInjector:access(conf)
    local jwt_cookie = ngx.var.cookie_access_token

    if jwt_cookie then
        -- decode JWT
        -- set X-User-Id
    end

    kong.service.request.set_header(
        "X-Gateway-Secret",
        conf.gateway_secret
    )
end

return HeaderInjector