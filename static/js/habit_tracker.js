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

const habitIcons = {
  water: '/static/images/habit-icons/water.png',
  food: '/static/images/habit-icons/food.png',
  exercise: '/static/images/habit-icons/exercise.png',
  sleep: '/static/images/habit-icons/sleep.png',
  mindfulness: '/static/images/habit-icons/mindfulness.png'
};

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

    // KPI Streak Elements
    const kpiStreak = document.getElementById('kpi-streak');
    const kpiStreakSub = document.getElementById('kpi-streak-sub');

    // KPI General Elements
    const kpiCompleted = document.getElementById('kpi-completed');
    const kpiRemaining = document.getElementById('kpi-remaining');
    const progressBar = document.getElementById('habit-progress-bar');
    const progressPercent = document.getElementById('habit-progress-percent');
    const completedProgress = document.getElementById('kpi-completed-progress');
    const focusProgress = document.getElementById('kpi-focus-progress');

    // KPI Focus Elements
    const kpiFocus = document.getElementById('kpi-focus');
    const kpiFocusTargetText = document.getElementById('kpi-focus-target-text');
    const badgeContainer = document.getElementById('kpi-focus-badge-container');

    // Update KPI Streak & Best Streak
    if (kpiStreak && data.summary.streak !== undefined) {
      kpiStreak.innerText = `${data.summary.streak} hari`;
    }
    if (kpiStreakSub && data.summary.best_streak !== undefined) {
      kpiStreakSub.innerText = `Rekor terbaik: ${data.summary.best_streak} hari`;
    }

    // Update KPI Kebiasaan
    if (kpiCompleted) kpiCompleted.innerText = `${data.summary.completed} / ${data.summary.total}`;
    if (kpiRemaining) kpiRemaining.innerText = `${data.summary.total - data.summary.completed} target belum selesai`;
    if (progressBar) progressBar.style.width = `${data.summary.progress_percent}%`;
    if (completedProgress) {
      completedProgress.style.width = `${data.summary.progress_percent}%`;
    }
    if (progressPercent) {
      progressPercent.innerText = `${data.summary.progress_percent}%`;
    }

    const weeklyChart = document.getElementById('weekly-consistency-chart');
    if (weeklyChart && data.summary.weekly_consistency) {
      weeklyChart.innerHTML = '';

      data.summary.weekly_consistency.forEach(day => {
        const column = document.createElement('div');
        const state = day.is_future
          ? 'future'
          : day.is_current
            ? 'current'
            : 'past';

        column.className = `weekly-consistency-column ${state}`;
        column.innerHTML = `
          <span class="weekly-consistency-percent">${day.percent}%</span>
          <div class="weekly-consistency-bar-wrap">
            <div class="weekly-consistency-bar" style="height: ${day.percent}%;"></div>
          </div>
          <span class="weekly-consistency-day">${day.day_name}</span>
        `;

        weeklyChart.appendChild(column);
      });
    }
    
    // Update KPI Waktu Fokus
    if (kpiFocus) {
      kpiFocus.innerText = data.summary.focus_time_str || '0m';
    }

    const hydration = data.summary.hydration;
    if (hydration) {
      const amount = document.getElementById('hydration-amount');
      const remaining = document.getElementById('hydration-remaining');
      const hydrationBottle = document.getElementById('hydration-bottle');
      const hydrationBottleWater = document.getElementById('hydration-bottle-water');
      const hydrationStatus = document.getElementById('hydration-status');

      if (amount) amount.innerText = `${hydration.amount_ml} ml`;
      if (remaining) {
        remaining.innerText = hydration.target_reached
          ? ''
          : `Sisa ${hydration.remaining_ml} ml`;
      }
      if (hydrationStatus) {
        hydrationStatus.innerHTML = hydration.target_reached
          ? '<span class="target-badge">✓ Target tercapai!</span>'
          : '';
      }
      if (hydrationBottleWater) {
        const remainingPercent = Math.max(0, 100 - hydration.progress_percent);
        hydrationBottleWater.style.height = `${remainingPercent}%`;
      }
      if (hydrationBottle) {
        hydrationBottle.classList.toggle('target-reached', hydration.target_reached);
      }
    }

    if (kpiFocusTargetText) {
      kpiFocusTargetText.innerText = `Target: ${data.summary.target_focus_str || '0m'}`;
      const inputFocusTarget = document.getElementById('input-focus-minutes');
      if (inputFocusTarget) inputFocusTarget.value = data.summary.target_focus_minutes;
    }

    if (focusProgress) {
      const target = Number(data.summary.target_focus_minutes || 0);
      const logged = Number(data.summary.logged_focus_minutes || 0);
      const focusPercent = target > 0
        ? Math.min(100, Math.round((logged / target) * 100))
        : 0;
      focusProgress.style.width = `${focusPercent}%`;
    }

    if (badgeContainer) {
      if (data.summary.is_target_reached) {
        badgeContainer.innerHTML = '<span class="target-badge">✓ Target tercapai!</span>';
      } else {
        badgeContainer.innerHTML = '';
      }
    }

    // Update Card Kualitas Tidur (7 Malam Terakhir)
    if (data.summary.sleep) {
      const sleepVal = document.getElementById('sleep-last-night-val');
      const sleepLegendTarget = document.getElementById('sleep-legend-target-text');
      const chartContainer = document.getElementById('sleep-chart-container');

      if (sleepVal) sleepVal.innerText = data.summary.sleep.last_night_str || '0j 0m';
      if (sleepLegendTarget) sleepLegendTarget.innerText = `Target ${data.summary.sleep.target_str}`;

      // Update input modal sleep
      const inputTarget = document.getElementById('input-sleep-target');
      const inputHours = document.getElementById('input-sleep-hours');
      const inputMins = document.getElementById('input-sleep-minutes');

      if (inputTarget) inputTarget.value = data.summary.sleep.target_hours;
      if (inputHours) inputHours.value = data.summary.sleep.last_night_hours;
      if (inputMins) inputMins.value = data.summary.sleep.last_night_mins;

      // Render 7 Bars
      if (chartContainer && data.summary.sleep.bars) {
        chartContainer.innerHTML = '';
        data.summary.sleep.bars.forEach(bar => {
          const col = document.createElement('div');
          col.className = 'sleep-bar-col';
          col.innerHTML = `
            <div class="sleep-bar-wrapper">
              <div class="sleep-bar ${bar.is_latest ? 'latest' : ''}" style="height: ${bar.height_percent}%;">
                <span class="sleep-tooltip">${bar.duration_str}</span>
              </div>
            </div>
            <div class="sleep-day-label">${bar.day_initial}</div>
          `;
          chartContainer.appendChild(col);
        });
      }
    }

    // Render Daftar Kebiasaan (Habit List)
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
      const habitIcon = habitIcons[h.category] || habitIcons.mindfulness;
      row.innerHTML = `
        <div class="habit-category-icon" aria-hidden="true">
          <img src="${habitIcon}" alt="">
        </div>
        <div class="habit-info">
          <h4>${escapeHtml(h.title)}</h4>
          <p>${h.current_value} / ${h.target_value} ${escapeHtml(h.unit)} ${h.logged_time ? '• pukul ' + h.logged_time : ''}</p>
          <div class="habit-mini-progress"><span style="width:${h.progress_percent}%;"></span></div>
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
          <button class="btn-add-progress" onclick="addHabitProgress(${h.id})" aria-label="Tambah progress">Tambah</button>
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

let activeHabitProgressId = null;

function addHabitProgress(habitId) {
  const modal = document.getElementById('habit-progress-modal');
  const input = document.getElementById('input-habit-progress');
  if (!modal || !input) return;

  activeHabitProgressId = habitId;
  input.value = '';
  modal.classList.add('active');
  input.focus();
}

async function submitHabitProgress() {
  const input = document.getElementById('input-habit-progress');
  const value = Number(input.value);

  if (!Number.isInteger(value) || value < 1) {
    showToast('Progress harus berupa bilangan positif', 'error');
    input.focus();
    return;
  }

  const formData = new FormData();
  formData.append('additional_value', value);

  const res = await fetch(`/habit-tracker/api/progress/${activeHabitProgressId}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
    body: formData
  });

  if (res.ok) {
    showToast('Progress kebiasaan diperbarui!');
    document.getElementById('habit-progress-modal').classList.remove('active');
    loadHabits();
  } else {
    showToast('Gagal memperbarui progress', 'error');
  }
}

async function addHydration(amountMl) {
  const formData = new FormData();
  formData.append('amount_ml', amountMl);

  const res = await fetch('/habit-tracker/api/hydration/add/', {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
    body: formData
  });

  if (res.ok) {
    showToast(`Hidrasi bertambah ${amountMl} ml`);
    loadHabits();
  } else {
    showToast('Gagal mencatat hidrasi', 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  renderWeeklyCalendar();
  loadHabits();

  const habitProgressModal = document.getElementById('habit-progress-modal');
  const habitProgressForm = document.getElementById('form-habit-progress');
  const closeHabitProgress = document.getElementById('btn-close-habit-progress');

  if (closeHabitProgress && habitProgressModal) {
    closeHabitProgress.onclick = () => habitProgressModal.classList.remove('active');
  }

  if (habitProgressForm) {
    habitProgressForm.onsubmit = async (event) => {
      event.preventDefault();
      await submitHabitProgress();
    };
  }

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

  // Modal Sleep Settings Form
  const modalSleep = document.getElementById('sleep-modal');
  const btnOpenSleep = document.getElementById('btn-open-sleep-modal');
  const btnCloseSleep = document.getElementById('btn-close-sleep-modal');
  const formLogSleep = document.getElementById('form-log-sleep');

  if (btnOpenSleep && modalSleep) btnOpenSleep.onclick = () => modalSleep.classList.add('active');
  if (btnCloseSleep && modalSleep) btnCloseSleep.onclick = () => modalSleep.classList.remove('active');

  if (formLogSleep) {
    formLogSleep.onsubmit = async (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);

      const res = await fetch('/habit-tracker/api/sleep/settings/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData
      });

      if (res.ok) {
        const result = await res.json();
        showToast(result.message || 'Pengaturan tidur disimpan!');
        if (modalSleep) modalSleep.classList.remove('active');
        loadHabits();
      } else {
        showToast('Gagal menyimpan pengaturan tidur', 'error');
      }
    };
  }
});
