def mask_email(email: str) -> str:
    local, domain = email.split("@")

    if len(local) <= 2:
        masked = local[0] + "*"
    else:
        masked = (
            local[0]
            + "*" * (len(local) - 2)
            + local[-1]
        )

    return f"{masked}@{domain}"