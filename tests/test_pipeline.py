from backend.pipeline import ingest, validate_candidate, url_allowed

def base(**changes):
    x=dict(source_id='fixture', external_id='release-1', title='Example release', summary='Fictional release summary', why_it_matters='Teams may need to review compatibility.', next_action='Check official release notes.', technology='Kubernetes', type='release', evidence={})
    return x | changes

def test_duplicates_merge_but_distinct_releases_survive():
    accepted, held = ingest([base(), base(), base(external_id='release-2')])
    assert len(accepted) == 2 and not held

def test_security_and_unsupported_claims_held():
    assert 'human review required' in validate_candidate(base(type='security'))
    assert 'version lacks evidence' in validate_candidate(base(version='1.2'))
    assert 'user impact unverified' in validate_candidate(base(claims_user_affected=True))

def test_source_url_allowlist():
    assert url_allowed('https://example.org/releases', 'example.org')
    assert not url_allowed('http://example.org/releases', 'example.org')
    assert not url_allowed('https://127.0.0.1/', '127.0.0.1')
    assert not url_allowed('https://example.org.evil.test/', 'example.org')

def test_overlong_card_copy_is_held_without_truncation():
    candidate = base(summary='A' * 146)
    accepted, held = ingest([candidate])
    assert not accepted
    assert 'summary exceeds 145 characters' in held[0]['errors']
    assert held[0]['candidate']['summary'] == candidate['summary']


def test_supporting_copy_is_required():
    assert 'next_action required' in validate_candidate(base(next_action=''))
