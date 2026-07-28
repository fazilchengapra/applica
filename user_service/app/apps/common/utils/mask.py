def mask_email(email: str) -> str:
    local, domain = email.split("@")

    if len(local) <= 2:
        masked = local[0] + "*"
    else:
        masked = local[0] + "*" * (len(local) - 2) + local[-1]

    return f"{masked}@{domain}"


def mask_phone_number(phone_number: str) -> str:
    if len(phone_number) <= 4:
        return "*" * len(phone_number)

    return phone_number[:2] + "*" * (len(phone_number) - 4) + phone_number[-2:]
