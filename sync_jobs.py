import argparse,json,os,tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from radar.core import now,merge
from radar.collect import BOARDS,FEEDS,collect_source,collect_lever

def run(path,feeds_only=False):
    previous=json.loads(path.read_text()) if path.exists() else {'jobs':[]}
    at=now(); offset=int(previous.get('runCount',0))*6
    tasks=[('feed',slug,company) for slug,company in FEEDS]
    if not feeds_only: tasks += [('web',name,None) for name in BOARDS]
    updates=[]; statuses=[]
    def collect(task):
        kind,a,b=task
        return collect_lever(a,b,previous['jobs']) if kind=='feed' else collect_source(a,previous['jobs'],offset)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for jobs,status in pool.map(collect,tasks):
            updates.extend(jobs); statuses.append({**status,'at':at})
    snapshot={**previous,'jobs':merge(previous['jobs'],updates,at),'lastAttempt':at,'lastSync':at if any(s['status']=='ok' for s in statuses) else previous.get('lastSync'),'sources':statuses,'runCount':previous.get('runCount',0)+1,'engine':'python-public-sources-v1'}
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False,encoding='utf-8') as f:
        json.dump(snapshot,f,ensure_ascii=False,indent=2); tmp=f.name
    os.replace(tmp,path)
    for s in statuses: print(s['source']+': '+s['status']+'; verified='+str(s['found'])+(' ('+s['error']+')' if s.get('error') else ''))
    print('Stored:',len(snapshot['jobs']),'jobs. Previous records preserved.')
    return snapshot
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--path',type=Path,default=Path('data/jobs.json')); parser.add_argument('--feeds-only',action='store_true'); args=parser.parse_args()
    run(args.path,args.feeds_only)
