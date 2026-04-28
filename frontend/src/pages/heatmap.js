import { api } from '../api.js';

export async function renderHeatmap(root) {
  root.innerHTML = `
    <div class="page-header">
      <h2>🗺️ Area Heatmap</h2>
      <p>Community Need Index and fairness gap across areas</p>
    </div>
    <div class="section-card">
      <div id="heatmap-content"><div class="spinner"></div></div>
    </div>
  `;

  try {
    const data = await api.getHeatmap();
    const items = data.items || [];
    const el = document.getElementById('heatmap-content');
    if (!items.length) {
      el.innerHTML = '<div class="empty-state"><div class="icon">🗺️</div><p>No area data available yet. Submit reports to populate the heatmap.</p></div>';
      return;
    }
    const maxNeeds = Math.max(...items.map(i => i.need_count), 1);
    el.innerHTML = `
      <div style="margin-bottom:24px">
        ${items.map(i => `
          <div class="heatmap-item">
            <div class="heatmap-area">${esc(i.area)}</div>
            <div class="heatmap-bar-wrap">
              <div class="heatmap-bar" style="width:${(i.need_count / maxNeeds * 100).toFixed(0)}%;background:${i.avg_cni >= 0.7 ? 'var(--gradient-warm)' : i.avg_cni >= 0.4 ? 'var(--gradient-primary)' : 'var(--gradient-success)'}"></div>
            </div>
            <div class="heatmap-value">${i.need_count}</div>
          </div>
        `).join('')}
      </div>
      <table class="data-table"><thead><tr>
        <th>Area</th><th>Needs</th><th>Avg CNI</th><th>Assigned</th><th>Fairness Gap</th>
      </tr></thead><tbody>${items.map(i => `<tr>
        <td style="font-weight:700">${esc(i.area)}</td>
        <td>${i.need_count}</td>
        <td><span class="match-score ${i.avg_cni >= 0.7 ? 'match-score-low' : i.avg_cni >= 0.4 ? 'match-score-med' : 'match-score-high'}">${i.avg_cni}</span></td>
        <td>${i.total_assigned}</td>
        <td><span style="font-weight:700;color:${i.fairness_gap >= 0.6 ? 'var(--accent-rose)' : i.fairness_gap >= 0.3 ? 'var(--accent-amber)' : 'var(--accent-emerald)'}">${(i.fairness_gap * 100).toFixed(0)}%</span></td>
      </tr>`).join('')}</tbody></table>
    `;
  } catch (e) {
    document.getElementById('heatmap-content').innerHTML = `<div class="empty-state"><p>⚠️ ${e.message}</p></div>`;
  }
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
