import { api } from '../api.js';
import { showToast } from '../toast.js';

export async function renderNeeds(root) {
  root.innerHTML = `
    <div class="page-header">
      <h2>📋 Community Needs</h2>
      <p>Track, filter, and monitor all detected community needs</p>
    </div>
    <div class="section-card" style="margin-bottom:24px">
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
        <div class="form-group" style="margin-bottom:0;flex:1;min-width:150px">
          <label for="filter-area">Area</label>
          <select class="form-control" id="filter-area">
            <option value="">All Areas</option>
            <option>Hadapsar</option><option>Yerawada</option><option>Kondhwa</option>
            <option>Bibwewadi</option><option>Wanawadi</option><option>Kothrud</option><option>Shivajinagar</option>
          </select>
        </div>
        <div class="form-group" style="margin-bottom:0;flex:1;min-width:150px">
          <label for="filter-urgency">Urgency</label>
          <select class="form-control" id="filter-urgency">
            <option value="">All</option>
            <option value="critical">Critical</option><option value="high">High</option>
            <option value="medium">Medium</option><option value="low">Low</option>
          </select>
        </div>
        <div class="form-group" style="margin-bottom:0;flex:1;min-width:150px">
          <label for="filter-status">Status</label>
          <select class="form-control" id="filter-status">
            <option value="">All</option>
            <option value="open">Open</option><option value="active">Active</option><option value="resolved">Resolved</option>
          </select>
        </div>
        <button class="btn btn-primary btn-sm" id="apply-filters" style="height:40px">🔍 Filter</button>
      </div>
    </div>
    <div class="section-card">
      <div id="needs-table"><div class="spinner"></div></div>
    </div>
  `;

  const load = async () => {
    const area = document.getElementById('filter-area').value;
    const urgency = document.getElementById('filter-urgency').value;
    const status = document.getElementById('filter-status').value;
    document.getElementById('needs-table').innerHTML = '<div class="spinner"></div>';
    try {
      const data = await api.getNeeds({ area, urgency, status });
      renderTable(data.items || []);
    } catch (e) {
      showToast(e.message, 'error');
      document.getElementById('needs-table').innerHTML = `<div class="empty-state"><p>⚠️ ${e.message}</p></div>`;
    }
  };

  document.getElementById('apply-filters').addEventListener('click', load);
  await load();
}

function renderTable(items) {
  const el = document.getElementById('needs-table');
  if (!items.length) {
    el.innerHTML = '<div class="empty-state"><div class="icon">📭</div><p>No needs found for the selected filters.</p></div>';
    return;
  }
  el.innerHTML = `<table class="data-table"><thead><tr>
    <th>Name</th><th>Area</th><th>Category</th><th>Urgency</th><th>Affected</th><th>CNI</th><th>Status</th><th>Volunteer</th>
  </tr></thead><tbody>${items.map(n => `<tr>
    <td style="color:var(--text-primary);font-weight:500;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(n.name)}</td>
    <td>${esc(n.area)}</td>
    <td><span class="cat-badge">${esc(n.category)}</span></td>
    <td><span class="urgency-badge urgency-${n.urgency}">● ${n.urgency}</span></td>
    <td style="font-weight:700">${n.affected_count}</td>
    <td>${n.cni_score}</td>
    <td><span class="status-badge status-${n.status}">${n.status}</span></td>
    <td>${n.assigned_volunteer_name ? esc(n.assigned_volunteer_name) : '<span style="color:var(--text-muted)">—</span>'}</td>
  </tr>`).join('')}</tbody></table>`;
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
