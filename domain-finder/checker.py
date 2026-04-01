"""RDAP-based domain availability checker. No API key required."""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

TLDS = [".ai", ".io", ".co"]

# RDAP endpoints: 404 = available, 200 = taken, error = unknown
RDAP_ENDPOINTS = {
    ".ai": "https://rdap.iana.org/domain/{name}.ai",
    ".io": "https://rdap.nic.io/domain/{name}.io",
    ".co": "https://rdap.nic.co/domain/{name}.co",
}

GODADDY_URL = "https://www.godaddy.com/domainsearch/find?checkAvail=1&domainToCheck={name}{tld}"
NAMECHEAP_URL = "https://www.namecheap.com/domains/registration/results/?domain={name}{tld}"


async def _check_one(client: httpx.AsyncClient, name: str, tld: str) -> str:
    """Returns 'available', 'taken', or 'unknown'."""
    url = RDAP_ENDPOINTS[tld].format(name=name)
    try:
        resp = await client.get(url)
        if resp.status_code == 404:
            return "available"
        elif resp.status_code == 200:
            return "taken"
        else:
            return "unknown"
    except Exception as e:
        logger.debug("RDAP check failed for %s%s: %s", name, tld, e)
        return "unknown"


async def check_all(names: list[str], tlds: list[str] = TLDS) -> dict[str, dict]:
    """
    Check availability for all name × TLD combos concurrently.

    Returns:
        {
            "mimir": {
                ".ai": {"status": "available", "godaddy": "https://...", "namecheap": "https://..."},
                ".io": {"status": "taken", ...},
            },
            ...
        }
    """
    results: dict[str, dict] = {name: {} for name in names}

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        tasks = [
            (name, tld, _check_one(client, name, tld))
            for name in names
            for tld in tlds
            if tld in RDAP_ENDPOINTS
        ]
        statuses = await asyncio.gather(*[t[2] for t in tasks], return_exceptions=True)

    for (name, tld, _), status in zip(tasks, statuses):
        if isinstance(status, Exception):
            status = "unknown"
        results[name][tld] = {
            "status": status,
            "godaddy": GODADDY_URL.format(name=name, tld=tld),
            "namecheap": NAMECHEAP_URL.format(name=name, tld=tld),
        }

    return results
