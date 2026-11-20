import {readFile,writeFile,mkdtemp,rm,mkdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';import {join} from 'node:path';import {spawnSync} from 'node:child_process';
import {seal,open} from '../web/crypto.mjs';
import {gunzipSync} from 'node:zlib';
const password=process.env.RADAR_PASSWORD;
if(!password||password.length<16)throw Error('Set GitHub Actions secret RADAR_PASSWORD (minimum 16 characters). No unencrypted fallback.');
const dir=await mkdtemp(join(tmpdir(),'radar-'));const path=join(dir,'jobs.json');
try{
 let previous={jobs:[]};
 try{previous=await open(JSON.parse(await readFile('web/data.enc.json','utf8')),password)}
 catch(e){if(e.code!=='ENOENT')throw Error('Existing data could not be decrypted. Preserve it; use the original password.');
  if(process.env.RADAR_SEED)previous=JSON.parse(gunzipSync(Buffer.from(process.env.RADAR_SEED,'base64')).toString('utf8'));
 }
 await writeFile(path,JSON.stringify(previous),{mode:0o600});
 const run=spawnSync('python',['sync_jobs.py','--path',path],{encoding:'utf8',timeout:600000,maxBuffer:1000000});
 if(run.status!==0)throw Error('Collector failed; previous encrypted data preserved.');
 const data=JSON.parse(await readFile(path,'utf8'));
 if(!data.sources?.some(s=>s.status==='ok'))throw Error('All sources failed; previous encrypted data preserved.');
 await writeFile('web/data.enc.json',JSON.stringify(await seal(data,password))+'\n');
 console.log('Encrypted sync completed; no job data or password written to logs.');
}finally{await rm(dir,{recursive:true,force:true});}
