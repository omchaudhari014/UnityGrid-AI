import { api } from '../api.js';

export async function renderDashboard(root) {
  root.innerHTML = `
    <div class="page-header">
      <h2>📊 Dashboard</h2>
      <p>Real-time community intelligence overview</p>
    </div>
    <div class="stats-grid" id="stats-grid"><div class="spinner"></div></div>
    <div class="grid-2">
      <div class="section-card" id="top-needs-section">
        <div class="section-title">🔥 Top Priority Needs</div>
        <div id="top-needs-list"><div class="spinner"></div></div>
      </div>
      <div>
        <div class="section-card" id="category-section">
          <div class="section-title">📂 Category Breakdown</div>
          <div id="category-list"><div class="spinner"></div></div>
        </div>
        <div class="section-card" id="area-section">
          <div class="section-title">📍 Area Overview</div>
          <div id="area-list"><div class="spinner"></div></div>
        </div>
      </div>
    </div>
  `;

  try {
    const data = await api.getDashboard();
    renderStats(data);
    renderTopNeeds(data.top_needs || []);
    renderCategories(data.category_breakdown || []);
    renderAreas(data.area_breakdown || []);
  } catch (e) {
    document.getElementById('stats-grid').innerHTML =
      `<div class="empty-state"><p>⚠️ Could not load dashboard. Is the backend running?</p><p style="margin-top:8px;font-size:12px">${e.message}</p></div>`;
  }
}

function renderStats(d) {
  document.getElementById('stats-grid').innerHTML = `
    <div class="stat-card">
      <div class="stat-icon">📋</div>
      <div class="stat-value">${d.open_needs}</div>
      <div class="stat-label">Open Needs</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">🚨</div>
      <div class="stat-value">${d.critical_urgency}</div>
      <div class="stat-label">Critical Urgency</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">🤝</div>
      <div class="stat-value">${d.volunteers_ready}</div>
      <div class="stat-label">Volunteers Ready</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">✅</div>
      <div class="stat-value">${d.resolved_7d}</div>
      <div class="stat-label">Resolved (7 days)</div>
    </div>
  `;
}

function renderTopNeeds(needs) {
  const el = document.getElementById('top-needs-list');
  if (!needs.length) { el.innerHTML = '<div class="empty-state"><div class="icon">🎉</div><p>No open needs right now!</p></div>'; return; }
  el.innerHTML = `<table class="data-table"><thead><tr>
    <th>Need</th><th>Area</th><th>Urgency</th><th>Affected</th><th>CNI</th>
  </tr></thead><tbody>${needs.map(n => `<tr>
    <td style="color:var(--text-primary);font-weight:500">${esc(n.name.length > 45 ? n.name.slice(0,45)+'…' : n.name)}</td>
    <td>${esc(n.area)}</td>
    <td><span class="urgency-badge urgency-${n.urgency}">● ${n.urgency}</span></td>
    <td style="font-weight:700">${n.affected_count}</td>
    <td><span class="match-score ${n.cni_score >= 0.7 ? 'match-score-high' : n.cni_score >= 0.4 ? 'match-score-med' : 'match-score-low'}">${n.cni_score}</span></td>
  </tr>`).join('')}</tbody></table>`;
}

function renderCategories(cats) {
  const el = document.getElementById('category-list');
  if (!cats.length) { el.innerHTML = '<div class="empty-state"><p>No data yet</p></div>'; return; }
  const max = Math.max(...cats.map(c => c.total));
  el.innerHTML = cats.map(c => `
    <div class="heatmap-item">
      <div class="heatmap-area"><span class="cat-badge">${esc(c.category)}</span></div>
      <div class="heatmap-bar-wrap"><div class="heatmap-bar" style="width:${(c.total/max*100).toFixed(0)}%;background:var(--gradient-accent)"></div></div>
      <div class="heatmap-value">${c.total}</div>
    </div>
  `).join('');
}

function renderAreas(areas) {
  const el = document.getElementById('area-list');
  if (!areas.length) { el.innerHTML = '<div class="empty-state"><p>No data yet</p></div>'; return; }
  el.innerHTML = `<table class="data-table"><thead><tr><th>Area</th><th>Reports</th><th>Avg CNI</th></tr></thead><tbody>
    ${areas.map(a => `<tr><td style="font-weight:600">${esc(a.area)}</td><td>${a.total_reports}</td><td>${(a.avg_cni || 0).toFixed(2)}</td></tr>`).join('')}
  </tbody></table>`;
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
