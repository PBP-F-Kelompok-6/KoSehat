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
  const toast = document.createElement('div');
  toast.className = `alert alert-${type}`;
  toast.style.padding = '12px 20px';
  toast.style.borderRadius = '8px';
  toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
  toast.innerText = message;

  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

async function loadHabits() {
  try {
    const res = await fetch('/habit-tracker/api/habits/');
    if (!res.ok) throw new Error('Gagal memuat data');
    const data = await res.json();

    // Render Summary KPIs
    document.getElementById('kpi-completed').innerText = `${data.summary.completed} / ${data.summary.total}`;
    document.getElementById('kpi-remaining').innerText = `${data.summary.total - data.summary.completed} target belum selesai`;
    document.getElementById('habit-progress-bar').style.width = `${data.summary.progress_percent}%`;

    // Render List Kebiasaan
    const container = document.getElementById('habit-list-container');
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

// Modal Toggle Handler
const modal = document.getElementById('habit-modal');
document.getElementById('btn-open-modal').onclick = () => modal.classList.add('active');
document.getElementById('btn-close-modal').onclick = () => modal.classList.remove('active');

// Submit Form Handler
document.getElementById('form-add-habit').onsubmit = async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  
  const res = await fetch('/habit-tracker/api/add/', {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
    body: formData
  });

  if (res.ok) {
    showToast('Kebiasaan baru berhasil disimpan!');
    modal.classList.remove('active');
    e.target.reset();
    loadHabits();
  } else {
    showToast('Gagal menyimpan kebiasaan', 'error');
  }
};

// Initial Load
document.addEventListener('DOMContentLoaded', loadHabits);

function renderWeeklyCalendar() {
  const today = new Date();

  // 1. Set Keterangan Bulan Berdasarkan Hari Ini
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const monthLabel = document.getElementById('calendar-month-label');
  if (monthLabel) {
    monthLabel.innerText = monthNames[today.getMonth()];
  }

  // 2. Hitung Tanggal Hari Senin pada Minggu Berjalan
  const dayOfWeek = today.getDay(); // 0 = Minggu, 1 = Senin, ..., 6 = Sabtu
  const distanceToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const monday = new Date(today);
  monday.setDate(today.getDate() + distanceToMonday);

  const dayNamesEng = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const stripContainer = document.getElementById('day-selector-strip');
  if (!stripContainer) return;

  stripContainer.innerHTML = '';

  // 3. Render 7 Hari (Mon - Sun)
  for (let i = 0; i < 7; i++) {
    const currentDate = new Date(monday);
    currentDate.setDate(monday.getDate() + i);

    // Cek Apakah Hari Ini
    const isToday =
      currentDate.getDate() === today.getDate() &&
      currentDate.getMonth() === today.getMonth() &&
      currentDate.getFullYear() === today.getFullYear();

    // Cek Apakah Berada di Bulan Lain Dibanding Hari Ini
    const isOtherMonth = currentDate.getMonth() !== today.getMonth();

    const dayNumStr = String(currentDate.getDate()).padStart(2, '0');

    // Buat Elemen Card
    const card = document.createElement('div');
    card.className = `day-card ${isToday ? 'active' : ''} ${isOtherMonth ? 'other-month' : ''}`;
    card.innerHTML = `
      <div class="day-name">${dayNamesEng[i]}</div>
      <div class="day-num">${dayNumStr}</div>
    `;

    stripContainer.appendChild(card);
  }
}

// Panggil fungsi saat halaman dimuat
document.addEventListener('DOMContentLoaded', () => {
  renderWeeklyCalendar();
  loadHabits(); // Fungsi loadHabits yang sudah ada sebelumnya
});