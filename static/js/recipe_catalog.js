document.addEventListener("DOMContentLoaded", function () {
const searchInput = document.getElementById("recipeSearchInput");
const recipeGrid = document.getElementById("recipeGrid");
const recipeCount = document.getElementById("recipeCount");
const filterBtns = document.querySelectorAll(".pill-btn");

const filterContainer = document.getElementById("filterContainer");
const baseUrl = filterContainer ? filterContainer.getAttribute("data-url") : "";

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
    <div class="recipe-card-item">
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
});