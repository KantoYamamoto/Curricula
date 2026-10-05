const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const original = d => d.entities.filter(e=>e.kind==='frameworkItem' && e.provenance.origin==='original');
const code = e => e.externalIDs['mext:course-of-study'] || e.sourceLocator;
function picker(id,label,multiple=false,selected='') {
  return `<label class="editor-field">${esc(label)}<input type="search" data-source-search="${id}" placeholder="原文のコードや語句で絞り込む"><select id="${id}" ${multiple?'multiple size="5"':'required'} data-selected="${esc(selected)}"></select></label>`;
}
function bindPicker(ctx,id,multiple) {
  const select=document.getElementById(id), input=document.querySelector(`[data-source-search="${id}"]`);
  const items=original(ctx.detail.dataset);
  const initial=ctx.detail.dataset.aliases[select.dataset.selected] || select.dataset.selected;
  const selected=new Set(initial?[initial]:[]);
  function draw() {
    const q=input.value.trim();
    const matches=items.filter(e=>!q || code(e).includes(q) || e.text.includes(q)).slice(0,40);
    for(const e of items) if(selected.has(e.id) && !matches.some(m=>m.id===e.id)) matches.unshift(e);
    select.innerHTML=`${multiple?'':'<option value="">適用範囲の原文を選ぶ</option>'}${matches.map(e=>`<option value="${esc(e.id)}" ${selected.has(e.id)?'selected':''}>${esc(code(e))} · ${esc(e.label)}</option>`).join('')}`;
  }
  input.addEventListener('input',draw);
  select.addEventListener('change',()=>{selected.clear();for(const o of select.selectedOptions)if(o.value)selected.add(o.value);});
  draw();
}
export function creationHTML(detail,source='') {
  const matters=detail.dataset.entities.filter(e=>e.kind==='subjectMatter'&&e.lifecycle==='active');
  return `<details class="creation" ${!matters.length?'open':''}><summary>学ぶ対象・目標を追加する</summary><form id="creation-form"><label class="editor-field">種類<select name="kind"><option value="subjectMatter">学ぶ対象</option><option value="goal">目標</option></select></label><label class="editor-field">見出し<input name="label" required maxlength="20000"></label><label class="editor-field">本文<textarea name="text" required rows="3" maxlength="20000"></textarea></label><label class="editor-field">条件・適用範囲（任意）<textarea name="conditions" rows="2" maxlength="20000"></textarea></label>${picker('creation-education','学年・教科の設定元となる原文',false,source)}<p class="meta" id="creation-scope"></p>${picker('creation-sources','本文の根拠とする原文（複数選択可）',true,source)}<p class="meta">原文は引用として保持し、この説明・目標の根拠に結び付けます。</p>${picker('creation-conditions','条件の根拠となる原文（任意・複数選択可）',true)}<div id="creation-goal" hidden><label class="editor-field">学ぶ対象（複数選択可）<select name="targetIDs" multiple size="4">${matters.map(e=>`<option value="${esc(e.id)}">${esc(e.label)}</option>`).join('')}</select></label><label class="editor-field">判定の観点・注釈（任意）<textarea name="annotations" rows="3" placeholder="複数の観点は空行で区切る" maxlength="20000"></textarea></label></div><label class="editor-field">作成・対応づけの理由<textarea name="reason" required rows="2" maxlength="4000"></textarea></label><button type="submit">追加して下書きに保存</button></form></details>`;
}
export function bindCreation(ctx) {
  const form=document.querySelector('#creation-form');if(!form)return;
  bindPicker(ctx,'creation-education',false);bindPicker(ctx,'creation-sources',true);bindPicker(ctx,'creation-conditions',true);
  const scope=()=>{
    const e=ctx.detail.dataset.entities.find(e=>e.id===document.querySelector('#creation-education').value);
    const taxons=new Map(ctx.detail.dataset.taxons.map(t=>[t.id,t.label]));
    document.querySelector('#creation-scope').textContent=e?.education.map(s=>`${s.stage==='elementary'?'小学校':s.stage==='lowerSecondary'?'中学校':s.stage} / ${s.grades.length?s.grades.join('・')+'年':'学年未指定'} / ${taxons.get(s.subjectID)}`).join('、') || '';
  };
  document.querySelector('#creation-education').addEventListener('change',scope);scope();
  form.elements.kind.addEventListener('change',()=>{document.querySelector('#creation-goal').hidden=form.elements.kind.value!=='goal';});
  form.addEventListener('input',ctx.dirty);
  form.addEventListener('submit',event=>{event.preventDefault();ctx.action(async()=>{
    const values=id=>[...document.getElementById(id).selectedOptions].map(o=>o.value).filter(Boolean);
    const payload={expectedHead:ctx.detail.draft.head_id,kind:form.elements.kind.value,label:form.elements.label.value,text:form.elements.text.value,conditions:form.elements.conditions.value,educationFrom:values('creation-education')[0],sourceItemIDs:values('creation-sources'),conditionItemIDs:values('creation-conditions'),targetIDs:form.elements.kind.value==='goal'?[...form.elements.targetIDs.selectedOptions].map(o=>o.value):[],annotations:form.elements.kind.value==='goal'?form.elements.annotations.value.split(/\n\s*\n/).map(s=>s.trim()).filter(Boolean):[],reason:form.elements.reason.value};
    const result=await ctx.api(`drafts/${ctx.detail.draft.id}/entities`,payload);
    ctx.updated(result,result.createdEntityID);ctx.message('新しい項目と根拠を下書きに保存しました。');
  });});
}
export function linkHTML() {
  return `<details class="creation"><summary>この項目に原文の根拠を追加する</summary><form id="source-link-form"><label class="editor-field">根拠を付ける箇所<select name="field"><option value="text">本文</option><option value="conditions">条件・適用範囲</option></select></label>${picker('link-sources','根拠とする原文（複数選択可）',true)}<label class="editor-field">結び付ける理由<textarea name="reason" required rows="2" maxlength="4000"></textarea></label><button type="submit">根拠を下書きに保存</button></form></details>`;
}
export function bindLink(ctx,entity) {
  const form=document.querySelector('#source-link-form');if(!form)return;
  bindPicker(ctx,'link-sources',true);form.addEventListener('input',ctx.dirty);
  form.addEventListener('submit',event=>{event.preventDefault();ctx.action(async()=>{
    const result=await ctx.api(`drafts/${ctx.detail.draft.id}/evidence`,{expectedHead:ctx.detail.draft.head_id,entityID:entity.id,field:form.elements.field.value,sourceItemIDs:[...document.querySelector('#link-sources').selectedOptions].map(o=>o.value),reason:form.elements.reason.value});ctx.updated(result,entity.id);ctx.message('原文の根拠を追加しました。');
  });});
}
export function workHTML() {
  return '<section class="publication"><h3>整理した範囲を進捗に記録する</h3><p class="meta">確認した原文と目標を選んで記録します。学年全体を終えていない場合は「整理中」になります。</p><div id="work-form-host">進捗を取得しています…</div></section>';
}
export async function bindWork(ctx) {
  const host=document.querySelector('#work-form-host');if(!host)return;
  try {
    const response=await fetch('/api/v1/coverage');if(!response.ok)throw new Error('作業台帳を取得できません。');
    const coverage=await response.json(),dataset=ctx.detail.dataset;
    const chunks=coverage.chunks.filter(c=>c.entityIDs.every(i=>dataset.entities.some(e=>e.id===i)));
    const goals=dataset.entities.filter(e=>e.kind==='goal'&&e.lifecycle==='active');
    const sourceIDs=new Set(dataset.evidence.filter(e=>goals.some(g=>g.id===e.target.id)&&e.field==='text').flatMap(e=>e.citations.map(c=>c.item?.id)).filter(Boolean));
    const first=chunks.find(c=>c.entityIDs.some(i=>sourceIDs.has(i))) || chunks[0];
    if(!first){host.textContent='この版には作業台帳の対象となる原文がありません。';return;}
    host.innerHTML=`<form id="work-form"><label class="editor-field">作業の区切り<select name="chunkID">${chunks.map(c=>`<option value="${esc(c.id)}" ${c.id===first.id?'selected':''}>${esc(c.label)}</option>`).join('')}</select></label><label class="editor-field">整理したまとまり<input name="label" required maxlength="4000" placeholder="例：読むこと"></label><label class="editor-field">確認した原文の枝<select name="branch"></select></label><button type="button" class="subtle" id="select-branch">この枝を確認済みに選ぶ</button><div id="work-originals" class="work-items"></div><fieldset id="work-goals"><legend>整理した目標</legend></fieldset><label class="editor-field">確認した内容<textarea name="note" required rows="2" maxlength="4000"></textarea></label><label class="editor-field">次に進める範囲<textarea name="next" required rows="2" maxlength="4000"></textarea></label><button type="submit">進捗を記録</button></form>`;
    const form=document.querySelector('#work-form');let chunk;
    function draw() {
      chunk=chunks.find(c=>c.id===form.elements.chunkID.value);
      const items=chunk.entityIDs.map(i=>dataset.entities.find(e=>e.id===i));
      const prior=chunk.goals;
      form.elements.label.value=prior.label||'';form.elements.note.value=prior.note||'';form.elements.next.value=coverage.next;
      form.elements.branch.innerHTML=items.map(e=>`<option value="${esc(e.id)}">${esc(e.label)}</option>`).join('');
      document.querySelector('#work-originals').innerHTML=items.map(e=>`<label class="check-label"><input type="checkbox" name="reviewed" value="${esc(e.id)}" ${prior.reviewedOriginalIDs.includes(e.id)?'checked':''}>${esc(code(e))} · ${esc(e.label)}</label>`).join('');
      document.querySelector('#work-goals').innerHTML='<legend>整理した目標</legend>'+goals.filter(g=>dataset.evidence.some(e=>e.target.id===g.id&&e.field==='text'&&e.citations.some(c=>chunk.entityIDs.includes(c.item?.id)))).map(g=>`<label class="check-label"><input type="checkbox" name="goal" value="${esc(g.id)}" ${prior.goalIDs.includes(g.id)?'checked':''}>${esc(g.label)}</label>`).join('');
    }
    form.elements.chunkID.addEventListener('change',draw);draw();
    document.querySelector('#select-branch').onclick=()=>{
      const ids=new Set([form.elements.branch.value]);for(let depth=0;depth<64;depth++){const before=ids.size;for(const e of dataset.entities)if(ids.has(e.parentID))ids.add(e.id);if(ids.size===before)break;}
      form.querySelectorAll('[name=reviewed]').forEach(box=>{if(ids.has(box.value))box.checked=true;});ctx.dirty();
    };
    form.addEventListener('input',ctx.dirty);
    form.onsubmit=event=>{event.preventDefault();ctx.action(async()=>{
      const selected=name=>[...form.querySelectorAll(`[name=${name}]:checked`)].map(e=>e.value);
      const goalIDs=selected('goal');
      await ctx.api('work',{expectedWorkID:chunk.goals.reviewID||null,chunkID:chunk.id,release:ctx.detail.draft.published_release,label:form.elements.label.value,note:form.elements.note.value,next:form.elements.next.value,reviewedOriginalIDs:selected('reviewed'),goalIDs,annotationIDs:dataset.annotations.filter(a=>goalIDs.includes(a.goal.id)).map(a=>a.id)});
      ctx.updated(ctx.detail);ctx.message('整理済みの範囲を進捗に記録しました。');
    });};
  } catch(error) { host.textContent=error.message; }
}
