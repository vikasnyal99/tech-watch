from pathlib import Path
import json
from backend.briefing_copy import validate_briefing_copy

FIXTURE = json.loads((Path(__file__).parents[1] / 'fixtures/sample_updates.json').read_text())
TECHNOLOGIES = ['Python', 'Go', 'Java', 'PHP', 'TypeScript', 'Rust', 'Ruby', '.NET', 'Kotlin', 'Swift',
                'React', 'Django', 'Spring', 'Angular', 'Next.js',
                'Kubernetes', 'AWS', 'Google Cloud', 'Azure', 'Cloudflare', 'Akamai',
                'GitHub', 'Docker', 'HashiCorp', 'PostgreSQL', 'Redis', 'Grafana', 'OpenAI',
                'Node.js', 'Anthropic', 'AI models', 'FastAPI', 'Vue', 'Terraform',
                'Laravel', 'Elasticsearch', 'Linux']
TOPICS = ['Backend & APIs', 'Frontend & Web', 'Cloud infrastructure', 'Kubernetes & containers', 'CI/CD & Developer tools', 'Reliability & observability', 'Security', 'AI models & APIs', 'Data & databases', 'Architecture & strategy']
ROLES = ['Software engineer', 'Platform engineer', 'DevOps / cloud engineer', 'SRE', 'Product manager', 'Engineering leader']

def fixture_items():
    for item in FIXTURE['items']:
        errors = validate_briefing_copy(item)
        if errors:
            raise ValueError(f"Fixture {item.get('id', '<unknown>')} does not fit the briefing card: {', '.join(errors)}")
    return [{**item, 'publisher': 'Fictional development fixture', 'source_url': None, 'fictional': True,
             'topic': 'AI models & APIs' if item['type'] == 'model' else ('Security' if item['type'] == 'security' else 'Kubernetes & containers'),
             'updated_at': None, 'source_label': 'No real source — sample only'} for item in FIXTURE['items']]
