# Official feed registry

43 configured official sources: RSS/Atom feeds, source pages, and GitHub's reviewed advisory API. Forty-two are enabled by default; Docker remains disabled. The Python downloads parser is a separate source and remains disabled by default, although an operator can enable it.

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
| Node.js | [node-blog](https://nodejs.org/en/feed/blog.xml), [node-security](https://nodejs.org/en/feed/vulnerability.xml) | Enabled; fetches linked articles because these feeds omit descriptions |
| Anthropic | [anthropic-news](https://www.anthropic.com/news), [anthropic-models](https://www.anthropic.com/news/models) | Enabled; extracts linked articles |
| FastAPI | [fastapi-releases](https://github.com/fastapi/fastapi/releases.atom) | Enabled |
| Vue | [vue-releases](https://github.com/vuejs/core/releases.atom) | Enabled |
| Terraform | [terraform-releases](https://github.com/hashicorp/terraform/releases.atom) | Enabled |
| Laravel | [laravel-releases](https://github.com/laravel/framework/releases.atom) | Enabled |
| Elasticsearch | [elasticsearch-releases](https://github.com/elastic/elasticsearch/releases.atom) | Enabled |
| Linux | [linux-releases](https://www.kernel.org/feeds/kdist.xml) | Enabled |
| Security advisories | [GitHub reviewed advisories](https://docs.github.com/en/rest/security-advisories/global-advisories) | Enabled; high and critical advisories only, with package and patched version retained |
| MongoDB | [MongoDB product updates](https://www.mongodb.com/products/updates/rss/) | Enabled; official product update descriptions |
| Kafka | [Apache Kafka release announcements](https://kafka.apache.org/blog/) | Enabled; extracts linked release articles |
| MySQL | [MySQL Server source tags](https://github.com/mysql/mysql-server/tags.atom) | Enabled for discovery only; a source tag is not proof that binaries or release notes are available |

## Ingestion and publication

The worker polls enabled sources hourly with size, timeout, HTTPS and host limits. It retains a bounded response when changed, extracts titles, dates, links and up to 4,000 characters of source text, rejects off-host article links unless explicitly allowed, deduplicates canonical URLs and same-day matching titles, and ranks drafts. Node.js, Anthropic and Kafka article fetches run as separate bounded jobs. GitHub reviewed advisories include package ecosystem, affected range and first patched version where supplied by the API. A human reviews the source excerpt, edits one-screen copy, and publishes or rejects each draft. The card links to the original publisher. Source excerpts are evidence of what the publisher posted; they are not independent verification of user impact.

The normal Feed shows reviewed live items matching the installation's selected topics and followed technologies; role interests apply when neither is selected. Following “AI models” matches the AI models & APIs topic across providers. Trending selects broadly significant reviewed stories independently of those interests. Fictional fixtures appear only when no live items exist or `?demo=true` is passed to the feed API. Docker is registered but disabled because TLS handshakes were intermittent in this environment. React and several other projects are sourced from their official GitHub releases feeds. New discoveries remain drafts until review; source count is not the number of published cards. Service incident monitoring is a separate proposed feature and is not covered by these announcement feeds.
