from ..constants import phone

def _generate_otp() -> str:
    import secrets

    return f"{secrets.randbelow(10 ** phone.OTP_LENGTH):0{phone.OTP_LENGTH}d}"