import {test} from 'node:test';import assert from 'node:assert/strict';import {seal,open} from '../web/crypto.mjs';
test('Encrypted data requires correct password and detects tampering',async()=>{
 const secret='test-only-long-password-93747';const input={jobs:[{title:'Confidential example'}]};const e=await seal(input,secret);
 assert(!JSON.stringify(e).includes('Confidential'));assert.deepEqual(await open(e,secret),input);
 await assert.rejects(open(e,'incorrect-password-12345'));
 const changed={...e,ciphertext:(e.ciphertext[0]==='A'?'B':'A')+e.ciphertext.slice(1)};await assert.rejects(open(changed,secret));
 const e2=await seal(input,secret);assert.notEqual(e.iv,e2.iv);assert.notEqual(e.salt,e2.salt);
 await assert.rejects(seal(input,''));
});
