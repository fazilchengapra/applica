from app.modules.jobs.utils.hashing import compute_dedup_hash
from app.modules.companies.utils.normalize import normalize_company_name

h1 = compute_dedup_hash(
    "Backend Engineer", "abc-123", normalize_company_name("Bangalore, India")
)
h2 = compute_dedup_hash(
    "backend engineer ", "abc-123", normalize_company_name("Bangalore India")
)
h3 = compute_dedup_hash(
    "Frontend Engineer", "abc-123", normalize_company_name("Bangalore, India")
)
print("h1:", h1)
print("h2:", h2)
print("h3:", h3)
print("h1 == h2 (should match, same normalized identity):", h1 == h2)
print("h1 == h3 (should differ):", h1 == h3)
