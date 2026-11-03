"""Curated official RSS/Atom sources and conservative entry extraction."""
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from urllib.parse import urlparse, urlunparse
import re

import feedparser
from bs4 import BeautifulSoup


SOURCES = (
    ('kubernetes-blog', 'Kubernetes', 'https://kubernetes.io/feed.xml', 'Kubernetes & containers'),
    ('github-changelog', 'GitHub', 'https://github.blog/changelog/feed/', 'CI/CD & Developer tools'),
    ('aws-news', 'AWS', 'https://aws.amazon.com/blogs/aws/feed/', 'Cloud infrastructure'),
    ('aws-security', 'AWS', 'https://aws.amazon.com/security/security-bulletins/rss/feed/', 'Security'),
    ('cloudflare-blog', 'Cloudflare', 'https://blog.cloudflare.com/rss/', 'Cloud infrastructure'),
    ('postgresql-news', 'PostgreSQL', 'https://www.postgresql.org/news.rss', 'Data & databases'),
    ('openai-news', 'OpenAI', 'https://openai.com/news/rss.xml', 'AI models & APIs'),
    ('gcp-blog', 'Google Cloud', 'https://cloudblog.withgoogle.com/rss/', 'Cloud infrastructure'),
    ('azure-blog', 'Azure', 'https://azure.microsoft.com/en-us/blog/feed/', 'Cloud infrastructure'),
    ('akamai-blog', 'Akamai', 'https://feeds.feedburner.com/akamai/blog', 'Cloud infrastructure'),
    ('python-blog', 'Python', 'https://blog.python.org/feeds/posts/default', 'Backend & APIs'),
    ('go-blog', 'Go', 'https://go.dev/blog/feed.atom', 'Backend & APIs'),
    ('java-news', 'Java', 'https://inside.java/feed.xml', 'Backend & APIs'),
    ('react-releases', 'React', 'https://github.com/react/react/releases.atom', 'Frontend & Web'),
    ('django-news', 'Django', 'https://www.djangoproject.com/rss/weblog/', 'Backend & APIs'),
    ('php-news', 'PHP', 'https://www.php.net/feed.atom', 'Backend & APIs'),
    ('rust-blog', 'Rust', 'https://blog.rust-lang.org/feed.xml', 'Backend & APIs'),
    ('ruby-news', 'Ruby', 'https://www.ruby-lang.org/en/feeds/news.rss', 'Backend & APIs'),
    ('typescript-blog', 'TypeScript', 'https://devblogs.microsoft.com/typescript/feed/', 'Frontend & Web'),
    ('redis-blog', 'Redis', 'https://redis.io/blog/feed/', 'Data & databases'),
    ('grafana-blog', 'Grafana', 'https://grafana.com/blog/index.xml', 'Reliability & observability'),
    ('dotnet-blog', '.NET', 'https://devblogs.microsoft.com/dotnet/feed/', 'Backend & APIs'),
    ('kotlin-blog', 'Kotlin', 'https://blog.jetbrains.com/kotlin/feed/', 'Backend & APIs'),
    ('swift-blog', 'Swift', 'https://www.swift.org/atom.xml', 'Backend & APIs'),
    ('spring-blog', 'Spring', 'https://spring.io/blog.atom', 'Backend & APIs'),
    ('angular-blog', 'Angular', 'https://blog.angular.dev/feed', 'Frontend & Web'),
    ('nextjs-blog', 'Next.js', 'https://nextjs.org/feed.xml', 'Frontend & Web'),
    ('hashicorp-blog', 'HashiCorp', 'https://www.hashicorp.com/blog/feed.xml', 'Cloud infrastructure'),
    ('docker-blog', 'Docker', 'https://www.docker.com/feed/', 'Kubernetes & containers'),
)

ENTRY_HOSTS = {
    'gcp-blog': {'cloud.google.com'},
    'akamai-blog': {'www.akamai.com'},
}

# This endpoint alternates between valid responses and TLS handshake failures here.
DISABLED_BY_DEFAULT = {'docker-blog'}


@dataclass(frozen=True)
class Entry:
    key: str
    title: str
    url: str
    excerpt: str
    published_at: str | None
    kind: str
    score: int


def clean(value: str) -> str:
    return re.sub(r'\s+', ' ', BeautifulSoup(value or '', 'html.parser').get_text(' ', strip=True)).strip()


def canonical_url(value: str, feed_url: str, allowed_hosts: set[str] | None = None) -> str | None:
    parsed, feed = urlparse(value), urlparse(feed_url)
    if parsed.scheme != 'https' or parsed.hostname not in (allowed_hosts or {feed.hostname}) or parsed.username or parsed.password:
        return None
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip('/') or '/', '', '', parsed.fragment))


def classify(title: str) -> str:
    lower = title.casefold()
    if any(word in lower for word in ('cve-', 'vulnerab', 'security advisory', 'security release')):
        return 'security'
    if any(word in lower for word in ('deprecat', 'breaking change', 'end of support', 'end-of-life')):
        return 'deprecation'
    if any(word in lower for word in ('release', 'general availability', 'now available', 'launch')):
        return 'release'
    return 'update'


def score(title: str, kind: str, published: str | None, stamp: datetime | None = None) -> int:
    value = {'security': 85, 'deprecation': 75, 'release': 65, 'update': 40}[kind]
    lower = title.casefold()
    if any(word in lower for word in ('major', 'general availability', 'stable', 'critical')):
        value += 10
    if any(word in lower for word in ('webinar', 'podcast', 'event', 'conference', 'hiring')):
        value -= 30
    if published:
        age = ((stamp or datetime.now(timezone.utc)).date() - datetime.fromisoformat(published).date()).days
        value += 10 if age <= 2 else (5 if age <= 7 else (-10 if age > 30 else 0))
    return max(0, min(100, value))


def parse_feed(xml: str, feed_url: str, limit: int = 12, allowed_hosts: set[str] | None = None) -> list[Entry]:
    parsed = feedparser.parse(xml)
    if parsed.bozo and not parsed.entries:
        raise ValueError('invalid RSS or Atom feed')
    if not parsed.entries:
        raise ValueError('feed has no entries')
    accepted = []
    seen = set()
    for item in parsed.entries:
        title = clean(item.get('title', ''))
        url = canonical_url(item.get('link', ''), feed_url, allowed_hosts)
        excerpt = clean(item.get('summary', '') or item.get('description', ''))
        if not title or not url or not excerpt or url in seen:
            continue
        published = None
        for key in ('published', 'updated'):
            try:
                if item.get(key):
                    published = parsedate_to_datetime(item[key]).astimezone(timezone.utc).date().isoformat()
                    break
            except (TypeError, ValueError, OverflowError):
                pass
        if not published:
            for key in ('published_parsed', 'updated_parsed'):
                if item.get(key):
                    published = datetime(*item[key][:3], tzinfo=timezone.utc).date().isoformat()
                    break
        kind = classify(title)
        accepted.append(Entry(sha256(url.encode()).hexdigest()[:24], title[:500], url,
                              excerpt[:4000], published, kind, score(title, kind, published)))
        seen.add(url)
        if len(accepted) >= limit:
            break
    if not accepted:
        raise ValueError('feed has no usable same-host entries with excerpts')
    return accepted
