import { api } from '../api.js';
import { showToast } from '../toast.js';

export async function renderReports(root) {
  root.innerHTML = `
    <div class="page-header">
      <h2>📝 Submit Field Report</h2>
      <p>Submit a ground-level report to extract community needs automatically</p>
    </div>
    <div class="grid-2">
      <div class="section-card">
        <div class="section-title">New Report</div>
        <div class="form-group">
          <label for="rpt-org">Organisation Name</label>
          <input class="form-control" id="rpt-org" placeholder="e.g. Pune Community Trust" />
        </div>
        <div class="form-group">
          <label for="rpt-area">Area</label>
          <select class="form-control" id="rpt-area">
            <option>Hadapsar</option><option>Yerawada</option><option>Kondhwa</option>
            <option>Bibwewadi</option><option>Wanawadi</option><option>Kothrud</option><option>Shivajinagar</option>
          </select>
        </div>
        <div class="form-group">
          <label for="rpt-content">Field Report Content</label>
          <textarea class="form-control" id="rpt-content" rows="8"
            placeholder="Describe the community situation in detail. Mention water, medical, food, education, shelter or transport issues with approximate number of affected people..."></textarea>
        </div>
        <div style="display:flex;gap:12px">
          <button class="btn btn-secondary" id="rpt-preview">🔍 Preview Analysis</button>
          <button class="btn btn-primary" id="rpt-submit">📤 Submit Report</button>
        </div>
      </div>
      <div class="section-card">
        <div class="section-title">Analysis Preview</div>
        <div id="analysis-preview">
          <div class="empty-state"><div class="icon">🔬</div><p>Enter a report and click "Preview Analysis" to see extracted needs before submitting.</p></div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('rpt-preview').addEventListener('click', async () => {
    const area = document.getElementById('rpt-area').value;
    const content = document.getElementById('rpt-content').value.trim();
    if (content.length < 20) { showToast('Report must be at least 20 characters', 'error'); return; }
    const el = document.getElementById('analysis-preview');
    el.innerHTML = '<div class="spinner"></div>';
    try {
      const data = await api.analyzeReport({ area, content });
      renderPreview(el, data);
    } catch (e) { showToast(e.message, 'error'); el.innerHTML = `<div class="empty-state"><p>⚠️ ${e.message}</p></div>`; }
  });

  document.getElementById('rpt-submit').addEventListener('click', async () => {
    const organisation = document.getElementById('rpt-org').value.trim();
    const area = document.getElementById('rpt-area').value;
    const content = document.getElementById('rpt-content').value.trim();
    if (!organisation) { showToast('Organisation name is required', 'error'); return; }
    if (content.length < 20) { showToast('Report must be at least 20 characters', 'error'); return; }
    try {
      const data = await api.createReport({ organisation, area, content });
      showToast(`Report submitted! ${data.extracted_need_count} needs extracted.`, 'success');
      document.getElementById('rpt-content').value = '';
      document.getElementById('analysis-preview').innerHTML =
        `<div class="empty-state"><div class="icon">✅</div><p>Report #${data.report_id} submitted successfully with ${data.extracted_need_count} needs.</p></div>`;
    } catch (e) { showToast(e.message, 'error'); }
  });
}

function renderPreview(el, data) {
  const needs = data.needs || [];
  el.innerHTML = `
    <p style="margin-bottom:16px;color:var(--text-secondary);font-size:14px">${esc(data.summary)}</p>
    <p style="margin-bottom:16px;font-weight:700;font-size:16px">Total Affected: <span style="color:var(--accent-amber)">${data.total_affected}</span></p>
    ${needs.map(n => `
      <div style="background:var(--bg-secondary);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:16px;margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span class="cat-badge">${esc(n.category)}</span>
          <span class="urgency-badge urgency-${n.urgency}">● ${n.urgency}</span>
        </div>
        <p style="font-weight:600;font-size:14px;margin-bottom:4px">${esc(n.name.length > 80 ? n.name.slice(0,80)+'…' : n.name)}</p>
        <p style="font-size:12px;color:var(--text-muted)">Affected: ${n.affected_count} · CNI: ${n.cni_score}</p>
        <p style="font-size:12px;color:var(--text-secondary);margin-top:4px">Task: ${esc(n.volunteer_task)}</p>
      </div>
    `).join('')}
  `;
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
