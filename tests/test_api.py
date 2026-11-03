import os
import uuid
os.environ['DATABASE_URL']='sqlite:///./test_techwire.db'
from fastapi.testclient import TestClient
from backend.main import app

def test_flow():
    with TestClient(app) as c:
        h={'X-Installation-ID':'test-'+uuid.uuid4().hex}
        assert c.get('/health').json()['mode']=='official-feeds-with-review'
        feed=c.get('/v1/feed?section=feed',headers=h).json()['items']
        assert len(feed)==3 and all(x['fictional'] and x['source_url'] is None for x in feed)
        assert c.get('/v1/feed?section=ai',headers=h).json()['items'][0]['type']=='model'
        assert not c.get('/v1/feed?section=stack',headers=h).json()['items']
        p=c.get('/v1/preferences',headers=h).json()
        p['follows']=['PHP'];p['onboarded']=True
        assert c.put('/v1/preferences',headers=h,json=p).status_code==200
        stack=c.get('/v1/feed?section=stack',headers=h).json()['items']
        assert len(stack)==1 and stack[0]['technology']=='PHP'
        assert c.get('/v1/feed?section=feed',headers=h).json()['items'][1]['id']==stack[0]['id']
        assert c.put('/v1/bookmarks/demo-php-1',headers=h).status_code==200
        assert len(c.get('/v1/bookmarks',headers=h).json()['items'])==1
        assert c.delete('/v1/bookmarks/demo-php-1',headers=h).status_code==200
        assert not c.get('/v1/bookmarks',headers=h).json()['items']
        assert c.put('/v1/bookmarks/demo-php-1',headers=h).status_code==200
        assert c.delete('/v1/me',headers=h).json()=={'deleted':True}
        assert not c.get('/v1/preferences',headers=h).json()['onboarded']
        assert not c.get('/v1/bookmarks',headers=h).json()['items']
        assert 'TechWatch Privacy Policy' in c.get('/privacy').text
        assert c.post('/admin/ingest-preview',json={'candidates':[]}).status_code==403
