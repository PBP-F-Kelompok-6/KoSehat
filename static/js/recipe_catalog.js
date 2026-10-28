document.addEventListener("DOMContentLoaded", function () {
const searchInput = document.getElementById("recipeSearchInput");
const recipeGrid = document.getElementById("recipeGrid");
const recipeCount = document.getElementById("recipeCount");
const filterBtns = document.querySelectorAll(".pill-btn");

const filterContainer = document.getElementById("filterContainer");
const baseUrl = filterContainer ? filterContainer.getAttribute("data-url") : "";

const modalOverlay = document.getElementById('recipeDetailModal');
const modalLoading = document.getElementById('modalLoading');
const modalBody = document.getElementById('modalBody');
const btnCloseModal = document.getElementById('btnCloseModal');
const btnCloseModalFooter = document.getElementById('btnCloseModalFooter');
const btnBookmarkModal = document.getElementById('btnBookmarkModal');

// Ambil Template URL dari Modal HTML
  const detailUrlTemplate = modalOverlay ? modalOverlay.getAttribute("data-detail-url") : "";
  const bookmarkUrlTemplate = modalOverlay ? modalOverlay.getAttribute("data-bookmark-url") : "";

function fetchFilteredRecipes(query = "", tag = "") {
    if (!baseUrl) {
        console.error("Gagal mengambil data-url dari HTML.");
        return;
    }

    const url = `${baseUrl}?q=${encodeURIComponent(query)}&tag=${encodeURIComponent(tag)}`;
    fetch(url)
    .then((res) => res.json())
    .then((data) => {
        if (data.status === "success") {
        renderRecipes(data.recipes);
        }
    })
    .catch((err) => console.error("Error fetching recipes:", err));
}

function renderRecipes(recipes) {
    if (recipeCount) recipeCount.textContent = recipes.length;
    if (!recipes || recipes.length === 0) {
    recipeGrid.innerHTML =
        '<p class="empty-msg">Tidak ada resep yang sesuai dari Spoonacular API.</p>';
    return;
    }
    recipeGrid.innerHTML = recipes
    .slice(0, 6)
    .map(
        (r) => `
    <div class="recipe-card-item" data-recipe-id="${r.id}" style="cursor: pointer;">
    <img src="${r.image_url}" alt="${r.title}" class="recipe-card-img" />
    <div class="recipe-card-content">
        <span class="recipe-tag">${r.tag}</span>
        <h3 class="font-serif-heading">${r.title}</h3>
        <div class="recipe-card-footer">
        🕒 ${r.prep_time_minutes} menit • ${r.estimated_cost_formatted} • ${r.protein_grams} g protein
        </div>
    </div>
    </div>
`,
    )
    .join("");
}

let timeout = null;
if (searchInput) {
    searchInput.addEventListener("input", function () {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
        fetchFilteredRecipes(searchInput.value);
    }, 300);
    });
}

filterBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
    filterBtns.forEach((b) => b.classList.remove("active"));
    this.classList.add("active");
    const tag = this.dataset.tag || "";
    fetchFilteredRecipes(
        searchInput ? searchInput.value : "",
        tag === "Semua" ? "" : tag,
    );
    });
});

let currentActiveRecipeId = null;

  // 2. Event Delegation untuk Klik Card Resep
  document.addEventListener('click', (event) => {
    const card = event.target.closest('.recipe-card-item, .featured-editor-card');
    if (card && card.dataset.recipeId) {
      event.preventDefault();
      openRecipeModal(card.dataset.recipeId);
    }
  });

  // 3. Fungsi Membuka Modal & Mengambil Detail Resep via AJAX
  function openRecipeModal(recipeId) {
    if (!detailUrlTemplate) {
      console.error("Template detail-url tidak ditemukan di HTML modal.");
      return;
    }

    currentActiveRecipeId = recipeId;

    // Replace dummy '0' dengan recipeId aktual
    const detailUrl = detailUrlTemplate.replace("0", recipeId);
    
    // Tampilkan modal overlay & spinner loading
    modalOverlay.classList.add('active');
    modalOverlay.setAttribute('aria-hidden', 'false');
    modalLoading.style.display = 'block';
    modalBody.style.display = 'none';

    // Reset status tombol bookmark
    btnBookmarkModal.textContent = 'Bookmark Resep';
    btnBookmarkModal.style.backgroundColor = '';

    fetch(detailUrl)
      .then((response) => {
        if (!response.ok) throw new Error('Gagal mengambil data resep.');
        return response.json();
      })
      .then((data) => {
        if (data.status === 'success') {
          populateModalData(data.recipe);
          modalLoading.style.display = 'none';
          modalBody.style.display = 'block';
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        alert('Terjadi kesalahan saat memuat detail resep.');
        closeModal();
      });
  }

  // 4. Inject Data Resep ke DOM Modal
  function populateModalData(recipe) {
    document.getElementById('modalRecipeImage').src = recipe.image_url;
    document.getElementById('modalRecipeTitle').textContent = recipe.title;
    document.getElementById('modalRecipeTag').textContent = recipe.tag;
    document.getElementById('modalRecipeTime').textContent = recipe.prep_time_minutes;
    document.getElementById('modalRecipeCost').textContent = recipe.estimated_cost_formatted;
    document.getElementById('modalRecipeProtein').textContent = recipe.protein_grams;
    document.getElementById('modalRecipeDesc').textContent = recipe.description;

    // Render Bahan
    const ingredientsList = document.getElementById('modalIngredientsList');
    ingredientsList.innerHTML = recipe.ingredients && recipe.ingredients.length > 0
      ? recipe.ingredients.map(ing => `<li>${ing.amount || ''} ${ing.unit || ''} ${ing.name}</li>`).join('')
      : '<li>Bahan-bahan tidak spesifik</li>';

    // Render Peralatan
    const equipmentsList = document.getElementById('modalEquipmentsList');
    equipmentsList.innerHTML = recipe.equipments && recipe.equipments.length > 0
      ? recipe.equipments.map(eq => `<li>${eq}</li>`).join('')
      : '<li>Alat standar dapur</li>';

    // Render Langkah Pembuatan
    const instructionsList = document.getElementById('modalInstructionsList');
    instructionsList.innerHTML = recipe.instructions && recipe.instructions.length > 0
      ? recipe.instructions.map(step => `<li>${step.step}</li>`).join('')
      : '<li>Ikuti petunjuk dasar penyiapan bahan.</li>';
  }

  // 5. Fungsi Menutup Modal
  function closeModal() {
    modalOverlay.classList.remove('active');
    modalOverlay.setAttribute('aria-hidden', 'true');
    currentActiveRecipeId = null;
  }

  // 6. Event Listeners Penutupan Modal (Klik Tombol X, Tombol Selesai, Backdrop, & Tombol ESC)
  if (btnCloseModal) btnCloseModal.addEventListener('click', closeModal);
  if (btnCloseModalFooter) btnCloseModalFooter.addEventListener('click', closeModal);

  modalOverlay.addEventListener('click', (event) => {
    if (event.target === modalOverlay) closeModal();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modalOverlay.classList.contains('active')) {
      closeModal();
    }
  });

  // 7. Handler Bookmark dari Modal (CSRF Protected)
  if (btnBookmarkModal) {
    btnBookmarkModal.addEventListener('click', () => {
      if (!currentActiveRecipeId) return;

      if (!detailBookmarkTemplate) {
        console.error("Template bookmark-url tidak ditemukan di HTML modal.");
        return;
        }

    // Replace dummy '0' dengan recipeId aktual
    const bookmarkUrl = bookmarkUrlTemplate.replace("0", currentActiveRecipeId);

      fetch(bookmarkUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'Content-Type': 'application/json'
        }
      })
      .then(res => res.json())
      .then(resData => {
        if (resData.status === 'bookmarked') {
          btnBookmarkModal.textContent = 'Disimpan ✓';
          btnBookmarkModal.style.backgroundColor = '#bbf7d0';
        } else {
          btnBookmarkModal.textContent = 'Bookmark Resep';
          btnBookmarkModal.style.backgroundColor = '#fce762';
        }
      })
      .catch(err => console.error('Gagal memperbarui bookmark:', err));
    });
  }

  // Helper untuk Membaca Cookie CSRF Token
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
});