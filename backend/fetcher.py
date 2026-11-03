"""Bounded official-source fetcher. Registered URLs, not user URLs, reach this code."""
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import ipaddress
import socket
import httpx


ALLOWED_HOSTS = {'www.python.org', 'kubernetes.io', 'github.blog', 'aws.amazon.com',
                 'blog.cloudflare.com', 'www.postgresql.org', 'openai.com',
                 'cloudblog.withgoogle.com', 'azure.microsoft.com', 'feeds.feedburner.com',
                 'blog.python.org', 'go.dev', 'inside.java', 'github.com',
                 'www.djangoproject.com', 'www.php.net', 'blog.rust-lang.org',
                 'www.ruby-lang.org', 'devblogs.microsoft.com', 'redis.io', 'grafana.com',
                 'blog.jetbrains.com', 'www.swift.org', 'spring.io', 'blog.angular.dev',
                 'nextjs.org', 'www.hashicorp.com', 'www.docker.com'}
MAX_BYTES = 2_000_000


@dataclass(frozen=True)
class FetchResult:
    status_code: int
    body: str | None
    etag: str | None
    last_modified: str | None
    final_url: str


def public_dns(host: str) -> bool:
    try:
        addresses = {record[4][0] for record in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        return bool(addresses) and all(ipaddress.ip_address(address).is_global for address in addresses)
    except (OSError, ValueError):
        return False


def check_url(url: str, resolver=public_dns) -> None:
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('source URL is not allowlisted')
    if not resolver(parsed.hostname):
        raise ValueError('source host did not resolve to public addresses')


def fetch_html(url: str, *, etag: str | None = None, last_modified: str | None = None,
               client: httpx.Client | None = None, resolver=public_dns) -> FetchResult:
    check_url(url, resolver)
    own_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(12.0, connect=5.0), follow_redirects=False,
                                    headers={'User-Agent': 'TechWatch/0.1 (+local source monitor; contact configured by operator)'})
    headers = {}
    if etag:
        headers['If-None-Match'] = etag
    if last_modified:
        headers['If-Modified-Since'] = last_modified
    current = url
    try:
        for _ in range(4):
            check_url(current, resolver)
            with client.stream('GET', current, headers=headers) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get('location')
                    if not location:
                        raise ValueError('redirect without location')
                    current = urljoin(current, location)
                    headers = {}
                    continue
                if response.status_code == 304:
                    return FetchResult(304, None, etag, last_modified, current)
                response.raise_for_status()
                content_type = response.headers.get('content-type', '').lower()
                if not any(kind in content_type for kind in ('text/html', 'xml', 'rss', 'atom', 'application/octet-stream')):
                    raise ValueError('source did not return a supported feed or HTML')
                chunks = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError('source response too large')
                    chunks.append(chunk)
                return FetchResult(response.status_code, b''.join(chunks).decode('utf-8', errors='replace'),
                                   response.headers.get('etag'), response.headers.get('last-modified'), current)
        raise ValueError('too many redirects')
    finally:
        if own_client:
            client.close()
