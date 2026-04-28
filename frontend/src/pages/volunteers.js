import { api } from '../api.js';
import { showToast } from '../toast.js';

export async function renderVolunteers(root) {
  root.innerHTML = `
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
      <div>
        <h2>🤝 Volunteers</h2>
        <p>Manage your volunteer workforce</p>
      </div>
      <button class="btn btn-primary" id="add-volunteer-btn">➕ Add Volunteer</button>
    </div>
    <div class="section-card">
      <div id="vol-table"><div class="spinner"></div></div>
    </div>
    <div id="vol-modal"></div>
  `;

  document.getElementById('add-volunteer-btn').addEventListener('click', showModal);
  await loadVolunteers();
}

async function loadVolunteers() {
  try {
    const data = await api.getVolunteers();
    const el = document.getElementById('vol-table');
    const items = data.items || [];
    if (!items.length) {
      el.innerHTML = '<div class="empty-state"><div class="icon">👥</div><p>No volunteers registered yet.</p></div>';
      return;
    }
    el.innerHTML = `<table class="data-table"><thead><tr>
      <th>Name</th><th>Skills</th><th>Area</th><th>Hrs/Week</th><th>Reliability</th><th>Available</th>
    </tr></thead><tbody>${items.map(v => `<tr>
      <td style="color:var(--text-primary);font-weight:600">${esc(v.name)}</td>
      <td>${esc(v.skills)}</td>
      <td>${esc(v.area)}</td>
      <td style="font-weight:600">${v.hours_per_week}</td>
      <td><span class="match-score ${v.reliability_score >= 0.8 ? 'match-score-high' : v.reliability_score >= 0.6 ? 'match-score-med' : 'match-score-low'}">${(v.reliability_score * 100).toFixed(0)}%</span></td>
      <td>${v.available ? '<span style="color:var(--accent-emerald)">● Yes</span>' : '<span style="color:var(--text-muted)">○ No</span>'}</td>
    </tr>`).join('')}</tbody></table>`;
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function showModal() {
  const modal = document.getElementById('vol-modal');
  modal.innerHTML = `
    <div class="modal-overlay" id="modal-overlay">
      <div class="modal">
        <div class="modal-title">Add New Volunteer</div>
        <div class="form-group">
          <label for="vol-name">Full Name</label>
          <input class="form-control" id="vol-name" placeholder="e.g. Priya Sharma" />
        </div>
        <div class="form-group">
          <label for="vol-skills">Skills (comma separated)</label>
          <input class="form-control" id="vol-skills" placeholder="e.g. medical, first aid, nursing" />
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label for="vol-area">Area</label>
            <select class="form-control" id="vol-area">
              <option>Hadapsar</option><option>Yerawada</option><option>Kondhwa</option>
              <option>Bibwewadi</option><option>Wanawadi</option><option>Kothrud</option>
              <option>Shivajinagar</option><option>Any</option>
            </select>
          </div>
          <div class="form-group">
            <label for="vol-hours">Hours / Week</label>
            <input type="number" class="form-control" id="vol-hours" min="1" max="80" value="10" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" id="modal-cancel">Cancel</button>
          <button class="btn btn-primary" id="modal-save">Save Volunteer</button>
        </div>
      </div>
    </div>
  `;
  document.getElementById('modal-cancel').addEventListener('click', () => { modal.innerHTML = ''; });
  document.getElementById('modal-overlay').addEventListener('click', (e) => { if (e.target === e.currentTarget) modal.innerHTML = ''; });
  document.getElementById('modal-save').addEventListener('click', async () => {
    const name = document.getElementById('vol-name').value.trim();
    const skills = document.getElementById('vol-skills').value.trim();
    const area = document.getElementById('vol-area').value;
    const hours = parseInt(document.getElementById('vol-hours').value, 10);
    if (!name || !skills) { showToast('Name and skills are required', 'error'); return; }
    try {
      await api.createVolunteer({ name, skills, area, hours_per_week: hours });
      showToast('Volunteer added successfully!', 'success');
      modal.innerHTML = '';
      await loadVolunteers();
    } catch (e) { showToast(e.message, 'error'); }
  });
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
