import logging
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from checker import check_all
from generator import generate_names

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Domain Finder")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/check", response_class=HTMLResponse)
async def check(
    request: Request,
    description: str = Form(...),
    seeds: str = Form(""),
):
    candidates = await generate_names(description, seeds)
    names = [c["name"].lower().strip() for c in candidates]
    meta = {c["name"].lower().strip(): c for c in candidates}

    availability = await check_all(names)

    # Merge Claude metadata into results
    results = []
    for name in names:
        tlds = availability.get(name, {})
        has_available = any(v["status"] == "available" for v in tlds.values())
        m = meta.get(name, {})
        results.append({
            "name": name,
            "tagline": m.get("tagline", ""),
            "story": m.get("story", ""),
            "technique": m.get("technique", ""),
            "phonetics": m.get("phonetics", ""),
            "verb": m.get("verb", ""),
            "origin": m.get("origin", ""),
            "score": m.get("score", 0),
            "tlds": tlds,
            "has_available": has_available,
        })

    # Sort: available first, then by score
    results.sort(key=lambda r: (not r["has_available"], -r["score"]))

    return templates.TemplateResponse("index.html", {
        "request": request,
        "results": results,
        "description": description,
        "seeds": seeds,
        "tld_list": [".ai", ".io", ".co"],
    })
