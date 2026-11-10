#!/usr/bin/env python3
"""Answer TenderBench LLM tasks inside a Claude Code session (TB_LLM_PROVIDER=session; no API needed).

  split  <n> <dir>            split the unanswered tasks in data/session_llm/tasks.jsonl into n shard files
  count  <shard.jsonl>        number of tasks in a shard and how many are answered
  show   <shard.jsonl> <i>    print task i (0-based): key, type, prompt and schema
  answer <shard.jsonl> <key>  record the response read from stdin (JSON for schema tasks, plain text otherwise)
  merge  <dir>                append every shard's validated responses to data/session_llm/responses.jsonl

Workflow: run the bench (tasks are queued), `split`, have session agents `show` and `answer` each task,
`merge`, run the bench again. Repeat while the report says tasks are pending (answers are graded in a later pass).
"""
import json
import sys
from pathlib import Path

SESSION = Path(__file__).resolve().parent.parent / "data" / "session_llm"


def _jsonl(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def _resp_path(shard):
    return Path(str(shard).replace(".jsonl", ".responses.jsonl"))


def _check(value, schema, where="response"):
    """Minimal JSON-schema check: objects (required, no extras), arrays, string enums."""
    t = schema.get("type")
    if t == "object":
        props = schema.get("properties", {})
        if not isinstance(value, dict) or set(value) - set(props) or set(schema.get("required", props)) - set(value):
            raise ValueError(f"{where}: need an object with keys {sorted(props)}")
        for k, v in value.items():
            _check(v, props[k], f"{where}.{k}")
    elif t == "array":
        if not isinstance(value, list):
            raise ValueError(f"{where}: need a list")
        for i, v in enumerate(value):
            _check(v, schema.get("items", {}), f"{where}[{i}]")
    elif t == "string":
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{where}: need non-empty text")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{where}: must be one of {schema['enum']}")


def validate(task, response):
    if task["schema"] is None:
        if not response.strip():
            raise ValueError("answer tasks need non-empty plain text")
        return response
    data = json.loads(response)
    _check(data, task["schema"])
    return data


def main(argv):
    cmd = argv[1]
    if cmd == "split":
        n, out = int(argv[2]), Path(argv[3])
        done = {r["key"] for r in _jsonl(SESSION / "responses.jsonl")}
        todo = [t for t in _jsonl(SESSION / "tasks.jsonl") if t["key"] not in done]
        out.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            part = todo[i::n]
            if part:
                (out / f"shard{i:02d}.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in part))
        print(f"{len(todo)} unanswered tasks in {min(n, len(todo))} shards under {out}")
    elif cmd == "merge":
        tasks = {t["key"]: t for t in _jsonl(SESSION / "tasks.jsonl")}
        done = {r["key"] for r in _jsonl(SESSION / "responses.jsonl")}
        added = 0
        with (SESSION / "responses.jsonl").open("a") as f:
            for rp in sorted(Path(argv[2]).glob("*.responses.jsonl")):
                for r in _jsonl(rp):
                    if r["key"] in tasks and r["key"] not in done:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                        done.add(r["key"])
                        added += 1
        print(f"merged {added} responses; {len(set(tasks) - done)} tasks still unanswered")
    else:
        shard = argv[2]
        ts = _jsonl(shard)
        if cmd == "count":
            a = {r["key"] for r in _jsonl(_resp_path(shard))}
            print(f"{len(ts)} tasks, {sum(t['key'] in a for t in ts)} answered")
        elif cmd == "show":
            t = ts[int(argv[3])]
            print("KEY:", t["key"])
            print("TYPE:", "JSON matching SCHEMA" if t["schema"] else "plain text")
            print("SYSTEM:", t["system"] or "(none)")
            print("PROMPT:\n" + t["prompt"])
            if t["schema"]:
                print("SCHEMA:", json.dumps(t["schema"]))
        elif cmd == "answer":
            t = next(x for x in ts if x["key"] == argv[3])
            resp = validate(t, sys.stdin.read().strip())
            with _resp_path(shard).open("a") as f:
                f.write(json.dumps({"key": t["key"], "response": resp}, ensure_ascii=False) + "\n")
            print("recorded", t["key"])
        else:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
