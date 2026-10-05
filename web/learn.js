const esc = value => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const main = document.querySelector('#lesson-main');
const drafts = new Map();
let lessons=[], current, mode='textbook', allAnswers=false;
const scope = l => `${l.subjectLabel} / 小学校 ${l.education.grades.join('・')}年`;
const refURL = ref => '/structure?'+new URLSearchParams({release:ref.release,entity:ref.id});
const table = t => `<div class="lesson-table"><table><thead><tr>${t.columns.map(c=>`<th scope="col">${esc(c)}</th>`).join('')}</tr></thead><tbody>${t.rows.map(row=>`<tr>${row.map((c,i)=>`<${i===0?'th scope="row"':'td'}>${esc(c)}</${i===0?'th':'td'}>`).join('')}</tr>`).join('')}</tbody></table></div>`;
const paragraphs = texts => texts.map(p=>`<p>${esc(p)}</p>`).join('');
function pendulum() {
  return `<figure class="pendulum-diagram"><svg viewBox="0 0 440 220" role="img" aria-labelledby="pendulum-title pendulum-desc"><title id="pendulum-title">振り子の長さと1往復</title><desc id="pendulum-desc">振り子の長さは支点からおもりの中心まで。1往復は左の端から右の端へ行き、左の端へ戻る動き。</desc><path d="M70 25H240" class="support"/><circle cx="155" cy="25" r="4"/><path d="M155 25V161" class="string"/><circle cx="155" cy="161" r="13" class="bob"/><path d="M155 25L106 153M155 25L204 153" class="ghost-string"/><circle cx="106" cy="153" r="13" class="ghost-bob"/><circle cx="204" cy="153" r="13" class="ghost-bob"/><path d="M87 186Q155 213 223 186" class="swing"/><path d="M90 194L87 186L96 185M214 185L223 186L220 194" class="swing"/><path d="M260 25V161M255 25H265M255 161H265" class="length"/><text x="278" y="96">振り子の長さ</text><text x="70" y="216">左 → 右 → 左で1往復</text><text x="167" y="19">支点</text></svg><figcaption>長さは、支点からおもりの中心まで。</figcaption></figure>`;
}
function material(m) {
  return `<section class="lesson-material"><div class="eyebrow">${m.kind==='passage'?'READING':'MATERIAL'}</div><h3>${esc(m.title)}</h3>${m.paragraphs?`<div class="passage">${paragraphs(m.paragraphs)}</div>`:''}${m.diagram==='pendulum'?pendulum():''}${m.kind==='records'?`<ol class="record-grid">${m.rows.map((r,i)=>`<li><span class="record-number">${i+1}</span><span>${esc(r[0])}<br><strong>${esc(r[1])}</strong></span></li>`).join('')}</ol>`:m.rows?table(m):''}<p class="material-caption">${esc(m.caption)}</p></section>`;
}
function answerText(q) {
  if(q.kind==='choice') return q.options.find(o=>o.value===q.answer).label;
  if(q.kind==='order') return q.answer.map((n,i)=>({n,text:q.items[i]})).sort((a,b)=>a.n-b.n).map(x=>x.text).join(' → ');
  return String(q.answer)+(q.unit?' '+q.unit:'');
}
function questionsHTML(l) {
  return `<section class="practice"><div class="section-label"><span class="eyebrow">PRACTICE / ${l.questions.length} QUESTIONS</span><button class="subtle" id="toggle-answers" aria-pressed="${allAnswers}">${allAnswers?'解答例を閉じる':'解答例をすべて表示'}</button></div><h3>${mode==='textbook'?'確かめてみよう':'練習問題'}</h3>${l.questions.map((q,i)=>`<article class="exercise" id="exercise-${q.id}"><div class="question-heading"><span class="question-number">${String(i+1).padStart(2,'0')}</span><h4>${esc(q.prompt)}</h4></div><form data-question="${q.id}">${q.kind==='choice'?`<fieldset><legend class="sr-only">${esc(q.prompt)}</legend>${q.options.map(o=>`<label class="choice-option"><input type="radio" name="answer" value="${esc(o.value)}"><span>${esc(o.label)}</span></label>`).join('')}</fieldset>`:q.kind==='order'?`<div class="order-items">${q.items.map((item,j)=>`<label><span>${esc(item)}</span><select name="step-${j}" aria-label="${esc(item)}の順番"><option value="">—</option>${q.items.map((_,n)=>`<option value="${n+1}">${n+1}</option>`).join('')}</select></label>`).join('')}</div>`:q.kind==='number'?`<label class="number-answer">あなたの答え <input name="answer" type="text" inputmode="decimal" autocomplete="off" aria-label="問題${i+1}の数値の答え">${esc(q.unit)}</label>`:`<label class="written-answer">あなたの考え<textarea name="answer" rows="3" placeholder="文章のことばや資料を手掛かりに書いてみよう"></textarea></label>`}<button type="submit">${q.kind==='text'?'解答例と観点を見る':'答えを確かめる'}</button><p class="answer-feedback" role="status"></p></form><details class="answer-key" ${allAnswers||drafts.get(q.id)?.open?'open':''}><summary>${q.kind==='text'?'解答例・解説・確かめる観点':'解答・解説'}</summary><p class="model-answer">${esc(answerText(q))}</p><p>${esc(q.explanation)}</p>${q.criteria?`<p class="small-label">確かめる観点</p><ul>${q.criteria.map(c=>`<li>${esc(c)}</li>`).join('')}</ul>`:''}</details></article>`).join('')}</section>`;
}
function values(form,q) {
  if(q.kind==='order')return q.items.map((_,i)=>form.elements['step-'+i].value);
  return q.kind==='choice'?(form.querySelector('[name=answer]:checked')?.value||''):form.elements.answer.value;
}
function assess(q,value) {
  if(q.kind==='text')return null;
  if(q.kind==='order')return value.every((v,i)=>Number(v)===q.answer[i]);
  if(q.kind==='choice')return value===q.answer;
  const normalized=value.normalize('NFKC').trim();
  return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized) && Number(normalized)===q.answer;
}
function bindQuestions(l) {
  for(const q of l.questions) {
    const article=document.getElementById('exercise-'+q.id), form=article.querySelector('form'), detail=article.querySelector('details'), feedback=article.querySelector('[role=status]');
    const saved=drafts.get(q.id);
    if(saved) {
      if(q.kind==='order')q.items.forEach((_,i)=>form.elements['step-'+i].value=saved.value?.[i]||'');
      else if(q.kind==='choice') {for(const radio of form.querySelectorAll('input'))radio.checked=radio.value===saved.value;}
      else form.elements.answer.value=saved.value||'';
      feedback.textContent=saved.message||'';feedback.className='answer-feedback '+(saved.result===true?'correct':saved.result===false?'retry':'');
    }
    form.oninput=()=>{
      drafts.set(q.id,{...drafts.get(q.id),value:values(form,q),message:'',result:null});
      feedback.textContent='';feedback.className='answer-feedback';
    };
    form.onsubmit=event=>{
      event.preventDefault();const value=values(form,q);
      if(q.kind!=='text' && (Array.isArray(value)?value.some(v=>!v):!value.trim())) {
        feedback.textContent=q.kind==='number'?'答えを入力してから確かめましょう。':'答えを選んでから確かめましょう。';return;
      }
      const result=assess(q,value), message=q.kind==='text'?'解答例と比べて、自分の考えを確かめましょう。':result?'合っています。解説で考え方も確かめましょう。':'もう一度考えてみましょう。解説を手掛かりにできます。';
      feedback.textContent=message;feedback.className='answer-feedback '+(result===true?'correct':result===false?'retry':'');
      drafts.set(q.id,{value,message,result,open:true});detail.open=true;
    };
    detail.ontoggle=()=>{if(document.contains(detail))drafts.set(q.id,{...drafts.get(q.id),value:values(form,q),open:detail.open});};
  }
  document.querySelector('#toggle-answers').onclick=()=>{
    allAnswers=!allAnswers;
    for(const q of l.questions)drafts.set(q.id,{...drafts.get(q.id),open:allAnswers});
    render();document.querySelector('#toggle-answers').focus();
  };
}
function render() {
  const l=current;
  document.title='Curricula — '+l.title;
  document.querySelector('#sidebar').innerHTML=lessons.map((unit,i)=>`<a class="${unit.id===l.id?'active':''}" ${unit.id===l.id?'aria-current="page"':''} href="/learn?${new URLSearchParams({unit:unit.slug,mode})}"><span class="lesson-nav-meta">${String(i+1).padStart(2,'0')} / ${esc(scope(unit))}</span><span>${esc(unit.title)}</span></a>`).join('');
  main.innerHTML=`<div class="lesson-toolbar"><div role="group" aria-label="教材の表示"><button type="button" data-mode="textbook" aria-pressed="${mode==='textbook'}">教科書</button><button type="button" data-mode="workbook" aria-pressed="${mode==='workbook'}">問題集</button></div><button id="print-lesson" class="subtle">この単元を印刷</button></div><div class="lesson-heading"><div class="eyebrow">${esc(l.kicker)}</div><h2>${esc(l.title)}</h2><p>${esc(l.summary)}</p><div class="lesson-meta"><span>${esc(scope(l))}</span><span>目安 ${l.minutes}分</span><span>${esc(l.provenance.label)}</span></div></div><section class="lesson-goal"><span class="small-label">この単元でできるようになること</span><ul>${l.goals.map(g=>`<li>${esc(g.label)}</li>`).join('')}</ul></section>${mode==='textbook'?l.explanations.map(s=>`<section class="lesson-explanation"><h3>${esc(s.title)}</h3>${paragraphs(s.paragraphs)}</section>`).join(''):''}${material(l.material)}${mode==='textbook'?`<section class="worked-example"><span class="eyebrow">WORKED EXAMPLE</span><h3>${esc(l.workedExample.title)}</h3>${l.workedExample.prompt?`<p>${esc(l.workedExample.prompt)}</p>`:''}${l.workedExample.table?table(l.workedExample.table):''}<p class="model-answer">${esc(l.workedExample.answer)}</p><p>${esc(l.workedExample.explanation)}</p></section>`:''}${questionsHTML(l)}<details class="curriculum-links"><summary>この教材の目標と指導要領</summary><p>教材の本文・問題はCurriculaのオリジナルです。学ぶ目標は、次の版の項目に結び付けています。</p><ul>${l.goals.map(g=>`<li><a href="${esc(refURL(g))}">${esc(g.label)}</a></li>`).join('')}</ul>${l.sourceItems.map(s=>`<blockquote><p>${esc(s.text)}</p><cite><a href="${esc(refURL(s))}">${esc(s.code)} · 学習指導要領の原文を見る</a></cite></blockquote>`).join('')}</details><a class="back-to-goals" href="/read">学ぶ対象と目標に戻る →</a>`;
  main.dataset.mode=mode;
  for(const button of main.querySelectorAll('button[data-mode]'))button.onclick=()=>{
    mode=button.dataset.mode;history.replaceState(null,'','/learn?'+new URLSearchParams({unit:l.slug,mode}));render();
  };
  document.querySelector('#print-lesson').onclick=()=>window.print();
  bindQuestions(l);
}
async function start() {
  try {
    const response=await fetch('/api/preview/lessons');if(!response.ok)throw new Error('教材を取得できません。');
    const body=await response.json();lessons=body.lessons;
    const params=new URLSearchParams(location.search);current=lessons.find(l=>l.slug===params.get('unit'))||lessons[0];
    mode=params.get('mode')==='workbook'?'workbook':'textbook';render();
    document.querySelector('#sidebar').onclick=event=>{
      const link=event.target.closest('a');if(!link || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button)return;
      event.preventDefault();current=lessons.find(l=>l.slug===new URL(link.href).searchParams.get('unit'));allAnswers=false;
      history.pushState(null,'',link.href);render();main.scrollIntoView({behavior:'smooth',block:'start'});
    };
    window.onpopstate=()=>{const p=new URLSearchParams(location.search);current=lessons.find(l=>l.slug===p.get('unit'))||lessons[0];mode=p.get('mode')==='workbook'?'workbook':'textbook';allAnswers=false;render();};
  } catch(error) {main.innerHTML=`<p class="status error">${esc(error.message)}</p>`;}
}
start();
