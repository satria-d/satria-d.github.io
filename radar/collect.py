"""Public-source collectors. Errors are recorded and never treated as job closure."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
import requests
from radar.core import canonical, clean, source, sourced_date, match

BOARDS = {
 'LinkedIn':['https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=data%20analyst%20fresh%20graduate&location=Indonesia&f_E=1%2C2&start=0','https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=graduate%20banking&location=Indonesia&f_E=1%2C2&start=0'],
 'JobStreet':['https://id.jobstreet.com/data-analyst-fresh-graduate-jobs/in-Jakarta','https://id.jobstreet.com/data-analyst-jobs/in-Bandung-West-Java'],
 'Glints':['https://glints.com/id/explore/data-analyst/in-bandung','https://glints.com/id/explore/data-analyst-fresh-graduate/in-jakarta'],
 'Kalibrr':['https://www.kalibrr.id/job-board/te/data-analyst','https://www.kalibrr.id/c/bfifinance/jobs'],
 'Dealls':['https://dealls.com/loker/posisi/loker-data-analyst','https://dealls.com/loker/posisi/loker-business-analyst'],
 'Karier perusahaan':['https://careers.danamon.co.id/search/','https://karir.bca.co.id/candidate/id/career?experience=Fresh+Graduate','https://group.bnpparibas/en/careers/all-job-offers/indonesia'],
}
FEEDS=[('GoToGroup','GoTo Group'),('amarbank','Amar Bank')]
DETAIL=re.compile(r'/jobs/view/|/job/\d+|/opportunities/(?:jobs|s)/|/jobs/\d+/|/loker/[^/?]+~|/careers/job-offer/|/candidate/id/career/[^/?]+|careers\.danamon\.co\.id/job/')
CLOSED=re.compile(r'no longer accepting applications|tidak lagi menerima lamaran|lowongan ini (?:telah|sudah) ditutup|this job (?:was|is|has been) closed|job (?:has expired|is no longer available)',re.I)

class FetchError(Exception): pass

def get(url):
    if not url.startswith('https://'): raise FetchError('HTTPS required')
    r=requests.get(url,timeout=(6,16),headers={'User-Agent':'RadarKarier/1.0 (personal career tracker; public pages only)','Accept':'application/json,text/html'},allow_redirects=False)
    if 300<=r.status_code<400:
        dest=urljoin(url,r.headers.get('Location',''))
        if urlsplit(dest).hostname!=urlsplit(url).hostname: raise FetchError('Cross-origin redirect skipped')
        r=requests.get(dest,timeout=(6,16),headers={'User-Agent':'RadarKarier/1.0'},allow_redirects=False)
    if r.status_code!=200: raise FetchError('HTTP '+str(r.status_code))
    if len(r.content)>6_000_000: raise FetchError('Response too large')
    return r

def nodes(value):
    if isinstance(value,list):
        for v in value: yield from nodes(v)
    elif isinstance(value,dict):
        if value.get('@type')=='JobPosting' or 'JobPosting' in (value.get('@type') or []): yield value
        if '@graph' in value: yield from nodes(value['@graph'])

def location_text(obj):
    if isinstance(obj,list): return ' / '.join(filter(None,(location_text(x) for x in obj)))
    if isinstance(obj,str): return obj
    if not isinstance(obj,dict): return ''
    a=obj.get('address',obj)
    if isinstance(a,str): return a
    country=a.get('addressCountry','')
    if isinstance(country,dict): country=country.get('name','')
    return ', '.join(clean(x) for x in [a.get('addressLocality'),a.get('addressRegion'),country] if x)

def salary_text(obj):
    if isinstance(obj,str): return obj
    if not isinstance(obj,dict): return None
    v=obj.get('value',{})
    if not isinstance(v,dict): return clean(str(obj.get('currency',''))+' '+str(v))
    amount=str(v['value']) if 'value' in v else ' – '.join(str(v[k]) for k in ('minValue','maxValue') if v.get(k) is not None)
    if not amount: return None
    return clean(str(obj.get('currency',''))+' '+amount+(' / '+str(v['unitText']) if v.get('unitText') else ''))

def parse_detail(url,html,existing=None):
    soup=BeautifulSoup(html,'html.parser')
    main=soup.find('main') or soup
    # Ignore other vacancies and footer links when interpreting the current job.
    for related in main.select('aside, footer, nav, .similar-jobs, .related-jobs, [data-testid="similar-jobs"]'):
        related.decompose()
    body=clean(main.get_text(' ',strip=True))
    # A page error, sign-in wall, or fetch failure is not a closed-job signal.
    heading=main.find('h1')
    own_heading=not heading or existing and clean(heading.get_text()).lower()==clean(existing.get('title')).lower()
    if CLOSED.search(body) and own_heading and (heading or len(body)<500):
        if existing: return {**existing,'closed':True,'verification':'closed','evidence':'Penutupan dinyatakan secara eksplisit di halaman detail sumber.'}
        return None
    for tag in soup.find_all('script',type='application/ld+json'):
        try: listings=list(nodes(json.loads(tag.string or tag.get_text())))
        except (ValueError,TypeError): continue
        for p in listings:
            title=clean(p.get('title')); org=p.get('hiringOrganization') or {}
            if p.get('url'):
                try:
                    if canonical(p['url'])!=canonical(url): continue
                except (ValueError,TypeError): continue
            company=clean(org.get('name') if isinstance(org,dict) else org)
            desc=clean(BeautifulSoup(p.get('description',''),'html.parser').get_text(' '))
            loc=location_text(p.get('jobLocation'))
            if p.get('jobLocationType')=='TELECOMMUTE': loc=clean(loc+' Remote')
            if not loc and existing: loc=existing.get('location','')
            fit=match(title,desc,loc)
            if not fit and not existing: continue
            if not title or not company: continue
            posted=sourced_date(p.get('datePosted')); deadline=sourced_date(p.get('validThrough'))
            from radar.core import today
            if posted and posted>today().isoformat(): posted=None
            return {'url':canonical(url),'title':title,'company':company,'location':loc,'employment':clean(p.get('employmentType')) or None,'salary':salary_text(p.get('baseSalary')),'postedAt':posted,'postedApprox':False if posted else None,'deadline':deadline,'evidence':desc[:1800],'closed':False,'source':source(url),'verification':'verified',**(fit or {})}
    # LinkedIn publicly rendered detail (not a search result card).
    title=soup.find('h1'); company=soup.select_one('.topcard__org-name-link'); desc=soup.select_one('.show-more-less-html__markup'); loc=soup.select_one('.topcard__flavor--bullet')
    if title and company and desc and loc:
        title,company,desc,loc=[clean(x.get_text(' ',strip=True)) for x in (title,company,desc,loc)]
        fit=match(title,desc,loc)
        if fit or existing:
            tm=soup.find('time',datetime=True); posted=sourced_date(tm.get('datetime')) if tm else None
            return {'url':canonical(url),'title':title,'company':company,'location':loc,'employment':None,'salary':None,'postedAt':posted,'postedApprox':False if posted else None,'deadline':None,'evidence':desc[:1800],'closed':False,'source':'LinkedIn','verification':'verified',**(fit or {})}
    # Existing listings need an actual job heading and an application control to be reverified.
    if existing:
        h=main.find('h1')
        has_apply=any(re.search(r'^(apply now|apply|lamar|lamar cepat|quick apply|lamaran cepat)',clean(x.get_text(' ',strip=True)),re.I) for x in main.find_all(['a','button']))
        if h and clean(h.get_text()).lower()==clean(existing.get('title')).lower() and has_apply:
            return {**existing,'verification':'verified','evidence':body[:1800],'closed':False}
    return None

def fetch_detail(pair):
    url,existing=pair
    try: return parse_detail(url,get(url).text,existing),None
    except Exception as e: return None,type(e).__name__+': '+str(e)[:100]

def collect_source(name,old,offset,limit=12):
    found=[]; candidates=[]; failures=[]; listing_ok=False
    for board in BOARDS[name]:
        try:
            soup=BeautifulSoup(get(board).text,'html.parser'); listing_ok=True
            host=urlsplit(board).hostname
            for a in soup.find_all('a',href=True):
                u=urljoin(board,a['href']); uh=urlsplit(u).hostname or ''
                if u.startswith('https://') and (source(u)==name or name=='Karier perusahaan' and uh==host) and DETAIL.search(u):
                    if u not in candidates: candidates.append(u)
        except Exception as e: failures.append(type(e).__name__+': '+str(e)[:80])
    historical=[j for j in old if source(j['url'])==name and not j.get('closed')]
    if historical:
        pos=offset%len(historical); historical=historical[pos:]+historical[:pos]
    lookup={canonical(j['url']):j for j in old}
    urls=list(dict.fromkeys(candidates[:limit//2]+[j['url'] for j in historical[:limit]]))[:limit]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(fetch_detail,[(u,lookup.get(canonical(u))) for u in urls]))
    verified=0
    for job,error in results:
        if job: found.append(job); verified+=1
        if error: failures.append(error)
    status='ok' if verified else 'error'
    return found,{'source':name,'status':status,'found':verified,'checked':len(urls),'error':None if status=='ok' else ('; '.join(failures[:2]) or ('Halaman tersedia tetapi detail terverifikasi tidak berhasil diekstrak.' if listing_ok else 'Sumber tidak tersedia.'))}

def collect_lever(slug,company,old):
    name=company+' · Karier'
    try:
        posts=get('https://api.lever.co/v0/postings/'+slug+'?mode=json').json()
        if not isinstance(posts,list): raise FetchError('Invalid feed')
        result=[]
        # The posting feed is an authoritative active-job list; creation time is not publication time.
        for p in posts:
            cat=p.get('categories') or {}; loc=' / '.join(cat.get('allLocations') or []) or cat.get('location','')
            desc=clean(p.get('descriptionPlain','')+' '+p.get('additionalPlain','')+' '+' '.join(BeautifulSoup(x.get('content',''),'html.parser').get_text(' ') for x in p.get('lists',[])))
            fit=match(p.get('text'),desc,loc)
            if not fit: continue
            url=p.get('hostedUrl','')
            if not url.startswith('https://jobs.lever.co/'+slug+'/'): continue
            result.append({'url':url,'title':p['text'],'company':company,'location':loc,'employment':cat.get('commitment'),'salary':None,'postedAt':None,'postedApprox':None,'deadline':None,'evidence':desc[:1800],'closed':False,'verification':'verified','source':name,**fit})
        return result,{'source':name,'status':'ok','found':len(result),'checked':len(posts),'error':None}
    except Exception as e:return [],{'source':name,'status':'error','found':0,'checked':0,'error':type(e).__name__+': '+str(e)[:120]}
