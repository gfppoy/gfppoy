"""Timestamped source cache: reuse preserves retrieval dates, never freshness."""
import datetime, hashlib, json, threading, urllib.request
from pathlib import Path

class SourceSnapshot:
    def __init__(self, directory, context=None):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.path=self.directory/'snapshot.json';self.context=context;self.lock=threading.Lock()
        if self.path.exists():self.metadata=json.loads(self.path.read_text())
        else:
            if any(self.directory.iterdir()):
                raise ValueError('Cache lacks retrieval metadata. Use a new empty snapshot directory; old files cannot be relabelled as freshly checked.')
            self.metadata={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{}}
            self.path.write_text(json.dumps(self.metadata,indent=2)+'\n')
    def fetch(self,name,url):
        p=self.directory/name
        with self.lock:
            record=self.metadata['files'].get(name)
            if record:
                data=p.read_bytes()
                if record['url']!=url or hashlib.sha256(data).hexdigest()!=record['sha256']:
                    raise ValueError('Snapshot URL/hash mismatch: '+name)
                return data
            if p.exists():raise ValueError('Untracked source file: '+name)
        req=urllib.request.Request(url,headers={'User-Agent':'packing-comparison-audit'})
        data=urllib.request.urlopen(req,context=self.context,timeout=45).read()
        record={'url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(data).hexdigest()}
        with self.lock:
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            self.metadata['files'][name]=record
            temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(self.metadata,indent=2)+'\n');temp.replace(self.path)
        return data
