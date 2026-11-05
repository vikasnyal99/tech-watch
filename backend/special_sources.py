"""Official sources that need article extraction or structured JSON parsing."""
import json
import re
from datetime import datetime
from hashlib import sha256
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import feedparser

from backend.rss_source import Entry, canonical_url, clean, classify, score


TECH_BY_ECOSYSTEM = {
    'npm': 'Node.js', 'pip': 'Python', 'maven': 'Java', 'composer': 'PHP',
    'go': 'Go', 'rust': 'Rust', 'rubygems': 'Ruby', 'nuget': '.NET',
    'swift': 'Swift', 'actions': 'GitHub',
}


def parse_anthropic_news(html: str, limit: int = 8) -> list[Entry]:
    soup = BeautifulSoup(html, 'html.parser')
    items, seen = [], set()
    for link in soup.select('a[href^="/news/"]'):
        heading = link.find(['h2', 'h3'])
        if not heading:
            continue
        title = clean(heading.get_text(' ', strip=True))
        if not re.search(r'\b(?:claude|model|api|developer|agent|tool|research|security|safety)\b', title, re.I):
            continue
        url = canonical_url(urljoin('https://www.anthropic.com', link['href']),
                            'https://www.anthropic.com/news')
        if not url or url in seen:
            continue
        items.append(Entry(sha256(url.encode()).hexdigest()[:24], title[:500], url, '', None,
                           classify(title), score(title, classify(title), None)))
        seen.add(url)
        if len(items) >= limit:
            break
    if not items:
        raise ValueError('Anthropic newsroom has no matching article links')
    return items


def article_excerpt(html: str, source_id: str) -> tuple[str, str | None]:
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('article') if source_id.startswith('anthropic-') else soup.find('main')
    if body is None:
        raise ValueError('article body missing')
    for element in body.select('script,style,nav,footer,aside,header'):
        element.decompose()
    parts = []
    for element in body.select('p,li'):
        if element.find_parent(['p', 'li']) is not None:
            continue
        value = clean(element.get_text(' ', strip=True))
        if len(value) >= 25 and value not in parts:
            parts.append(value)
        if sum(map(len, parts)) >= 3900:
            break
    excerpt = ' '.join(parts)[:4000]
    if len(excerpt) < 80:
        raise ValueError('article has too little source text')
    date = None
    meta = soup.find('meta', attrs={'property': 'article:published_time'})
    if meta and meta.get('content'):
        try:
            date = datetime.fromisoformat(meta['content'].replace('Z', '+00:00')).date().isoformat()
        except ValueError:
            pass
    return excerpt, date


def parse_github_advisories(raw: str, limit: int = 12) -> list[Entry]:
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError('GitHub advisories response is not a list')
    items = []
    for advisory in data:
        if advisory.get('withdrawn_at') or advisory.get('severity') not in ('high', 'critical'):
            continue
        url = canonical_url(advisory.get('html_url', ''), 'https://github.com/advisories', {'github.com'})
        title = clean(advisory.get('summary', ''))
        if not url or not title:
            continue
        vulnerabilities = advisory.get('vulnerabilities') or []
        first = next((v for v in vulnerabilities if isinstance(v, dict) and v.get('package')), {})
        package = first.get('package') or {}
        technology = TECH_BY_ECOSYSTEM.get(package.get('ecosystem'), 'Security advisories')
        details = []
        if package.get('name'):
            details.append(f"Package: {package['name']} ({package.get('ecosystem', 'unknown')}).")
        if first.get('vulnerable_version_range'):
            details.append(f"Affected versions: {first['vulnerable_version_range']}.")
        if first.get('first_patched_version'):
            details.append(f"First patched version: {first['first_patched_version']}.")
        description = clean(advisory.get('description', ''))
        excerpt = f"{title}. {' '.join(details)} {description}".strip()[:4000]
        published = advisory.get('published_at')
        try:
            published = datetime.fromisoformat(published.replace('Z', '+00:00')).date().isoformat() if published else None
        except ValueError:
            published = None
        key = advisory.get('ghsa_id') or sha256(url.encode()).hexdigest()[:24]
        items.append(Entry(key, title[:500], url, excerpt, published, 'security',
                           95 if advisory['severity'] == 'critical' else 88, technology))
        if len(items) >= limit:
            break
    return items


def parse_kernel_releases(xml: str, limit: int = 8) -> list[Entry]:
    """Use distinct official changelogs; kernel.org feed items all link to its homepage."""
    entries = []
    for item in feedparser.parse(xml).entries:
        summary = item.get('summary', '')
        link = next((a for a in BeautifulSoup(summary, 'html.parser').select('a[href]')
                     if a.get_text(' ', strip=True).casefold().startswith('changelog-')), None)
        url = canonical_url(link['href'], 'https://cdn.kernel.org/', {'cdn.kernel.org'}) if link else None
        if not url:
            continue
        title = clean(item.get('title', ''))
        excerpt = clean(summary)
        if not title or not excerpt:
            continue
        date = None
        match = re.search(r'Released:\s*(\d{4}-\d{2}-\d{2})', excerpt)
        if match:
            date = match.group(1)
        entries.append(Entry(sha256(url.encode()).hexdigest()[:24], title[:500], url,
                             excerpt[:4000], date, 'release', score(title, 'release', date)))
        if len(entries) >= limit:
            break
    if not entries:
        raise ValueError('kernel feed has no official changelog links')
    return entries


def parse_kafka_blog(html: str, limit: int = 8) -> list[Entry]:
    soup = BeautifulSoup(html, 'html.parser')
    entries, seen = [], set()
    for link in soup.select('.td-blog-posts-list__body h5 a[href]'):
        title = clean(link.get_text(' ', strip=True))
        if 'release announcement' not in title.casefold():
            continue
        url = canonical_url(urljoin('https://kafka.apache.org', link['href']),
                            'https://kafka.apache.org/blog/')
        if not url or url in seen:
            continue
        date_match = re.search(r'/blog/(\d{4})/(\d{2})/(\d{2})/', url)
        published = '-'.join(date_match.groups()) if date_match else None
        entries.append(Entry(sha256(url.encode()).hexdigest()[:24], title[:500], url, '',
                             published, 'release', score(title, 'release', published)))
        seen.add(url)
        if len(entries) >= limit:
            break
    if not entries:
        raise ValueError('Kafka blog has no official release announcements')
    return entries


def parse_mysql_tags(xml: str, limit: int = 8) -> list[Entry]:
    """Source tags are discovery leads, not a claim that binaries are available."""
    entries = []
    for item in feedparser.parse(xml).entries:
        match = re.match(r'(mysql-\d[^:\s]*)', clean(item.get('title', '')))
        url = canonical_url(item.get('link', ''), 'https://github.com/mysql/mysql-server/tags.atom')
        if not match or not url:
            continue
        version = match.group(1).removeprefix('mysql-')
        excerpt = clean(item.get('summary', ''))
        if not excerpt:
            continue
        published = None
        if item.get('updated_parsed'):
            published = datetime(*item.updated_parsed[:3]).date().isoformat()
        title = f'MySQL {version} source tag'
        entries.append(Entry(sha256(url.encode()).hexdigest()[:24], title, url,
                             f'Official MySQL Server source tag {version}. Associated commit: {excerpt}'[:4000],
                             published, 'update', score(title, 'update', published)))
        if len(entries) >= limit:
            break
    if not entries:
        raise ValueError('MySQL tags feed has no server version tags')
    return entries
