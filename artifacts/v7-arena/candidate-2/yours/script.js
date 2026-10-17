(function(){
'use strict';
var $=function(s,r){return (r||document).querySelector(s)};
var $$=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))};
var params=new URLSearchParams(location.search);
var CLIP=params.get("clip")==="1";
var COUNTS=[["Fetched rows",4],["Matched rows",3],["Unique matched connections",2],["Unmatched rows",1],["Newly inserted events",1],["Already-present events",1]];
var RUNTIME="Run time: 2026-09-30 10:00:00 CEST";
function report(status){
  var L=["LinkedIn CONNECTIONS reconciliation","Status: "+status,RUNTIME];
  COUNTS.forEach(function(c){L.push(c[0]+": "+(status==="COMPLETE"?c[1]:"unknown"))});
  if(status==="COMPLETE")L.push("Next action: review the aggregate counts; investigate unmatched rows if needed.");
  else if(status==="BLOCKED")L.push("Next action: restore a complete LinkedIn CONNECTIONS snapshot, then rerun.");
  return L;
}
var SCEN={
  complete:{exit:0,status:"COMPLETE",cls:"st-complete",cap:"<b>Exit 0.</b> The run is COMPLETE. All six counts are known."},
  later_404:{exit:1,status:"BLOCKED",cls:"st-blocked",cap:"<b>Exit 1.</b> LinkedIn answers 404 on a later page. Status is BLOCKED and counts are unknown."},
  supabase_timeout:{exit:1,status:"FAILED",cls:"st-failed",cap:"<b>Exit 1.</b> The Supabase write times out. Status is FAILED and writes may have happened."},
  sharing:{exit:2,status:null,cls:"st-none",cap:"<b>Exit 2.</b> The Doc is shared. The run stops early and writes nothing."}
};
var cur="complete";
function setScen(name,animate){
  cur=name; var sc=SCEN[name];
  $$(".scen-btns button").forEach(function(b){b.setAttribute("aria-pressed",b.dataset.scen===name?"true":"false")});
  var stamp=$('[data-run="status"] .stamp');
  stamp.textContent=sc.status||"no status"; stamp.className="stamp "+sc.cls;
  var dl=$('[data-run="counts"]'); dl.innerHTML="";
  COUNTS.forEach(function(c){
    var v=sc.status==="COMPLETE"?String(c[1]):(sc.status?'unknown':'no run');
    var div=document.createElement("div"); if(sc.status!=="COMPLETE")div.className="unknown";
    var dt=document.createElement("dt"); dt.textContent=c[0];
    var dd=document.createElement("dd"); dd.textContent=v; div.appendChild(dt); div.appendChild(dd); dl.appendChild(div);
  });
  $('[data-run="meta"]').textContent="Exit code "+sc.exit+". "+RUNTIME+".";
  var news=$('[data-doc="news"]'); var old=$('[data-doc="old"]'); var stopped=$('[data-doc="stopped"]');
  if(sc.status){ stopped.hidden=true; old.style.display="";
    news.style.display=""; news.innerHTML="";
    report(sc.status).forEach(function(line,i){
      var p=document.createElement("p");
      if(i===0){p.className="news-title";p.textContent=line}
      else if(/^Status/.test(line)){p.className="news-status";p.textContent=line}
      else if(/^Next|^Database/.test(line)){p.className="next";p.textContent=line}
      else p.textContent=line;
      news.appendChild(p);
    });
    var st=$(".news-status",news); if(st){st.style.color=sc.status==="COMPLETE"?"var(--green)":(sc.status==="BLOCKED"?"var(--amber)":"var(--red)")}
  } else { news.style.display="none"; old.style.display=""; stopped.hidden=false; }
  $('[data-cap="doc"]').innerHTML=sc.cap;
  if(animate&&!matchMedia("(prefers-reduced-motion: reduce)").matches){
    news.style.transition="none"; news.style.opacity="0";
    requestAnimationFrame(function(){news.style.transition="opacity .3s ease";news.style.opacity="1"})
  }
}
$$(".scen-btns button").forEach(function(b){b.addEventListener("click",function(){setScen(b.dataset.scen,true)})});
setScen("complete",false);
function revealAll(){ $$(".sheet,.codewrap,.tip,.flow,.scen").forEach(function(el){el.classList.add("rv");el.classList.add("in")}); }
if(!CLIP){
  if("IntersectionObserver" in window&&!matchMedia("(prefers-reduced-motion: reduce)").matches){
    var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add("in");io.unobserve(e.target)}})},{threshold:.12});
    $$(".sheet,.codewrap,.tip,.flow,.scen").forEach(function(el){el.classList.add("rv");io.observe(el)});
  } else revealAll();
}
function sleep(ms){return new Promise(function(r){setTimeout(r,ms)})}
var reduced=function(){return matchMedia("(prefers-reduced-motion: reduce)").matches};
async function playMoment(i){
  var m=$('.moment[data-moment="' + i + '"]'); if(!m)return;
  var items=$$(".sheet,.codewrap,.tip,.scen,.flow,.figcap,.codewrap .cl",m);
  items.forEach(function(el){el.classList.add("rv")});
  void m.offsetWidth;
  var step=reduced()?0:360;
  for(var k=0;k<items.length;k++){
    if(items[k].closest(".moment")!==m)continue;
    if(items[k].classList.contains("cl")&&k>9)break;
    items[k].classList.add("in"); await sleep(step);
  }
  if(i===2&&!reduced()){
    var marks=$$('.moment[data-moment="2"] .cl[data-line]');
    marks.forEach(function(el){el.classList.remove("mark","mark-bad")});
    var l36=$('.cl[data-line="36"]'); if(l36)l36.classList.add("mark");
    await sleep(850);
    ["43","44"].forEach(function(n){var e=$('.cl[data-line="' + n + '"]');if(e)e.classList.add("mark-bad")});
    await sleep(850);
    ["50","51"].forEach(function(n){var e=$('.cl[data-line="' + n + '"]');if(e)e.classList.add("mark-bad")});
    await sleep(850);
  }
}
function resetClip(){
  $$(".moment").forEach(function(m){m.classList.remove("live")});
  $$(".rv").forEach(function(el){el.classList.remove("in")});
  $$(".cl.mark,.cl.mark-bad").forEach(function(el){el.classList.remove("mark","mark-bad")});
  setScen("complete",false);
}
if(CLIP){
  document.body.classList.add("clip");
  window.__marks=[]; window.__clipDone=false; window.__ready=false;
  window.startClip=async function(){
    resetClip(); var t0=performance.now(); window.__marks=[];
    for(var i=1;i<=3;i++){
      var m=$('.moment[data-moment="' + i + '"]');
      m.classList.add("live");
      if(i>1){var prev=$('.moment[data-moment="' + (i-1) + '"]');setTimeout(function(p){p.classList.remove("live")},550,prev)}
      await sleep(420);
      await playMoment(i);
      window.__marks.push((performance.now()-t0)/1000);
      await sleep(1000);
    }
    await sleep(400); window.__clipDone=true;
  };
  (document.fonts?document.fonts.ready:Promise.resolve()).then(function(){window.__ready=true});
  setTimeout(function(){window.__ready=true},3500);
} else { window.__ready=true; }
})();
