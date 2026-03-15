const state = {
  collections: [],
  cards: [],
  quizzes: [],
  subjects: [],
  activeCollectionId: null,
};

const fieldLabels = {
  formula_name: "名称",
  composition: "组成",
  effect: "功效",
  indication: "主治",
  pathogenesis: "病机",
  usage_notes: "用法",
  memory_tip: "记忆",
  acupoint_name: "穴名",
  meridian: "经络",
  location: "定位",
  technique: "操作",
  caution: "注意",
  pattern_name: "证候",
  stage: "阶段",
  syndrome: "表现",
  treatment: "治法",
  formula: "方药",
  differentiation: "鉴别",
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (error) {
      // Ignore non-JSON error bodies.
    }
    throw new Error(detail);
  }

  return response.json();
}

function setStatus(message) {
  document.getElementById("status-bar").textContent = message;
}

function updateCounters() {
  document.getElementById("collection-count").textContent = state.collections.length;
  document.getElementById("card-count").textContent = state.cards.length;
  document.getElementById("quiz-count").textContent = state.quizzes.length;
}

function setButtonBusy(button, isBusy, busyLabel) {
  if (!button) {
    return;
  }

  if (!button.dataset.defaultLabel) {
    button.dataset.defaultLabel = button.textContent;
  }

  button.disabled = isBusy;
  button.textContent = isBusy ? busyLabel : button.dataset.defaultLabel;
}

function upsertCollection(collection) {
  const existingIndex = state.collections.findIndex((item) => item.id === collection.id);
  if (existingIndex >= 0) {
    state.collections[existingIndex] = collection;
    return;
  }

  state.collections = [collection, ...state.collections];
}

function syncCollectionSelects() {
  const selects = [
    document.getElementById("collection-select"),
    document.getElementById("quiz-collection-select"),
  ];

  selects.forEach((select) => {
    const current = String(state.activeCollectionId || "");
    select.innerHTML = state.collections.length
      ? state.collections
          .map(
            (collection) => `
              <option value="${collection.id}" ${
                String(collection.id) === current ? "selected" : ""
              }>
                ${collection.title} · ${collection.subject_display_name}
              </option>
            `,
          )
          .join("")
      : '<option value="">请先创建集合</option>';
  });
}

function renderSubjects() {
  const select = document.getElementById("subject-select");
  select.innerHTML = state.subjects
    .map(
      (subject) => `
        <option value="${subject.display_name}">
          ${subject.display_name} · ${subject.entity_label}
        </option>
      `,
    )
    .join("");
}

function renderCollections() {
  const container = document.getElementById("collections-list");
  if (!state.collections.length) {
    container.innerHTML = '<div class="empty-state">还没有学习集合，先在左侧创建一个。</div>';
    return;
  }

  container.innerHTML = state.collections
    .map(
      (collection) => `
        <article
          class="collection-item ${collection.id === state.activeCollectionId ? "is-active" : ""}"
          data-collection-id="${collection.id}"
        >
          <div class="chip">${collection.subject_display_name}</div>
          <h3>${collection.title}</h3>
          <p>${collection.description || "暂时没有备注。"}</p>
        </article>
      `,
    )
    .join("");

  container.querySelectorAll("[data-collection-id]").forEach((item) => {
    item.addEventListener("click", async () => {
      state.activeCollectionId = Number(item.dataset.collectionId);
      syncCollectionSelects();
      renderCollections();
      await refreshActiveCollection();
    });
  });
}

function renderCards() {
  const container = document.getElementById("cards-list");
  const hint = document.getElementById("current-collection-hint");
  const active = state.collections.find((item) => item.id === state.activeCollectionId);
  hint.textContent = active
    ? `当前集合：${active.title} · ${active.subject_display_name}`
    : "还没有选择集合。";

  if (!state.cards.length) {
    container.className = "feed-list empty-state";
    container.textContent = active ? "这个集合还没有卡片。" : "暂无卡片";
    return;
  }

  container.className = "feed-list";
  container.innerHTML = state.cards
    .map((card) => {
      const detailRows = Object.entries(card.normalized_content || {})
        .filter(([, value]) => value)
        .map(
          ([key, value]) => `
            <div class="detail-row">
              <strong>${fieldLabels[key] || key}</strong>
              <span>${value}</span>
            </div>
          `,
        )
        .join("");

      return `
        <article class="feed-card">
          <div class="meta">
            <span class="chip">${card.subject_display_name}</span>
            <span class="chip">${card.category}</span>
          </div>
          <h3>${card.title}</h3>
          <p>${card.raw_excerpt || "无摘录"}</p>
          <div class="detail-grid">${detailRows}</div>
        </article>
      `;
    })
    .join("");
}

function renderQuizzes() {
  const container = document.getElementById("quizzes-list");
  if (!state.quizzes.length) {
    container.className = "feed-list empty-state";
    container.textContent = "暂无题目";
    return;
  }

  container.className = "feed-list";
  container.innerHTML = state.quizzes
    .map(
      (quiz) => `
        <article class="quiz-card">
          <div class="meta">
            <span class="chip">${quiz.difficulty}</span>
            <span class="chip">${quiz.type}</span>
          </div>
          <h3>${quiz.question}</h3>
          <p>${(quiz.options || [])
            .map((option) => `${option.key}. ${option.value}`)
            .join(" / ")}</p>
        </article>
      `,
    )
    .join("");
}

async function loadSubjects() {
  state.subjects = await api("/api/subjects");
  renderSubjects();
}

async function loadCollections() {
  state.collections = await api("/api/collections");
  if (!state.activeCollectionId && state.collections.length) {
    state.activeCollectionId = state.collections[0].id;
  }
  syncCollectionSelects();
  renderCollections();
}

async function refreshActiveCollection() {
  if (!state.activeCollectionId) {
    state.cards = [];
    state.quizzes = [];
    renderCards();
    renderQuizzes();
    updateCounters();
    return;
  }

  state.cards = await api(`/api/cards?collection_id=${state.activeCollectionId}`);
  state.quizzes = await api(`/api/quizzes?collection_id=${state.activeCollectionId}&limit=5`);
  renderCards();
  renderQuizzes();
  updateCounters();
}

async function createCollection(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  const submitButton = formElement.querySelector('button[type="submit"]');
  const form = new FormData(formElement);
  const payload = Object.fromEntries(form.entries());
  payload.user_id = 1;

  try {
    setButtonBusy(submitButton, true, "创建中...");
    setStatus("正在创建集合...");

    const collection = await api("/api/collections", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    upsertCollection(collection);
    state.activeCollectionId = collection.id;
    state.cards = [];
    state.quizzes = [];

    formElement.reset();
    syncCollectionSelects();
    renderCollections();
    renderCards();
    renderQuizzes();
    updateCounters();
    setStatus(`已创建集合：${collection.title}`);

    // Re-sync from the backend in case ordering or derived fields changed.
    await loadCollections();
    await refreshActiveCollection();
  } catch (error) {
    setStatus(`创建集合失败：${error.message}`);
  } finally {
    setButtonBusy(submitButton, false, "创建中...");
  }
}

async function importTextAndGenerate(event) {
  event.preventDefault();
  if (!state.collections.length) {
    setStatus("请先创建集合。");
    return;
  }

  const form = new FormData(event.currentTarget);
  const collectionId = Number(form.get("collection_id"));
  const text = String(form.get("text") || "").trim();
  if (!text) {
    setStatus("请先输入学习内容。");
    return;
  }

  const imported = await api("/api/import/text", {
    method: "POST",
    body: JSON.stringify({
      collection_id: collectionId,
      text,
    }),
  });

  await api("/api/cards/generate", {
    method: "POST",
    body: JSON.stringify({ document_id: imported.document_id }),
  });

  state.activeCollectionId = collectionId;
  syncCollectionSelects();
  renderCollections();
  await refreshActiveCollection();
  setStatus(`文本已导入，并为集合 ${collectionId} 生成卡片。`);
}

async function generateQuiz(event) {
  event.preventDefault();
  if (!state.collections.length) {
    setStatus("请先创建集合。");
    return;
  }

  const form = new FormData(event.currentTarget);
  const payload = {
    collection_id: Number(form.get("collection_id")),
    count: Number(form.get("count")),
    difficulty: String(form.get("difficulty")),
  };

  state.quizzes = await api("/api/quizzes/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.activeCollectionId = payload.collection_id;
  syncCollectionSelects();
  renderCollections();
  renderQuizzes();
  updateCounters();
  setStatus(`已生成 ${state.quizzes.length} 道${payload.difficulty}难度题目。`);
}

async function bootstrap() {
  try {
    setStatus("正在加载项目数据...");
    await loadSubjects();
    await loadCollections();
    await refreshActiveCollection();
    updateCounters();
    document
      .getElementById("collection-form")
      .addEventListener("submit", createCollection);
    document
      .getElementById("import-form")
      .addEventListener("submit", importTextAndGenerate);
    document.getElementById("quiz-form").addEventListener("submit", generateQuiz);
    document.getElementById("refresh-button").addEventListener("click", refreshActiveCollection);
    setStatus("准备就绪，可以开始导入内容。");
  } catch (error) {
    setStatus(`初始化失败：${error.message}`);
  }
}

bootstrap();
