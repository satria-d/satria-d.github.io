export const categories=['MT / ODP','Aktuaria','Risk & Kredit','Data & BI','Perbankan'];
export const colors={'MT / ODP':'green',Aktuaria:'purple','Risk & Kredit':'blue','Data & BI':'sand',Perbankan:'teal'};
export function relevanceScore(value){
 if(typeof value!=='number'&&typeof value!=='string'||typeof value==='string'&&!value.trim())return null;
 const score=Number(value);return Number.isFinite(score)&&score>=0&&score<=100?score:null;
}
export function today(now=new Date()){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Jakarta',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);}
export function daysAgo(value,now=new Date()){return value?Math.floor((Date.parse(today(now))-Date.parse(value.slice(0,10)))/86400000):null;}
export function ageLabel(value,approx=false,now=new Date()){const days=daysAgo(value,now);if(days===null||!Number.isFinite(days)||days<0)return'Tanggal posting belum tercantum';return(approx?'≈ ':'')+(days===0?'Hari ini':days===1?'Kemarin':days<7?days+' hari lalu':days<30?Math.floor(days/7)+' minggu lalu':days<365?Math.floor(days/30)+' bulan lalu':Math.floor(days/365)+' tahun lalu');}
export function sourcesOf(job){return [...new Set([job.source,...(job.sources||[]).map(s=>s.name)].filter(Boolean))];}
export function normalized(jobs,now=new Date()){
 const date=today(now),groups=new Map();
 for(const raw of jobs){const j={...raw,closed:!!(raw.closed||(raw.deadline&&raw.deadline<date))};const k=[j.company,j.title,j.location].join('|').replace(/&amp;/g,'&').toLowerCase();const old=groups.get(k);if(!old||old.closed&&!j.closed)groups.set(k,j);}
 return [...groups.values()];
}
export function filterJobs(jobs,{query='',category='',source='',location='',age='',scope='active',sort='fit'}={},now=new Date()){
 const text=query.toLowerCase().trim();return jobs.filter(j=>{
  if(scope!=='all'&&j.closed!==(scope==='closed'))return false;
  if(category&&j.category!==category)return false;
  if(source&&!sourcesOf(j).includes(source))return false;
  if(location&&!(j.location||'').toLowerCase().includes(location.toLowerCase()))return false;
  if(text&&![j.title,j.company,j.location,j.category].join(' ').toLowerCase().includes(text))return false;
  if(age==='unknown')return!j.postedAt;
  if(age){const days=daysAgo(j.postedAt,now);if(days===null||!Number.isFinite(days)||days<0)return false;return age==='old'?days>=30:age==='0'?days===0:days<Number(age);}
  return true;
 }).sort((a,b)=>{if(sort==='deadline')return(a.deadline||'9999').localeCompare(b.deadline||'9999');const newest=(b.postedAt||'').localeCompare(a.postedAt||'')||(b.firstSeen||'').localeCompare(a.firstSeen||'');return sort==='new'?newest:(Number(b.match)||0)-(Number(a.match)||0)||newest;});
}
export function metrics(jobs,now=new Date()){
 const date=today(now),active=jobs.filter(j=>!j.closed);return {active:active.length,recent:active.filter(j=>{const n=daysAgo(j.postedAt,now);return n!==null&&n>=0&&n<7}).length,deadline:active.filter(j=>j.deadline&&j.deadline>=date&&(Date.parse(j.deadline)-Date.parse(date))/86400000<=7).length};
}
