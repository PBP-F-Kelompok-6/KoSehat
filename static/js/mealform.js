// Hitung kalori otomatis di form menu (modul Meal Planner).
// Mengirim daftar bahan ke server (AJAX/fetch), server memanggil API USDA,
// lalu hasilnya mengisi kolom kalori tanpa reload halaman.
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('calc-kcal');
  if (!btn) return;

  const result = document.getElementById('calc-result');
  const input = document.getElementById('ingredients-input');
  const caloriesField = document.getElementById('id_calories');
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    btn.textContent = 'Menghitung...';
    result.textContent = '';
    try {
      const res = await fetch(btn.dataset.url, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: new URLSearchParams({ ingredients: input.value }),
      });
      const data = await res.json();
      if (!res.ok) {
        result.textContent = data.error;
        return;
      }
      caloriesField.value = data.kcal;
      result.textContent =
        data.items
          .map((i) => `${i.name} (${i.per_100g} kkal/100 g) x ${i.grams} g = ${i.kcal} kkal`)
          .join(' | ') + ` -> total ${data.kcal} kkal (perkiraan, boleh diubah)`;
    } catch (e) {
      result.textContent = 'Gagal menghubungi server.';
    } finally {
      btn.disabled = false;
      btn.textContent = 'Hitung kalori';
    }
  });
});