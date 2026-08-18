'use strict';
/* Карточки направлений: данные из /api/destinations (конфиг config/destinations.yaml) */
(function () {
  const grid = document.getElementById('destinationsGrid');
  if (!grid) return;

  const CONFIG = {
    destinationsApi: '/api/destinations',
    chatUrl: id => `/chat.html?dest=${encodeURIComponent(id)}`,
  };

  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  fetch(CONFIG.destinationsApi)
    .then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)))
    .then(data => {
      const list = data.destinations || data || [];
      if (!Array.isArray(list) || !list.length) {
        grid.innerHTML = '<p class="section-subtitle">Направления скоро появятся 🌱</p>';
        return;
      }
      grid.innerHTML = list.map(d => `
        <div class="destination-card">
          <div class="card-icon">${d.emoji || d.image || '🌍'}</div>
          <h3 class="card-title">${esc(d.name)}</h3>
          <p class="card-description">${esc(d.description || '')}</p>
          <button class="card-btn" data-dest="${esc(d.destination_id || d.name)}">Подробнее →</button>
        </div>`).join('');
      grid.querySelectorAll('.card-btn').forEach(btn =>
        btn.addEventListener('click', () => { location.href = CONFIG.chatUrl(btn.dataset.dest); }));
    })
    .catch(() => {
      grid.innerHTML = '<p class="section-subtitle">Не удалось загрузить направления: проверьте, что бэкенд отдаёт /api/destinations.</p>';
    });
})();