const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const kinds = {subjectMatter:'学ぶ対象', competency:'できること', goal:'目標', frameworkItem:'指導要領・要求'};
const origins = {original:'原文', editorial:'独自の説明', synthetic:'合成例'};
const strengths = {required:'この経路の必須前提', recommended:'推奨前提', alternative:'代替経路'};
const states = {uninvestigated:'前提の調査は未完了', scopedBoundary:'今回の調査境界に到達', investigated:'選定範囲の前提を調査済み'};
let release, schema, overview, generation = 0;
const entityLabels = new Map();
const view = location.pathname === '/structure' ? 'structure' : 'read';
function href(path, params = {}) { return `${path}?${new URLSearchParams({release, ...params})}`; }
function link(id, label = entityLabels.get(id) || id) { return `<a href="${esc(href('/structure',{entity:id}))}">${esc(label)}</a>`; }
async function json(url) {
  const response = await fetch(url);
  const body = await response.json();
  if (!response.ok) throw new Error(`取得失敗 (${response.status}): ${body.error?.code || 'unknown'}`);
  return body;
}
async function api(path) {
  const expectedRelease = release, expectedSchema = schema;
  const body = await json(`/api/v1/releases/${encodeURIComponent(expectedRelease)}/${path}`);
  if (body.release !== expectedRelease || body.schemaVersion !== expectedSchema) throw new Error('データ版が一致しません。再読み込みしてください。');
  if (schema === '0.2.0' && body.data?.kind && body.data.targetIDs) {
    body.data.annotations = body.annotations || [];
    body.data.evidence = body.evidence || [];
    body.data.prerequisites = body.prerequisites || [];
    body.data.changes = body.changes || [];
    body.data.criteria = [];
    body.data.provenance.sourceIDs = [...new Set(body.data.evidence.flatMap(e=>e.citations.map(c=>c.source.id)))];
  }
  return body;
}
const stages = {elementary:'小学校',lowerSecondary:'中学校',upperSecondary:'高校',higherEducation:'大学等',other:'その他'};
function educationText(scopes = []) {
  return scopes.map(s=>[stages[s.stage], s.gradeStatus==='specified'?`${s.grades.join('・')}年`:s.gradeStatus==='notApplicable'?'学年を適用しない':'学年未指定', overview.taxons?.find(t=>t.id===s.subjectID)?.label, overview.taxons?.find(t=>t.id===s.courseID)?.label].filter(Boolean).join(' / ')).join('、');
}
function evidenceHTML(e) {
  const fields = {text:'記述',conditions:'条件',education:'学年・教科',coverage:'対応範囲',expression:'前提経路'};
  return (e.evidence || []).map(item=>{
    const note = (e.annotations || []).find(a=>a.id===item.target.id);
    return `<p>${esc(note?`観点 ${note.position+1}`:fields[item.field])}の根拠：${item.citations.map(c=>`${c.item?link(c.item.id,'原典の該当項目'):''} <span>${esc(c.locator)}</span>`).join(' / ')}</p>`;
  }).join('');
}
function annotationsHTML(e) {
  if (!e.annotations) return '';
  if (!e.annotations.length && e.kind==='goal') return '<p class="meta">判定の観点はまだ記載されていません。</p>';
  return e.annotations.length ? `<span class="small-label">判定のための観点・注釈</span><ol>${e.annotations.map(a=>`<li>${esc(a.text)} <span class="meta">（${a.evaluationMode==='humanObservation'?'人による観察':'判定方法は未指定'}）</span></li>`).join('')}</ol>` : '';
}
function expressionHTML(expression) {
  return expression.op==='goal' ? link(expression.goalID) : `<div class="requirement"><strong>${expression.op==='allOf'?'すべて必要':'いずれか必要'}</strong><ul>${expression.operands.map(x=>`<li>${expressionHTML(x)}</li>`).join('')}</ul></div>`;
}
function prerequisiteHTML(e) {
  return (e.prerequisites?.length?'<h3>学習の前提</h3>':'') + (e.prerequisites || []).map(p=>`<div class="relation"><p>${p.strength==='required'?'必要な前提':'推奨する前提'} · ${esc(overview.contexts.find(c=>c.id===p.contextID)?.label)}</p>${expressionHTML(p.expression)}</div>`).join('');
}
function filterHTML(params) {
  const stage = params.get('stage') || '';
  return `<form id="scope-filter" class="scope-filter"><label>教科<select name="subjectId"><option value="">すべて</option>${(overview.taxons||[]).filter(t=>t.kind==='subject').map(t=>`<option value="${esc(t.id)}" ${params.get('subjectId')===t.id?'selected':''}>${esc(t.label)}</option>`).join('')}</select></label><label>学校段階<select name="stage"><option value="">すべて</option>${Object.entries(stages).map(([id,label])=>`<option value="${id}" ${stage===id?'selected':''}>${label}</option>`).join('')}</select></label><label>学年<input name="grade" type="number" min="1" ${stage==='elementary'?'max="6"':['lowerSecondary','upperSecondary'].includes(stage)?'max="3"':''} value="${esc(params.get('grade')||'')}" ${stage?'':'disabled'} placeholder="未指定"></label><button type="submit">絞り込む</button></form>`;
}
function details(e) {
  return `<details><summary>出典・識別子・編集上の根拠</summary><dl><dt>ID</dt><dd>${esc(e.id)}</dd>${e.revisionID?`<dt>編集版</dt><dd>${esc(e.revisionID)}</dd>`:''}<dt>根拠</dt><dd>${esc(e.provenance.rationale)}</dd>${e.sourceLocator ? `<dt>原典の位置</dt><dd>${esc(e.sourceLocator)}</dd>`:''}${Object.entries(e.externalIDs).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>${evidenceHTML(e)}<div class="sources" data-source-entity="${esc(e.id)}"></div></details>`;
}
function card(e) {
  return `<article class="card" id="${esc(e.id)}"><div class="badges"><span class="badge">${esc(kinds[e.kind])}</span><span class="badge">${esc(origins[e.provenance.origin])}</span></div><h3>${esc(e.label)}</h3>${e.education?.length?`<p class="meta">${esc(educationText(e.education))}</p>`:''}${e.lifecycle==='retired'?`<p class="notice">分割・統合前の目標です。後継：${e.successorIDs.map(id=>link(id)).join('、')}</p>`:''}${e.text !== e.label ? `<p>${esc(e.text)}</p>`:''}${e.conditions ? `<div class="conditions"><span class="small-label">条件・適用範囲</span>${esc(e.conditions)}</div>`:''}${e.criteria.length ? `<span class="small-label">達成を確認する観点</span><ul>${e.criteria.map(c=>`<li>${esc(c)}</li>`).join('')}</ul>`:''}${annotationsHTML(e)}${e.prerequisiteStatus ? `<p class="meta">${esc(states[e.prerequisiteStatus])}</p>`:''}<div class="links">${e.parentID?link(e.parentID,'上位の原典項目を読む →'):''}${e.targetIDs.map(id=>link(id)).join('')}${link(e.id,'対応・前提・出典をたどる →')}</div>${details(e)}</article>`;
}
async function sourceDetails(entities, token) {
  const ids = [...new Set(entities.flatMap(e=>e.provenance.sourceIDs))];
  const sources = await Promise.all(ids.map(id=>api(`sources/${encodeURIComponent(id)}`).then(x=>x.data)));
  if (token !== generation) return;
  for (const e of entities) {
    const node = document.querySelector(`[data-source-entity="${CSS.escape(e.id)}"]`);
    if (!node) continue;
    node.innerHTML = sources.filter(s=>e.provenance.sourceIDs.includes(s.id)).map(s=>{
      const url = s.url ? new URL(s.url) : null;
      const title = url && ['https:','http:'].includes(url.protocol) ? `<a href="${esc(url.href)}" target="_blank" rel="noreferrer">${esc(s.title)}</a>` : esc(s.title);
      return `<p>${title}<br>${esc([s.publisher,s.distributionVersion||s.edition,s.retrievedOn?'取得 '+s.retrievedOn:''].filter(Boolean).join(' · '))}${s.scope?`<br>${esc(s.scope)}`:''}${s.verification?`<br>${esc(s.verification)}`:''}${s.sha256?`<br>SHA-256: ${esc(s.sha256)}`:''}</p>`;
    }).join('') || '<p>外部原典の直接引用はありません。上記の編集上の根拠を参照してください。</p>';
  }
}
function tree(items, parent = undefined, visited = new Set()) {
  return `<ul class="tree">${items.filter(e=>e.parentID===parent).map(e=>{
    if (visited.has(e.id)) return '';
    const next = new Set(visited).add(e.id);
    return `<li>${link(e.id,e.label)}${items.some(c=>c.parentID===e.id)?tree(items,e.id,next):''}</li>`;
  }).join('')}</ul>`;
}
async function render() {
  const token = ++generation;
  $('#main').innerHTML = '<p class="status">データを取得しています…</p>';
  try {
    const params = new URLSearchParams(location.search);
    $('.brand').href = href('/read'); $('#read-nav').href = href('/read'); $('#structure-nav').href = href('/structure');
    $(`#${view}-nav`).setAttribute('aria-current','page');
    $('#version').textContent = `${release} / schema ${schema}`;
    let displayed = [];
    if (view === 'read') {
      const outlineID = params.get('outline') || overview.readingOutlines[0]?.id;
      if (!outlineID) throw new Error('このデータ版には目次がありません。');
      const outline = (await api(`reading-outlines/${encodeURIComponent(outlineID)}`)).data;
      let sectionID = params.get('section') || outline.sections[0].id;
      if (schema==='0.2.0' && params.has('section') && !outline.sections.some(s=>s.id===sectionID)) sectionID = (await api(`resolve/${encodeURIComponent(sectionID)}`)).data.id;
      const index = outline.sections.findIndex(s=>s.id===sectionID);
      if (index < 0) throw new Error('指定された節が存在しません。');
      const section = outline.sections[index];
      displayed = await Promise.all(section.entityIDs.map(id=>api(`entities/${encodeURIComponent(id)}`).then(x=>x.data)));
      const targets = [...new Set(displayed.flatMap(e=>[...e.targetIDs,...(e.successorIDs||[])]))];
      for (const target of await Promise.all(targets.map(id=>api(`entities/${encodeURIComponent(id)}`).then(x=>x.data)))) entityLabels.set(target.id,target.label);
      if (token !== generation) return;
      $('#sidebar').innerHTML = outline.sections.map((s,i)=>`<a class="${s.id===sectionID?'active':''}" href="${esc(href('/read',{outline:outline.id,section:s.id}))}">${String(i+1).padStart(2,'0')}　${esc(s.label)}</a>`).join('');
      $('#main').innerHTML = `<div class="eyebrow">SECTION ${String(index+1).padStart(2,'0')}</div><h2>${esc(section.label)}</h2>${displayed.map(card).join('')}<div class="pager">${index>0?`<a href="${esc(href('/read',{outline:outline.id,section:outline.sections[index-1].id}))}">← 前の節</a>`:'<span></span>'}${index<outline.sections.length-1?`<a href="${esc(href('/read',{outline:outline.id,section:outline.sections[index+1].id}))}">次の節 →</a>`:'<span>この目次の最後の節です</span>'}</div>`;
    } else {
      $('#side-label').textContent = 'FRAMEWORKS';
      const entityID = params.get('entity');
      const frameworkID = params.get('framework') || overview.frameworks[0]?.id;
      const contextID = params.get('context') || '';
      $('#sidebar').innerHTML = overview.frameworks.map(f=>`<a class="${!entityID&&f.id===frameworkID?'active':''}" href="${esc(href('/structure',{framework:f.id}))}">${esc(f.label)}${f.origin==='synthetic'?' · 合成例':''}</a>`).join('');
      if (entityID) {
        const entity = (await api(`entities/${encodeURIComponent(entityID)}`)).data;
        displayed = [entity];
        const query = new URLSearchParams({entityId:entityID,...(contextID?{contextId:contextID}:{})});
        const relations = (await api(`relations?${query}`)).relations;
        function leaves(x) { return x.op==='goal'?[x.goalID]:x.operands.flatMap(leaves); }
        const relatedIDs = [...new Set([...entity.targetIDs, ...(entity.successorIDs||[]), ...(entity.prerequisites||[]).flatMap(p=>leaves(p.expression)), ...relations.flatMap(r=>[r.from,r.to])])];
        const related = await Promise.all(relatedIDs.map(id=>api(`entities/${encodeURIComponent(id)}`).then(x=>x.data)));
        const labels = new Map(related.map(e=>[e.id,e.label]));
        related.forEach(e=>entityLabels.set(e.id,e.label));
        const relationHTML = relations.length ? relations.map(r=>`<div class="relation"><span class="badge">${esc(r.kind==='alignment'?'原典との対応':r.kind==='knowledge'?'知識の関係':r.kind==='enrollment'?'履修規則':strengths[r.strength])}</span><p>${link(r.from,labels.get(r.from))} → ${link(r.to,labels.get(r.to))}</p>${r.coverage?`<p>${r.coverage==='partial'?'部分対応':'完全対応'}${r.excluded.length?' · この対応の対象外：'+esc(r.excluded.join('、')):''}</p>`:''}<p>文脈：${esc(overview.contexts.find(c=>c.id===r.contextID)?.label || '指定なし（普遍的な前提を意味しません）')}</p><p>${esc(r.provenance.rationale)} · ${esc(origins[r.provenance.origin])}</p></div>`).join('') : schema==='0.2.0' ? '<p class="status">この条件に該当する原典対応・知識関係・履修規則はありません。</p>' : '<p class="status">この条件に該当する登録済みの関係はありません。未調査の可能性は対象の調査状態を参照してください。</p>';
        if (token !== generation) return;
        $('#main').innerHTML = `<div class="eyebrow">ENTITY DETAIL</div><h2>学びのつながり</h2>${card(entity)}${prerequisiteHTML({...entity,prerequisites:(entity.prerequisites||[]).filter(p=>!contextID||p.contextID===contextID)})}${(entity.changes||[]).length?`<details><summary>編集・分割・統合の履歴</summary>${entity.changes.map(c=>`<p>${esc({edit:'編集',split:'分割',merge:'統合'}[c.kind])}：${esc(c.rationale)}</p>${[...c.before,...c.after].map(x=>`<a href="${esc('/structure?'+new URLSearchParams({release:x.release,entity:x.record.id}))}">${esc(x.release)} の記録</a>`).join(' / ')}`).join('')}</details>`:''}<h3>${schema==='0.2.0'?'原典との対応・その他の関係':'対応と前提'}</h3><label class="meta">文脈で絞り込む <select id="context"><option value="">すべて（文脈を保持）</option>${overview.contexts.map(c=>`<option value="${esc(c.id)}" ${c.id===contextID?'selected':''}>${esc(c.label)}</option>`).join('')}</select></label>${relationHTML}`;
        $('#context').addEventListener('change',e=>{location.href=href('/structure',{entity:entityID,...(e.target.value?{context:e.target.value}:{})});});
      } else {
        const filters = new URLSearchParams();
        for (const key of ['stage','grade','subjectId','courseId','kind']) if (params.has(key)) filters.set(key,params.get(key));
        const searching = schema==='0.2.0' && (filters.size > 0 || !frameworkID);
        const body = await api(searching?`entities?${filters}`:`frameworks/${encodeURIComponent(frameworkID)}`);
        if (searching) {
          $('#main').innerHTML = `<h2>学年・教科から探す</h2>${filterHTML(params)}<p>${body.entities.length}件。学年を指定した場合は、その学年が明記された項目を表示します。</p>${body.entities.map(e=>`<article class="card"><span class="badge">${esc(kinds[e.kind])}</span><h3>${link(e.id,e.label)}</h3><p class="meta">${esc(educationText(e.education))}</p></article>`).join('')}`;
        } else {
        if (token !== generation) return;
        $('#main').innerHTML = `<div class="eyebrow">FRAMEWORK</div><h2>${esc(body.data.label)}</h2><p class="meta">${esc(body.data.issuer)} / ${esc(body.data.version)} / ${esc(origins[body.data.origin])}</p><div class="notice">収録した項目の抜粋です。原典全体の階層と収録範囲を表すものではありません。</div>${schema==='0.2.0'?filterHTML(params):''}${tree(body.items)}<details open><summary>この版の確認範囲と限界</summary><ul>${overview.limitations.map(l=>`<li>${esc(l)}</li>`).join('')}</ul></details>`;
        }
        const form = $('#scope-filter');
        if (form) {
          form.elements.stage.onchange = () => { form.elements.grade.value=''; form.elements.grade.disabled=!form.elements.stage.value; const max={elementary:6,lowerSecondary:3,upperSecondary:3}[form.elements.stage.value]; if(max) form.elements.grade.max=max; else form.elements.grade.removeAttribute('max'); };
          form.onsubmit = event => { event.preventDefault(); const values=Object.fromEntries([...new FormData(form)].filter(([,value])=>value)); location.href=href('/structure',values); };
        }
      }
    }
    await sourceDetails(displayed, token);
  } catch (error) {
    if (token !== generation) return;
    $('#main').innerHTML = `<div class="status error"><h2>データを表示できません</h2><p>${esc(error.message)}</p><button id="retry">再試行</button></div>`;
    $('#retry').onclick = render;
  }
}
async function start() {
  try {
    const releases = (await json('/api/v1/releases')).releases;
    if (!releases.length) throw new Error('利用できるデータ版がありません。');
    release = new URLSearchParams(location.search).get('release') || (releases.find(r=>r.release==='cross-subject-0.2.0') || releases[0]).release;
    schema = releases.find(r=>r.release===release)?.schemaVersion;
    if (!schema) throw new Error(`指定されたデータ版は存在しません: ${release}`);
    $('#release').innerHTML = releases.map(r=>`<option ${r.release===release?'selected':''}>${esc(r.release)}</option>`).join('');
    $('#release').onchange = e => { location.search = new URLSearchParams({release:e.target.value}); };
    if ((await json('/api/v1/capabilities')).localEditing) {
      const edit = document.createElement('a');
      edit.href = '/edit?' + new URLSearchParams({baseRelease:release});
      edit.textContent = '編集する';
      $('nav').append(edit);
    }
    overview = await api('overview');
    const firstOutline = overview.readingOutlines[0];
    const isCross = release.startsWith('cross-subject-') || (overview.taxons?.filter(t=>t.kind==='subject').length > 1 && overview.frameworks.some(f=>f.origin==='original'));
    const isExample = release.startsWith('examples-') || release.startsWith('editing-') || (!isCross && overview.frameworks.every(f=>f.origin==='synthetic'));
    $('.hero h1').textContent = firstOutline?.label || '学びをたどる';
    document.title = `Curricula — ${firstOutline?.label || release}`;
    $('.hero .eyebrow').textContent = isCross ? 'CURRICULUM / CROSS SUBJECTS' : isExample ? 'STRUCTURE / SYNTHETIC SAMPLES' : 'MATHEMATICS / PILOT 01';
    $('.hero p').textContent = isCross ? '国語・理科・社会・外国語・音楽・道徳・算数・情報。学習指導要領の原文から、学ぶ対象とできることをたどる。' : isExample ? '学校段階・機関・定義・学習経路の違いを、小さな合成例で確かめる。' : '数量の関係から、表・式・グラフへ。学ぶ対象とできることを、指導要領につなぐ。';
    $('.hero-meta').innerHTML = `<span>${isCross?'小学校・中学校・高校':isExample?'構造検証用の合成例':'小6 → 中1'}</span><span>全${firstOutline?.sections.length || 0}節</span>`;
    await render();
  } catch (error) {
    $('#main').innerHTML = `<div class="status error"><h2>データを取得できません</h2><p>${esc(error.message)}</p><button id="retry">再試行</button></div>`;
    $('#retry').onclick = start;
  }
}
start();
