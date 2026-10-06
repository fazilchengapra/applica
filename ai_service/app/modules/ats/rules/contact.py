"""Contact-detail checks -- presence and basic sanity of the header block."""

import re

from app.modules.ats.rules.text import missing, normalize, present
from app.modules.ats.rules.types import CheckResult

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_PHONE_DIGITS = re.compile(r"\d")


def _contact(parsed: dict) -> dict:
    contact = parsed.get("contact")
    return contact if isinstance(contact, dict) else {}


def check_contact(parsed: dict) -> list[CheckResult]:
    contact = _contact(parsed)
    results: list[CheckResult] = []

    name = normalize(contact.get("full_name"))
    if name:
        results.append(present("contact_name", "Present", evidence={"full_name": contact.get("full_name")}))
    else:
        results.append(missing("contact_name", "Name missing", "A CV without a name cannot be matched to an application."))

    email = (contact.get("email") or "").strip()
    if email and _EMAIL.match(email):
        results.append(present("contact_email", "Present", evidence={"email": email}))
    elif email:
        results.append(
            missing(
                "contact_email",
                "Email malformed",
                f"'{email}' is not a valid email address; an ATS cannot route a confirmation to it.",
                evidence={"email": email},
            )
        )
    else:
        results.append(missing("contact_email", "Email missing", "Automated replies and rejection notices go to this address."))

    phone_digits = _PHONE_DIGITS.findall(contact.get("phone") or "")
    if len(phone_digits) >= 7:
        results.append(present("contact_phone", "Present", evidence={"phone": contact.get("phone")}))
    else:
        results.append(missing("contact_phone", "Phone missing", "Recruiters call shortlisted candidates; a number is expected in the header."))

    if normalize(contact.get("location")):
        results.append(present("contact_location", "Present", evidence={"location": contact.get("location")}))
    else:
        results.append(missing("contact_location", "Location missing", "Location is used to filter by relocation and time zone."))

    links = [
        str(contact.get(key) or "").strip()
        for key in ("linkedin", "github", "portfolio")
        if str(contact.get(key) or "").strip()
    ]
    if links:
        results.append(present("contact_links", "Present", evidence={"links": links}))
    else:
        results.append(
            missing(
                "contact_links",
                "No profile link",
                "Add a LinkedIn, GitHub or portfolio URL so a recruiter can verify the CV.",
            )
        )

    return results
