import hashlib
import re
from datetime import datetime, date, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

WIB = timezone(timedelta(hours=7))
PROVIDERS = {'linkedin.com':'LinkedIn','jobstreet.com':'JobStreet','glints.com':'Glints','kalibrr.id':'Kalibrr','kalibrr.com':'Kalibrr','dealls.com':'Dealls'}

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def today(): return datetime.now(WIB).date()
def clean(text): return re.sub(r'\s+', ' ', str(text or '')).strip()
def canonical(url):
    u = urlsplit(url)
    if u.scheme != 'https' or u.username or u.password or not u.hostname: raise ValueError('HTTPS required')
    ignored = {'trk','trackingid','refid','ref','source','origin','type','traceinfo','trid'}
    q = [(k,v) for k,v in parse_qsl(u.query) if not k.lower().startswith('utm_') and k.lower() not in ignored]
    return urlunsplit((u.scheme,u.netloc.lower(),u.path.rstrip('/') or '/',urlencode(q),''))
def source(url):
    host = urlsplit(url).hostname or ''
    return next((name for domain,name in PROVIDERS.items() if host == domain or host.endswith('.'+domain)), 'Karier perusahaan')
def sourced_date(value):
    if not value or not isinstance(value,str): return None
    try: return date.fromisoformat(value[:10]).isoformat()
    except ValueError: return None

def match(title, description, location):
    title, description, location = map(lambda x: clean(x).lower(), (title,description,location))
    if re.search(r'\b(senior|sr\.?|principal|head|director|vp|chief|manager|supervisor|lead)\b', title) and not re.search(r'junior|trainee|management development', title): return None
    required = re.findall(r'(?:minimum|minimal|min\.?|at least|minimum of)\s*(\d+)\s*(?:[-–]\s*\d+)?\s*\+?\s*(?:years?|tahun)', description)
    ranges = re.findall(r'\b(\d+)\s*[-–]\s*(\d+)\s*(?:years?|tahun)(?:\s+of)?\s*(?:relevant |working |work )?(?:experience|pengalaman)',description)
    direct = re.findall(r'\b(\d+)\+?\s*(?:years?|tahun)(?:\s+of)?\s*(?:relevant |working |work |professional )?(?:experience|pengalaman)',description)
    if any(int(n)>2 for n in required) or any(int(a)>2 for a,b in ranges) or any(int(n)>2 for n in direct): return None
    early = bool(re.search(r'fresh\s*grad|lulusan baru|recent graduate|no (?:prior )?(?:professional )?experience|entry.level|pengalaman kurang dari', description+' '+title)) or any(int(n)<=2 for n in required) or any(int(a)<=2 for a,b in ranges)
    if not early: return None
    if not re.search(r'indonesia|jakarta|bandung|tangerang|bogor|bekasi|surabaya|depok|semarang|yogyakarta|bali|medan|makassar|remote', location): return None
    if re.search(r'odp|bflp|management trainee|bankers trainee|graduate program|graduate programme|officer development|management development|wealth management program',title): category='MT / ODP'
    elif re.search(r'actuar|aktuar|underwrit|insurance pricing',title): category='Aktuaria'
    elif re.search(r'risk|risiko|credit analyst|credit reviewer|analis kredit|credit scoring',title): category='Risk & Kredit'
    elif re.search(r'data analyst|data analytics|data scientist|business intelligence|business analyst|reporting analyst|analis data|data reporting',title): category='Data & BI'
    elif re.search(r'banking|credit operation|loan operation|market operations|settlement|teller|frontliner|staf perbankan',title): category='Perbankan'
    else: return None
    score = 75 + (10 if re.search(r'mathematics|matematika|statistics|statistika|any major|semua jurusan', description) else 0) + (5 if re.search('bandung|jakarta|remote',location) else 0)
    return {'category':category,'match':score,'eligibility':'Fresh graduate / minimum pengalaman ≤2 tahun; cek persyaratan lengkap sumber.'}

def merge(previous, updates, timestamp):
    rows={canonical(j['url']):dict(j) for j in previous}
    for incoming in updates:
        url=canonical(incoming['url']); old=rows.get(url,{})
        row={**old,**{k:v for k,v in incoming.items() if v is not None}}
        # Missing dates are never replaced by discovery dates; exact dates beat approximate ones.
        if old.get('postedAt') and not old.get('postedApprox') and incoming.get('postedApprox'):
            row['postedAt']=old['postedAt']; row['postedApprox']=False
        row.update(url=url,firstSeen=old.get('firstSeen') or timestamp,lastSeen=timestamp,lastVerified=timestamp)
        rows[url]=row
    # Expiry is based on the source's date, never on fetch failure or absence from a feed.
    for row in rows.values():
        deadline=sourced_date(row.get('deadline'))
        if deadline and deadline < today().isoformat(): row['closed']=True
    return list(rows.values())

def key(job):
    company=re.sub(r'\b(pt|tbk|persero|ltd|limited)\b','',job.get('company','').lower())
    title=re.sub(r'\s*\((data analytics|banking operations|management trainee)\)\s*','',job.get('title','').lower())
    city=job.get('location','').lower()
    if 'jakarta' in city: city='jakarta'
    return re.sub(r'[^a-z0-9]','',company+':'+title+':'+city)

def deduplicate(jobs):
    groups={}
    for j in sorted(jobs,key=lambda x:(bool(x.get('closed')),x.get('source')=='LinkedIn')):
        k=key(j)
        if k not in groups: groups[k]=dict(j)
        else:
            existing=groups[k]
            for field in ('salary','deadline','postedAt','employment'):
                if not existing.get(field) and j.get(field): existing[field]=j[field]
    return list(groups.values())
