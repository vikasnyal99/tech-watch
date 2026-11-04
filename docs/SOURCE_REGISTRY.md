# Official feed registry

29 configured official RSS/Atom feeds; 28 enabled by default. The Python downloads parser is a separate source and remains disabled by default.

| Technology | Feed | Default |
|---|---|---|
| Kubernetes | [kubernetes-blog](https://kubernetes.io/feed.xml) | Enabled |
| GitHub | [github-changelog](https://github.blog/changelog/feed/) | Enabled |
| AWS | [aws-news](https://aws.amazon.com/blogs/aws/feed/) | Enabled |
| AWS | [aws-security](https://aws.amazon.com/security/security-bulletins/rss/feed/) | Enabled |
| Cloudflare | [cloudflare-blog](https://blog.cloudflare.com/rss/) | Enabled |
| PostgreSQL | [postgresql-news](https://www.postgresql.org/news.rss) | Enabled |
| OpenAI | [openai-news](https://openai.com/news/rss.xml) | Enabled |
| Google Cloud | [gcp-blog](https://cloudblog.withgoogle.com/rss/) | Enabled |
| Azure | [azure-blog](https://azure.microsoft.com/en-us/blog/feed/) | Enabled |
| Akamai | [akamai-blog](https://feeds.feedburner.com/akamai/blog) | Enabled |
| Python | [python-blog](https://blog.python.org/feeds/posts/default) | Enabled |
| Go | [go-blog](https://go.dev/blog/feed.atom) | Enabled |
| Java | [java-news](https://inside.java/feed.xml) | Enabled |
| React | [react-releases](https://github.com/react/react/releases.atom) | Enabled |
| Django | [django-news](https://www.djangoproject.com/rss/weblog/) | Enabled |
| PHP | [php-news](https://www.php.net/feed.atom) | Enabled |
| Rust | [rust-blog](https://blog.rust-lang.org/feed.xml) | Enabled |
| Ruby | [ruby-news](https://www.ruby-lang.org/en/feeds/news.rss) | Enabled |
| TypeScript | [typescript-blog](https://devblogs.microsoft.com/typescript/feed/) | Enabled |
| Redis | [redis-blog](https://redis.io/blog/feed/) | Enabled |
| Grafana | [grafana-blog](https://grafana.com/blog/index.xml) | Enabled |
| .NET | [dotnet-blog](https://devblogs.microsoft.com/dotnet/feed/) | Enabled |
| Kotlin | [kotlin-blog](https://blog.jetbrains.com/kotlin/feed/) | Enabled |
| Swift | [swift-blog](https://www.swift.org/atom.xml) | Enabled |
| Spring | [spring-blog](https://spring.io/blog.atom) | Enabled |
| Angular | [angular-blog](https://blog.angular.dev/feed) | Enabled |
| Next.js | [nextjs-blog](https://nextjs.org/feed.xml) | Enabled |
| HashiCorp | [hashicorp-blog](https://www.hashicorp.com/blog/feed.xml) | Enabled |
| Docker | [docker-blog](https://www.docker.com/feed/) | Disabled: intermittent TLS |

## Ingestion and publication

The worker polls enabled sources hourly with size, timeout, HTTPS and host limits. It retains a bounded feed response when changed, parses source titles, dates, links and up to 4,000 characters of feed-provided description/content, rejects off-host article links unless explicitly allowed, deduplicates canonical URLs and same-day matching titles, and ranks drafts. A human reviews the source excerpt, edits one-screen copy, and publishes or rejects each draft. The card links to the original publisher. RSS excerpts are evidence of what the publisher posted; they are not an independent verification of product impact, affected versions or mitigations.

The normal Feed shows reviewed live items matching the installation's selected topics and followed technologies; role interests apply when neither is selected. Trending selects broadly significant reviewed stories independently of those interests. Fictional fixtures appear only when no live items exist or `?demo=true` is passed to the feed API. Docker is registered but disabled because TLS handshakes were intermittent in this environment. Node.js publishes an official feed without item descriptions, so it needs an article-page adapter before it can generate useful briefings. React is sourced from the project’s GitHub releases feed.
