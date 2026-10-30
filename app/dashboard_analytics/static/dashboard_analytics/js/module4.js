(() => {
  const toast = document.getElementById("m4-toast");
  const modal = document.getElementById("m4-habit-modal");
  const budgetModal = document.getElementById("m4-budget-modal");
  const walkingModal = document.getElementById("m4-walking-modal");
  const walkingEditModal = document.getElementById("m4-walking-edit-modal");
  let toastTimer;

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.hidden = false;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => { toast.hidden = true; }, 3600);
  }

  function openModal() {
    if (!modal) return;
    modal.hidden = false;
    const amount = document.getElementById("m4-habit-amount");
    if (amount) amount.focus();
  }
  function closeModal() {
    if (modal) modal.hidden = true;
  }

  function openBudgetModal() {
  if (!budgetModal) return;
  budgetModal.hidden = false;

  const amount = document.getElementById("m4-budget-amount");
  if (amount) amount.focus();
}

  function closeBudgetModal() {
  if (budgetModal) budgetModal.hidden = true;
}

  function openWalkingModal() {
    if (!walkingModal) return;
    walkingModal.hidden = false;
    document.getElementById("m4-walking-duration")?.focus();
  }

  function closeWalkingModal() {
    if (walkingModal) walkingModal.hidden = true;
  }

  function closeWalkingEditModal() {
    if (walkingEditModal) walkingEditModal.hidden = true;
  }

  document.addEventListener("click", async (event) => {
    const control = event.target.closest("[data-action]");
    if (!control) {
      if (event.target === modal) closeModal();
      if (event.target === budgetModal) closeBudgetModal();
      if (event.target === walkingModal) closeWalkingModal();
      if (event.target === walkingEditModal) closeWalkingEditModal();
      return;
    }
    const action = control.dataset.action;
    if (action === "add-habit") openModal();
    if (action === "close-modal") closeModal();
    if (action === "set-budget") openBudgetModal();
    if (action === "close-budget-modal") closeBudgetModal();
    if (action === "add-walking") openWalkingModal();
    if (action === "close-walking-modal") closeWalkingModal();
    if (action === "close-walking-edit") closeWalkingEditModal();
    if (action === "notifications") showToast("Belum ada notifikasi baru. Catatan kebiasaanmu bisa dilihat di Dashboard.");
    if (action === "habit-detail") {
      const panel = document.getElementById("m4-habits");
      if (panel) {
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
        panel.setAttribute("tabindex", "-1");
        panel.focus({ preventScroll: true });
      }
    }
    if (action === "panel-options") {
      const panel = control.dataset.panel || "Panel";
      showToast(`${panel}: detail yang tersedia sudah ditampilkan di halaman ini.`);
    }
    if (action === "share-impact") {
      const shareText = "Aku sedang membangun kebiasaan hidup sehat dan mengurangi sampah kemasan bersama KoSehat!";
      try {
        if (navigator.share) {
          await navigator.share({ title: "Dampak KoSehat", text: shareText, url: window.location.href });
        } else if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(`${shareText} ${window.location.href}`);
          showToast("Teks pencapaian berhasil disalin. Kamu bisa membagikannya!");
        } else {
          window.prompt("Salin teks ini untuk dibagikan:", `${shareText} ${window.location.href}`);
        }
      } catch (error) {
        if (error.name !== "AbortError") showToast("Belum bisa membagikan otomatis. Coba salin tautan halaman ini.");
      }
    }
  });

  const typeSelect = document.getElementById("m4-habit-type");
  const hint = document.getElementById("m4-habit-hint");
  const hints = {
    water: "Masukkan total hidrasi hari ini dalam ml, misalnya 1500.",
    steps: "Masukkan total langkah hari ini, misalnya 6842.",
    sleep: "Masukkan total durasi tidur dalam menit, misalnya 440 untuk 7 jam 20 menit.",
    active: "Masukkan total menit gerak aktif hari ini, misalnya 38."
  };
  if (typeSelect && hint) {
    typeSelect.addEventListener("change", () => { hint.textContent = hints[typeSelect.value]; });
  }

  const habitForm = document.getElementById("m4-habit-form");
  if (habitForm) {
    habitForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submitButton = habitForm.querySelector('button[type="submit"]');
      const formData = new FormData(habitForm);
      const csrf = habitForm.querySelector('[name="csrfmiddlewaretoken"]')?.value;
      submitButton.disabled = true;
      submitButton.textContent = "Menyimpan...";
      try {
        const response = await fetch("/api/habits/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
          body: JSON.stringify({
            habit_type: formData.get("habit_type"),
            amount: formData.get("amount")
          })
        });
        const contentType = response.headers.get("content-type") || "";

        if (!contentType.includes("application/json")) {
          if (response.redirected) {
            throw new Error("Sesi login tidak tersedia. Silakan login terlebih dahulu.");
          }

          throw new Error("Server memberikan respons yang tidak dikenali.");
        }

        const result = await response.json();

        if (response.status === 401) {
          throw new Error("Silakan login terlebih dahulu untuk mencatat kebiasaan.");
        }

        if (!response.ok || !result.ok) {
          throw new Error(result.message || "Catatan gagal disimpan.");
        }
        closeModal();
        showToast(result.message);
        window.setTimeout(() => window.location.reload(), 700);
      } catch (error) {
        showToast(error.message || "Terjadi kesalahan saat menyimpan catatan.");
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Simpan catatan";
      }
    });
  }

  // ===== Anggaran Mingguan =====
const budgetForm = document.getElementById("m4-budget-form");

if (budgetForm) {
  budgetForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const submitButton = budgetForm.querySelector(
      'button[type="submit"]'
    );

    const amountInput = document.getElementById("m4-budget-amount");
    const csrf = budgetForm.querySelector(
      '[name="csrfmiddlewaretoken"]'
    )?.value;

    submitButton.disabled = true;
    submitButton.textContent = "Menyimpan...";

    try {
      const response = await fetch("/api/budget/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
        },
        body: JSON.stringify({
          amount: amountInput.value,
        }),
      });

      const contentType = response.headers.get("content-type") || "";

      if (!contentType.includes("application/json")) {
        throw new Error("Server memberikan respons yang tidak dikenali.");
      }

      const result = await response.json();

      if (response.status === 401) {
        throw new Error("Silakan login terlebih dahulu untuk mengatur anggaran.");
      }

      if (!response.ok || !result.ok) {
        throw new Error(result.message || "Anggaran gagal disimpan.");
      }

      closeBudgetModal();
      showToast(result.message);

      window.setTimeout(() => window.location.reload(), 700);

    } catch (error) {
      showToast(error.message || "Terjadi kesalahan saat menyimpan anggaran.");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Simpan anggaran";
    }
  });
}
// ===== Akhir Anggaran Mingguan =====

  // ===== Aktivitas Berjalan Kaki =====
  const WALKING_SPEEDS = { slow: 3, normal: 4.5, fast: 5.5 };
  const WALKING_STEP_LENGTH_METERS = 0.75;
  const numberFormatter = new Intl.NumberFormat("id-ID");

  function walkingEstimate(form, distanceTarget, stepsTarget) {
    const duration = Number(form?.querySelector('[name="duration_minutes"]')?.value || 0);
    const speed = WALKING_SPEEDS[form?.querySelector('[name="speed_level"]:checked')?.value] || 0;
    const distance = speed * duration / 60;
    const steps = Math.round(distance * 1000 / WALKING_STEP_LENGTH_METERS);
    if (distanceTarget) distanceTarget.textContent = `± ${distance.toLocaleString("id-ID", { maximumFractionDigits: 2 })} km`;
    if (stepsTarget) stepsTarget.textContent = `± ${numberFormatter.format(steps)} langkah`;
  }

  function enableWalkingPreview(form, distanceId, stepsId) {
    if (!form) return;
    const refresh = () => walkingEstimate(
      form,
      document.getElementById(distanceId),
      document.getElementById(stepsId)
    );
    form.addEventListener("input", refresh);
    form.addEventListener("change", refresh);
    refresh();
  }

  async function walkingRequest(url, options) {
    const response = await fetch(url, options);
    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result.ok) {
      throw new Error(result.message || "Aktivitas berjalan kaki tidak dapat diproses.");
    }
    return result;
  }

  const walkingForm = document.getElementById("m4-walking-form");
  enableWalkingPreview(walkingForm, "m4-walking-distance", "m4-walking-steps");
  if (walkingForm) {
    walkingForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submitButton = walkingForm.querySelector('button[type="submit"]');
      const csrf = walkingForm.querySelector('[name="csrfmiddlewaretoken"]')?.value;
      const formData = new FormData(walkingForm);
      submitButton.disabled = true;
      submitButton.textContent = "Menyimpan...";
      try {
        const result = await walkingRequest(walkingForm.dataset.createUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
          body: JSON.stringify(Object.fromEntries(formData)),
        });
        closeWalkingModal();
        showToast(result.message);
        window.setTimeout(() => window.location.reload(), 600);
      } catch (error) {
        showToast(error.message);
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Simpan aktivitas";
      }
    });
  }

  const walkingList = document.getElementById("m4-walking-list");
  const walkingListContent = document.getElementById("m4-walking-list-content");
  const walkingEditForm = document.getElementById("m4-walking-edit-form");
  let selectedWalkingActivity = null;
  enableWalkingPreview(walkingEditForm, "m4-walking-edit-distance", "m4-walking-edit-steps");

  function walkingEndpoint(template, id) {
    return template.replace("/0/", `/${id}/`);
  }

  function walkingRow(activity) {
    const row = document.createElement("article");
    row.className = "m4-walking-row";
    const summary = document.createElement("div");
    summary.innerHTML = `<strong>${activity.activity_date}</strong><span>${activity.duration_minutes} menit • ${activity.speed_label} (${String(activity.speed_kmh).replace(".", ",")} km/jam)</span><small>± ${String(activity.distance_km).replace(".", ",")} km • ± ${numberFormatter.format(activity.steps)} langkah</small>`;
    const actions = document.createElement("div");
    actions.className = "m4-walking-row-actions";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.textContent = "Ubah";
    edit.addEventListener("click", () => openWalkingEdit(activity));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Hapus";
    remove.addEventListener("click", () => deleteWalkingActivity(activity));
    actions.append(edit, remove);
    row.append(summary, actions);
    return row;
  }

  async function loadWalkingActivities() {
    if (!walkingList || !walkingListContent) return;
    try {
      const result = await walkingRequest(walkingList.dataset.listUrl, { headers: { Accept: "application/json" } });
      walkingListContent.replaceChildren();
      if (!result.activities.length) {
        walkingListContent.textContent = "Belum ada catatan berjalan kaki.";
        return;
      }
      result.activities.forEach((activity) => walkingListContent.append(walkingRow(activity)));
    } catch (error) {
      walkingListContent.textContent = error.message;
    }
  }

  function openWalkingEdit(activity) {
    if (!walkingEditModal || !walkingEditForm) return;
    selectedWalkingActivity = activity;
    walkingEditForm.elements.duration_minutes.value = activity.duration_minutes;
    walkingEditForm.elements.speed_level.value = activity.speed_level;
    walkingEditForm.elements.activity_date.value = activity.activity_date;
    walkingEstimate(
      walkingEditForm,
      document.getElementById("m4-walking-edit-distance"),
      document.getElementById("m4-walking-edit-steps")
    );
    walkingEditModal.hidden = false;
    walkingEditForm.elements.duration_minutes.focus();
  }

  async function deleteWalkingActivity(activity) {
    if (!window.confirm("Hapus catatan berjalan kaki ini?")) return;
    try {
      const csrf = walkingEditForm?.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
      const result = await walkingRequest(
        walkingEndpoint(walkingList.dataset.deleteUrlTemplate, activity.id),
        { method: "POST", headers: { "X-CSRFToken": csrf } }
      );
      showToast(result.message);
      await loadWalkingActivities();
    } catch (error) {
      showToast(error.message);
    }
  }

  if (walkingEditForm) {
    walkingEditForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!selectedWalkingActivity) return;
      const submitButton = walkingEditForm.querySelector('button[type="submit"]');
      submitButton.disabled = true;
      submitButton.textContent = "Menyimpan...";
      try {
        const result = await walkingRequest(
          walkingEndpoint(walkingList.dataset.updateUrlTemplate, selectedWalkingActivity.id),
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": walkingEditForm.querySelector('[name="csrfmiddlewaretoken"]')?.value,
            },
            body: JSON.stringify(Object.fromEntries(new FormData(walkingEditForm))),
          }
        );
        closeWalkingEditModal();
        showToast(result.message);
        await loadWalkingActivities();
      } catch (error) {
        showToast(error.message);
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Simpan perubahan";
      }
    });
  }
  loadWalkingActivities();
  // ===== Akhir Aktivitas Berjalan Kaki =====

  // ===== Komunitas KoSehat =====
  const communityList = document.getElementById("m4-community-list");
  const communityForm = document.getElementById("m4-community-form");
  const communityStatus = document.getElementById("m4-community-status");
  const communityContent = document.getElementById("m4-community-content");
  
  const communityToggle = document.getElementById("m4-community-toggle");
  const communityCancel = document.getElementById("m4-community-cancel");

  
  function setCommunityFormOpen(isOpen) {
    if (!communityForm || !communityToggle) return;

    communityForm.hidden = !isOpen;
    communityToggle.setAttribute("aria-expanded", String(isOpen));

    const symbol = communityToggle.querySelector("span");
    if (symbol) {
      symbol.textContent = isOpen ? "−" : "＋";
    }

    if (isOpen) {
      communityContent?.focus();
    }
  }


  communityToggle?.addEventListener("click", () => {
    setCommunityFormOpen(communityForm.hidden);
  });

  communityCancel?.addEventListener("click", () => {
    communityForm.reset();
    addCommunityMessage("");
    setCommunityFormOpen(false);
  });


  const communitySection = document.getElementById("m4-community");
  const canPost = communitySection?.dataset.canPost === "true";

  function communityDeleteUrl(commentId) {
    return (communitySection?.dataset.deleteUrlTemplate || "").replace(
      "/0/delete/",
      `/${commentId}/delete/`
    );
  }

  function getCsrfToken() {
    return communityForm?.querySelector(
      '[name="csrfmiddlewaretoken"]'
    )?.value || "";
  }

  function addCommunityMessage(message) {
    if (communityStatus) {
      communityStatus.textContent = message;
    }
  }

  function createCommunityElement(tag, text, className) {
    const element = document.createElement(tag);
    element.textContent = text;
    if (className) element.className = className;
    return element;
  }

  async function deleteCommunityComment(comment) {
    if (!window.confirm("Hapus komentar ini? Tindakan ini tidak dapat dibatalkan.")) {
      return;
    }

    try {
      const response = await fetch(communityDeleteUrl(comment.id), {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken() }
      });
      const result = await response.json().catch(() => ({}));

      if (!response.ok || !result.ok) {
        throw new Error(result.message || "Komentar tidak dapat dihapus.");
      }

      addCommunityMessage(result.message);
      await loadCommunityComments();
    } catch (error) {
      addCommunityMessage(error.message || "Terjadi kesalahan saat menghapus komentar.");
    }
  }

  
  async function loadCommunityComments() {
    if (!communityList) return;

    try {
      const response = await fetch("/api/community/comments/");
      const result = await response.json();

      if (!response.ok || !result.ok) {
        throw new Error("Postingan komunitas gagal dimuat.");
      }

      communityList.replaceChildren();

      if (result.comments.length === 0) {
        communityList.append(
          createCommunityElement(
            "p",
            "Belum ada cerita. Jadilah yang pertama berbagi!"
          )
        );
        return;
      }

      result.comments.forEach((comment) => {
        const card = document.createElement("article");
        card.className = "m4-community-post";

        const heading = document.createElement("div");
        heading.className = "m4-community-post-heading";
        heading.append(
          createCommunityElement("strong", comment.author),
          createCommunityElement(
            "small",
            new Date(comment.created_at).toLocaleString("id-ID")
          )
        );

        if (comment.can_delete) {
          const deleteButton = createCommunityElement(
            "button",
            "Hapus",
            "m4-community-delete-button"
          );
          deleteButton.type = "button";
          deleteButton.setAttribute("aria-label", "Hapus komentar");
          deleteButton.addEventListener("click", () => deleteCommunityComment(comment));
          heading.append(deleteButton);
        }

        card.append(
          heading,
          createCommunityElement("p", comment.content)
        );

        // Wadah semua tombol agar tersusun vertikal.
        const communityActions = document.createElement("div");
        communityActions.className = "m4-community-actions";

        // Tombol balas dan form balasan.
        if (canPost) {
          const replyButton = createCommunityElement(
            "button",
            "＋ Balas komentar",
            "m4-community-reply-button"
          );
          replyButton.type = "button";

          const replyForm = document.createElement("form");
          replyForm.hidden = true;
          replyForm.className = "m4-community-reply-form";

          const replyInput = document.createElement("textarea");
          replyInput.maxLength = 1000;
          replyInput.required = true;
          replyInput.rows = 2;
          replyInput.placeholder = "Tulis balasan...";

          const sendReply = createCommunityElement(
            "button",
            "Kirim balasan"
          );
          sendReply.type = "submit";

          replyForm.append(replyInput, sendReply);

          replyButton.addEventListener("click", () => {
            const isOpening = replyForm.hidden;
            replyForm.hidden = !isOpening;
            replyButton.textContent = isOpening
              ? "− Balas komentar"
              : "＋ Balas komentar";

            if (isOpening) replyInput.focus();
          });

          replyForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            if (!replyInput.value.trim()) {
              replyInput.focus();
              return;
            }

            sendReply.disabled = true;

            try {
              const response = await fetch(
                "/api/community/comments/add/",
                {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken()
                  },
                  body: JSON.stringify({
                    content: replyInput.value.trim(),
                    parent_id: comment.id
                  })
                }
              );

              const result = await response.json();

              if (!response.ok || !result.ok) {
                throw new Error(
                  result.message || "Balasan gagal dikirim."
                );
              }

              addCommunityMessage("Balasan berhasil dikirim.");
              await loadCommunityComments();
            } catch (error) {
              addCommunityMessage(
                error.message || "Terjadi kesalahan saat membalas."
              );
            } finally {
              sendReply.disabled = false;
            }
          });

          communityActions.append(replyButton, replyForm);
        }

        // Tombol untuk melihat atau menyembunyikan balasan.
        if (comment.replies?.length) {
          const repliesToggle = createCommunityElement(
            "button",
            `Lihat balasan (${comment.replies.length}) ▾`,
            "m4-community-replies-toggle"
          );
          repliesToggle.type = "button";
          repliesToggle.setAttribute("aria-expanded", "false");

          const repliesContainer = document.createElement("div");
          repliesContainer.className = "m4-community-replies";
          repliesContainer.hidden = true;

          comment.replies.forEach((reply) => {
            const replyCard = document.createElement("div");
            replyCard.className = "m4-community-reply";

            const avatar = createCommunityElement(
              "span",
              "👤",
              "m4-community-avatar"
            );

            const replyHeading = document.createElement("div");
            replyHeading.className = "m4-community-reply-heading";
            replyHeading.append(
              avatar,
              createCommunityElement("strong", reply.author),
              createCommunityElement(
                "small",
                new Date(reply.created_at).toLocaleString("id-ID")
              )
            );

            if (reply.can_delete) {
              const deleteReplyButton = createCommunityElement(
                "button",
                "Hapus",
                "m4-community-delete-button"
              );
              deleteReplyButton.type = "button";
              deleteReplyButton.setAttribute("aria-label", "Hapus balasan");
              deleteReplyButton.addEventListener("click", () => deleteCommunityComment(reply));
              replyHeading.append(deleteReplyButton);
            }

            replyCard.append(
              replyHeading,
              createCommunityElement("p", reply.content)
            );

            repliesContainer.append(replyCard);
          });

          repliesToggle.addEventListener("click", () => {
            const isOpening = repliesContainer.hidden;
            repliesContainer.hidden = !isOpening;
            repliesToggle.setAttribute(
              "aria-expanded",
              String(isOpening)
            );
            repliesToggle.textContent = isOpening
              ? "Sembunyikan balasan ▴"
              : `Lihat balasan (${comment.replies.length}) ▾`;
          });

          communityActions.append(repliesToggle, repliesContainer);
        }

        if (communityActions.children.length > 0) {
          card.append(communityActions);
        }

        communityList.append(card);
      });
    } catch (error) {
      communityList.replaceChildren(
        createCommunityElement(
          "p",
          error.message || "Postingan gagal dimuat."
        )
      );
    }
  }


  

  if (communityForm && canPost) {
    communityForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const submitButton = communityForm.querySelector(
        'button[type="submit"]'
      );

      if (!communityContent.value.trim()) {
        addCommunityMessage("Cerita tidak boleh kosong.");
        return;
      }

      submitButton.disabled = true;
      submitButton.textContent = "Mengirim...";

      try {
        const response = await fetch(
          "/api/community/comments/add/",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrfToken()
            },
            body: JSON.stringify({
              content: communityContent.value.trim()
            })
          }
        );

        const result = await response.json();

        if (!response.ok || !result.ok) {
          throw new Error(
            result.message || "Postingan gagal dikirim."
          );
        }

        communityContent.value = "";
        setCommunityFormOpen(false);
        addCommunityMessage("Postingan berhasil dibagikan!");
        await loadCommunityComments();
      } catch (error) {
        addCommunityMessage(
          error.message || "Terjadi kesalahan saat mengirim."
        );
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Posting";
      }
    });
  }

  loadCommunityComments();
  // ===== Akhir Komunitas KoSehat =====


  // Make the analytics line smooth while preserving its server-rendered coordinates.
  document.querySelectorAll(".m4-chart-svg polyline").forEach((polyline) => {
    const raw = (polyline.getAttribute("points") || "").trim();
    const points = raw.split(/\s+/).filter(Boolean).map((pair) => pair.split(",").map(Number));
    if (points.length < 3 || points.some((point) => point.length !== 2 || point.some(Number.isNaN))) return;
    let path = `M ${points[0][0]} ${points[0][1]}`;
    for (let i = 0; i < points.length - 1; i++) {
      const current = points[i];
      const next = points[i + 1];
      const midX = (current[0] + next[0]) / 2;
      path += ` C ${midX} ${current[1]}, ${midX} ${next[1]}, ${next[0]} ${next[1]}`;
    }
    const smooth = document.createElementNS("http://www.w3.org/2000/svg", "path");
    smooth.setAttribute("d", path);
    smooth.setAttribute("class", polyline.getAttribute("class") || "");
    polyline.replaceWith(smooth);
  });
})();
