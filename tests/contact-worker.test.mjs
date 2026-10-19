import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHandler } from '../contact-worker/worker.mjs';
const origin='https://example.test';
const env={ ALLOWED_ORIGINS:origin, TURNSTILE_SECRET_KEY:'private-test-secret', CONTACT_EMAIL:'researcher@example.test' };
const request=(body={token:'token'}, options={})=>new Request('https://contact.example.test/reveal-email',{
 method:'POST',headers:{Origin:origin,'Content-Type':'application/json',...options.headers},body:JSON.stringify(body),...options
});
const valid=()=>({success:true,hostname:'example.test',action:'email-reveal',challenge_ts:new Date().toISOString()});
const mock=result=>createHandler(async()=>Response.json(result));
async function noEmail(response,status){assert.equal(response.status,status);assert.equal(response.headers.get('Cache-Control'),'no-store');assert.ok(!(await response.text()).includes(env.CONTACT_EMAIL));}
test('only a server-verified matching token reveals the secret address',async()=>{
 let calls=0;const handler=createHandler(async(url,options)=>{
  calls++;assert.equal(url,'https://challenges.cloudflare.com/turnstile/v0/siteverify');
  const sent=JSON.parse(options.body);assert.equal(sent.secret,env.TURNSTILE_SECRET_KEY);assert.equal(sent.response,'token');
  return Response.json(valid());
 });
 const response=await handler.fetch(request(),env);assert.equal(calls,1);assert.equal(response.status,200);
 assert.equal(response.headers.get('Access-Control-Allow-Origin'),origin);assert.equal(response.headers.get('Cache-Control'),'no-store');
 assert.deepEqual(await response.json(),{email:env.CONTACT_EMAIL});
});
for(const [label,patch] of [ ['failed',{success:false}],['wrong host',{hostname:'elsewhere.test'}],['wrong action',{action:'login'}],['missing timestamp',{challenge_ts:undefined}],['expired',{challenge_ts:new Date(Date.now()-360000).toISOString()}],['future',{challenge_ts:new Date(Date.now()+60000).toISOString()}] ]){
 test(`rejects ${label} verification`,async()=>noEmail(await mock({...valid(),...patch}).fetch(request(),env),403));
}
test('a replayed token is reverified and rejected; success is never cached',async()=>{
 let used=false;const handler=createHandler(async()=>{const result=used?{success:false,'error-codes':['timeout-or-duplicate']}:valid();used=true;return Response.json(result);});
 assert.equal((await handler.fetch(request(),env)).status,200);await noEmail(await handler.fetch(request(),env),403);
});
test('missing configuration and network failure fail closed',async()=>{
 await noEmail(await mock(valid()).fetch(request(),{}),403);
 await noEmail(await mock(valid()).fetch(request(),{...env,TURNSTILE_SECRET_KEY:''}),503);
 await noEmail(await createHandler(async()=>{throw Error('offline');}).fetch(request(),env),503);
 await noEmail(await createHandler(async()=>new Response('bad',{status:503})).fetch(request(),env),503);
});
test('malformed and oversized input is rejected before calling Cloudflare',async()=>{
 let calls=0;const handler=createHandler(async()=>{calls++;return Response.json(valid());});
 for(const body of [{},null,{token:3},{token:''},{token:'a'.repeat(2049)}])await noEmail(await handler.fetch(request(body),env),400);
 await noEmail(await handler.fetch(request({}, {body:'{broken'}),env),400);
 await noEmail(await handler.fetch(request({token:'a'.repeat(5000)}),env),413);
 assert.equal(calls,0);
});
test('CORS, route, method and media type restrictions do not disclose the address',async()=>{
 const handler=mock(valid());
 const r=await handler.fetch(request({}, {headers:{Origin:'https://evil.test','Content-Type':'application/json'}}),env);
 assert.equal(r.headers.get('Access-Control-Allow-Origin'),null);await noEmail(r,403);
 await noEmail(await handler.fetch(new Request('https://contact.example.test/reveal-email',{headers:{Origin:origin}}),env),405);
 await noEmail(await handler.fetch(new Request('https://contact.example.test/elsewhere',{headers:{Origin:origin}}),env),404);
 await noEmail(await handler.fetch(request({}, {headers:{Origin:origin,'Content-Type':'text/plain'}}),env),415);
 const preflight=await handler.fetch(new Request('https://contact.example.test/reveal-email',{method:'OPTIONS',headers:{Origin:origin}}),env);
 assert.equal(preflight.status,204);assert.equal(preflight.headers.get('Access-Control-Allow-Methods'),'POST');assert.equal(await preflight.text(),'');
});
