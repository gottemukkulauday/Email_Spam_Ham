const app=document.getElementById('app');let state={page:'home',email:{},result:null,history:[],dash:null,menuOpen:false};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(url,opt){let r=await fetch(url,opt);let d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d}
function nav(){return `<nav class="nav"><button class="menu-toggle" aria-label="Open navigation menu" aria-expanded="${state.menuOpen}" onclick="toggleMenu()"><span></span><span></span><span></span></button><div class="brand">SpamSense</div>${state.menuOpen?`<div class="menu-backdrop" onclick="closeMenu()"></div><div class="menu-panel">${[['home','Home'],['detection','Detection'],['history','History'],['dashboard','Dashboard']].map(([p,label])=>`<button class="menu-item ${state.page===p?'active':''}" onclick="go('${p}')">${label}</button>`).join('')}</div>`:''}</nav>`}
function about(){return `<div class="wrap"><section class="hero"><h1>Email Spam Detection</h1><p>Detect spam, phishing, and suspicious emails using intelligent AI-powered analysis.</p></section><div class="grid4">${[['URL Analysis'],['Context Analysis'],['Sender Analysis'],['Risk Assessment']].map(x=>`<div class="card"><h3>${x[0]}</h3><div class="muted">Explainable signals for every message.</div></div>`).join('')}</div><div class="card" style="margin-top:20px"><h3>How it works</h3><div class="steps">${['Type Email','Analyze','Explain Signals','View Results'].map((x,i)=>`<div class="step"><b>${i+1}</b><div style="margin-top:8px">${x}</div></div>`).join('')}</div></div><section class="home-performance"><div class="section-label">Model Performance</div><div class="home-metrics">${[['Precision',96.59],['Recall',96.97],['Accuracy',97.12],['F1 Score',96.78]].map(([label,value])=>`<div class="card performance-card home-metric"><div class="performance-label">${label}</div><div class="performance-value">${value.toFixed(2)}%</div></div>`).join('')}</div></section></div>`}
function detection(){let e=state.email||{};return `<div class="wrap"><div class="page-title"><div><h2>Analyze Email</h2></div></div><div class="detect-grid"><section class="panel"><div class="panel-head"><h3>Email Input</h3><button class="secondary clear-btn" onclick="clearEmail()">Clear</button></div><div class="input-field"><label class="muted">Sender</label><input id="sender" placeholder="Enter sender email" value="${esc(e.sender)}"></div><div class="input-field body-field"><label class="muted">Email Subject</label><input id="subject" placeholder="Enter email subject" value="${esc(e.subject)}"></div><div class="input-field body-field"><label class="muted">Email Body</label><textarea id="body" placeholder="Paste or type the email body here...">${esc(e.body)}</textarea></div><button class="detect" type="button" onclick="detect()">ANALYZE EMAIL</button></section><section class="panel">${state.result?resultView():`<div class="ready"><div><div style="font-size:50px">◎</div><h3>Ready to Analyze</h3><p>Enter an email subject and body to begin analysis.</p></div></div>`}</section></div></div>`}
function resultView(){let r=state.result,ham=r.prediction==='HAM';if(ham){return `<div class="result-top"><div><div class="eyebrow">Detection Result</div><div class="badge ham">HAM</div><div class="muted" style="margin-top:6px">Not Spam</div><div class="risk" style="margin-top:14px">Domain: ${esc(r.domain_category)}</div></div></div><div class="card" style="margin-top:14px"><h3>Why is this not spam?</h3>${r.reasons.map(x=>`<div class="pill" style="display:block;margin:8px 0">${esc(x)}</div>`).join('')}</div>`}return `<div class="result-top"><div><div class="eyebrow">Detection Result</div><div class="badge spam">SPAM</div></div><div class="confidence"><strong>${r.spam_risk}%</strong></div></div><div class="risk-level" style="margin-top:10px"><b>Risk Level: ${esc(r.risk_level)}</b></div><div class="card" style="margin-top:14px"><h3>Why is this spam?</h3>${r.reasons.map(x=>`<div class="pill" style="display:block;margin:8px 0">${esc(x)}</div>`).join('')}</div><div class="analysis-grid" style="margin-top:14px">${score('URL Analysis','',r.url_analysis.suspicious_urls?Math.min(100,r.url_analysis.suspicious_urls/r.url_analysis.urls_detected*100):0)}${score('Context Analysis','',r.context_analysis.score)}${senderMetric(r.sender_analysis)}</div>`}
function senderMetric(s){let label=s.domain?s.domain:'Sender';let n=Math.min(100,Math.max(0,s.score||0));return `<div class="card metric"><h4>Sender Analysis</h4><div class="muted">${esc(label)}</div><div class="num">${n}%</div><div class="bar"><i style="width:${n}%"></i></div>${s.indicators?.length?`<div class="muted">${esc(s.indicators[0])}</div>`:`<div class="muted">Sender indicators based on available information.</div>`}</div>`}
function score(t,icon,v){return `<div class="card metric"><h4>${t}</h4><div class="num">${Number(v).toFixed(0)}%</div><div class="bar"><i style="width:${Math.min(100,v)}%"></i></div></div>`}
async function history(){state.history=await api('/api/history');return `<div class="wrap"><div class="page-title"><div><div class="eyebrow">Audit trail</div><h2>History</h2></div></div><div class="filters"><input id="hs" placeholder="Search sender or subject" oninput="filterHistory()" style="max-width:340px"><button class="secondary" onclick="filterRows('SPAM')">Spam</button><button class="secondary" onclick="filterRows('HAM')">Ham</button><button class="secondary" onclick="render()">All</button></div><div class="panel"><div id="historyTable">${historyRows(state.history)}</div></div></div>`}
function historyRows(rows){if(!rows.length)return '<div class="empty">No detections yet.</div>';return `<table class="history-table"><thead><tr><th>#</th><th>Date</th><th>Subject</th><th>Result</th><th>Spam Risk</th><th>Confidence</th><th></th></tr></thead><tbody>${rows.map((x,i)=>`<tr><td>${i+1}</td><td>${new Date(x.created_at).toLocaleString()}</td><td>${esc(x.subject)}</td><td class="${x.classification==='SPAM'?'spam':'ham'}"><b>${x.classification}</b></td><td>${x.spam_risk}%</td><td>${x.confidence}%</td><td><button class="secondary" onclick="showDetail('${x.id}')">View</button> <button class="secondary" onclick="del('${x.id}')">Delete</button></td></tr>`).join('')}</tbody></table>`}
const MODEL_METRICS={precision:96.59,recall:96.97,accuracy:97.12,f1:96.78};
let senderModal=null;
function dashboard(){let d=state.dash||{total:0,spam:0,not_spam:0,domains:[]};return `<div class="wrap"><div class="page-title"><div><h2>Dashboard</h2></div></div><div class="stats three-stats">${[['Total Emails Analysed',d.total],['Spam Emails',d.spam],['HAM Emails',d.not_spam]].map(x=>`<div class="card stat"><div class="muted">${x[0]}</div><strong>${x[1]}</strong></div>`).join('')}</div><section class="sender-analysis-section"><div class="section-label">Sender Analysis</div><div class="sender-grid">${(d.domains||[]).length?(d.domains.map((x,i)=>senderCard(x,i)).join('')):`<div class="card empty">No sender/domain analysis data yet.</div>`}</div></section></div>`}
function senderCard(x,i){return `<div class="card sender-card"><div class="sender-card-head"><div><h3>${esc(x.domain)}</h3><div class="muted">Total Emails: ${x.spam+x.ham}</div></div><button class="visualise-btn" type="button" onclick="visualiseSender(${i})">Visualise</button></div><div class="sender-counts"><span><b class="spam">Spam</b> ${x.spam}</span><span><b class="ham">HAM</b> ${x.ham}</span></div></div>`}
function visualiseSender(i){let d=state.dash||{};let x=(d.domains||[])[i];if(!x)return;openSenderModal(x)}
function openSenderModal(x){senderModal={x};renderModal()}
function closeSenderModal(){senderModal=null;renderModal()}
function renderModal(){
  let old=document.getElementById('senderModal');
  if(old)old.remove();
  if(!senderModal)return;

  const x=senderModal.x;
  const spam=Number(x.spam)||0;
  const ham=Number(x.ham)||0;
  const total=spam+ham;
  const spamPct=total?(spam/total)*100:0;
  const hamPct=total?(ham/total)*100:0;

  const maxValue=Math.max(spam,ham,1);
  const chartW=460, chartH=250, left=58, right=18, top=24, bottom=52;
  const plotW=chartW-left-right, plotH=chartH-top-bottom;
  const barW=90, gap=85;
  const spamX=left+(plotW-(barW*2+gap))/2;
  const hamX=spamX+barW+gap;
  const y=v=>top+plotH-(v/maxValue)*plotH;
  const ticks=[0,0.25,0.5,0.75,1].map(r=>Math.round(maxValue*r));
  const grid=ticks.map(v=>{const yy=y(v);return `<line x1="${left}" y1="${yy}" x2="${chartW-right}" y2="${yy}" class="sender-chart-grid-line"/><text x="${left-9}" y="${yy+4}" text-anchor="end" class="sender-chart-axis-text">${v}</text>`}).join('');
  const spamH=(spam/maxValue)*plotH;
  const hamH=(ham/maxValue)*plotH;

  const modal=document.createElement('div');
  modal.id='senderModal';
  modal.className='modal-backdrop';
  modal.innerHTML=`<div class="modal-card sender-viz-modal" role="dialog" aria-modal="true" aria-label="Sender visualization">
    <button class="modal-close" onclick="closeSenderModal()" aria-label="Close">×</button>
    <div class="eyebrow">Sender Analysis</div>
    <h3>Sender: ${esc(x.domain)}</h3>
    <div class="modal-title">Spam vs Ham</div>
    <div class="sender-bar-chart-wrap">
      <svg class="sender-bar-chart" viewBox="0 0 ${chartW} ${chartH}" role="img" aria-label="Bar graph for ${esc(x.domain)} showing ${spam} spam emails and ${ham} HAM emails">
        ${grid}
        <line x1="${left}" y1="${top+plotH}" x2="${chartW-right}" y2="${top+plotH}" class="sender-chart-axis-line"/>
        <line x1="${left}" y1="${top}" x2="${left}" y2="${top+plotH}" class="sender-chart-axis-line"/>
        <rect x="${spamX}" y="${y(spam)}" width="${barW}" height="${spamH}" rx="7" class="sender-bar-spam"/>
        <rect x="${hamX}" y="${y(ham)}" width="${barW}" height="${hamH}" rx="7" class="sender-bar-ham"/>
        <text x="${spamX+barW/2}" y="${Math.max(top+15,y(spam)-8)}" text-anchor="middle" class="sender-chart-value">${spam}</text>
        <text x="${hamX+barW/2}" y="${Math.max(top+15,y(ham)-8)}" text-anchor="middle" class="sender-chart-value">${ham}</text>
        <text x="${spamX+barW/2}" y="${chartH-25}" text-anchor="middle" class="sender-chart-label">Spam</text>
        <text x="${hamX+barW/2}" y="${chartH-25}" text-anchor="middle" class="sender-chart-label">HAM</text>
        <text x="18" y="${top+plotH/2}" text-anchor="middle" transform="rotate(-90 18 ${top+plotH/2})" class="sender-chart-axis-title">Email Count</text>
        <text x="${chartW/2}" y="${chartH-4}" text-anchor="middle" class="sender-chart-axis-title">Classification</text>
      </svg>
    </div>
    <div class="sender-percentages">
      <div><span class="spam">Spam Percentage</span><strong>${spamPct.toFixed(2)}%</strong></div>
      <div><span class="ham">Ham Percentage</span><strong>${hamPct.toFixed(2)}%</strong></div>
    </div>
  </div>`;
  modal.addEventListener('click',e=>{if(e.target===modal)closeSenderModal()});
  document.body.appendChild(modal);
}

function toggleMenu(){state.menuOpen=!state.menuOpen;render()}
function closeMenu(){if(state.menuOpen){state.menuOpen=false;render()}}
async function render(){app.innerHTML=nav()+(state.page==='home'?about():state.page==='detection'?detection():state.page==='history'?await history():await dashboard());}

async function go(p){state.page=p;state.menuOpen=false;if(p==='dashboard')state.dash=await api('/api/dashboard');await render()}
async function detect(){let e={sender:document.getElementById('sender').value,recipient:'',subject:document.getElementById('subject').value,body:document.getElementById('body').value};if(!e.sender.trim()&&!e.subject.trim()&&!e.body.trim()){toast('Enter email information first');return}try{let d=await api('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(e)});state.email=e;state.result=d.result;toast('Detection saved to History and Dashboard');await render()}catch(err){toast(err.message)}}
function clearEmail(){state.email={sender:'',recipient:'',subject:'',body:''};state.result=null;render()}
function filterRows(type){let rows=state.history.filter(x=>x.classification===type);document.getElementById('historyTable').innerHTML=historyRows(rows)}function filterHistory(){let q=document.getElementById('hs').value.toLowerCase();document.getElementById('historyTable').innerHTML=historyRows(state.history.filter(x=>(x.sender+' '+x.subject+' '+x.body).toLowerCase().includes(q)))}
function showDetail(id){let x=state.history.find(a=>a.id===id);if(!x)return;state.email={sender:x.sender,recipient:x.recipient,subject:x.subject,body:x.body};state.result=x.features;state.page='detection';render()}
async function del(id){await api('/api/history/'+id,{method:'DELETE'});state.history=await api('/api/history');render()}
function toast(t){let x=document.createElement('div');x.className='toast';x.textContent=t;document.body.appendChild(x);setTimeout(()=>x.remove(),2400)}
go('home');
