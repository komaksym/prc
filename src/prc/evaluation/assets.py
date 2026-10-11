"""Light review page for one assigned reading at a time."""

from __future__ import annotations


def study_page() -> str:
    return STUDY_HTML


STUDY_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paired PR evaluation</title>
<style>
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#182738;background:#f5f7fa}
*{box-sizing:border-box}body{margin:0}main{max-width:1120px;margin:32px auto;padding:0 24px}
header{display:flex;justify-content:space-between;gap:24px;align-items:center}h1{font-size:32px;margin:0 0 8px}h2{font-size:23px}
p{line-height:1.55}.muted{color:#566779}.panel{background:white;border:1px solid #d5dfe8;border-radius:12px;padding:24px;margin:24px 0}
.notice{background:#eef7ff;border-left:4px solid #246aac;padding:16px}.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px}
button,.link{font:inherit;border:1px solid #b3c4d3;border-radius:8px;padding:11px 17px;background:white;color:#17496d;cursor:pointer}
button.primary{background:#17689e;color:white;border-color:#17689e}button:disabled{opacity:.55;cursor:wait}
label{display:block;margin:12px 0}input[type=checkbox]{margin-right:10px}textarea,select,input[type=number],input[type=text]{font:inherit;width:100%;padding:10px;border:1px solid #bacbd9;border-radius:6px}
textarea{min-height:100px;resize:vertical}input[type=number]{max-width:150px}.question{border-top:1px solid #dde5ed;padding-top:18px;margin-top:24px}.frame{width:100%;height:680px;border:1px solid #d5dfe8;border-radius:8px;background:white}
#timer{font-size:22px;font-variant-numeric:tabular-nums;white-space:nowrap}[hidden]{display:none!important}#error{color:#8e231b;background:#fff0ec;padding:14px}#save{color:#285b46}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;background:#f5f7fa;padding:12px;border-radius:6px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #dde5ed}code{overflow-wrap:anywhere}.grade-anchor{font-weight:600}
@media(max-width:600px){main{padding:0 14px}header{display:block}.panel{padding:17px}.frame{height:540px}}
</style></head><body><main>
<header><div><h1>Paired PR evaluation</h1><div class="muted">Two similar PRs. One reading per PR.</div></div><div id="timer" aria-live="off"></div></header>
<p id="reading-notice" class="notice">Use GitHub and the assigned aid for this reading. Keep artifact acceptance separate. No scores appear during the study.</p>
<p id="error" role="alert" hidden></p>
<section id="landing" class="panel"><h2>Start a new reading</h2><p>Prepare the next PR to report prior familiarity. Content and questions appear when the timer starts.</p><button id="prepare" class="primary">Prepare next reading</button></section>
<section id="preview" class="panel" hidden><h2 id="previewtitle"></h2><p id="identity" class="muted"></p>
<label><input id="familiar" type="checkbox">I have seen this PR before</label>
<label><input id="prioraid" type="checkbox">I have seen another explanation for this PR</label>
<label>Familiarity note<input id="priornote" type="text"></label>
<button id="start" class="primary">Start timed reading</button></section>
<section id="trial" hidden>
<div class="panel"><h2 id="title"></h2><p id="aidlabel"></p><div class="actions"><a id="github" class="link" target="_blank" rel="noopener noreferrer">Open GitHub PR</a><a id="aidlink" class="link" target="_blank" rel="noopener noreferrer">Open assigned aid</a></div><p class="muted">GitHub opens at Files changed. You can use its other review surfaces. Avoid the other tool's explanation.</p><iframe id="aid" class="frame" title="Assigned review aid" sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"></iframe></div>
<form id="answers" class="panel"><h2>Comprehension questions</h2><p class="muted">Answer from this reading. Blank answers receive zero. Optional confidence ranges from 0 to 100.</p><div id="questions"></div><p id="save" role="status">Saved</p>
<label><input id="otheraid" type="checkbox">I used or saw an unassigned aid during this reading</label><label>Exposure or delivery note<input id="note" type="text"></label>
<div class="actions"><button id="submit" class="primary" type="submit">Submit reading</button><button id="abort" type="button">Abort reading</button></div></form>
</section>
<section id="finished" class="panel" hidden><h2>All readings are saved</h2><p>Close the study to enable condition-blinded grading. This action ends further readings.</p><button id="close" class="primary">Close study</button></section>
<section id="closed" class="panel" hidden><h2>Study closed</h2><p>Answers are frozen. Grade each saved response against its frozen key and rubric. Blank answers receive zero.</p>
<form id="grading" hidden><h2>Condition-blinded grading</h2><p id="blinding" class="muted"></p><p id="grading-caveat" class="muted"></p><div id="grading-items"></div><div class="actions"><button class="primary" type="submit">Save grades and analyze</button></div><p class="muted">Complete every short-answer score before analysis. Multiple-choice scores use the exact frozen key automatically.</p></form></section>
<section id="analysis" class="panel" hidden><h2>Exploratory pilot analysis</h2><p id="interpretation" class="notice"></p><p id="decision" class="grade-anchor"></p><p>Paired accuracy difference in percentage points. Positive values favor GitHub + PRC over GitHub + Lens CI.</p><table><thead><tr><th>Missing-data scenario</th><th>Difference</th><th>95% interval</th></tr></thead><tbody id="scenarios"></tbody></table><p id="missing"></p><p id="time-summary"></p><p id="confidence-summary"></p><p>Frozen study digest</p><code id="digest"></code><details><summary>Full analysis and recorded deviations</summary><pre id="analysis-report"></pre></details></section>
</main><script>
let state=null,preview=null,current=null,busy=false,saveTimer=null,queue=Promise.resolve(),grading=null,report=null,loadingGrades=false;
const el=id=>document.getElementById(id);
async function api(path,body){const r=await fetch('/api/'+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data;}
function error(e){el('error').textContent=e.message;el('error').hidden=false;}
function draft(){const answers={},confidence={};for(const q of state.active.questions){answers[q.qid]=el('answer-'+q.qid).value;const c=el('confidence-'+q.qid).value;if(c!=='')confidence[q.qid]=Number(c);}return {trial_id:state.active.trial_id,answers,confidence};}
function save(){clearTimeout(saveTimer);const data=draft();queue=queue.catch(()=>{}).then(()=>api('answers',data)).then(()=>{el('save').textContent='Saved';el('error').hidden=true;}).catch(e=>{el('save').textContent='Save failed. Keep this page open.';error(e);});return queue;}
function changed(){el('save').textContent='Saving…';clearTimeout(saveTimer);saveTimer=setTimeout(save,350);}
function buildQuestions(a){el('questions').replaceChildren();a.questions.forEach((q,i)=>{const box=document.createElement('div');box.className='question';const label=document.createElement('label');label.htmlFor='answer-'+q.qid;label.textContent='Question '+(i+1);box.append(label);const prompt=document.createElement('p');prompt.textContent=q.prompt;box.append(prompt);let input;
if(q.kind==='multiple_choice'){input=document.createElement('select');input.add(new Option('Select an answer',''));q.options.forEach(o=>input.add(new Option(o,o)));}else input=document.createElement('textarea');input.id='answer-'+q.qid;input.value=a.answers[q.qid]||'';input.oninput=changed;box.append(input);
const confLabel=document.createElement('label');confLabel.htmlFor='confidence-'+q.qid;confLabel.textContent='Confidence for question '+(i+1);const conf=document.createElement('input');conf.id=confLabel.htmlFor;conf.type='number';conf.min=0;conf.max=100;conf.value=a.confidence[q.qid]??'';conf.oninput=changed;box.append(confLabel,conf);el('questions').append(box);});}
function textNode(tag,text){const node=document.createElement(tag);node.textContent=text;return node;}
function buildGrading(){el('grading-items').replaceChildren();el('blinding').textContent=grading.blinding_label;el('grading-caveat').textContent=grading.rubric_evidence_caveat;
grading.items.forEach((item,i)=>{const box=document.createElement('div');box.className='question';box.append(textNode('h3','Item '+(i+1)),textNode('p',item.prompt),textNode('p','Saved answer'),textNode('pre',item.answer===null||item.answer===''?'(blank)':item.answer),textNode('p','Frozen key'),textNode('pre',item.key),textNode('p','Required elements'),textNode('pre',(item.required_elements??[]).join('; ')||'(none)'),textNode('p','Frozen rubric'),textNode('pre',JSON.stringify(item.rubric)),textNode('p','Score meanings'),textNode('pre',Object.entries(item.rubric_anchors??{}).map(([score,text])=>score+' = '+text).join('\n')||'Use the frozen required elements.'));
const blank=item.answer===null||item.answer==='';const automatic=blank||item.kind==='multiple_choice';const score=blank?0:Number(item.answer===item.key);const label=textNode('label','Score for item '+(i+1));label.htmlFor='grade-'+i;const input=document.createElement('select');input.id=label.htmlFor;input.required=true;
if(automatic){input.add(new Option(String(score),String(score)));input.disabled=true;box.append(textNode('p',blank?'Automatic score: 0 for a blank answer.':'Automatic score: '+score+' from the exact frozen key.'));}else{input.add(new Option('Choose a score',''));[0,0.5,1].forEach(value=>input.add(new Option(String(value),String(value))));}
box.append(label,input);el('grading-items').append(box);});if(!grading.items.length)el('grading-items').append(textNode('p','No readings have saved answers. Analysis will retain every outcome as unknown.'));el('grading').hidden=false;}
function byCondition(values,suffix=''){return 'GitHub + PRC '+(values.product??'not recorded')+suffix+'; GitHub + Lens CI '+(values.baseline??'not recorded')+suffix;}
function showAnalysis(){el('grading').hidden=true;el('closed').hidden=true;el('analysis').hidden=false;el('interpretation').textContent=report.interpretation;el('decision').textContent='Pilot signal: '+report.decision;el('digest').textContent=report.study_digest;el('scenarios').replaceChildren();for(const [name,result] of Object.entries(report.scenarios)){const row=document.createElement('tr');row.append(textNode('td',name),textNode('td',result.estimate_pp.toFixed(2)+' pp'),textNode('td',result.lower_pp.toFixed(2)+' to '+result.upper_pp.toFixed(2)+' pp'));el('scenarios').append(row);}el('missing').textContent='Unknown outcomes: '+byCondition(report.missing_by_condition)+'. Aborted readings: '+byCondition(report.abort_counts)+'.';el('time-summary').textContent='Mean paired reading time difference: '+(report.time.mean_pair_difference_seconds===null?'not recorded':report.time.mean_pair_difference_seconds.toFixed(2)+' seconds, PRC minus Lens CI')+'. Pairs with both times: '+report.time.pairs_with_both_times+'.';el('confidence-summary').textContent='Mean reported confidence: '+byCondition(report.confidence.mean_by_condition)+'. Missing confidence answers: '+byCondition(report.confidence.missing_by_condition)+'.';el('analysis-report').textContent=JSON.stringify(report,null,2);}
async function loadClosed(){if(loadingGrades)return;loadingGrades=true;try{grading=await api('grading');if(state.graded){report=await api('analysis');showAnalysis();}else buildGrading();}catch(e){grading=null;error(e);}finally{loadingGrades=false;}}
function render(){const a=state.active;el('landing').hidden=!!a||!!preview||state.closed||!state.next;el('preview').hidden=!preview||!!a||state.closed;el('trial').hidden=!a;el('finished').hidden=!!a||!!state.next||state.closed;el('closed').hidden=!state.closed;
if(state.closed){el('reading-notice').hidden=true;el('questions').replaceChildren();el('title').textContent='';el('aidlabel').textContent='';el('identity').textContent='';el('previewtitle').textContent='';el('github').removeAttribute('href');el('aidlink').removeAttribute('href');preview=null;if(report)showAnalysis();else if(!grading)loadClosed();}
if(a){el('timer').textContent=Math.ceil(a.remaining_seconds/60)+' min remaining';if(current!==a.trial_id){current=a.trial_id;buildQuestions(a);el('title').textContent=a.snapshot_title;el('aidlabel').textContent=a.aid_kind==='prc'?'Assigned condition: GitHub + PRC':'Assigned condition: GitHub + Lens CI';el('github').href=a.github_url;el('aidlink').href=a.aid_url;el('aid').src=a.aid_url;el('otheraid').checked=false;el('note').value='';el('save').textContent='Saved';}}else{current=null;el('timer').textContent='';el('aid').removeAttribute('src');}}
async function refresh(){if(busy)return;try{state=await api('state');render();}catch(e){error(e);}}
async function action(fn){if(busy)return;busy=true;el('error').hidden=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);try{await fn();state=await api('state');render();}catch(e){error(e);if(e.message.includes('familiar PR')){preview=null;state=await api('state');render();}}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);}}
el('prepare').onclick=()=>action(async()=>{preview=await api('preview');el('previewtitle').textContent=preview.title;el('identity').textContent=preview.pr_identity+' · '+preview.head_sha.slice(0,12);el('familiar').checked=false;el('prioraid').checked=false;el('priornote').value='';});
el('start').onclick=()=>action(async()=>{await api('start',{trial_id:preview.trial_id,familiarity:{seen_before:el('familiar').checked,note:el('priornote').value},cross_tool_exposure:{saw_other_aid:el('prioraid').checked}});preview=null;});
async function finish(kind){await action(async()=>{clearTimeout(saveTimer);await queue;const data=draft();data.cross_tool_exposure={saw_other_aid:el('otheraid').checked,note:el('note').value};await api(kind,data);});}
el('answers').onsubmit=e=>{e.preventDefault();finish('submit');};el('abort').onclick=()=>finish('abort');el('close').onclick=()=>action(()=>api('close',{}));
el('grading').onsubmit=e=>{e.preventDefault();action(async()=>{const scores={};grading.items.forEach((item,i)=>{const value=el('grade-'+i).value;if(value==='')throw Error('Choose a score for every short answer.');(scores[item.trial_id]??={})[item.qid]=Number(value);});report=await api('grade',{study_digest:grading.study_digest,scores});showAnalysis();});};
refresh();setInterval(refresh,5000);
</script></body></html>"""
