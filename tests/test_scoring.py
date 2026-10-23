import pytest

from job_triage.scoring import adjust_level, analyze_text, cap_total, cv_active_terms, score


def test_score_components_sum_to_total():
    parts, total = score("Sustainability Analyst")
    assert total == sum(parts)
    assert len(parts) == 4


def test_junior_title_beats_senior_title():
    _, junior = score("Junior Sustainability Analyst")
    _, senior = score("Senior Sustainability Analyst")
    assert junior > senior


def test_professor_is_hard_capped():
    _, total = score("Professor of Sustainable Energy Systems")
    assert total <= 35


def test_finance_role_capped_unless_sustainability_title():
    _, banking = score("Corporate Finance Associate")
    _, green = score("Sustainable Finance Associate")
    assert banking <= 45
    assert green > banking


def test_danish_title_lowers_language_score():
    english, _ = score("Sustainability Consultant")
    danish, _ = score("Bæredygtighedskonsulent til og med vores team")
    assert danish[2] < english[2]


def test_cap_total_cuts_skills_first_and_never_goes_negative():
    capped = cap_total([20, 15, 20, 10], 45)
    assert sum(capped) == 45
    assert capped[0] == 0 and capped[1:] == [15, 20, 10]
    assert all(x >= 0 for x in cap_total([1, 1, 1, 1], 0))


def test_cv_active_terms_uses_cv_and_always_adds_market_terms():
    terms = cv_active_terms("I know LCA and python")
    assert "lca" in terms and "python" in terms
    assert "power market" in terms
    assert "simapro" not in terms


def test_cv_active_terms_falls_back_when_cv_empty():
    assert cv_active_terms("")


def test_analyze_text_reads_years_and_danish_requirement():
    active = cv_active_terms("lca ghg python")
    (skills, exp, lang, other), note = analyze_text("We need 5 years of experience with LCA and GHG. Fluent Danish required.", active)
    assert exp == 3 and lang == 6
    assert "asks 5+ yrs" in note and "Danish required" in note
    assert skills > 6


def test_analyze_text_graduate_posting_gets_level_bonus():
    (_, exp, lang, _), _ = analyze_text("Graduate role. LCA, sustainability, python.", cv_active_terms("lca"))
    assert exp == 25 and lang == 20


def test_adjust_level_penalises_seniority_and_phd():
    sc, note = adjust_level("Senior Analyst", "PhD is required. Proven experience.", [20, 15, 20, 10], "")
    assert sc[1] <= 5
    assert "senior title" in note and "PhD asked for" in note


@pytest.mark.parametrize("title", ["Head of ESG", "Principal LCA Consultant", "Director Sustainability"])
def test_senior_titles_never_exceed_cap(title):
    assert score(title)[1] <= 65
