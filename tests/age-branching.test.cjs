const {test}=require('node:test');
const assert=require('node:assert/strict');
require('../growth-physics.js');const P=globalThis.GrowthPhysics;
test('age-dependent fork times follow the integrated Poisson hazard',()=>{
 for(const age of [0,260,1040]){
  const rng=P.seeded(42+age),n=40000,horizon=400;let forks=0,never=0;
  for(let i=0;i<n;i++){const wait=P.ageDecayingFork(age,1/260,520,rng);if(wait<=horizon)forks++;if(wait===Infinity)never++;}
  const remaining=2*Math.exp(-age/520);
  assert.ok(Math.abs(forks/n-(1-Math.exp(-remaining*(1-Math.exp(-horizon/520)))))<.01);
  assert.ok(Math.abs(never/n-Math.exp(-remaining))<.01);
 }
});
test('finite lifetime branching hazard gives finite expected growth without a tip cap',()=>{
 const rng=P.seeded(123);let sum=0;const runs=6000;
 for(let i=0;i<runs;i++){
  const queue=[0];let leaves=0;
  for(let j=0;j<queue.length;j++){
   const age=queue[j],wait=P.ageDecayingFork(age,1/260,520,rng);
   if(wait===Infinity)leaves++;else queue.push(age+wait,age+wait);
  }
  sum+=leaves;
 }
 assert.ok(Math.abs(sum/runs-Math.exp(2))<.3);
});
test('zero remaining hazard produces no future fork',()=>{
 assert.equal(P.ageDecayingFork(0,0,520,P.seeded(1)),Infinity);
 assert.equal(P.ageDecayingFork(1e9,1/260,520,P.seeded(1)),Infinity);
});
function animationHarness(limit) {
 const vm=require('node:vm'),fs=require('node:fs');
 const context=new Proxy({}, {get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>(o[k]=v,true)});
 const canvas={getContext:()=>context,getBoundingClientRect:()=>({width:10000,height:10000})};
 const button={addEventListener(){},setAttribute(){}};
 const math=Object.create(Math);math.random=P.seeded(17);
 const env={Math:math,Map,Object,devicePixelRatio:1,matchMedia:()=>({matches:false,addEventListener(){}}),requestAnimationFrame:()=>1,document:{getElementById:id=>id==='ecology'?canvas:button,addEventListener(){}},addEventListener(){},GrowthPhysics:P};
 env.window=env;vm.createContext(env);
 vm.runInContext(fs.readFileSync(require.resolve('../growth-physics.js'),'utf8'),env);
 let source=fs.readFileSync(require.resolve('../animation.js'),'utf8').replace('  window.ecologySimulation=', '  window.testAdvance=update;\n  window.ecologySimulation=');
 if(limit)source=source.replace('EMERGENCY_NODE_LIMIT = 400000',`EMERGENCY_NODE_LIMIT = ${limit}`);
 vm.runInContext(source,env);return env;
}
test('animation daughters retain founder age across forks',()=>{
 const env=animationHarness();env.testAdvance(500);const s=env.ecologySimulation.getState();
 assert.ok(s.tips.length>4);assert.equal(s.nodes.filter(n=>n.parent<0).length,4);
 for(const tip of s.tips.filter(t=>t.alive))assert.ok(Math.abs(tip.age-500)<1e-6);
});
test('emergency capacity pauses without killing tips or reporting completion',()=>{
 const env=animationHarness(4);assert.equal(env.testAdvance(10),false);const s=env.ecologySimulation.getState();
 assert.equal(s.phase,'capacity');assert.equal(s.paused,true);assert.equal(s.totalLength,0);assert.ok(s.tips.every(t=>t.alive));
});
