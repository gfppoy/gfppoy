/* Simultaneously growing species. Winding paths, colour-based exclusion,
   length-weighted steering and founder-age Poisson branching. Natural contact
   or boundary deaths end growth, followed by a hold, fade and fresh seeds. */
(() => {
  'use strict';
  const canvas = document.getElementById('ecology'), toggle = document.getElementById('animation-toggle');
  if (!canvas || !toggle || !window.GrowthPhysics) return;
  const ctx = canvas.getContext('2d'); if (!ctx) return;
  const P = window.GrowthPhysics;
  const COLORS = ['#3c8b72', '#4e79b2', '#b08b3d', '#783cb0'];
  const CELL_SIZE = 8, FIELD_RADIUS = 14, FIELD_GAIN = .55;
  const GROWTH_SPEED = 47;
  const EMERGENCY_NODE_LIMIT = 400000; // Pause visibly; never pretend a truncated run finished.
  const CURVATURE_LENGTH = 90, CURVATURE_SCALE = .004, BRANCH_SPACING = 260;
  const AGE_DECAY_LENGTH = 2 * BRANCH_SPACING;
  const nextFork = age => P.ageDecayingFork(age, 1 / BRANCH_SPACING, AGE_DECAY_LENGTH);
  const HOLD_DURATION = 2000, FADE_DURATION = 2600;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const random = (a,b) => a + Math.random()*(b-a);
  let width=0,height=0,dpr=1,nodes=[],tips=[],cells=new Map(),totalLength=0;
  let phase='growing',phaseTime=0,opacity=1,paused=reduce.matches,frame=null,last=null,cycle=0;
  const mouse={x:-999,y:-999};
  let inView=true;
  function index(node) {
    const key=`${Math.floor(node.x/CELL_SIZE)},${Math.floor(node.y/CELL_SIZE)}`;
    if(!cells.has(key))cells.set(key,[]);cells.get(key).push(node);
  }
  function nearby(x,y,fn) {
    const col=Math.floor(x/CELL_SIZE),row=Math.floor(y/CELL_SIZE);
    for(let dx=-2;dx<=2;dx++)for(let dy=-2;dy<=2;dy++) {
      const list=cells.get(`${col+dx},${row+dy}`);if(list)for(const node of list)fn(node);
    }
  }
  function field(x,y,color) {
    let fx=0,fy=0;
    nearby(x,y,o=>{
      if(o.color===color)return;
      const dx=x-o.x,dy=y-o.y,d2=dx*dx+dy*dy;
      if(d2<FIELD_RADIUS**2){const weight=o.length*P.sourceWeight(d2,FIELD_RADIUS);fx+=dx*weight;fy+=dy*weight;}
    });
    const mx=x-mouse.x,my=y-mouse.y,m2=mx*mx+my*my;
    if(m2<55**2){const weight=P.sourceWeight(m2,55,47);fx+=mx*weight;fy+=my*weight;}
    return [fx,fy];
  }
  function pointDistance(p,a,b) {
    const dx=b.x-a.x,dy=b.y-a.y,d2=dx*dx+dy*dy;
    const u=d2?Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/d2)):0;
    return (p.x-a.x-u*dx)**2+(p.y-a.y-u*dy)**2;
  }
  function contact(a,b,color) {
    let hit=false;
    nearby(b.x,b.y,o=>{
      if(hit||o.color===color)return;
      const p=o.parent<0?o:nodes[o.parent];
      // Segments are at most .75 px; test both ends against each segment.
      hit=Math.min(pointDistance(a,p,o),pointDistance(b,p,o),pointDistance(p,a,b),pointDistance(o,a,b))<=36;
    });return hit;
  }
  function integrate(tip,k,distance) {
    const parent=nodes[tip.id];let state={x:parent.x,y:parent.y,angle:tip.angle},remaining=distance,travelled=0;
    while(remaining>1e-9) {
      if(nodes.length>=EMERGENCY_NODE_LIMIT){phase='capacity';paused=true;syncLabel();break;}
      const f=field(state.x,state.y,tip.color);
      let h=Math.min(remaining,.75,.04/Math.max(.001,Math.abs(k)+FIELD_GAIN*Math.hypot(...f)));
      let result=P.rk4(state,k,h,(x,y)=>field(x,y,tip.color),FIELD_GAIN);
      while((result.positionError>.001||result.angleError>.0001||Math.abs(result.next.angle-state.angle)>.05)&&h>1e-5) {
        h/=2;result=P.rk4(state,k,h,(x,y)=>field(x,y,tip.color),FIELD_GAIN);
      }
      const n=result.next;
      if(n.x<6||n.y<6||n.x>width-6||n.y>height-6||contact(state,n,tip.color)){tip.alive=false;break;}
      const node={x:n.x,y:n.y,parent:tip.id,color:tip.color,length:h};
      tip.id=nodes.length;nodes.push(node);index(node);tip.angle=n.angle;
      totalLength+=h;remaining-=h;travelled+=h;state=n;
    }
    return travelled;
  }
  function update(step) {
    const queue=tips.filter(t=>t.alive).map(tip=>({tip,remaining:step}));
    for(let i=0;i<queue.length;i++) {
      const work=queue[i],tip=work.tip;
      while(tip.alive&&work.remaining>1e-9&&phase==='growing') {
        const h=Math.min(work.remaining,1,tip.forkRemaining);
        const k=P.ou(tip.curvature,h/2,CURVATURE_LENGTH,CURVATURE_SCALE);
        const travelled=integrate(tip,k,h);
        tip.curvature=P.ou(k,travelled/2,CURVATURE_LENGTH,CURVATURE_SCALE);
        work.remaining-=travelled;tip.forkRemaining-=travelled;tip.age+=travelled;
        if(tip.alive&&tip.forkRemaining<1e-9) {
          // Both daughters inherit the founder's age, never a fresh clock.
          // Their independent future event clocks use the integrated hazard.
          const child={...tip,curvature:-tip.curvature,forkRemaining:nextFork(tip.age)};
          tips.push(child);queue.push({tip:child,remaining:work.remaining});
          tip.forkRemaining=nextFork(tip.age);
        }
      }
    }
    return phase==='growing'&&tips.every(t=>!t.alive);
  }
  function reset() {
    nodes=[];tips=[];cells=new Map();totalLength=0;phase='growing';phaseTime=0;opacity=1;cycle++;
    const count=COLORS.length;
    // Leave room for each founder to grow before reaching a boundary.
    const marginX=width*.2,marginY=height*.2;
    for(let i=0;i<count;i++) {
      const node={x:random(marginX,width-marginX),y:random(marginY,height-marginY),parent:-1,color:i,length:0};
      nodes.push(node);index(node);tips.push({id:i,color:i%4,angle:random(0,2*Math.PI),curvature:CURVATURE_SCALE*P.normal(),alive:true,age:0,forkRemaining:nextFork(0)});
    }
  }
  function render() {
    ctx.clearRect(0,0,width,height);ctx.lineWidth=2.4;ctx.lineCap='round';
    for(let color=0;color<4;color++) {
      ctx.strokeStyle=COLORS[color];ctx.globalAlpha=.62*opacity;ctx.beginPath();
      for(const n of nodes)if(n.parent>=0&&n.color===color){const p=nodes[n.parent];ctx.moveTo(p.x,p.y);ctx.lineTo(n.x,n.y);}ctx.stroke();
    }
    ctx.globalAlpha=.7*opacity;
    for(const tip of tips)if(tip.alive){const n=nodes[tip.id];ctx.fillStyle=COLORS[tip.color];ctx.beginPath();ctx.arc(n.x,n.y,2.5,0,2*Math.PI);ctx.fill();}
    ctx.globalAlpha=1;
  }
  function animate(now) {
    frame=null;const elapsed=last===null?0:Math.min(100,now-last);last=now;
    if(!paused&&!document.hidden&&inView){
      if(phase==='growing'){if(update(GROWTH_SPEED*elapsed/1000)){phase='holding';phaseTime=0;}}
      else {phaseTime+=elapsed;if(phase==='holding'&&phaseTime>=HOLD_DURATION){phase='fading';phaseTime=0;}
        else if(phase==='fading'){opacity=Math.max(0,1-phaseTime/FADE_DURATION);if(opacity===0)reset();}}
    }
    render();if(!paused&&!document.hidden&&inView)frame=requestAnimationFrame(animate);
  }
  function syncLabel(){toggle.textContent=phase==='capacity'?'Restart animation':paused?'Play animation':'Pause animation';toggle.title=phase==='capacity'?'Drawing capacity reached; restart with new seeds':'';toggle.setAttribute('aria-pressed',String(paused));}
  function wake(){last=null;syncLabel();if(frame===null)frame=requestAnimationFrame(animate);}
  function resize(){const box=canvas.getBoundingClientRect(),ratio=Math.min(devicePixelRatio||1,2);if(box.width<1||box.height<1)return;if(width===box.width&&height===box.height&&dpr===ratio)return;width=box.width;height=box.height;dpr=ratio;canvas.width=width*dpr;canvas.height=height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);reset();render();wake();}
  window.ecologySimulation=Object.freeze({pause(){paused=true;wake();},resume(){if(phase==='capacity')return;paused=false;wake();},getState(){return {width,height,colors:[...COLORS],nodes:nodes.map(n=>({...n})),tips:tips.map(t=>({...t})),phase,paused,cycle,totalLength};}});
  toggle.addEventListener('click',()=>{if(phase==='capacity'){reset();paused=reduce.matches;}else paused=!paused;wake();});
  reduce.addEventListener('change',e=>{paused=e.matches||phase==='capacity';wake();});
  document.addEventListener('visibilitychange',wake);
  document.addEventListener('pointermove',e=>{const bounds=canvas.getBoundingClientRect();mouse.x=e.clientX-bounds.left;mouse.y=e.clientY-bounds.top;},{passive:true});
  document.addEventListener('pointerleave',()=>{mouse.x=mouse.y=-999;});
  window.addEventListener('scroll',()=>{mouse.x=mouse.y=-999;},{passive:true});
  if('IntersectionObserver' in window)new IntersectionObserver(([entry])=>{inView=entry.isIntersecting&&entry.intersectionRatio>0;wake();},{threshold:[0,.001]}).observe(canvas);
  window.addEventListener('resize',resize,{passive:true});
  if('ResizeObserver' in window)new ResizeObserver(resize).observe(canvas);
  resize();toggle.hidden=false;
})();
