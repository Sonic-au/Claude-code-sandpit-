import trafilatura
from bs4 import BeautifulSoup


def extract_text(html: str) -> str:
    """Extract clean body text from HTML, falling back to BeautifulSoup."""
    text = trafilatura.extract(html)
    if text:
        return text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)
