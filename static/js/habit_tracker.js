function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function escapeHtml(str) {
  return String(str ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `alert alert-${type}`;
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// Fungsi pembantu untuk tombol cepat (+15m, +25m, dll.) pada modal fokus
function setQuickMinutes(mins) {
  const input = document.getElementById('input-additional-minutes');
  if (input) input.value = mins;
}

function renderWeeklyCalendar() {
  const today = new Date();
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const monthLabel = document.getElementById('calendar-month-label');
  if (monthLabel) {
    monthLabel.innerText = monthNames[today.getMonth()];
  }

  const dayOfWeek = today.getDay();
  const distanceToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const monday = new Date(today);
  monday.setDate(today.getDate() + distanceToMonday);

  const dayNamesEng = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const stripContainer = document.getElementById('day-selector-strip');
  if (!stripContainer) return;

  stripContainer.innerHTML = '';

  for (let i = 0; i < 7; i++) {
    const currentDate = new Date(monday);
    currentDate.setDate(monday.getDate() + i);

    const isToday =
      currentDate.getDate() === today.getDate() &&
      currentDate.getMonth() === today.getMonth() &&
      currentDate.getFullYear() === today.getFullYear();

    const isOtherMonth = currentDate.getMonth() !== today.getMonth();
    const dayNumStr = String(currentDate.getDate()).padStart(2, '0');

    const card = document.createElement('div');
    card.className = `day-card ${isToday ? 'active' : ''} ${isOtherMonth ? 'other-month' : ''}`;
    card.innerHTML = `
      <div class="day-name">${dayNamesEng[i]}</div>
      <div class="day-num">${dayNumStr}</div>
    `;

    stripContainer.appendChild(card);
  }
}

async function loadHabits() {
  try {
    const res = await fetch('/habit-tracker/api/habits/');
    if (!res.ok) throw new Error('Gagal memuat data');
    const data = await res.json();

    const kpiCompleted = document.getElementById('kpi-completed');
    const kpiRemaining = document.getElementById('kpi-remaining');
    const progressBar = document.getElementById('habit-progress-bar');
    const kpiEnergy = document.getElementById('kpi-energy');

    // KPI Focus Elements
    const kpiFocus = document.getElementById('kpi-focus');
    const kpiFocusTargetText = document.getElementById('kpi-focus-target-text');
    const badgeContainer = document.getElementById('kpi-focus-badge-container');

    if (kpiCompleted) kpiCompleted.innerText = `${data.summary.completed} / ${data.summary.total}`;
    if (kpiRemaining) kpiRemaining.innerText = `${data.summary.total - data.summary.completed} target belum selesai`;
    if (progressBar) progressBar.style.width = `${data.summary.progress_percent}%`;
    
    if (kpiEnergy && data.summary.energy_level !== undefined) {
      kpiEnergy.innerText = `${data.summary.energy_level} / 10`;
      const inputEnergy = document.getElementById('input-energy-level');
      if (inputEnergy) inputEnergy.value = data.summary.energy_level;
    }

    // Update KPI Waktu Fokus
    if (kpiFocus) {
      kpiFocus.innerText = data.summary.focus_time_str || '0m';
    }

    if (kpiFocusTargetText) {
      kpiFocusTargetText.innerText = `Target: ${data.summary.target_focus_str || '0m'}`;
      const inputFocusTarget = document.getElementById('input-focus-minutes');
      if (inputFocusTarget) inputFocusTarget.value = data.summary.target_focus_minutes;
    }

    if (badgeContainer) {
      if (data.summary.is_target_reached) {
        badgeContainer.innerHTML = '<span class="target-badge">✓ Target tercapai!</span>';
      } else {
        badgeContainer.innerHTML = '';
      }
    }

    const container = document.getElementById('habit-list-container');
    if (!container) return;
    container.innerHTML = '';

    if (data.habits.length === 0) {
      container.innerHTML = '<p style="text-align:center; color:#888; padding:20px;">Belum ada kebiasaan. Tambahkan sekarang!</p>';
      return;
    }

    data.habits.forEach(h => {
      const row = document.createElement('div');
      row.className = `habit-row ${h.is_completed ? 'completed' : ''}`;
      row.innerHTML = `
        <div class="habit-info">
          <h4>${escapeHtml(h.title)}</h4>
          <p>${h.current_value} ${escapeHtml(h.unit)} ${h.logged_time ? '• pukul ' + h.logged_time : ''}</p>
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
          <button class="checkbox-circle ${h.is_completed ? 'checked' : ''}" onclick="toggleHabit(${h.id})">
            ${h.is_completed ? '✓' : ''}
          </button>
          <button onclick="deleteHabit(${h.id})" style="background:none; border:none; color:#dc2626; cursor:pointer; font-size:12px;">Hapus</button>
        </div>
      `;
      container.appendChild(row);
    });
  } catch (err) {
    showToast('Gagal memperbarui kebiasaan', 'error');
  }
}

async function toggleHabit(habitId) {
  const res = await fetch(`/habit-tracker/api/toggle/${habitId}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') }
  });
  if (res.ok) {
    showToast('Progres kebiasaan diperbarui!');
    loadHabits();
  }
}

async function deleteHabit(habitId) {
  if (!confirm('Hapus kebiasaan ini?')) return;
  const res = await fetch(`/habit-tracker/api/delete/${habitId}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') }
  });
  if (res.ok) {
    showToast('Kebiasaan berhasil dihapus');
    loadHabits();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  renderWeeklyCalendar();
  loadHabits();

  // Modal Habit Form
  const modalHabit = document.getElementById('habit-modal');
  const btnOpenHabit = document.getElementById('btn-open-modal');
  const btnCloseHabit = document.getElementById('btn-close-modal');
  const formAddHabit = document.getElementById('form-add-habit');

  if (btnOpenHabit && modalHabit) btnOpenHabit.onclick = () => modalHabit.classList.add('active');
  if (btnCloseHabit && modalHabit) btnCloseHabit.onclick = () => modalHabit.classList.remove('active');

  if (formAddHabit) {
    formAddHabit.onsubmit = async (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);
      const res = await fetch('/habit-tracker/api/add/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData
      });

      if (res.ok) {
        showToast('Kebiasaan baru berhasil disimpan!');
        if (modalHabit) modalHabit.classList.remove('active');
        e.target.reset();
        loadHabits();
      } else {
        showToast('Gagal menyimpan kebiasaan', 'error');
      }
    };
  }

  // Modal Energy Form
  const modalEnergy = document.getElementById('energy-modal');
  const btnOpenEnergy = document.getElementById('btn-open-energy-modal');
  const btnCloseEnergy = document.getElementById('btn-close-energy-modal');
  const formLogEnergy = document.getElementById('form-log-energy');

  if (btnOpenEnergy && modalEnergy) btnOpenEnergy.onclick = () => modalEnergy.classList.add('active');
  if (btnCloseEnergy && modalEnergy) btnCloseEnergy.onclick = () => modalEnergy.classList.remove('active');

  if (formLogEnergy) {
    formLogEnergy.onsubmit = async (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);
      const res = await fetch('/habit-tracker/api/energy/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData
      });

      if (res.ok) {
        showToast('Refleksi energi & fokus disimpan!');
        if (modalEnergy) modalEnergy.classList.remove('active');
        loadHabits();
      } else {
        showToast('Gagal menyimpan refleksi energi', 'error');
      }
    };
  }

  // Modal Add Focus Time Form
  const modalAddFocus = document.getElementById('add-focus-modal');
  const btnOpenAddFocus = document.getElementById('btn-open-add-focus-modal');
  const btnCloseAddFocus = document.getElementById('btn-close-add-focus-modal');
  const formAddFocus = document.getElementById('form-add-focus-time');

  if (btnOpenAddFocus && modalAddFocus) btnOpenAddFocus.onclick = () => modalAddFocus.classList.add('active');
  if (btnCloseAddFocus && modalAddFocus) btnCloseAddFocus.onclick = () => modalAddFocus.classList.remove('active');

  if (formAddFocus) {
    formAddFocus.onsubmit = async (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);
      
      const res = await fetch('/habit-tracker/api/focus/add/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData
      });

      if (res.ok) {
        const result = await res.json();
        showToast(result.message || 'Waktu fokus berhasil ditambahkan!');
        if (modalAddFocus) modalAddFocus.classList.remove('active');
        e.target.reset();
        const inputMinutes = document.getElementById('input-additional-minutes');
        if (inputMinutes) inputMinutes.value = 25;
        loadHabits();
      } else {
        showToast('Gagal menambahkan waktu fokus', 'error');
      }
    };
  }
});