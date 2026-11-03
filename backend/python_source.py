"""Narrow, source-backed parser for python.org release pages."""
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re

from bs4 import BeautifulSoup, Tag
from packaging.version import Version, InvalidVersion


RELEASE_PATH = re.compile(r'^/downloads/release/python-[0-9a-z]+/?$')
HEADING = re.compile(r'^Python\s+(\d+\.\d+(?:\.\d+)?(?:a\d+|b\d+|rc\d+)?)$', re.I)


@dataclass(frozen=True)
class ReleaseLink:
    version: str
    url: str


@dataclass(frozen=True)
class ParsedRelease:
    version: str
    url: str
    release_type: str
    published_at: str | None
    evidence: str
    evidence_section: str
    raw_text: str


def official_release_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == 'https' and parsed.hostname == 'www.python.org' and not parsed.username and not parsed.password and bool(RELEASE_PATH.fullmatch(parsed.path))


def discover_releases(html: str, base_url: str = 'https://www.python.org/downloads/', limit: int = 5) -> list[ReleaseLink]:
    soup = BeautifulSoup(html, 'html.parser')
    found = {}
    for anchor in soup.find_all('a', href=True):
        title = anchor.get_text(' ', strip=True)
        match = HEADING.fullmatch(title)
        if not match:
            continue
        url = urljoin(base_url, anchor['href'])
        if not official_release_url(url):
            continue
        try:
            version = str(Version(match.group(1)))
        except InvalidVersion:
            continue
        found.setdefault(version, ReleaseLink(version, url))
    return sorted(found.values(), key=lambda item: Version(item.version), reverse=True)[:limit]


def parse_release(html: str, url: str, expected_version: str | None = None) -> ParsedRelease:
    if not official_release_url(url):
        raise ValueError('not an official Python release URL')
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer']):
        tag.decompose()
    heading = next((h for h in soup.find_all(['h1', 'h2']) if HEADING.fullmatch(h.get_text(' ', strip=True))), None)
    if heading is None:
        raise ValueError('Python release heading missing')
    match = HEADING.fullmatch(heading.get_text(' ', strip=True))
    version = str(Version(match.group(1)))
    if expected_version and Version(expected_version) != Version(version):
        raise ValueError('release version does not match discovery')
    body = heading.find_parent('article') or heading.find_parent('main') or heading.find_parent('section', class_='main-content') or heading.parent
    text = body.get_text(' ', strip=True)
    release_type = 'security' if 'security release' in text[:1200].lower() else 'release'
    date_match = re.search(r'Release date:\s*([A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4})', text)
    published = None
    if date_match:
        try:
            published = datetime.strptime(date_match.group(1).replace('.', ''), '%b %d, %Y').date().isoformat()
        except ValueError:
            try:
                published = datetime.strptime(date_match.group(1).replace('.', ''), '%B %d, %Y').date().isoformat()
            except ValueError:
                pass
    evidence = None
    section = heading.get_text(' ', strip=True)
    if release_type == 'security':
        for subheading in body.find_all(['h2', 'h3']):
            if 'security content' not in subheading.get_text(' ', strip=True).lower():
                continue
            for sibling in subheading.next_siblings:
                if getattr(sibling, 'name', None) in ('h2', 'h3'):
                    break
                first_item = sibling.find('li') if isinstance(sibling, Tag) else None
                if first_item:
                    evidence = first_item.get_text(' ', strip=True)
                    section = subheading.get_text(' ', strip=True)
                    break
            if evidence:
                break
    if not evidence:
        paragraph = next((p for p in body.find_all('p') if len(p.get_text(' ', strip=True)) >= 35 and not p.get_text(' ', strip=True).lower().startswith('release date:')), None)
        if paragraph is None:
            raise ValueError('release description missing')
        evidence = paragraph.get_text(' ', strip=True)
        section = next((h.get_text(' ', strip=True) for h in body.find_all(['h2', 'h3']) if h.find_next('p') == paragraph), section)
    return ParsedRelease(version, url, release_type, published, evidence, section, text[:50000])
