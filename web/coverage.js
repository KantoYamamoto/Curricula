const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stages = {elementary:'小学校',lowerSecondary:'中学校'};
const status = {pending:'未着手',inProgress:'整理中',complete:'整理済み'};
const main = document.querySelector('#coverage');
try {
  const response = await fetch('/api/v1/coverage');
  if (!response.ok) throw new Error(`取得失敗 (${response.status})`);
  const data = await response.json();
  document.querySelector('#coverage-meta').textContent = `${data.release} · ${data.updatedOn} 更新`;
  main.innerHTML = `<div class="coverage-stats"><div><strong>${data.totals.originalItems.toLocaleString()}</strong><span>原文項目 収録済み</span></div><div><strong>${data.totals.originalChunks} / ${data.totals.originalChunks}</strong><span>原文の区切り 完了</span></div><div><strong>${data.totals.goalChunksComplete} 完了 / ${data.totals.goalChunksInProgress||0} 整理中</strong><span>全${data.totals.originalChunks}区切り · 原文${data.totals.reviewedOriginalItems||0}項目を整理</span></div></div><p>${esc(data.scope)}</p>${data.totals.goals?`<p>目標 ${data.totals.goals}件 · 判定の観点・注釈 ${data.totals.annotations}件</p>`:''}<div class="next-work"><span class="small-label">次に進める範囲</span><p>${esc(data.next)}</p></div><p class="meta">${esc(data.sequence)}</p><form class="scope-filter" id="coverage-filter"><label>学校段階<select name="stage"><option value="">すべて</option><option value="elementary">小学校</option><option value="lowerSecondary">中学校</option></select></label><label>教科・領域<select name="subject"><option value="">すべて</option>${[...new Set(data.chunks.map(c=>c.subject))].map(s=>`<option>${esc(s)}</option>`).join('')}</select></label></form><div id="work-groups"></div>`;
  const filter = document.querySelector('#coverage-filter');
  function renderGroups() {
    const selected = new FormData(filter);
    const groups = new Map();
    for (const c of data.chunks) {
      if (selected.get('stage') && selected.get('stage')!==c.stage || selected.get('subject') && selected.get('subject')!==c.subject) continue;
      const key = c.stage+':'+c.subject;
      if (!groups.has(key)) groups.set(key,[]);
      groups.get(key).push(c);
    }
    document.querySelector('#work-groups').innerHTML = [...groups.values()].map(chunks=>`<details class="coverage-group" ${selected.get('subject')?'open':''}><summary><strong>${esc(stages[chunks[0].stage])} · ${esc(chunks[0].subject)}</strong><span>${chunks.reduce((n,c)=>n+c.original.imported,0)} 項目 / ${chunks.length} 区切り</span></summary><div class="coverage-table-wrap"><table><thead><tr><th scope="col">区切り</th><th scope="col">原文</th><th scope="col">目標の整理</th></tr></thead><tbody>${chunks.map(c=>`<tr><td><a href="/read?${esc(new URLSearchParams({release:c.release,outline:c.outlineID,section:c.sectionID}))}">${esc(c.label)}</a></td><td>${c.original.imported} / ${c.original.expected} <span class="badge">収録済み</span></td><td>${esc(status[c.goals.status]||c.goals.status)}${c.goals.release?`<br><span class="meta">${esc(c.goals.label)} · 原文${c.goals.reviewedOriginalIDs.length}/${c.entityIDs.length}項目</span><br><a href="/read?${esc(new URLSearchParams({release:c.goals.release,outline:'reading.authored'}))}">整理した学びを読む →</a>`:''}</td></tr>`).join('')}</tbody></table></div></details>`).join('');
  }
  filter.addEventListener('change',renderGroups);
  filter.addEventListener('submit',e=>e.preventDefault());
  renderGroups();
} catch (error) { main.innerHTML = `<p class="status">${esc(error.message)}</p>`; }
