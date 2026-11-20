const enc=new TextEncoder(),dec=new TextDecoder();
export const ITERATIONS=600000;
const unb64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const b64=b=>{let s='';for(const c of new Uint8Array(b))s+=String.fromCharCode(c);return btoa(s)};
async function key(password,salt,usage){
 const material=await crypto.subtle.importKey('raw',enc.encode(password),'PBKDF2',false,['deriveKey']);
 return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:ITERATIONS,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,usage);
}
export async function seal(data,password){
 if(typeof password!=='string'||password.length<16)throw Error('Gunakan password minimal 16 karakter.');
 const salt=crypto.getRandomValues(new Uint8Array(32)),iv=crypto.getRandomValues(new Uint8Array(12));
 const ciphertext=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:enc.encode('radar-karier-v1')},await key(password,salt,['encrypt']),enc.encode(JSON.stringify(data)));
 return {v:1,kdf:'PBKDF2-SHA256',iterations:ITERATIONS,salt:b64(salt),iv:b64(iv),ciphertext:b64(ciphertext)};
}
export async function open(envelope,password){
 if(envelope.v!==1||envelope.iterations!==ITERATIONS||envelope.kdf!=='PBKDF2-SHA256')throw Error('Format data tidak didukung.');
 const salt=unb64(envelope.salt),iv=unb64(envelope.iv);
 if(salt.length!==32||iv.length!==12)throw Error('Format data rusak.');
 const plain=await crypto.subtle.decrypt({name:'AES-GCM',iv,additionalData:enc.encode('radar-karier-v1')},await key(password,salt,['decrypt']),unb64(envelope.ciphertext));
 return JSON.parse(dec.decode(plain));
}
