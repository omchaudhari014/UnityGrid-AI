const BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

async function request(path, opts = {}) {
  const url = `${BASE}${path}`;
  const config = { ...opts };
  if (opts.body && typeof opts.body === 'object') {
    config.headers = { 'Content-Type': 'application/json', ...opts.headers };
    config.body = JSON.stringify(opts.body);
  }
  const res = await fetch(url, config);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  getDashboard: () => request('/api/dashboard/summary'),
  getNeeds: (params = {}) => {
    const q = new URLSearchParams();
    if (params.area) q.set('area', params.area);
    if (params.urgency) q.set('urgency', params.urgency);
    if (params.status) q.set('status', params.status);
    const qs = q.toString();
    return request(`/api/needs${qs ? '?' + qs : ''}`);
  },
  getVolunteers: (availableOnly = false) =>
    request(`/api/volunteers${availableOnly ? '?available_only=true' : ''}`),
  createVolunteer: (data) =>
    request('/api/volunteers', { method: 'POST', body: data }),
  getHeatmap: () => request('/api/heatmap'),
  createReport: (data) =>
    request('/api/reports', { method: 'POST', body: data }),
  analyzeReport: (data) =>
    request('/api/reports/analyze', { method: 'POST', body: data }),
  runMatching: (max = 10) =>
    request(`/api/matching/run?max_assignments=${max}`, { method: 'POST' }),
  getAssignments: (status) => {
    const qs = status ? `?status=${status}` : '';
    return request(`/api/assignments${qs}`);
  },
  completeAssignment: (id, note = '') =>
    request(`/api/assignments/${id}/complete`, {
      method: 'POST',
      body: { completion_note: note },
    }),
};
