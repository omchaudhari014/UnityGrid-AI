import { api } from '../api.js';
import { showToast } from '../toast.js';

export async function renderMatching(root) {
  root.innerHTML = `
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
      <div>
        <h2>⚡ Volunteer Matching</h2>
        <p>AI-powered volunteer-to-need matching with fairness scoring</p>
      </div>
      <button class="btn btn-primary" id="run-match-btn">🚀 Run Matching Engine</button>
    </div>
    <div class="section-card">
      <div class="section-title">Assignments <span class="badge" id="assign-count">—</span></div>
      <div id="assign-table"><div class="spinner"></div></div>
    </div>
  `;

  document.getElementById('run-match-btn').addEventListener('click', async () => {
    const btn = document.getElementById('run-match-btn');
    btn.disabled = true; btn.textContent = '⏳ Running...';
    try {
      const result = await api.runMatching(10);
      showToast(`Matching complete! ${result.count} assignments created.`, 'success');
      await loadAssignments();
    } catch (e) { showToast(e.message, 'error'); }
    btn.disabled = false; btn.textContent = '🚀 Run Matching Engine';
  });

  await loadAssignments();
}

async function loadAssignments() {
  try {
    const data = await api.getAssignments();
    const items = data.items || [];
    const badge = document.getElementById('assign-count');
    if (badge) badge.textContent = items.length;
    const el = document.getElementById('assign-table');
    if (!items.length) {
      el.innerHTML = '<div class="empty-state"><div class="icon">🔗</div><p>No assignments yet. Submit reports and run the matching engine.</p></div>';
      return;
    }
    el.innerHTML = `<table class="data-table"><thead><tr>
      <th>Volunteer</th><th>Need</th><th>Area</th><th>Urgency</th><th>Score</th><th>Rationale</th><th>Status</th><th>Action</th>
    </tr></thead><tbody>${items.map(a => `<tr>
      <td style="color:var(--text-primary);font-weight:600">${esc(a.volunteer_name)}</td>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(a.need_name)}</td>
      <td>${esc(a.need_area)}</td>
      <td><span class="urgency-badge urgency-${a.need_urgency}">● ${a.need_urgency}</span></td>
      <td><span class="match-score ${a.match_score >= 70 ? 'match-score-high' : a.match_score >= 50 ? 'match-score-med' : 'match-score-low'}">${a.match_score}%</span></td>
      <td style="font-size:12px;color:var(--text-muted)">${esc(a.rationale)}</td>
      <td><span class="status-badge status-${a.status}">${a.status}</span></td>
      <td>${a.status !== 'completed' ? `<button class="btn btn-sm btn-primary complete-btn" data-id="${a.id}">✓ Complete</button>` : '<span style="color:var(--accent-emerald)">Done</span>'}</td>
    </tr>`).join('')}</tbody></table>`;

    el.querySelectorAll('.complete-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await api.completeAssignment(btn.dataset.id, 'Completed via dashboard');
          showToast('Assignment completed!', 'success');
          await loadAssignments();
        } catch (e) { showToast(e.message, 'error'); }
      });
    });
  } catch (e) { showToast(e.message, 'error'); }
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
