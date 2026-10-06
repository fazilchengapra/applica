"""Pure rule checks that decide a user's score.

Several of these look obviously correct and are not: the keyword matcher's
handling of punctuation-heavy terms, a year with no month only ever *shrinking*
a gap, and the summary section warning instead of failing.
"""

import pytest

from app.modules.ats.constants import CHECKS_BY_ID, CheckStatus
from app.modules.ats.rules import contact, impact, integrity, keywords, sections, structure
from app.modules.ats.rules.impact import metric_candidate_bullets
from app.modules.ats.rules.structure import parse_month
from app.modules.ats.rules.text import collect_bullets, normalize


def _complete_header():
    return {
        "contact": {
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "phone": "+44 20 7946 0018",
            "location": "London, UK",
            "linkedin": "https://linkedin.com/in/ada",
        }
    }


class TestContact:
    def test_every_contact_check_fails_on_an_empty_header(self):
        results = {r.id: r for r in contact.check_contact({})}
        assert set(results) == {
            "contact_name",
            "contact_email",
            "contact_phone",
            "contact_location",
            "contact_links",
        }
        assert all(r.status is CheckStatus.FAIL for r in results.values())
        assert all(r.score == 0.0 for r in results.values())

    def test_a_complete_header_passes_every_contact_check(self):
        results = {r.id: r for r in contact.check_contact(_complete_header())}
        assert all(r.status is CheckStatus.PASS for r in results.values())

    def test_malformed_email_is_reported_as_malformed_not_missing(self):
        """A CV with an unrouteable address must not read as merely absent."""
        parsed = _complete_header()
        parsed["contact"]["email"] = "ada at example dot com"

        results = {r.id: r for r in contact.check_contact(parsed)}

        assert results["contact_email"].status is CheckStatus.FAIL
        assert results["contact_email"].value == "Email malformed"

    def test_a_linkedin_url_alone_satisfies_the_link_check(self):
        parsed = {"contact": {**_complete_header()["contact"], "github": None}}
        results = {r.id: r for r in contact.check_contact(parsed)}
        assert results["contact_links"].status is CheckStatus.PASS


class TestSections:
    def test_a_missing_summary_warns_instead_of_failing(self):
        """The summary is the only section a competent CV can legitimately omit."""
        parsed = {"experience": [{"title": "Dev"}], "education": [{"degree": "BSc"}], "skills": ["Python"]}

        results = {r.id: r for r in sections.check_sections(parsed)}

        assert results["section_summary"].status is CheckStatus.WARN
        assert results["section_experience"].status is CheckStatus.PASS
        assert results["section_skills"].status is CheckStatus.PASS

    def test_a_missing_experience_section_is_a_hard_failure(self):
        results = {r.id: r for r in sections.check_sections({})}
        assert results["section_experience"].status is CheckStatus.FAIL
        assert results["section_education"].status is CheckStatus.FAIL
        assert results["section_skills"].status is CheckStatus.FAIL

    def test_an_empty_section_list_counts_as_absent(self):
        results = {r.id: r for r in sections.check_sections({"skills": [], "summary": "   "})}
        assert results["section_skills"].status is CheckStatus.FAIL
        assert results["section_summary"].status is CheckStatus.WARN


class TestKeywordCoverage:
    def test_punctuation_heavy_terms_are_matched(self):
        """`\\b` cannot match ``C++`` -- the term would be reported missing forever."""
        matched, missing_terms = keywords.match_terms(
            ["python", "c++", "nodejs"],
            "Built services in C++ and Python. Nothing else here.",
        )
        assert matched == ["python", "c++"]
        assert missing_terms == ["nodejs"]

    def test_a_term_does_not_match_inside_a_longer_word(self):
        matched, missing_terms = keywords.match_terms(["go"], "We algorithms are fast")
        assert missing_terms == ["go"]

    def test_value_states_how_many_terms_are_left(self):
        result = keywords.check_keyword_coverage(
            ["python", "kubernetes", "terraform", "graphql"],
            "Python only",
            [],
        )
        assert result.value == "Add 3 more"
        assert result.status is CheckStatus.FAIL
        assert result.evidence["missing"] == ["kubernetes", "terraform", "graphql"]

    def test_full_coverage_reports_all_matched(self):
        result = keywords.check_keyword_coverage(["python", "django"], "Python and Django", [])
        assert result.value == "All 2 matched"
        assert result.status is CheckStatus.PASS
        assert result.score == 1.0

    def test_an_unavailable_vocabulary_skips_rather_than_scoring_zero(self):
        result = keywords.check_keyword_coverage([], "whatever", [])
        assert result.status is CheckStatus.SKIPPED
        assert result.score == 0.0

    def test_structured_skills_are_searched_too(self):
        result = keywords.check_keyword_coverage(["kubernetes"], "no mention here", ["Kubernetes"])
        assert result.score == 1.0


class TestDates:
    def test_common_cv_date_formats_parse(self):
        assert parse_month("Jan 2020") == (2020, 1)
        assert parse_month("March 2020") == (2020, 3)
        assert parse_month("2020-03") == (2020, 3)
        assert parse_month("03/2020") == (2020, 3)

    def test_present_is_not_a_date(self):
        assert parse_month("Present") is None
        assert parse_month("Current") is None
        assert parse_month("") is None

    def test_a_year_only_expands_outward_so_a_gap_can_only_shrink(self):
        """Treating '2020' as January for an end date would invent an 11-month gap."""
        assert parse_month("2020", end=False) == (2020, 1)
        assert parse_month("2020", end=True) == (2020, 12)

    def test_missing_dates_fail_the_completeness_check(self):
        parsed = {
            "experience": [
                {"title": "Dev", "company": "Acme", "start_date": "2020"},
                {"title": "Dev", "company": "Acme", "start_date": "2021", "is_current": False},
            ]
        }
        result = structure.check_date_completeness(parsed)
        assert result.status is CheckStatus.FAIL
        assert result.evidence["incomplete"] == ["Dev (Acme)", "Dev (Acme)"]

    def test_no_experience_skips_the_date_check(self):
        result = structure.check_date_completeness({})
        assert result.status is CheckStatus.SKIPPED

    def test_a_long_gap_is_reported_in_months(self):
        parsed = {
            "experience": [
                {"title": "Dev", "start_date": "2019-01", "end_date": "2021-12"},
                {"title": "Dev", "start_date": "2023-01", "is_current": True},
            ]
        }
        result = structure.check_employment_gaps(parsed)
        assert result.status is CheckStatus.FAIL
        assert result.value == "13-month gap"
        assert result.evidence["longest_months"] == 13

    def test_back_to_back_roles_report_no_gap(self):
        parsed = {
            "experience": [
                {"title": "Dev", "start_date": "2020-01", "end_date": "2021-12"},
                {"title": "Dev", "start_date": "2022-01", "is_current": True},
            ]
        }
        result = structure.check_employment_gaps(parsed)
        assert result.status is CheckStatus.PASS
        assert result.value == "No material gaps"

    def test_a_single_dated_role_has_nothing_to_measure(self):
        parsed = {"experience": [{"title": "Dev", "start_date": "2020-01", "end_date": "2021-12"}]}
        assert structure.check_employment_gaps(parsed).status is CheckStatus.SKIPPED


class TestBullets:
    def test_bullets_are_split_per_line_and_strip_the_marker(self):
        parsed = {
            "experience": [
                {
                    "title": "Dev",
                    "company": "Acme",
                    "description": "- Built the API\n* Led the migration\n  Rewrote the parser",
                    "is_current": True,
                }
            ]
        }
        bullets = collect_bullets(parsed)

        assert [b.text for b in bullets] == ["Built the API", "Led the migration", "Rewrote the parser"]
        assert bullets[2].ref == "experience[0].bullet[2]"
        assert bullets[0].is_current is True

    def test_very_long_bullets_fail_the_length_check(self):
        long_text = "x" * 400
        parsed = {
            "experience": [
                {
                    "title": "Dev",
                    "company": "Acme",
                    "description": "\n".join([long_text, long_text, long_text, long_text]),
                    "is_current": True,
                }
            ]
        }
        result = structure.check_bullet_length(collect_bullets(parsed))
        assert result.status is CheckStatus.FAIL
        assert result.score == 0.0

    def test_no_bullets_skips_both_content_checks(self):
        assert structure.check_bullet_length([]).status is CheckStatus.SKIPPED
        assert impact.check_action_verbs([]).status is CheckStatus.SKIPPED

    def test_action_verbs_score_the_opening_word_only(self):
        bullets = collect_bullets(
            {
                "experience": [
                    {
                        "title": "Dev",
                        "company": "Acme",
                        "description": "Led the team\nResponsible for the database\nBuilt the API",
                        "is_current": True,
                    }
                ]
            }
        )
        result = impact.check_action_verbs(bullets)
        assert result.evidence["weak_refs"] == ["experience[0].bullet[1]"]
        assert result.score == pytest.approx(2 / 3)


class TestMetricCandidates:
    def test_metric_candidates_are_recognised(self):
        bullets = collect_bullets(
            {
                "experience": [
                    {
                        "title": "Dev",
                        "company": "Acme",
                        "description": (
                            "Raised conversion 15%\n"
                            "Cut spend by $40k\n"
                            "Shipped 3x faster\n"
                            "Served 1,000 users\n"
                            "Rewrote the docs"
                        ),
                        "is_current": True,
                    }
                ]
            }
        )
        refs = [b.ref for b in metric_candidate_bullets(bullets)]
        assert refs == [
            "experience[0].bullet[0]",
            "experience[0].bullet[1]",
            "experience[0].bullet[2]",
            "experience[0].bullet[3]",
        ]


class TestDataIntegrity:
    def test_parsed_content_absent_from_the_source_is_flagged(self):
        parsed = {"summary": "A summary nobody wrote", "skills": ["Elixir"]}
        result = integrity.check_data_integrity(parsed, "Totally unrelated source text")

        assert result.status is CheckStatus.FAIL
        assert set(result.evidence["unmatched"]) == {"summary", "skills[0]"}

    def test_matching_content_is_consistent(self):
        parsed = {"summary": "Backend engineer in London", "skills": ["Python"]}
        result = integrity.check_data_integrity(
            parsed, "Backend engineer in London. Skills: Python, Go."
        )
        assert result.status is CheckStatus.PASS

    def test_an_empty_source_skips_instead_of_failing(self):
        """No extractable text means there is nothing to compare against."""
        result = integrity.check_data_integrity({"summary": "x"}, "")
        assert result.status is CheckStatus.SKIPPED

    def test_this_check_carrying_no_weight_is_the_catalogue_contract(self):
        assert CHECKS_BY_ID["data_integrity"].weight == 0


def test_normalize_collapses_whitespace():
    assert normalize("  Senior   Engineer \n") == "senior engineer"
    assert normalize(None) == ""
