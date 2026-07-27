(() => {
  // Mobile nav toggle
  const navToggle = document.getElementById('nav-toggle');
  const navLinks = document.getElementById('nav-links');
  navToggle.addEventListener('click', () => {
    const open = navLinks.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(open));
  });
  navLinks.addEventListener('click', (e) => {
    if (e.target.tagName === 'A') navLinks.classList.remove('open');
  });

  // Footer year
  document.getElementById('footer-year').textContent = new Date().getFullYear();

  const projectGrid = document.getElementById('projects-grid');

  const escapeHtml = (value) => String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

  const statusClass = (status) => `badge-${String(status).toLowerCase().replaceAll(' ', '-')}`;

  const renderProjects = (projects) => {
    projectGrid.innerHTML = projects.map((project) => `
      <article class="project-card">
        <h3 class="project-card-title">${escapeHtml(project.name)}</h3>
        <p class="project-card-desc">${escapeHtml(project.description)}</p>
        <div class="project-card-meta">
          <span class="badge ${statusClass(project.status)}">${escapeHtml(project.status)}</span>
          <span class="badge">${escapeHtml(project.license)}</span>
        </div>
        <a class="project-card-link" href="${escapeHtml(project.url)}">View project</a>
      </article>
    `).join('');
  };

  fetch('data/projects.json')
    .then((response) => {
      if (!response.ok) throw new Error(`Unable to load projects: ${response.status}`);
      return response.json();
    })
    .then(renderProjects)
    .catch(() => {
      projectGrid.innerHTML = '<p class="project-card-desc">Projects could not be loaded.</p>';
    });
})();
