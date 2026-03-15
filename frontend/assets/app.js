const state = {
  collections: [],
  cards: [],
  quizzes: [],
  subjects: [],
  activeCollectionId: null,
  currentPaper: null,
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

const modeLabels = {
  quick_practice: "速练",
  chapter_drill: "章节训练",
  final_mock: "期末模拟",
};

const typeLabels = {
  choice: "选择题",
  single_choice: "单选题",
  true_false: "判断题",
  term_explanation: "名词解释",
  short_answer: "简答题",
  case_analysis: "病例分析",
};

const studyGuides = {
  formula: {
    title: "方剂学答题提醒",
    tips: [
      "选择题先抓功效、主治和方义，不要只背药物名称。",
      "简答题尽量按病机、治法、方义三步写。",
      "病例题先辨证，再解释为什么选这个方，不要直接报方名。",
    ],
  },
  acupuncture: {
    title: "针灸学答题提醒",
    tips: [
      "单选和判断常考经络归属、定位、特定穴和刺灸法。",
      "主观题先写取穴结论，再补经络依据、手法和配穴原则。",
      "病例题建议按辨病、辨经、取穴、手法、加减顺序作答。",
    ],
  },
  warm_disease: {
    title: "温病学答题提醒",
    tips: [
      "选择题重点看卫气营血辨证、三焦辨证和代表方药。",
      "名词解释不要只写定义，要带上临床表现、治法与方药。",
      "论述题建议固定写成病因、病机、辨证、治则、方药五步。",
    ],
  },
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
      // Ignore non-JSON bodies.
    }
    throw new Error(detail);
  }

  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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

function getActiveCollection() {
  return state.collections.find((item) => item.id === state.activeCollectionId) || null;
}

function syncCollectionSelects() {
  const selects = [
    document.getElementById("collection-select"),
    document.getElementById("paper-collection-select"),
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
                ${escapeHtml(collection.title)} · ${escapeHtml(collection.subject_display_name)}
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
        <option value="${escapeHtml(subject.display_name)}">
          ${escapeHtml(subject.display_name)} · ${escapeHtml(subject.entity_label)}
        </option>
      `,
    )
    .join("");
}

function renderGuidance() {
  const container = document.getElementById("study-guidance");
  const active = getActiveCollection();
  if (!active) {
    container.className = "guidance-panel empty-state";
    container.textContent = "请先选择学习集合。";
    return;
  }

  const guide = studyGuides[active.subject_key] || studyGuides.formula;
  container.className = "guidance-panel";
  container.innerHTML = `
    <div class="guide-card">
      <p class="guide-subject">${escapeHtml(active.subject_display_name)} · ${escapeHtml(active.title)}</p>
      <h3>${escapeHtml(guide.title)}</h3>
      <ul class="guide-list">
        ${guide.tips
          .map((tip) => `<li>${escapeHtml(tip)}</li>`)
          .join("")}
      </ul>
    </div>
  `;
}

function renderCollections() {
  const container = document.getElementById("collections-list");
  if (!state.collections.length) {
    container.innerHTML = '<div class="empty-state">还没有学习集合，先创建一个复习专题。</div>';
    return;
  }

  container.innerHTML = state.collections
    .map(
      (collection) => `
        <article
          class="collection-item ${collection.id === state.activeCollectionId ? "is-active" : ""}"
          data-collection-id="${collection.id}"
        >
          <div class="collection-topline">
            <div class="chip">${escapeHtml(collection.subject_display_name)}</div>
            <button
              type="button"
              class="collection-delete"
              data-delete-collection-id="${collection.id}"
            >
              删除
            </button>
          </div>
          <h3>${escapeHtml(collection.title)}</h3>
          <p>${escapeHtml(collection.description || "暂时没有备注。")}</p>
        </article>
      `,
    )
    .join("");

  container.querySelectorAll("[data-collection-id]").forEach((item) => {
    item.addEventListener("click", async () => {
      state.activeCollectionId = Number(item.dataset.collectionId);
      state.currentPaper = null;
      syncCollectionSelects();
      renderCollections();
      renderGuidance();
      renderPaper();
      await refreshActiveCollection();
    });
  });

  container.querySelectorAll("[data-delete-collection-id]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      await deleteCollection(Number(button.dataset.deleteCollectionId));
    });
  });
}

function renderCards() {
  const container = document.getElementById("cards-list");
  const hint = document.getElementById("current-collection-hint");
  const active = getActiveCollection();
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
              <strong>${escapeHtml(fieldLabels[key] || key)}</strong>
              <span>${escapeHtml(value)}</span>
            </div>
          `,
        )
        .join("");

      return `
        <article class="feed-card">
          <div class="meta">
            <span class="chip">${escapeHtml(card.subject_display_name)}</span>
            <span class="chip">${escapeHtml(card.category)}</span>
          </div>
          <h3>${escapeHtml(card.title)}</h3>
          <p>${escapeHtml(card.raw_excerpt || "无摘录")}</p>
          <div class="detail-grid">${detailRows}</div>
        </article>
      `;
    })
    .join("");
}

function renderRecentPractice() {
  const container = document.getElementById("recent-practice-list");
  if (!state.quizzes.length) {
    container.className = "feed-list empty-state";
    container.textContent = "暂无练习记录";
    return;
  }

  container.className = "feed-list";
  container.innerHTML = state.quizzes
    .map((quiz) => {
      const options = (quiz.options || [])
        .map(
          (option) => `
            <li><strong>${escapeHtml(option.key)}.</strong> ${escapeHtml(option.value)}</li>
          `,
        )
        .join("");

      return `
        <article class="quiz-card">
          <div class="meta">
            <span class="chip">${escapeHtml(typeLabels[quiz.type] || quiz.type)}</span>
            <span class="chip">${escapeHtml(quiz.difficulty)}</span>
          </div>
          <h3>${escapeHtml(quiz.question)}</h3>
          ${
            options
              ? `<ol class="option-list compact-option-list">${options}</ol>`
              : '<p class="practice-note">主观题已生成，可展开查看参考答案。</p>'
          }
          <details class="answer-sheet">
            <summary>查看答案</summary>
            <p><strong>参考答案：</strong>${escapeHtml(quiz.answer || "暂无")}</p>
            <p>${escapeHtml(quiz.explanation || "暂无解析")}</p>
          </details>
        </article>
      `;
    })
    .join("");
}

function renderPaper() {
  const container = document.getElementById("paper-view");
  if (!state.currentPaper) {
    container.className = "paper-view empty-state";
    container.textContent = "还没有生成训练卷。选择集合后试试“期末模拟”，页面会按大题结构展开。";
    return;
  }

  const paper = state.currentPaper;
  container.className = "paper-view";
  container.innerHTML = `
    <div class="paper-header">
      <p class="paper-kicker">${escapeHtml(modeLabels[paper.mode] || paper.mode)}</p>
      <h2>${escapeHtml(paper.paper_title)}</h2>
      <div class="paper-meta">
        <span>${escapeHtml(paper.subject_display_name)}</span>
        <span>总分 ${escapeHtml(paper.total_score)}</span>
        <span>${escapeHtml(paper.sections.length)} 个大题</span>
      </div>
      <p class="paper-notice">${escapeHtml(paper.exam_notice)}</p>
    </div>
    ${paper.sections
      .map(
        (section) => `
          <section class="paper-section">
            <div class="paper-section-heading">
              <div>
                <h3>${escapeHtml(section.title)}</h3>
                <p>${escapeHtml(section.instructions)}</p>
              </div>
              <div class="section-score">${escapeHtml(section.total_score)} 分</div>
            </div>
            <div class="question-stack">
              ${section.questions
                .map(
                  (question, index) => `
                    <article class="paper-question">
                      <div class="question-topline">
                        <span class="question-index">${index + 1}</span>
                        <div class="meta">
                          <span class="chip">${escapeHtml(typeLabels[question.type] || question.type)}</span>
                          <span class="chip">${escapeHtml(question.score)} 分</span>
                        </div>
                      </div>
                      <h4>${escapeHtml(question.question)}</h4>
                      ${
                        (question.options || []).length
                          ? `<ol class="option-list">
                              ${question.options
                                .map(
                                  (option) => `
                                    <li>
                                      <strong>${escapeHtml(option.key)}.</strong>
                                      ${escapeHtml(option.value)}
                                    </li>
                                  `,
                                )
                                .join("")}
                            </ol>`
                          : `<div class="answer-template">
                              <strong>建议答题结构</strong>
                              <p>${escapeHtml(question.answer_template || "先写核心结论，再展开作答。")}</p>
                            </div>`
                      }
                      <details class="answer-sheet">
                        <summary>展开参考答案与得分点</summary>
                        <p><strong>参考答案：</strong>${escapeHtml(question.answer || "暂无")}</p>
                        <p>${escapeHtml(question.explanation || "暂无解析")}</p>
                        ${
                          (question.rubric || []).length
                            ? `<div class="rubric-list">
                                ${question.rubric
                                  .map((item) => `<span class="rubric-chip">${escapeHtml(item)}</span>`)
                                  .join("")}
                              </div>`
                            : ""
                        }
                      </details>
                    </article>
                  `,
                )
                .join("")}
            </div>
          </section>
        `,
      )
      .join("")}
  `;
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
  renderGuidance();
}

async function refreshActiveCollection() {
  if (!state.activeCollectionId) {
    state.cards = [];
    state.quizzes = [];
    state.currentPaper = null;
    renderCards();
    renderRecentPractice();
    renderPaper();
    renderGuidance();
    updateCounters();
    return;
  }

  state.cards = await api(`/api/cards?collection_id=${state.activeCollectionId}`);
  state.quizzes = await api(`/api/quizzes?collection_id=${state.activeCollectionId}&limit=8`);
  renderCards();
  renderRecentPractice();
  renderGuidance();
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
    state.currentPaper = null;

    formElement.reset();
    syncCollectionSelects();
    renderCollections();
    renderCards();
    renderRecentPractice();
    renderPaper();
    renderGuidance();
    updateCounters();
    setStatus(`已创建集合：${collection.title}`);

    await loadCollections();
    await refreshActiveCollection();
  } catch (error) {
    setStatus(`创建集合失败：${error.message}`);
  } finally {
    setButtonBusy(submitButton, false, "创建中...");
  }
}

async function deleteCollection(collectionId) {
  const target = state.collections.find((item) => item.id === collectionId);
  if (!target) {
    return;
  }

  try {
    setStatus(`正在删除集合：${target.title}`);
    await api(`/api/collections/${collectionId}`, { method: "DELETE" });
    state.collections = state.collections.filter((item) => item.id !== collectionId);

    if (state.activeCollectionId === collectionId) {
      state.activeCollectionId = state.collections[0]?.id || null;
      state.currentPaper = null;
    }

    syncCollectionSelects();
    renderCollections();
    renderPaper();
    await refreshActiveCollection();
    updateCounters();
    setStatus(`已删除集合：${target.title}`);
  } catch (error) {
    setStatus(`删除集合失败：${error.message}`);
  }
}

async function importTextAndGenerate(event) {
  event.preventDefault();
  if (!state.collections.length) {
    setStatus("请先创建集合。");
    return;
  }

  const formElement = event.currentTarget;
  const submitButton = formElement.querySelector('button[type="submit"]');
  const form = new FormData(formElement);
  const collectionId = Number(form.get("collection_id"));
  const text = String(form.get("text") || "").trim();

  if (!text) {
    setStatus("请先输入学习内容。");
    return;
  }

  try {
    setButtonBusy(submitButton, true, "导入中...");
    setStatus("正在导入文本并生成卡片...");

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
  } catch (error) {
    setStatus(`导入失败：${error.message}`);
  } finally {
    setButtonBusy(submitButton, false, "导入中...");
  }
}

async function generatePaper(event) {
  event.preventDefault();
  if (!state.collections.length) {
    setStatus("请先创建集合。");
    return;
  }

  const formElement = event.currentTarget;
  const submitButton = formElement.querySelector('button[type="submit"]');
  const form = new FormData(formElement);
  const payload = {
    collection_id: Number(form.get("collection_id")),
    mode: String(form.get("mode")),
    difficulty: String(form.get("difficulty")),
  };

  try {
    setButtonBusy(submitButton, true, "生成中...");
    setStatus(`正在生成${modeLabels[payload.mode] || payload.mode}...`);

    state.currentPaper = await api("/api/quizzes/generate-paper", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.activeCollectionId = payload.collection_id;
    syncCollectionSelects();
    renderCollections();
    renderPaper();
    await refreshActiveCollection();
    setStatus(`已生成${modeLabels[payload.mode] || payload.mode}。`);
  } catch (error) {
    setStatus(`生成训练卷失败：${error.message}`);
  } finally {
    setButtonBusy(submitButton, false, "生成中...");
  }
}

async function bootstrap() {
  try {
    setStatus("正在加载项目数据...");
    await loadSubjects();
    await loadCollections();
    await refreshActiveCollection();
    renderPaper();
    updateCounters();
    document
      .getElementById("collection-form")
      .addEventListener("submit", createCollection);
    document
      .getElementById("import-form")
      .addEventListener("submit", importTextAndGenerate);
    document.getElementById("paper-form").addEventListener("submit", generatePaper);
    document.getElementById("refresh-button").addEventListener("click", refreshActiveCollection);
    setStatus("准备就绪，可以开始生成训练卷。");
  } catch (error) {
    setStatus(`初始化失败：${error.message}`);
  }
}

bootstrap();
