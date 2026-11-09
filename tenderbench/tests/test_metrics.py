from tenderbench.metrics import (best_teds, check_rule, contains_answer, reciprocal_rank, recall_at_k,
                                 score_requirements, teds, text_similarity, token_f1)
from tenderbench.normalize import content_text, extract_tables, table_grid
from tenderbench.parsers.base import ParseResult

GOLD_TABLE = ("<table><tr><th>Criterion</th><th>Weighting</th></tr>"
              "<tr><td>Relevant Experience</td><td>25%</td></tr><tr><td>Price</td><td>50%</td></tr></table>")


def result(pages, page_map=None):
    return ParseResult("t", "d", pages, page_map or list(range(1, len(pages) + 1)), 1.0)


def test_text_similarity_ignores_markup_and_quotes():
    assert text_similarity("## Hello **world** “quoted”", "Hello world \"quoted\"") == 1.0
    assert text_similarity("", "") == 1.0
    assert text_similarity("completely different", "Hello world") < 0.5


def test_text_similarity_penalises_reordering():
    gold = "first clause. second clause. third clause."
    assert text_similarity("third clause. first clause. second clause.", gold) < 1.0


def test_markdown_table_extraction_and_teds_identity():
    md = "| Criterion | Weighting |\n|---|---|\n| Relevant Experience | 25% |\n| Price | 50% |\n"
    tabs = extract_tables(md)
    assert len(tabs) == 1
    assert abs(teds(tabs[0], GOLD_TABLE) - 1.0) < 1e-9


def test_teds_partial_and_structure():
    wrong = ("<table><tr><th>Criterion</th><th>Weighting</th></tr>"
             "<tr><td>Relevant Experience</td><td>20%</td></tr></table>")
    s = teds(wrong, GOLD_TABLE)
    assert 0.3 < s < 1.0
    assert best_teds([], GOLD_TABLE) == 0.0
    assert teds(GOLD_TABLE.replace("25%", "99%"), GOLD_TABLE, structure_only=True) == 1.0


def test_table_grid_expands_spans():
    g = table_grid('<table><tr><td colspan="2">A</td></tr><tr><td>b</td><td>c</td></tr></table>')
    assert g == [["A", "A"], ["b", "c"]]


def test_rules():
    md = "## 4.4 Qualitative Criteria\n\nTenderers must provide three referees.\n\n" + \
         "| Criterion | Weighting |\n|---|---|\n| Price | 50% |\n"
    r = result([md], [17])
    assert check_rule({"type": "present", "text": "Tenderers must provide three referees", "page": 17}, r)
    assert not check_rule({"type": "present", "text": "Tenderers must provide five referees and a bond", "page": 17}, r)
    assert check_rule({"type": "absent", "text": "PART 4 COMPLETE AND RETURN"}, r)
    assert check_rule({"type": "order", "before": "Qualitative Criteria", "after": "three referees"}, r)
    assert not check_rule({"type": "order", "before": "three referees", "after": "Qualitative Criteria"}, r)
    assert check_rule({"type": "heading", "text": "4.4 Qualitative Criteria"}, r)
    assert check_rule({"type": "table_value", "page": 17, "row": "Price", "col": "Weighting", "value": "50%"}, r)
    assert not check_rule({"type": "table_value", "page": 17, "row": "Price", "col": "Weighting", "value": "25%"}, r)


def test_requirements_matching():
    gold = [{"id": "g1", "page": 1, "text": "Tenderers must provide at least three referees.", "obligation": "mandatory"},
            {"id": "g2", "page": 1, "text": "Describe your experience in completing similar projects.",
             "obligation": "evaluated"}]
    preds = [{"page": 1, "text": "Tenderers must provide at least three referees", "obligation": "mandatory"},
             {"page": 2, "text": "Something unrelated about parking.", "obligation": "informational"}]
    s = score_requirements(preds, gold)
    assert s["matched"] == 1 and s["recall"] == 0.5 and s["precision"] == 0.5
    assert s["recall_mandatory"] == 1.0 and s["all_mandatory_found"] is True
    assert s["obligation_accuracy"] == 1.0 and s["missed"] == ["g2"]


def test_retrieval_and_answers():
    assert recall_at_k([3, 5, 9], [9], 3) == 1.0 and recall_at_k([3, 5, 9], [9], 2) == 0.0
    assert reciprocal_rank([3, 5, 9], [5]) == 0.5
    assert token_f1("The weighting is 25%", "25%") > 0
    assert contains_answer("Relevant experience is weighted at 25% of the score.", "25%")
    assert not contains_answer("It is weighted at 20%.", "25%")


def test_content_text_handles_html_tables():
    assert "price 50%" in content_text("<table><tr><td>Price</td><td>50%</td></tr></table>")


def test_steps_and_near_rules():
    md = ("WARNING Disconnect power before servicing.\n\n1. Remove the cover.\n2. Check the seal.\n3. Refit the cover.\n\n"
          "| Coupling size | Torque |\n|---|---|\n| 5 | 120 in-lb |\n")
    r = result([md], [32])
    assert check_rule({"type": "steps", "steps": ["Remove the cover", "Check the seal", "Refit the cover"]}, r)
    assert not check_rule({"type": "steps", "steps": ["Check the seal", "Remove the cover"]}, r)
    assert check_rule({"type": "near", "a": "Disconnect power before servicing", "b": "Remove the cover", "window": 80}, r)
    assert not check_rule({"type": "near", "a": "Disconnect power", "b": "120 in-lb", "window": 20}, r)


def test_extract_safety_baseline():
    from tenderbench.extract import extract_safety
    md = ("WARNING: Disconnect and lock out electrical power before servicing.\n\n"
          "Note that the pump is heavy.\n\n"
          "CAUTION\n\nDo not crank engine for more than 15 seconds.\n\n"
          "NOTE: Check the oil level daily.\n")
    items = extract_safety([md], [7])
    kinds = sorted(i["kind"] for i in items)
    assert kinds == ["caution", "note", "warning"]
    assert any("15 seconds" in i["text"] for i in items)


def test_identifiers_keep_underscores():
    assert "pg_wal" in content_text("Copy the pg\\_wal directory")
    assert "archive_command" in content_text("Set `archive_command` and _restart_ the server")
    assert "restart" in content_text("_restart_") and "_" not in content_text("_restart_")
