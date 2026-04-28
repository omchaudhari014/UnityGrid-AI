import './style.css';
import { renderDashboard } from './pages/dashboard.js';
import { renderNeeds } from './pages/needs.js';
import { renderVolunteers } from './pages/volunteers.js';
import { renderReports } from './pages/reports.js';
import { renderMatching } from './pages/matching.js';
import { renderHeatmap } from './pages/heatmap.js';

const PAGES = {
  dashboard:  { label: 'Dashboard',  icon: '📊', render: renderDashboard },
  needs:      { label: 'Needs',      icon: '📋', render: renderNeeds },
  reports:    { label: 'Submit Report', icon: '📝', render: renderReports },
  matching:   { label: 'Matching',   icon: '⚡', render: renderMatching },
  volunteers: { label: 'Volunteers', icon: '🤝', render: renderVolunteers },
  heatmap:    { label: 'Heatmap',    icon: '🗺️', render: renderHeatmap },
};

let currentPage = 'dashboard';

function buildLayout() {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="layout">
      <nav class="sidebar" id="sidebar">
        <div class="sidebar-brand">
          <div class="logo">U</div>
          <div>
            <h1>UnityGrid AI</h1>
            <span>Community Intelligence</span>
          </div>
        </div>
        <div class="nav-section">
          <div class="nav-section-title">Main</div>
          ${Object.entries(PAGES).map(([key, p]) => `
            <div class="nav-item ${key === currentPage ? 'active' : ''}" data-page="${key}" id="nav-${key}">
              <span class="icon">${p.icon}</span>
              <span>${p.label}</span>
            </div>
          `).join('')}
        </div>
        <div class="sidebar-footer">
          <p>UnityGrid AI v1.0</p>
          <p style="margin-top:4px">Backend: localhost:8000</p>
        </div>
      </nav>
      <main class="main-content" id="page-content"></main>
    </div>
    <button class="btn btn-primary" id="mobile-menu" style="
      display:none;position:fixed;bottom:20px;right:20px;z-index:200;
      width:50px;height:50px;border-radius:50%;padding:0;justify-content:center;font-size:20px;
    ">☰</button>
  `;

  // Nav click handlers
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const page = item.dataset.page;
      if (page && PAGES[page]) navigate(page);
    });
  });

  // Mobile menu
  const mobileBtn = document.getElementById('mobile-menu');
  const sidebar = document.getElementById('sidebar');
  if (window.innerWidth <= 1024) mobileBtn.style.display = 'flex';
  mobileBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
  window.addEventListener('resize', () => {
    mobileBtn.style.display = window.innerWidth <= 1024 ? 'flex' : 'none';
    if (window.innerWidth > 1024) sidebar.classList.remove('open');
  });
}

async function navigate(page) {
  currentPage = page;
  // Update active nav
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
  // Close mobile sidebar
  document.getElementById('sidebar').classList.remove('open');
  // Render page
  const content = document.getElementById('page-content');
  content.innerHTML = '<div class="spinner"></div>';
  try {
    await PAGES[page].render(content);
  } catch (e) {
    content.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><p>Error loading page: ${e.message}</p></div>`;
  }
}

// Init
buildLayout();
navigate('dashboard');
