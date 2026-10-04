"""Import a public job advert URL into Placement OS."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class ImportError(RuntimeError):
    pass


class _JobPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title = ""
        self.site_name = ""
        self.description = ""
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            prop = (attrs.get("property") or attrs.get("name") or "").lower()
            content = attrs.get("content") or ""
            if prop == "og:site_name":
                self.site_name = content
            elif prop in {"description", "og:description"} and not self.description:
                self.description = content

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self.in_title:
            self.title += (" " if self.title else "") + text
        self.parts.append(text)


def fetch_job(url: str, *, opener=urlopen) -> dict:
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ImportError("Enter a valid http or https job URL")

    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 Placement-OS/0.4",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with opener(req, timeout=15) as response:
            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                raise ImportError("That URL did not return a normal web page")
            raw = response.read(2_000_000).decode("utf-8", errors="replace")
    except ImportError:
        raise
    except Exception as exc:
        raise ImportError(f"Could not read that job page: {exc}") from exc

    parser = _JobPageParser()
    parser.feed(raw)

    title = html.unescape(parser.title).strip()
    company = html.unescape(parser.site_name).strip()
    if not company:
        company = parsed.netloc.removeprefix("www.").split(".")[0].replace("-", " ").title()

    # Body text is intentionally approximate; JavaScript-only sites may not expose the advert server-side.
    body = " ".join(parser.parts)
    body = re.sub(r"\s+", " ", html.unescape(body)).strip()
    if len(body) < 120:
        raise ImportError(
            "I could open the URL, but the advert text was not available in the page HTML. "
            "This site may load jobs with JavaScript; paste the advert manually instead."
        )

    role = title
    if " | " in role:
        role = role.split(" | ", 1)[0].strip()
    elif " - " in role and len(role.split(" - ", 1)[0]) > 8:
        role = role.split(" - ", 1)[0].strip()

    return {
        "company": company or "Unknown employer",
        "role": role or "Imported job",
        "job_url": url,
        "job_advert": body[:50_000],
        "page_description": parser.description.strip(),
    }
