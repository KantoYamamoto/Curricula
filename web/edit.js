const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const params = new URLSearchParams(location.search);
let token, detail, busy = false, dirty = false;
const errors = {
  edit_conflict:'別のタブで下書きが更新されました。入力を控えてから最新の下書きを読み込んでください。',
  draft_already_published:'この下書きは版として保存済みです。編集を続けるには、その版から新しい下書きを作ってください。',
  reason_required:'変更・確認の理由を記入してください。', title_required:'下書きの名前を記入してください。',
  no_changes:'文言の変更、注釈の追加、または未確認の関連の引き継ぎを指定してください。',
  validation_failed:'確認が必要な項目があります。', review_required:'この編集版の差分を確認して、確認記録を保存してください。',
  release_exists:'そのデータ版名は使用済みです。別の名前を指定してください。',
  invalid_release_name:'版名には英小文字から始まる英数字・ハイフン・ピリオドを使ってください。',
  local_session_required:'編集セッションが切れました。再読み込みしてください。',
  database_busy:'保存処理が混み合っています。少し待ってから再試行してください。',
  emptyEntity:'見出しと本文を記入してください。'
};
async function api(path, payload) {
  const response = await fetch('/api/edit/' + path, payload === undefined ? {} : {
    method:'POST', headers:{'Content-Type':'application/json','X-Curricula-Token':token}, body:JSON.stringify(payload)
  });
  const body = await response.json();
  if (!response.ok) {
    const error = new Error(errors[body.error?.code] || `保存・取得に失敗しました (${response.status}: ${body.error?.code || 'unknown'})`);
    error.issues = body.error?.issues; throw error;
  }
  return body;
}
function issueHTML(issues) {
  if (!issues.length) return '<p class="meta">参照・版・データ構造の検証を通過しています。</p>';
  const labels = new Map([...detail.dataset.entities, ...detail.dataset.annotations].map(r=>[r.id,r.label || '判定の観点']));
  for (const e of detail.dataset.evidence) labels.set(e.id,'根拠の結び付け');
  return `<div class="notice"><strong>新しい版にまとめる前に確認が必要です（${issues.length}件）</strong><ul>${issues.map(i=>`<li>${esc(labels.get(i.path)||i.path)}：${esc(i.code==='staleRevision'?'以前の編集版を参照しています。該当項目を開き、引き継ぐ内容を確認してください。':errors[i.code]||i.message)}</li>`).join('')}</ul></div>`;
}
function message(text, isError=false) {
  $('#message').className = `status ${isError?'error':''}`;
  $('#message').textContent = text;
  $('#message').hidden = false;
}
async function action(fn) {
  if (busy) return;
  busy = true;
  const states = [...document.querySelectorAll('button')].map(b=>[b,b.disabled]);
  states.forEach(([b])=>b.disabled=true);
  try { await fn(); }
  catch(error) { message(error.message,true); }
  finally {
    busy = false;
    states.forEach(([b,disabled])=>{if(b.isConnected)b.disabled=disabled;});
  }
}
function refLink(id, label, release=detail.base.release) {
  return `<a href="${esc('/structure?'+new URLSearchParams({release,entity:id}))}" target="_blank" rel="noopener">${esc(label)}</a>`;
}
function difference(before, after, label) {
  if (before === after) return '';
  return `<div class="edit-diff"><h4>${esc(label)}</h4><div><span class="small-label">元の版</span><p>${esc(before || '（記載なし）')}</p></div><div><span class="small-label">下書き</span><p>${esc(after || '（記載なし）')}</p></div></div>`;
}
function diffHTML() {
  const old = new Map([...detail.base.entities,...detail.base.annotations].map(r=>[r.id,r]));
  return [...detail.dataset.entities,...detail.dataset.annotations].map(r=>{
    const b=old.get(r.id);
    if (b?.revisionID===r.revisionID) return '';
    return `<article class="card"><h3>${esc(r.label || '判定の観点')}</h3>${['label','text','conditions'].map(k=>difference(b?.[k],r[k],{label:'見出し',text:'本文・観点',conditions:'条件'}[k])).join('')}${b && ['label','text','conditions'].every(k=>b[k]===r[k])?'<p class="meta">目標との関連を確認し、新しい編集版へ引き継ぎました。</p>':''}</article>`;
  }).join('') || '<p class="meta">本文・観点の変更はまだありません。</p>';
}
function renderDraft() {
  dirty=false;
  const {draft,dataset,issues,review}=detail;
  const entities=dataset.entities.filter(e=>e.kind!=='frameworkItem' && e.provenance.origin!=='original' && e.lifecycle==='active');
  const entity=entities.find(e=>e.id===params.get('entity')) || entities[0];
  const published=!!draft.published_id;
  const notes=dataset.annotations.filter(a=>a.goal.id===entity?.id).sort((a,b)=>a.position-b.position);
  const evidence=dataset.evidence.filter(e=>[entity?.id,...notes.map(a=>a.id)].includes(e.target.id));
  const fields={text:'本文・観点',conditions:'条件',education:'学年・教科',coverage:'対応範囲',expression:'前提経路'};
  const sources=new Map(dataset.sources.map(s=>[s.id,s]));
  $('#main').innerHTML=`<div class="eyebrow">${published?'SAVED RELEASE':'DRAFT'}</div><h2>${esc(draft.title)}</h2><p class="meta">元の版：${esc(detail.base.release)} · ${published?'版として保存済み':'下書きは閲覧用の版に反映されません'}</p><div id="message" role="status" hidden></div>${issueHTML(issues)}
  ${entity?`<label class="editor-field">編集する項目<select id="entity-choice">${entities.map(e=>`<option value="${esc(e.id)}" ${entity.id===e.id?'selected':''}>${esc(e.label)} · ${e.kind==='goal'?'目標':'学ぶ対象'}</option>`).join('')}</select></label>
  <form id="edit-form"><fieldset ${published?'disabled':''}><legend>文言と観点</legend><label class="editor-field">見出し<input name="label" required maxlength="20000" value="${esc(entity.label)}"></label><label class="editor-field">本文<textarea name="text" rows="4" required maxlength="20000">${esc(entity.text)}</textarea></label><label class="editor-field">条件・適用範囲<textarea name="conditions" rows="2" maxlength="20000">${esc(entity.conditions)}</textarea></label>
  ${notes.map((a,i)=>`<div class="note-editor"><label class="editor-field">観点 ${i+1}<textarea data-annotation="${esc(a.id)}" rows="2" required maxlength="20000">${esc(a.text)}</textarea></label><label class="check-label"><input type="checkbox" name="confirmAnnotation" value="${esc(a.id)}"> この観点を編集後の目標に引き継ぐ</label>${a.goal.revisionID!==entity.revisionID?'<span class="badge draft">以前の目標の版を参照中</span>':''}</div>`).join('')}
  ${entity.kind==='goal'?'<label class="editor-field">新しい観点・注釈（任意）<textarea name="newAnnotation" rows="2" maxlength="20000" placeholder="目標の達成を見取るための観点を自然言語で記入"></textarea></label>':''}
  ${evidence.length?`<details class="evidence-editor" open><summary>根拠の確認（${evidence.length}件）</summary><p class="meta">編集後にも同じ出典・箇所が根拠として使えるものを選択してください。</p>${evidence.map(e=>`<div class="evidence-row"><label class="check-label"><input type="checkbox" name="confirmEvidence" value="${esc(e.id)}"> ${esc(e.target.id===entity.id?fields[e.field]:'観点 '+(notes.findIndex(a=>a.id===e.target.id)+1))}の根拠を引き継ぐ</label><p>${esc(e.rationale)}</p>${e.citations.map(c=>`<p>${esc(sources.get(c.source.id)?.title)} · ${esc(c.locator)} ${c.item?refLink(c.item.id,'原典の該当項目'):''}</p>`).join('')}</div>`).join('')}</details>`:''}
  <label class="editor-field">変更・引き継ぎの理由<textarea name="reason" rows="2" required maxlength="4000"></textarea></label><button type="submit" data-busy>下書きに保存</button> <button type="button" class="subtle" id="reset-inputs" data-busy>入力を戻す</button></fieldset></form>`:'<p>編集できる独自項目がありません。</p>'}
  <details class="draft-differences" open><summary>元の版からの差分</summary>${diffHTML()}</details>
  <details><summary>編集履歴（${detail.events.length}件）</summary>${detail.events.map(e=>`<p>${esc(e.reason)}<br><span class="meta">${esc(new Date(e.created_at).toLocaleString('ja-JP'))} · ${esc(e.actor)}</span> <button type="button" class="subtle" data-history="${esc(e.after_id)}" data-busy>この時点の内容を見る</button></p>`).join('')}</details><div id="history-preview"></div>
  ${published?`<p class="status">${esc(draft.published_release)} として保存済みです。 ${refLink(entity?.id,'保存した版を読む',draft.published_release)} · <a href="${esc('/edit?'+new URLSearchParams({baseRelease:draft.published_release}))}">この版から下書きを作る</a> · <a href="${esc('/api/edit/releases/'+encodeURIComponent(draft.published_release)+'/export')}" download="${esc(draft.published_release)}.json">JSONを書き出す</a></p>`:`<section class="publication"><h3>差分を確認して版にまとめる</h3>${review?'<p class="badge">この編集版の確認記録があります</p>':'<p class="meta">差分・注釈・根拠を確認し、その内容を記録してください。保存後に編集すると確認記録は再取得が必要です。</p>'}<form id="review-form"><label class="editor-field">確認した内容<textarea name="note" required rows="2" maxlength="4000"></textarea></label><button type="submit" data-busy ${issues.length?'disabled':''}>確認記録を保存</button></form><form id="publish-form"><label class="editor-field">新しいデータ版名<input name="release" required pattern="[a-z][a-z0-9.\\-]{0,79}" placeholder="local-0.3.0"></label><button type="submit" ${issues.length||!review?'disabled':''}>新しい版を保存</button></form></section>`}`;
  $('#entity-choice')?.addEventListener('change', e=>{
    if(dirty) { e.target.value=entity.id; message('編集中の内容を保存してから項目を切り替えてください。',true); return; }
    params.set('entity',e.target.value); history.replaceState(null,'','/edit?'+params); renderDraft();
  });
  $('#reset-inputs')?.addEventListener('click',()=>{renderDraft();message('入力を保存済みの内容に戻しました。');});
  $('#edit-form')?.addEventListener('input',()=>{dirty=true;});
  $('#edit-form')?.addEventListener('submit', e=>{e.preventDefault(); action(async()=>{
    const form=e.target;
    const payload={expectedHead:draft.head_id,entityID:entity.id,entity:Object.fromEntries(['label','text','conditions'].map(k=>[k,form.elements[k].value])),
      annotations:Object.fromEntries([...form.querySelectorAll('[data-annotation]')].map(n=>[n.dataset.annotation,n.value])),newAnnotation:form.elements.newAnnotation?.value||'',
      confirmAnnotationIDs:[...form.querySelectorAll('[name=confirmAnnotation]:checked')].map(n=>n.value),
      confirmEvidenceIDs:[...form.querySelectorAll('[name=confirmEvidence]:checked')].map(n=>n.value),reason:form.elements.reason.value};
    detail=await api(`drafts/${draft.id}/save`,payload); renderDraft(); message('下書きを保存しました。');
  });});
  $('#review-form')?.addEventListener('submit',e=>{e.preventDefault();action(async()=>{
    if(dirty) throw new Error('編集中の内容を先に保存してください。');
    detail=await api(`drafts/${draft.id}/review`,{expectedHead:draft.head_id,note:e.target.elements.note.value});renderDraft();message('この編集版の確認記録を保存しました。');
  });});
  $('#publish-form')?.addEventListener('submit',e=>{e.preventDefault();action(async()=>{
    if(dirty) throw new Error('編集中の内容を先に保存してください。');
    const result=await api(`drafts/${draft.id}/publish`,{expectedHead:draft.head_id,release:e.target.elements.release.value});
    dirty=false;detail=await api(`drafts/${draft.id}`);renderDraft();
    $('#message').hidden=false;$('#message').className='status';$('#message').innerHTML=`${esc(result.release)} を保存しました。 ${refLink(entity.id,'新しい版を読む',result.release)} · <a href="${esc('/api/edit/releases/'+encodeURIComponent(result.release)+'/export')}" download="${esc(result.release)}.json">JSONを書き出す</a>`;
  });});
  document.querySelectorAll('[data-history]').forEach(b=>b.onclick=()=>action(async()=>{
    const snapshot=(await api(`drafts/${draft.id}/history/${b.dataset.history}`)).dataset;
    const r=snapshot.entities.find(e=>e.id===entity.id);
    $('#history-preview').innerHTML=`<div class="status"><h3>選択した時点の内容</h3>${r?`<strong>${esc(r.label)}</strong><p class="preserve-lines">${esc(r.text)}</p><p>${esc(r.conditions)}</p><ul>${snapshot.annotations.filter(a=>a.goal.id===r.id).map(a=>`<li>${esc(a.text)}</li>`).join('')}</ul>`:'この時点にはありません。'}</div>`;
  }));
}
async function start() {
  try {
    token=(await api('session')).token;
    const drafts=(await api('drafts')).drafts;
    $('#sidebar').innerHTML=drafts.map(d=>`<a class="${params.get('draft')===d.id?'active':''}" href="${esc('/edit?'+new URLSearchParams({draft:d.id}))}">${esc(d.title)}${d.published_id?' · 保存済み':''}</a>`).join('')||'<p class="meta">まだ下書きがありません。</p>';
    if(params.has('draft')) { detail=await api('drafts/'+encodeURIComponent(params.get('draft'))); renderDraft(); return; }
    const response=await fetch('/api/v1/releases');const releases=(await response.json()).releases.filter(r=>r.schemaVersion==='0.2.0');
    const base=params.get('baseRelease')||'cross-subject-0.2.0';
    $('#main').innerHTML=`<h2>下書きを作る</h2><div id="message" role="status" hidden></div><form id="create-form"><label class="editor-field">元にするデータ版<select name="baseRelease">${releases.map(r=>`<option ${r.release===base?'selected':''}>${esc(r.release)}</option>`).join('')}</select></label><label class="editor-field">下書きの名前<input name="title" required maxlength="200" placeholder="例：国語の目標と観点を見直す"></label><button type="submit" data-busy>下書きを作成</button></form>`;
    $('#create-form').onsubmit=e=>{e.preventDefault();action(async()=>{
      const result=await api('drafts',{baseRelease:e.target.elements.baseRelease.value,title:e.target.elements.title.value});
      location.href='/edit?'+new URLSearchParams({draft:result.draft.id,...(params.has('entity')?{entity:params.get('entity')}:{})});
    });};
  } catch(error) { $('#main').innerHTML=`<div class="status error"><h2>編集データを読み込めません</h2><p>${esc(error.message)}</p><a href="/edit">再読み込み</a></div>`; }
}
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
start();
