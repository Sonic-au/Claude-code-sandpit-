"""Write a compact copy of a knowledge graph for the technician app's Graph view.

Usage: python scripts/export_app_graph.py graph/hvac.json <app_dir>

Output <app_dir>/graph.json: {"corpus", "nodes": [{"t", "l", "a", "s", "q"} (manual nodes also carry "d", their document id)], "edges": [[src, dst], ...]}
where t is the node type, l the label, a the aliases, s up to eight unique [doc, page] sources and q the first
supporting quote. Edges refer to node positions.
"""
import json
import sys
from pathlib import Path


def main() -> None:
    src, app_dir = Path(sys.argv[1]), Path(sys.argv[2])
    graph = json.loads(src.read_text())
    index = {n["id"]: i for i, n in enumerate(graph["nodes"])}
    nodes = []
    for n in graph["nodes"]:
        pages, seen = [], set()
        for s in n.get("sources", []):
            key = (s["doc"], s["page"])
            if key not in seen and len(pages) < 8:
                seen.add(key)
                pages.append([s["doc"], s["page"]])
        quote = next((s.get("quote", "") for s in n.get("sources", []) if s.get("quote")), "")
        node = {"t": n["type"], "l": n["label"], "a": n.get("aliases", [])[:4], "s": pages, "q": quote[:220]}
        if n["type"] == "manual":
            node["d"] = n["id"].split(":", 1)[-1]      # the manual's document id, so the app can match it to its library entry
        nodes.append(node)
    edges = sorted({(index[e["src"]], index[e["dst"]]) for e in graph["edges"] if e["src"] in index and e["dst"] in index})
    out = app_dir / "graph.json"
    out.write_text(json.dumps({"corpus": graph.get("corpus", ""), "nodes": nodes, "edges": edges}, separators=(",", ":")))
    print(f"{out}: {len(nodes)} nodes, {len(edges)} edges, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
