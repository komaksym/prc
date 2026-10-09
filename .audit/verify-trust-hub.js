const probeScript="(async()=> {\n const deadline=performance.now()+8000;\n while((location.pathname.endsWith('/doc.html') && !window.docReady) ||\n       (location.pathname.endsWith('/map.html') && !window.prcTour) ||\n       (document.querySelector('video') && document.querySelector('video').readyState<2) ||\n       (document.contentType.startsWith('image/') && !document.querySelector('img')?.naturalWidth)) {\n   if(performance.now()>deadline) throw new Error('artifact did not become ready');\n   await new Promise(resolve=>setTimeout(resolve,50));\n }\n const result={url:location.href,type:document.contentType,title:document.title,\n   errors:window.__prcErrors||[],text:document.body.innerText.slice(0,240)};\n const img=document.querySelector('img');\n if(document.contentType.startsWith('image/')) result.image={width:img.naturalWidth,height:img.naturalHeight};\n const v=document.querySelector('video');\n if(v) {\n   v.muted=true;\n   await v.play();\n   const start=v.currentTime;\n   await new Promise(resolve=>setTimeout(resolve,650));\n   v.pause();\n   result.video={width:v.videoWidth,height:v.videoHeight,duration:v.duration,start,end:v.currentTime,error:v.error&&v.error.message};\n }\n if(location.pathname.endsWith('/doc.html')) result.scenes=document.querySelectorAll('.shot').length;\n if(location.pathname.endsWith('/map.html')) result.nodes=document.querySelectorAll('[data-node]').length;\n return result;\n})()";

const session = load("hubSession"), proof = load("hubProof"), hub = load("hubUrl");
const links = load("hubLinks"), records = load("hubRecords") || [];
const start = records.length, end = Math.min(start + 5, links.length);
const calls = load("hubCalls") || [];
async function run(name, args) {
 const response = await tools[name](args);
 const success = !response.isError && response.structuredContent?.response?.success !== false;
 calls.push({at: new Date().toISOString(), tool: name, args, success});
 if (!success) throw new Error(JSON.stringify(response.structuredContent || response.content));
 return response.structuredContent?.response?.data;
}
for (let n = start; n < end; n++) {
 const link = links[n], row = {index:n, link, started:new Date().toISOString()};
 try {
  await run("mcp__agent_browser__agent_browser_open", {session, url:hub, headed:false});
  const snapshot = await run("mcp__agent_browser__agent_browser_snapshot", {session, interactive:true, includeUrls:true});
  row.sourceSnapshot = snapshot.snapshot;
  await run("mcp__agent_browser__agent_browser_click", {session, selector:"a[href="+JSON.stringify(link.href)+"]"});
  const data = await run("mcp__agent_browser__agent_browser_eval", {session, script:probeScript});
  row.result=data.result;
  const screenshot=proof+"/"+String(n+1).padStart(2,"0")+"-"+link.href.split("/").at(-1).replace(/\W/g,"-")+".png";
  await run("mcp__agent_browser__agent_browser_screenshot", {session,path:screenshot});
  row.screenshot=screenshot;
  const value=row.result;
  if(value.url!==link.url) throw new Error("link destination mismatch");
  if(value.errors.length) throw new Error("page errors "+JSON.stringify(value.errors));
  if(value.video && (!(value.video.end>value.video.start) || value.video.error || value.video.width!==1920 || value.video.height!==1080)) throw new Error("video playback failed");
  if(value.image && (value.image.width!==2400 || value.image.height!==1260)) throw new Error("card dimensions differ");
  if(value.scenes!==undefined && value.scenes<1) throw new Error("walkthrough scenes missing");
  row.passed=true;
 } catch(error) { row.passed=false; row.error=String(error); }
 row.ended=new Date().toISOString();
 records.push(row);
}
store("hubRecords",records); store("hubCalls",calls);
const payload=JSON.stringify({hub,session,links:links.length,clicked:records.length,passed:records.filter(r=>r.passed).length,records,calls},null,2);
text(await tools.exec_command({cmd:"python3 - <<'PY'\nfrom pathlib import Path\nPath("+JSON.stringify(proof+"/checks.json")+").write_text("+JSON.stringify(payload)+")\nPY",login:false,max_output_tokens:200}));
text({clicked:records.length,total:links.length,passed:records.filter(r=>r.passed).length,failures:records.filter(r=>!r.passed).map(r=>({index:r.index,error:r.error}))});
