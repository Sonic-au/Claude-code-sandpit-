"""Parsers that call a service. Each declares its data residency.

None of these were run when the bench was first built (no keys or GPU in that session);
they are written against each service's documented API and should be smoke-tested on one
document before a full run.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import time
import urllib.request
from pathlib import Path

from .base import Parser

VLM_PROMPT = (
    "Transcribe this document page to Markdown, exactly as written. Keep reading order. "
    "Use # headings for headings, '-' for bullets, and HTML <table> for every table, with colspan/rowspan "
    "for merged cells. Keep clause numbers, form labels and checkbox text. Do not add commentary, do not "
    "summarise, and do not invent text that is not on the page. Skip running page headers and footers."
)


def _http_json(url: str, data: bytes | None = None, headers: dict | None = None, method: str | None = None,
               timeout: int = 300):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        return json.loads(body) if body else {}, dict(r.headers)


def _page_pngs(pdf: Path, dpi: int = 150) -> list[bytes]:
    import pypdfium2 as pdfium
    out = []
    for page in pdfium.PdfDocument(str(pdf)):
        buf = io.BytesIO()
        page.render(scale=dpi / 72).to_pil().save(buf, format="PNG")
        out.append(buf.getvalue())
    return out


class AzureDocumentIntelligence(Parser):
    """Azure AI Document Intelligence prebuilt-layout, Markdown output.

    Onshore when the resource is created in Australia East / Southeast (or run as a container).
    Env: AZURE_DI_ENDPOINT, AZURE_DI_KEY.
    """
    name = "azure-di-layout"
    licence = "Commercial (Microsoft)"
    residency = "cloud-au"
    cost_per_page_usd = 0.01   # prebuilt layout list price, about US$10 per 1,000 pages
    notes = "Choose an Australian region for onshore processing; containers available for on-premises."

    def available(self):
        ok = bool(os.environ.get("AZURE_DI_ENDPOINT") and os.environ.get("AZURE_DI_KEY"))
        return (ok, "" if ok else "set AZURE_DI_ENDPOINT and AZURE_DI_KEY")

    def _parse(self, pdf, n_pages):
        ep = os.environ["AZURE_DI_ENDPOINT"].rstrip("/")
        url = (f"{ep}/documentintelligence/documentModels/prebuilt-layout:analyze"
               "?api-version=2024-11-30&outputContentFormat=markdown")
        _, hdrs = _http_json(url, data=pdf.read_bytes(), method="POST",
                             headers={"Ocp-Apim-Subscription-Key": os.environ["AZURE_DI_KEY"],
                                      "Content-Type": "application/pdf"})
        op = hdrs.get("Operation-Location") or hdrs.get("operation-location")
        for _ in range(600):
            res, _ = _http_json(op, headers={"Ocp-Apim-Subscription-Key": os.environ["AZURE_DI_KEY"]})
            if res.get("status") in ("succeeded", "failed"):
                break
            time.sleep(2)
        if res.get("status") != "succeeded":
            raise RuntimeError(f"Azure DI status {res.get('status')}")
        content = res["analyzeResult"]["content"]
        pages = []
        for p in res["analyzeResult"]["pages"]:
            spans = p.get("spans", [])
            if spans:
                a = spans[0]["offset"]
                b = spans[-1]["offset"] + spans[-1]["length"]
                pages.append(content[a:b])
            else:
                pages.append("")
        # Page spans can miss tables that the Markdown places after the page; fall back to page breaks.
        if sum(len(x) for x in pages) < 0.6 * len(content):
            pages = re.split(r"<!--\s*PageBreak\s*-->", content)
        return (pages + [""] * n_pages)[:n_pages]


class OpenAICompatibleVLM(Parser):
    """Any OpenAI-compatible chat endpoint serving a vision model, one page image per request.

    Use for self-hosted open models (olmOCR-2, Chandra, Qwen-VL, dots.ocr) behind vLLM or
    Ollama, which keeps documents on your own hardware.
    Env: TB_VLM_BASE_URL (e.g. http://gpu-box:8000/v1), TB_VLM_MODEL, optional TB_VLM_API_KEY.
    """
    licence = "depends on model"
    residency = "self-hosted"
    cost_per_page_usd = None

    def __init__(self, model: str | None = None, base_url: str | None = None, label: str | None = None):
        self.model = model or os.environ.get("TB_VLM_MODEL", "")
        self.base_url = (base_url or os.environ.get("TB_VLM_BASE_URL", "")).rstrip("/")
        self.name = label or f"vlm-{self.model.split('/')[-1] or 'openai-compatible'}"

    def available(self):
        ok = bool(self.model and self.base_url)
        return (ok, "" if ok else "set TB_VLM_BASE_URL and TB_VLM_MODEL (e.g. vLLM serving allenai/olmOCR-2-7B)")

    def _parse(self, pdf, n_pages):
        out = []
        key = os.environ.get("TB_VLM_API_KEY", "none")
        for png in _page_pngs(pdf):
            body = {
                "model": self.model, "temperature": 0, "max_tokens": 6000,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": VLM_PROMPT},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}},
                ]}],
            }
            res, _ = _http_json(f"{self.base_url}/chat/completions", data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
            out.append(res["choices"][0]["message"]["content"])
        return out


class ClaudeVLM(Parser):
    """Claude reading page images. Onshore via Amazon Bedrock in ap-southeast-2 (Sydney).

    Env for Bedrock: TB_CLAUDE_BEDROCK_REGION=ap-southeast-2 plus standard AWS credentials,
    TB_CLAUDE_MODEL=<Bedrock model or inference-profile id available in that region>.
    Env for the Anthropic API (offshore): ANTHROPIC_API_KEY, TB_CLAUDE_MODEL.
    """
    licence = "Commercial (Anthropic)"
    cost_per_page_usd = None

    def __init__(self):
        self.region = os.environ.get("TB_CLAUDE_BEDROCK_REGION")
        self.model = os.environ.get("TB_CLAUDE_MODEL", "")
        self.residency = "cloud-au" if (self.region or "").startswith("ap-southeast") else "offshore"
        self.name = "claude-vlm" + ("-bedrock" if self.region else "")

    def available(self):
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False, "pip install 'anthropic[bedrock]'"
        if not self.model:
            return False, "set TB_CLAUDE_MODEL (and TB_CLAUDE_BEDROCK_REGION for onshore Bedrock)"
        if not self.region and not os.environ.get("ANTHROPIC_API_KEY"):
            return False, "set TB_CLAUDE_BEDROCK_REGION + AWS credentials, or ANTHROPIC_API_KEY"
        return True, ""

    def _client(self):
        import anthropic
        if self.region:
            return anthropic.AnthropicBedrock(aws_region=self.region)
        return anthropic.Anthropic()

    def _parse(self, pdf, n_pages):
        client = self._client()
        out = []
        for png in _page_pngs(pdf):
            msg = client.messages.create(
                model=self.model, max_tokens=8000, temperature=0,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                 "data": base64.b64encode(png).decode()}},
                    {"type": "text", "text": VLM_PROMPT},
                ]}],
            )
            out.append("".join(b.text for b in msg.content if getattr(b, "type", "") == "text"))
        return out


class LlamaParseAPI(Parser):
    """LlamaParse hosted API (North America or EU only - offshore for Australian data).

    Env: LLAMA_CLOUD_API_KEY, optional LLAMA_CLOUD_BASE_URL (https://api.cloud.eu.llamaindex.ai for EU),
    TB_LLAMAPARSE_TIER (cost_effective | agentic | agentic_plus).
    """
    licence = "Commercial (LlamaIndex)"
    residency = "offshore"

    def __init__(self, tier: str | None = None):
        self.tier = tier or os.environ.get("TB_LLAMAPARSE_TIER", "agentic")
        self.name = f"llamaparse-{self.tier}"
        self.cost_per_page_usd = {"cost_effective": 0.00375, "agentic": 0.0125, "agentic_plus": 0.05625}.get(self.tier)

    def available(self):
        ok = bool(os.environ.get("LLAMA_CLOUD_API_KEY"))
        return (ok, "" if ok else "set LLAMA_CLOUD_API_KEY (offshore: public documents only)")

    def _parse(self, pdf, n_pages):
        base = os.environ.get("LLAMA_CLOUD_BASE_URL", "https://api.cloud.llamaindex.ai").rstrip("/")
        key = os.environ["LLAMA_CLOUD_API_KEY"]
        boundary = "----manual_app"
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"tier\"\r\n\r\n{self.tier}\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{pdf.name}\"\r\n"
                "Content-Type: application/pdf\r\n\r\n").encode() + pdf.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        job, _ = _http_json(f"{base}/api/v1/parsing/upload", data=body, method="POST",
                            headers={"Authorization": f"Bearer {key}",
                                     "Content-Type": f"multipart/form-data; boundary={boundary}"})
        jid = job["id"]
        for _ in range(900):
            st, _ = _http_json(f"{base}/api/v1/parsing/job/{jid}", headers={"Authorization": f"Bearer {key}"})
            if st.get("status") in ("SUCCESS", "ERROR", "CANCELED"):
                break
            time.sleep(2)
        if st.get("status") != "SUCCESS":
            raise RuntimeError(f"LlamaParse job {st.get('status')}")
        res, _ = _http_json(f"{base}/api/v1/parsing/job/{jid}/result/json", headers={"Authorization": f"Bearer {key}"})
        pages = [p.get("md", "") for p in res.get("pages", [])]
        return (pages + [""] * n_pages)[:n_pages]


class ReductoAPI(Parser):
    """Reducto parse API. Reducto states it offers an AU endpoint - confirm, then set REDUCTO_BASE_URL.

    Env: REDUCTO_API_KEY, REDUCTO_BASE_URL (default https://platform.reducto.ai).
    """
    name = "reducto"
    licence = "Commercial (Reducto)"
    cost_per_page_usd = 0.015

    def __init__(self):
        base = os.environ.get("REDUCTO_BASE_URL", "https://platform.reducto.ai")
        self.base = base.rstrip("/")
        self.residency = "cloud-au" if "au" in base.lower() else "offshore"

    def available(self):
        ok = bool(os.environ.get("REDUCTO_API_KEY"))
        return (ok, "" if ok else "set REDUCTO_API_KEY (and REDUCTO_BASE_URL for an AU endpoint)")

    def _parse(self, pdf, n_pages):
        key = os.environ["REDUCTO_API_KEY"]
        boundary = "----manual_app"
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{pdf.name}\"\r\n"
                "Content-Type: application/pdf\r\n\r\n").encode() + pdf.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        up, _ = _http_json(f"{self.base}/upload", data=body, method="POST",
                           headers={"Authorization": f"Bearer {key}",
                                    "Content-Type": f"multipart/form-data; boundary={boundary}"})
        req = {"input": up["file_id"], "formatting": {"table_output_format": "html"},
               "retrieval": {"chunking": {"chunk_mode": "page"}}}
        res, _ = _http_json(f"{self.base}/parse", data=json.dumps(req).encode(), method="POST",
                            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                            timeout=1800)
        result = res.get("result", {})
        if result.get("type") == "url":
            result, _ = _http_json(result["url"])
        chunks = result.get("chunks", [])
        pages = [""] * n_pages
        for ch in chunks:
            blocks = ch.get("blocks", [])
            pg = (blocks[0].get("bbox", {}).get("page", 1) if blocks else 1) - 1
            if 0 <= pg < n_pages:
                pages[pg] += ch.get("content", "") + "\n\n"
        return pages
