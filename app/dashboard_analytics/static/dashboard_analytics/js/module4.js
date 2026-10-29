(() => {
  const toast = document.getElementById("m4-toast");
  const modal = document.getElementById("m4-habit-modal");
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

  document.addEventListener("click", async (event) => {
    const control = event.target.closest("[data-action]");
    if (!control) {
      if (event.target === modal) closeModal();
      return;
    }
    const action = control.dataset.action;
    if (action === "add-habit") openModal();
    if (action === "close-modal") closeModal();
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
      showToast(`${panel}: data ditampilkan di halaman ini. Opsi lanjutan akan tersedia setelah integrasi modul selesai.`);
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
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.message || "Catatan gagal disimpan.");
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
  const canPost = true; // Testing lokal sementara

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
              createCommunityElement("strong", reply.author)
            );

            replyCard.append(
              replyHeading,
              createCommunityElement("p", reply.content),
              createCommunityElement(
                "small",
                new Date(reply.created_at).toLocaleString("id-ID")
              )
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
