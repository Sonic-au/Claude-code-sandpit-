from manual_app.metrics import (best_teds, check_rule, contains_answer, reciprocal_rank, recall_at_k,
                                 score_requirements, teds, text_similarity, token_f1)
from manual_app.normalize import content_text, extract_tables, table_grid
from manual_app.parsers.base import ParseResult

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
    from manual_app.extract import extract_safety
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


def test_shell_pipes_in_rules():
    r = result(["or:\n\n```\ncat filename.gz | gunzip | psql dbname\n```\n"], [825])
    assert check_rule({"type": "present", "text": "cat filename.gz | gunzip | psql dbname", "page": 825}, r)


def test_answer_coverage_is_fair_to_long_gold_answers():
    from manual_app.metrics import answer_coverage
    gold = "The lamp goes out approximately 10 seconds after releasing the switch trigger."
    assert answer_coverage("The lamp goes out about 10 seconds after releasing the switch trigger [1].", gold) >= 0.7
    assert answer_coverage("Approximately 30 minutes.", gold) < 0.7


def test_judge_marks_not_found_incorrect_without_calling_the_llm():
    from manual_app.retrieve import judge
    assert judge(None, "q", "gold", "NOT FOUND", "doc") == "incorrect"

    class Fake:
        def complete_json(self, prompt, schema, system="", max_tokens=0):
            assert "2,000 lbs" in prompt and "2,000 pounds" in prompt
            return {"verdict": "correct"}
    assert judge(Fake(), "Breaking strength?", "2,000 pounds", "2,000 lbs [1].", "doc") == "correct"


def test_session_provider_queues_then_reads_back(tmp_path, monkeypatch):
    import json
    from manual_app import corpus
    from manual_app.llm import LLM, LLMPending
    monkeypatch.setattr(corpus, "DATA", tmp_path)
    try:
        LLM("session", "s", "session").complete("What is X?")
        raise AssertionError("expected LLMPending")
    except LLMPending as e:
        key = str(e)
    task = json.loads((tmp_path / "session_llm" / "tasks.jsonl").read_text())
    assert task["key"] == key and task["prompt"] == "What is X?"
    (tmp_path / "session_llm" / "responses.jsonl").write_text(json.dumps({"key": key, "response": "42"}) + "\n")
    assert LLM("session", "s", "session").complete("What is X?") == "42"


class _FakeJev:
    """Stands in for the Jev API: returns fixed probabilities and records the request body."""
    model = "jev-test"

    def __init__(self, probs):
        from manual_app.judge import Jev
        self._jev, self.probs, self.bodies = Jev(model="jev-test"), probs, []
        self.usage = self._jev.usage

    def grade(self, question, gold, answer, title):
        from manual_app.judge import parse_response
        self.bodies.append(self._jev.request_body(question, gold, answer, title))
        return parse_response({"answers": {"verdict": {"type": "choice", "probabilities": self.probs}}})


class _FakeClaude:
    def __init__(self, verdict):
        self.verdict, self.calls = verdict, 0

    def complete_json(self, prompt, schema, system="", max_tokens=0):
        self.calls += 1
        return {"verdict": self.verdict}


def test_jev_request_follows_the_typed_choice_format():
    from manual_app.judge import JEV_CRITERIA, Jev
    body = Jev(model="jev-1.13.0").request_body("Q?", "2,000 pounds", "2,000 lbs [1]", "FAA AC 43")
    assert body["model"] == "jev-1.13.0"
    assert body["state"]["reference_answer"] == "2,000 pounds" and body["state"]["candidate_answer"] == "2,000 lbs [1]"
    v = body["questions"]["verdict"]
    assert v["type"] == "choice" and set(v["criteria"]) == set(JEV_CRITERIA) == {"correct", "partial", "incorrect"}


def test_parse_response_takes_top_probability_as_confidence():
    from manual_app.judge import parse_response
    verdict, q, _ = parse_response({"answers": {"verdict": {"choice": "correct", "confidence": 0.5,
                                                            "probabilities": {"correct": 0.7, "partial": 0.2,
                                                                              "incorrect": 0.1}}}})
    assert verdict == "correct" and q == 0.7


def test_cascade_accepts_confident_jev_and_escalates_the_rest():
    from manual_app.judge import Grader, summarise, threshold_sweep
    claude = _FakeClaude("partial")
    sure = Grader(claude, "cascade", _FakeJev({"correct": 0.95, "partial": 0.04, "incorrect": 0.01}), tau=0.9)
    r1 = sure.grade("Q?", "gold", "answer", "doc")
    assert r1["final"] == "correct" and r1["by"] == "jev" and claude.calls == 0
    unsure = Grader(claude, "cascade", _FakeJev({"correct": 0.6, "partial": 0.3, "incorrect": 0.1}), tau=0.9)
    r2 = unsure.grade("Q?", "gold", "answer", "doc")
    assert r2["final"] == "partial" and r2["by"] == "claude" and claude.calls == 1
    assert sure.grade("Q?", "gold", "NOT FOUND", "doc") == {"final": "incorrect", "by": "rule"}
    s = summarise([r1, r2], 2)
    assert s["judged_accuracy"] == 0.5 and s["escalated"] == 0.5 and s["jev_claude_agreement"] == 0.0
    cmp = Grader(claude, "compare", _FakeJev({"correct": 0.95, "partial": 0.04, "incorrect": 0.01}), tau=0.9)
    r3 = cmp.grade("Q?", "gold", "answer", "doc")
    assert r3["final"] == "correct" and r3["claude"] == "partial"
    sweep = {row["threshold"]: row for row in threshold_sweep([r2, r3])}
    assert sweep[1.01]["escalated"] == 1.0 and sweep[1.01]["agrees_with_claude"] == 1.0
    assert sweep[0.5]["escalated"] == 0.0
