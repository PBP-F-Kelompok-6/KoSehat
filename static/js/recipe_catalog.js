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

const articleDetailModal = document.getElementById("articleDetailModal");
const articleFormModal = document.getElementById("articleFormModal");

const articleModalLoading = document.getElementById("articleModalLoading");
const articleModalBody = document.getElementById("articleModalBody");

const articleForm = document.getElementById("articleForm");
const articleIdInput = document.getElementById("articleIdInput");
const articleTitleInput = document.getElementById("articleTitleInput");
const articleCategoryInput = document.getElementById("articleCategoryInput");
const articleReadTimeInput = document.getElementById("articleReadTimeInput");
const articleSnippetInput = document.getElementById("articleSnippetInput");
const articleContentInput = document.getElementById("articleContentInput");

const btnAddArticle = document.getElementById("btnAddArticle");
const btnDeleteArticle = document.getElementById("btnDeleteArticle");
const articleFormModalTitle = document.getElementById("articleFormModalTitle");

// URLs
const articleDetailUrlTemplate = articleDetailModal ? articleDetailModal.getAttribute("data-detail-url") : "";
  const articleCreateUrl = articleFormModal ? articleFormModal.getAttribute("data-create-url") : "";
  const articleUpdateUrlTemplate = articleFormModal ? articleFormModal.getAttribute("data-update-url") : "";
  const articleDeleteUrlTemplate = articleFormModal ? articleFormModal.getAttribute("data-delete-url") : "";

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

      if (!bookmarkUrlTemplate) {
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

  // Event Delegation: Tombol Tambah / Edit / Kartu Artikel
  document.addEventListener("click", (e) => {
    // Tombol Tambah Artikel
    const addBtn = e.target.closest("#btnAddArticle, .btn-add-article-icon");
    if (addBtn) {
      e.preventDefault();
      console.log("➕ [KoSehat] Tombol tambah artikel diklik!");
      openArticleFormModal();
      return;
    }

    // Tombol Edit Artikel
    const editBtn = e.target.closest(".btn-edit-article-sm");
    if (editBtn && editBtn.dataset.editId) {
      e.stopPropagation();
      console.log("✏️ [KoSehat] Tombol edit artikel diklik! ID:", editBtn.dataset.editId);
      openArticleFormModal(editBtn.dataset.editId);
      return;
    }

    // Klik Kartu Artikel (Lihat Detail)
    const card = e.target.closest(".article-card");
    if (card && card.dataset.articleId) {
      e.preventDefault();
      console.log("📖 [KoSehat] Kartu artikel diklik! ID:", card.dataset.articleId);
      openArticleDetailModal(card.dataset.articleId);
    }
  });

  // Fungsi Buka Modal Form (Create / Edit)
  function openArticleFormModal(articleId = null) {
    if (!articleFormModal) {
      console.error("❌ [KoSehat] Element #articleFormModal tidak ditemukan di DOM! Pastikan {% include 'article_modal.html' %} sudah terpasang.");
      return;
    }

    if (articleForm) articleForm.reset();
    if (articleIdInput) articleIdInput.value = "";

    if (articleId) {
      // Edit Mode
      if (articleFormModalTitle) articleFormModalTitle.textContent = "Edit Artikel Edukasi";
      if (btnDeleteArticle) btnDeleteArticle.style.display = "block";

      if (articleDetailUrlTemplate) {
        const url = articleDetailUrlTemplate.replace("0", articleId);
        fetch(url)
          .then((res) => res.json())
          .then((data) => {
            if (data.status === "success") {
              const a = data.article;
              if (articleIdInput) articleIdInput.value = a.id;
              if (articleTitleInput) articleTitleInput.value = a.title;
              if (articleCategoryInput) articleCategoryInput.value = a.category;
              if (articleReadTimeInput) articleReadTimeInput.value = a.read_time_minutes;
              if (articleSnippetInput) articleSnippetInput.value = a.snippet;
              if (articleContentInput) articleContentInput.value = a.content;
            }
          })
          .catch((err) => console.error("Error fetching article detail for edit:", err));
      }
    } else {
      // Create Mode
      if (articleFormModalTitle) articleFormModalTitle.textContent = "Tambah Artikel Edukasi";
      if (btnDeleteArticle) btnDeleteArticle.style.display = "none";
    }

    articleFormModal.classList.add("active");
    articleFormModal.setAttribute("aria-hidden", "false");
  }

  // Detail Reader Modal
  function openArticleDetailModal(articleId) {
    if (!articleDetailModal || !articleDetailUrlTemplate) {
      console.error("❌ [KoSehat] Element #articleDetailModal tidak ditemukan di DOM.");
      return;
    }

    const url = articleDetailUrlTemplate.replace("0", articleId);
    articleDetailModal.classList.add("active");
    articleDetailModal.setAttribute("aria-hidden", "false");
    
    if (articleModalLoading) articleModalLoading.style.display = "block";
    if (articleModalBody) articleModalBody.style.display = "none";

    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "success") {
          const a = data.article;
          const setTxt = (id, txt) => {
            const el = document.getElementById(id);
            if (el) el.textContent = txt;
          };

          setTxt("articleModalTitle", a.title);
          setTxt("articleCategoryBadge", a.category);
          setTxt("articleReadTime", a.read_time_minutes);
          setTxt("articleDate", a.created_at);
          setTxt("articleSnippet", a.snippet);
          setTxt("articleContentBody", a.content);

          if (articleModalLoading) articleModalLoading.style.display = "none";
          if (articleModalBody) articleModalBody.style.display = "block";
        }
      })
      .catch((err) => console.error("Gagal memuat detail artikel:", err));
  }

  // 4. Submit Form Handler (Create / Update)
  if (articleForm) {
    articleForm.addEventListener("submit", (e) => {
      e.preventDefault();

      const articleId = articleIdInput ? articleIdInput.value : "";
      const isEdit = Boolean(articleId);
      
      const targetUrl = isEdit
        ? (articleUpdateUrlTemplate ? articleUpdateUrlTemplate.replace("0", articleId) : "")
        : articleCreateUrl;

      if (!targetUrl) {
        console.error("❌ [KoSehat] Target URL submit artikel tidak valid.");
        return;
      }

      const payload = {
        title: articleTitleInput ? articleTitleInput.value : "",
        category: articleCategoryInput ? articleCategoryInput.value : "Nutrisi",
        read_time_minutes: articleReadTimeInput ? parseInt(articleReadTimeInput.value, 10) : 5,
        snippet: articleSnippetInput ? articleSnippetInput.value : "",
        content: articleContentInput ? articleContentInput.value : "",
      };

      fetch(targetUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify(payload),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.status === "success") {
            closeArticleModals();
            window.location.reload();
          } else {
            alert("Gagal menyimpan artikel. Periksa kembali inputan Anda.");
          }
        })
        .catch((err) => console.error("Error submit article:", err));
    });
  }

  // Delete Handler
  if (btnDeleteArticle) {
    btnDeleteArticle.addEventListener("click", () => {
      const articleId = articleIdInput ? articleIdInput.value : "";
      if (!articleId || !articleDeleteUrlTemplate) return;

      if (confirm("Apakah Anda yakin ingin menghapus artikel ini?")) {
        const deleteUrl = articleDeleteUrlTemplate.replace("0", articleId);

        fetch(deleteUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
          },
        })
          .then((res) => res.json())
          .then((data) => {
            if (data.status === "success") {
              closeArticleModals();
              window.location.reload();
            }
          })
          .catch((err) => console.error("Error delete article:", err));
      }
    });
  }

  // Close Modals Helper
  function closeArticleModals() {
    if (articleDetailModal) {
      articleDetailModal.classList.remove("active");
      articleDetailModal.setAttribute("aria-hidden", "true");
    }
    if (articleFormModal) {
      articleFormModal.classList.remove("active");
      articleFormModal.setAttribute("aria-hidden", "true");
    }
  }

  const btnCloseArticleDetail = document.getElementById("btnCloseArticleDetail");
  const btnCloseArticleDetailFooter = document.getElementById("btnCloseArticleDetailFooter");
  const btnCloseArticleForm = document.getElementById("btnCloseArticleForm");
  const btnCancelArticleForm = document.getElementById("btnCancelArticleForm");

  if (btnCloseArticleDetail) btnCloseArticleDetail.addEventListener("click", closeArticleModals);
  if (btnCloseArticleDetailFooter) btnCloseArticleDetailFooter.addEventListener("click", closeArticleModals);
  if (btnCloseArticleForm) btnCloseArticleForm.addEventListener("click", closeArticleModals);
  if (btnCancelArticleForm) btnCancelArticleForm.addEventListener("click", closeArticleModals);
  
  const modeTabs = document.querySelectorAll(".mode-tab");
  const catalogContainer = document.getElementById("catalogContainer");

  if (modeTabs.length > 0) {
    modeTabs.forEach((tab) => {
      tab.addEventListener("click", function (e) {
        e.preventDefault();
        
        // Pindah class 'active' ke tombol yang baru diklik
        modeTabs.forEach((t) => t.classList.remove("active"));
        this.classList.add("active");

        // Ambil nilai data-mode (semua / resep / edukasi)
        const selectedMode = this.dataset.mode || "semua";

        // Ubah attribute data-view-mode di container utama
        if (catalogContainer) {
          catalogContainer.setAttribute("data-view-mode", selectedMode);
        }
      });
    });
  }
});