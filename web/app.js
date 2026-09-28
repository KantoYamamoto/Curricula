const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const kinds = {subjectMatter:'学ぶ対象', competency:'できること', frameworkItem:'指導要領・要求'};
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
  return body;
}
function details(e) {
  return `<details><summary>出典・識別子・編集上の根拠</summary><dl><dt>ID</dt><dd>${esc(e.id)}</dd><dt>根拠</dt><dd>${esc(e.provenance.rationale)}</dd>${e.sourceLocator ? `<dt>原典の位置</dt><dd>${esc(e.sourceLocator)}</dd>`:''}${Object.entries(e.externalIDs).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl><div class="sources" data-source-entity="${esc(e.id)}"></div></details>`;
}
function card(e) {
  return `<article class="card" id="${esc(e.id)}"><div class="badges"><span class="badge">${esc(kinds[e.kind])}</span><span class="badge">${esc(origins[e.provenance.origin])}</span></div><h3>${esc(e.label)}</h3>${e.text !== e.label ? `<p>${esc(e.text)}</p>`:''}${e.conditions ? `<div class="conditions"><span class="small-label">条件・適用範囲</span>${esc(e.conditions)}</div>`:''}${e.criteria.length ? `<span class="small-label">達成を確認する観点</span><ul>${e.criteria.map(c=>`<li>${esc(c)}</li>`).join('')}</ul>`:''}${e.prerequisiteStatus ? `<p class="meta">${esc(states[e.prerequisiteStatus])}</p>`:''}<div class="links">${e.parentID?link(e.parentID,'上位の原典項目を読む →'):''}${e.targetIDs.map(id=>link(id)).join('')}${link(e.id,'対応・前提・出典をたどる →')}</div>${details(e)}</article>`;
}
async function sourceDetails(entities, token) {
  const ids = [...new Set(entities.flatMap(e=>e.provenance.sourceIDs))];
  const sources = await Promise.all(ids.map(id=>api(`sources/${encodeURIComponent(id)}`).then(x=>x.data)));
  if (token !== generation) return;
  for (const e of entities) {
    const node = document.querySelector(`[data-source-entity="${CSS.escape(e.id)}"]`);
    if (!node) continue;
    node.innerHTML = sources.filter(s=>e.provenance.sourceIDs.includes(s.id)).map(s=>{
      const url = new URL(s.url);
      const title = ['https:','http:'].includes(url.protocol) ? `<a href="${esc(url.href)}" target="_blank" rel="noreferrer">${esc(s.title)}</a>` : esc(s.title);
      return `<p>${title}<br>${esc(s.publisher)} · ${esc(s.distributionVersion)} · 取得 ${esc(s.retrievedOn)}<br>${esc(s.verification)}<br>SHA-256: ${esc(s.sha256)}</p>`;
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
      const sectionID = params.get('section') || outline.sections[0].id;
      const index = outline.sections.findIndex(s=>s.id===sectionID);
      if (index < 0) throw new Error('指定された節が存在しません。');
      const section = outline.sections[index];
      displayed = await Promise.all(section.entityIDs.map(id=>api(`entities/${encodeURIComponent(id)}`).then(x=>x.data)));
      const targets = [...new Set(displayed.flatMap(e=>e.targetIDs))];
      for (const target of await Promise.all(targets.map(id=>api(`entities/${encodeURIComponent(id)}`).then(x=>x.data)))) entityLabels.set(target.id,target.label);
      if (token !== generation) return;
      $('#sidebar').innerHTML = outline.sections.map((s,i)=>`<a class="${s.id===sectionID?'active':''}" href="${esc(href('/read',{outline:outline.id,section:s.id}))}">${String(i+1).padStart(2,'0')}　${esc(s.label)}</a>`).join('');
      $('#main').innerHTML = `<div class="eyebrow">SECTION ${String(index+1).padStart(2,'0')}</div><h2>${esc(section.label)}</h2>${displayed.map(card).join('')}<div class="pager">${index>0?`<a href="${esc(href('/read',{outline:outline.id,section:outline.sections[index-1].id}))}">← 前の節</a>`:'<span></span>'}${index<outline.sections.length-1?`<a href="${esc(href('/read',{outline:outline.id,section:outline.sections[index+1].id}))}">次の節 →</a>`:'<span>この目次の最後の節です</span>'}</div>`;
    } else {
      $('#side-label').textContent = 'FRAMEWORKS';
      const entityID = params.get('entity');
      const frameworkID = params.get('framework') || overview.frameworks[0].id;
      const contextID = params.get('context') || '';
      $('#sidebar').innerHTML = overview.frameworks.map(f=>`<a class="${!entityID&&f.id===frameworkID?'active':''}" href="${esc(href('/structure',{framework:f.id}))}">${esc(f.label)}${f.origin==='synthetic'?' · 合成例':''}</a>`).join('');
      if (entityID) {
        const entity = (await api(`entities/${encodeURIComponent(entityID)}`)).data;
        displayed = [entity];
        const query = new URLSearchParams({entityId:entityID,...(contextID?{contextId:contextID}:{})});
        const relations = (await api(`relations?${query}`)).relations;
        const relatedIDs = [...new Set([...entity.targetIDs, ...relations.flatMap(r=>[r.from,r.to])])];
        const related = await Promise.all(relatedIDs.map(id=>api(`entities/${encodeURIComponent(id)}`).then(x=>x.data)));
        const labels = new Map(related.map(e=>[e.id,e.label]));
        related.forEach(e=>entityLabels.set(e.id,e.label));
        const relationHTML = relations.length ? relations.map(r=>`<div class="relation"><span class="badge">${esc(r.kind==='alignment'?'原典との対応':r.kind==='knowledge'?'知識の関係':r.kind==='enrollment'?'履修規則':strengths[r.strength])}</span><p>${link(r.from,labels.get(r.from))} → ${link(r.to,labels.get(r.to))}</p>${r.coverage?`<p>${r.coverage==='partial'?'部分対応':'完全対応'}${r.excluded.length?' · この対応の対象外：'+esc(r.excluded.join('、')):''}</p>`:''}<p>文脈：${esc(overview.contexts.find(c=>c.id===r.contextID)?.label || '指定なし（普遍的な前提を意味しません）')}</p><p>${esc(r.provenance.rationale)} · ${esc(origins[r.provenance.origin])}</p></div>`).join('') : '<p class="status">この条件に該当する登録済みの関係はありません。未調査の可能性は対象の調査状態を参照してください。</p>';
        if (token !== generation) return;
        $('#main').innerHTML = `<div class="eyebrow">ENTITY DETAIL</div><h2>学びのつながり</h2>${card(entity)}<h3>対応と前提</h3><label class="meta">文脈で絞り込む <select id="context"><option value="">すべて（文脈を保持）</option>${overview.contexts.map(c=>`<option value="${esc(c.id)}" ${c.id===contextID?'selected':''}>${esc(c.label)}</option>`).join('')}</select></label>${relationHTML}`;
        $('#context').addEventListener('change',e=>{location.href=href('/structure',{entity:entityID,...(e.target.value?{context:e.target.value}:{})});});
      } else {
        const body = await api(`frameworks/${encodeURIComponent(frameworkID)}`);
        if (token !== generation) return;
        $('#main').innerHTML = `<div class="eyebrow">FRAMEWORK</div><h2>${esc(body.data.label)}</h2><p class="meta">${esc(body.data.issuer)} / ${esc(body.data.version)} / ${esc(origins[body.data.origin])}</p><div class="notice">収録した項目の抜粋です。原典全体の階層と収録範囲を表すものではありません。</div>${tree(body.items)}<details open><summary>この版の確認範囲と限界</summary><ul>${overview.limitations.map(l=>`<li>${esc(l)}</li>`).join('')}</ul></details>`;
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
    release = new URLSearchParams(location.search).get('release') || (releases.find(r=>r.release==='cross-subject-0.1.0') || releases[0]).release;
    schema = releases.find(r=>r.release===release)?.schemaVersion;
    if (!schema) throw new Error(`指定されたデータ版は存在しません: ${release}`);
    $('#release').innerHTML = releases.map(r=>`<option ${r.release===release?'selected':''}>${esc(r.release)}</option>`).join('');
    $('#release').onchange = e => { location.search = new URLSearchParams({release:e.target.value}); };
    overview = await api('overview');
    const firstOutline = overview.readingOutlines[0];
    const isExample = release.startsWith('examples-');
    const isCross = release.startsWith('cross-subject-');
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
