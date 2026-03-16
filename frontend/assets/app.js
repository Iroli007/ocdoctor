const state = {
  collections: [],
  documents: [],
  cards: [],
  templates: [],
  activeCollectionId: null,
  activeDocumentId: null,
  activeCardId: null,
  activeTemplateKey: null,
  currentUserId: null,
  users: [],
};

function normalizeTitleKey(value) {
  return String(value || "")
    .replace(/\s+/g, "")
    .replace(/[（(].*?[）)]/g, "")
    .replace(/[^\u4e00-\u9fa5A-Za-z0-9]/g, "")
    .toLowerCase();
}

function pickPrimaryCollection(collections) {
  return [...collections].sort((left, right) => {
    const leftExact = left.title === left.subject_display_name ? 1 : 0;
    const rightExact = right.title === right.subject_display_name ? 1 : 0;
    if (leftExact !== rightExact) {
      return rightExact - leftExact;
    }
    return left.title.length - right.title.length;
  })[0];
}

function mergeCollectionsBySubject(collections) {
  const grouped = new Map();
  for (const collection of collections) {
    if (!grouped.has(collection.subject_key)) {
      grouped.set(collection.subject_key, []);
    }
    grouped.get(collection.subject_key).push(collection);
  }

  return Array.from(grouped.values())
    .map((group) => {
      const primary = pickPrimaryCollection(group);
      return {
        id: `subject:${primary.subject_key}`,
        title: primary.subject_display_name,
        subject: primary.subject,
        subject_key: primary.subject_key,
        subject_display_name: primary.subject_display_name,
        description:
          group.length > 1
            ? `已自动合并 ${group.length} 个同学科来源，前台不再分开显示。`
            : primary.description,
        primary_collection_id: primary.id,
        member_collection_ids: group.map((item) => item.id).sort((left, right) => left - right),
      };
    })
    .sort((left, right) => left.title.localeCompare(right.title, "zh-CN"));
}

function pickBetterDocument(current, candidate) {
  if (!current) {
    return candidate;
  }
  const currentScore = (current.chunk_count || 0) * 10 + (current.page_count || 0);
  const candidateScore = (candidate.chunk_count || 0) * 10 + (candidate.page_count || 0);
  return candidateScore >= currentScore ? candidate : current;
}

function dedupeDocuments(documents) {
  const deduped = new Map();
  for (const document of documents) {
    const key = document.file_name || `document:${document.id}`;
    deduped.set(key, pickBetterDocument(deduped.get(key), document));
  }
  return Array.from(deduped.values()).sort((left, right) => right.id - left.id);
}

function pickBetterCard(current, candidate) {
  if (!current) {
    return candidate;
  }
  const scoreCard = (card) => {
    const fieldCount = Object.entries(card.normalized_content || {}).filter(
      ([key, value]) => value && !["template_key", "template_label"].includes(key),
    ).length;
    const citationCount = card.citations?.length || 0;
    return fieldCount * 10 + citationCount;
  };
  return scoreCard(candidate) >= scoreCard(current) ? candidate : current;
}

function getCardDedupeKey(card) {
  const canonicalName =
    card.normalized_content?.acupoint_name ||
    card.normalized_content?.disease_name ||
    card.normalized_content?.pattern_name ||
    card.title;
  return `${card.template_key}:${normalizeTitleKey(canonicalName) || card.id}`;
}

function dedupeCards(cards) {
  const deduped = new Map();
  for (const card of cards) {
    const key = getCardDedupeKey(card);
    deduped.set(key, pickBetterCard(deduped.get(key), card));
  }
  return Array.from(deduped.values()).sort((left, right) => right.id - left.id);
}

const fieldLabels = {
  acupoint_name: "穴位名称",
  meridian: "经络",
  location: "定位",
  indication: "主治",
  technique: "刺灸法",
  caution: "注意事项",
  disease_name: "病证名称",
  treatment_principle: "治法原则",
  acupoint_prescription: "处方取穴",
  notes: "加减按语",
  pattern_name: "证候名称",
  stage: "阶段",
  syndrome: "证候表现",
  treatment: "治法",
  formula: "方药",
  differentiation: "辨证要点",
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
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

function syncCollectionSelects() {
  const switcher = document.getElementById("collection-switcher");
  const current = String(state.activeCollectionId || "");

  if (switcher) {
    switcher.innerHTML = state.collections.length
      ? state.collections
          .map(
            (collection) => `
              <option value="${collection.id}" ${
                String(collection.id) === current ? "selected" : ""
              }>
                ${escapeHtml(collection.title)}
              </option>
            `,
          )
          .join("")
      : '<option value="">暂无集合</option>';
  }
}

function getActiveCollection() {
  return state.collections.find((item) => item.id === state.activeCollectionId) || null;
}

function getActiveCard() {
  return state.cards.find((item) => item.id === state.activeCardId) || null;
}

function getActiveDocument() {
  return state.documents.find((item) => item.id === state.activeDocumentId) || null;
}

function findTemplateLabel(templateKey) {
  return state.templates.find((item) => item.key === templateKey)?.label || templateKey;
}

function pickRandomItem(items) {
  if (!items.length) {
    return null;
  }
  return items[Math.floor(Math.random() * items.length)];
}

function renderImportanceStars(card) {
  const current = Number(card.importance_level || 0);
  return Array.from({ length: 5 }, (_, index) => {
    const level = index + 1;
    return `
      <button
        type="button"
        class="importance-star ${level <= current ? "is-active" : ""}"
        data-importance-level="${level}"
        aria-label="重要程度 ${level} 星"
        title="重要程度 ${level} 星"
      >
        ★
      </button>
    `;
  }).join("");
}

function getTemplateCards(templateKey = state.activeTemplateKey) {
  return state.cards.filter((card) => card.template_key === templateKey);
}

function getRandomDrawPool(templateKey = state.activeTemplateKey) {
  return getTemplateCards(templateKey);
}

function getDocumentTemplateScore(document, templateKey, subjectKey) {
  const haystack = `${document.file_name || ""}\n${document.preview || ""}`;
  let score = 0;

  if (subjectKey === "acupuncture") {
    if (templateKey === "clinical_treatment") {
      if (/病症|诊治|治疗|治法|治则|处方|取穴|主穴|配穴|加减|病机/.test(haystack)) score += 5;
      if (/疼症|心脑病症|肺系病症|妇儿科病症|五官病症|其他病症/.test(haystack)) score += 4;
      if (/【定位】|定位[：:]/.test(haystack)) score -= 3;
      if (/刺灸法|操作[：:]/.test(haystack)) score -= 2;
      if (/目录|前言|编写说明|绪论|总论/.test(haystack)) score -= 6;
    } else {
      if (/【定位】|定位[：:]/.test(haystack)) score += 4;
      if (/【主治】|主治[：:]/.test(haystack)) score += 4;
      if (/【操作】|刺灸法|操作[：:]/.test(haystack)) score += 3;
      if (/\d+\.[\u4e00-\u9fa5]{1,8}(?:\*|\s)*\(/.test(haystack)) score += 4;
      if (/(LU|LI|ST|SP|HT|SI|BL|KI|PC|SJ|GB|LR|CV|GV)\s?\d+/i.test(haystack)) score += 3;
      if (/腧穴|俞穴|经穴|原穴|络穴|合穴|井穴|荥穴|输穴|郄穴/.test(haystack)) score += 2;
      if (/前置页|目录|前言|编写说明|绪论|总论/.test(haystack)) score -= 6;
    }
  }

  if (subjectKey === "warm_disease") {
    if (/证候|表现[：:]/.test(haystack)) score += 4;
    if (/治法[：:]/.test(haystack)) score += 4;
    if (/方药|代表方/.test(haystack)) score += 4;
    if (/辨证要点|卫分|气分|营分|血分|上焦|中焦|下焦/.test(haystack)) score += 2;
    if (/前言|目录|总论|绪论/.test(haystack)) score -= 4;
  }

  if (templateKey?.includes("review")) {
    score += 1;
  }

  return score;
}

function pickBestDocumentForCurrentTemplate(excludedDocumentId = null) {
  const activeCollection = getActiveCollection();
  if (!activeCollection || !state.documents.length || !state.activeTemplateKey) {
    return null;
  }

  let best = null;
  for (const document of state.documents) {
    if (document.id === excludedDocumentId) {
      continue;
    }
    const score = getDocumentTemplateScore(
      document,
      state.activeTemplateKey,
      activeCollection.subject_key,
    );
    if (!best || score > best.score) {
      best = { document, score };
    }
  }
  return best;
}

function syncBestDocumentSelection() {
  if (!state.documents.length) {
    state.activeDocumentId = null;
    return;
  }

  const current = getActiveDocument();
  const best = pickBestDocumentForCurrentTemplate();
  if (!current) {
    state.activeDocumentId = best?.document.id || state.documents[0].id;
    return;
  }

  const activeCollection = getActiveCollection();
  if (!activeCollection) {
    return;
  }
  const currentScore = getDocumentTemplateScore(
    current,
    state.activeTemplateKey,
    activeCollection.subject_key,
  );
  if (best && best.score > currentScore && currentScore <= 0) {
    state.activeDocumentId = best.document.id;
  }
}

function renderWorkspaceHeader() {
  const active = getActiveCollection();
  const title = document.getElementById("workspace-title");
  if (title) {
    title.textContent = active ? active.title : "选择一个集合";
  }
}

function renderTemplates() {
  const container = document.getElementById("template-list");
  if (!state.templates.length) {
    container.innerHTML = '<div class="empty-inline">当前学科还没有可用模板。</div>';
    return;
  }

  if (!state.activeTemplateKey) {
    state.activeTemplateKey = state.templates[0].key;
  }

  container.innerHTML = state.templates
    .map(
      (template) => `
        <button
          type="button"
          class="template-chip ${template.key === state.activeTemplateKey ? "is-active" : ""}"
          data-template-key="${template.key}"
        >
          <strong>${escapeHtml(template.label)}</strong>
          <span>${escapeHtml(template.description)}</span>
        </button>
      `,
    )
    .join("");

  container.querySelectorAll("[data-template-key]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeTemplateKey = button.dataset.templateKey;
      const templateCards = getTemplateCards(state.activeTemplateKey);
      state.activeCardId = templateCards[0]?.id || null;
      syncBestDocumentSelection();
      renderTemplates();
      renderCards();
    });
  });
}

function renderCards() {
  const container = document.getElementById("cards-list");
  if (!container) {
    renderCardDetail();
    return;
  }
  if (!state.cards.length) {
    container.className = "empty-state";
    container.textContent = "还没有卡片。";
    renderCardDetail();
    return;
  }

  if (!state.activeCardId && state.cards.length) {
    state.activeCardId = getTemplateCards()[0]?.id || state.cards[0].id;
  }
  const card = getActiveCard() || getTemplateCards()[0] || state.cards[0];
  if (!card) {
    container.className = "empty-state";
    container.textContent = "还没有卡片。";
    renderCardDetail();
    return;
  }
  state.activeCardId = card.id;

  const detailRows = Object.entries(card.normalized_content || {})
    .filter(([key, value]) => value && !["template_key", "template_label"].includes(key))
    .map(
      ([key, value]) => `
        <div class="detail-row">
          <strong>${escapeHtml(fieldLabels[key] || key)}</strong>
          <span>${escapeHtml(value)}</span>
        </div>
      `,
    )
    .join("");

  container.className = "focus-card";
  container.innerHTML = `
    <article class="focus-card-shell">
      <div class="focus-card-top">
        <div class="list-meta">
          <span class="chip">${escapeHtml(card.subject_display_name)}</span>
          <span class="chip">${escapeHtml(findTemplateLabel(card.template_key))}</span>
        </div>
        <div class="importance-picker" title="按重要程度手动标星">
          <span class="importance-label">重要程度</span>
          <div class="importance-stars">
            ${renderImportanceStars(card)}
          </div>
        </div>
      </div>
      <div class="focus-card-header">
        <h3>${escapeHtml(card.title)}</h3>
        <p>${escapeHtml(card.source_document_name || "后台已保存来源文档")}</p>
      </div>
      <div class="detail-grid">
        ${detailRows || '<div class="empty-inline">这张卡片还没有结构化字段。</div>'}
      </div>
    </article>
  `;
  container.querySelectorAll("[data-importance-level]").forEach((button) => {
    button.addEventListener("click", async () => {
      await updateCardImportance(card.id, Number(button.dataset.importanceLevel));
    });
  });
  renderCardDetail();
}

function renderCardDetail() {
  const container = document.getElementById("card-detail");
  if (!container) {
    return;
  }
  const card = getActiveCard();
  if (!card) {
    container.className = "empty-state";
    container.textContent = "点击“随机抽卡”后，这里会显示对应原文。";
    return;
  }

  const citations = (card.citations || [])
    .map(
      (citation) => `
        <article class="citation-card">
          <div class="list-meta">
            <span class="chip">${escapeHtml(citation.document_name)}</span>
            <span>第 ${escapeHtml(citation.page_number)} 页</span>
          </div>
          <p>${escapeHtml(citation.quote)}</p>
        </article>
      `,
    )
    .join("");

  container.className = "detail-stack";
  container.innerHTML = `
    <div class="detail-header">
      <p class="workspace-kicker">原文指引</p>
      <h3>${escapeHtml(card.title)}</h3>
      <p>${escapeHtml(card.source_document_name || "无来源文档")}</p>
    </div>
    <div class="citation-stack">
      <h4>原文引用</h4>
      ${citations || '<div class="empty-inline">这张卡片还没有引用。</div>'}
    </div>
  `;
}

async function loadCollections() {
  const collections = await api("/api/collections");
  state.collections = mergeCollectionsBySubject(collections);
  if (!state.activeCollectionId && state.collections.length) {
    state.activeCollectionId = state.collections[0].id;
  }
  syncCollectionSelects();
}

async function loadDocumentsForActiveCollection() {
  const active = getActiveCollection();
  if (!active) {
    return [];
  }

  const documents = await Promise.all(
    active.member_collection_ids.map((collectionId) =>
      api(`/api/documents?collection_id=${collectionId}`),
    ),
  );
  return dedupeDocuments(documents.flat());
}

async function loadCardsForActiveCollection(userId) {
  const active = getActiveCollection();
  if (!active) {
    return [];
  }

  const cards = await Promise.all(
    active.member_collection_ids.map((collectionId) =>
      api(`/api/cards?collection_id=${collectionId}&user_id=${userId}`),
    ),
  );
  return dedupeCards(cards.flat());
}

async function refreshWorkspace() {
  renderWorkspaceHeader();

  const active = getActiveCollection();
  if (!active) {
    state.documents = [];
    state.cards = [];
    state.templates = [];
    state.activeTemplateKey = null;
    state.activeDocumentId = null;
    state.activeCardId = null;
    renderTemplates();
    renderCards();
    return;
  }

  const userId = state.currentUserId || 1;
  state.documents = await loadDocumentsForActiveCollection();
  state.cards = await loadCardsForActiveCollection(userId);
  state.templates = await api(`/api/templates?subject=${active.subject_key}`);

  if (!state.templates.find((template) => template.key === state.activeTemplateKey)) {
    state.activeTemplateKey = state.templates[0]?.key || null;
  }
  const activeTemplateCards = getTemplateCards();
  if (
    !state.cards.find((card) => card.id === state.activeCardId) ||
    (activeTemplateCards.length &&
      !activeTemplateCards.find((card) => card.id === state.activeCardId))
  ) {
    state.activeCardId = activeTemplateCards[0]?.id || state.cards[0]?.id || null;
  }
  syncBestDocumentSelection();

  renderWorkspaceHeader();
  renderTemplates();
  renderCards();
}

async function updateCardImportance(cardId, importanceLevel) {
  const userId = state.currentUserId || 1;
  const updatedCard = await api(`/api/cards/${cardId}/importance?user_id=${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ importance_level: importanceLevel }),
  });
  state.cards = state.cards.map((card) => (card.id === updatedCard.id ? updatedCard : card));
  state.activeCardId = updatedCard.id;
  renderCards();
  setStatus(`已将「${updatedCard.title}」标记为 ${importanceLevel} 星重要程度。`);
  return updatedCard;
}

async function handleUserSelected(userId) {
  state.currentUserId = userId;
  localStorage.setItem("ocdoctor_user_id", userId);

  const overlay = document.getElementById("user-select-overlay");
  if (overlay) {
    overlay.classList.add("hidden");
  }

  renderCurrentUserDisplay();

  if (state.collections.length) {
    await refreshWorkspace();
    setStatus("已切换账号。");
    return;
  }

  await bootstrapWorkspace();
}

async function drawRandomCard() {
  if (!state.activeTemplateKey) {
    setStatus("请先选择一个模板。");
    return;
  }

  const button = document.getElementById("generate-button");

  try {
    setButtonBusy(button, true, "抽卡中...");
    const existingCards = getRandomDrawPool();
    if (existingCards.length) {
      setStatus("正在随机抽卡...");
      const drawnCard = pickRandomItem(existingCards);
      state.activeCardId = drawnCard.id;
      renderCards();
      setStatus(`已随机抽到「${drawnCard.title}」。`);
      return;
    }

    let activeDocument = getActiveDocument();
    if (!activeDocument) {
      activeDocument = pickBestDocumentForCurrentTemplate()?.document || null;
    }
    if (!activeDocument) {
      setStatus("当前集合里还没有可抽卡的后台文档。");
      return;
    }
    if (state.activeDocumentId !== activeDocument.id) {
      state.activeDocumentId = activeDocument.id;
    }

    setStatus("正在整理内容并随机抽卡...");
    const userId = state.currentUserId || 1;
    let payload;
    try {
      payload = await api(`/api/cards/generate?user_id=${userId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: activeDocument.id,
          template_key: state.activeTemplateKey,
        }),
      });
    } catch (error) {
      const bestAlternative = pickBestDocumentForCurrentTemplate(activeDocument.id);
      if (
        error.message.includes("No cards could be generated") &&
        bestAlternative &&
        bestAlternative.score > 0
      ) {
        activeDocument = bestAlternative.document;
        state.activeDocumentId = activeDocument.id;
        setStatus(`当前文档不适合该模板，已自动改用《${activeDocument.file_name}》继续抽卡...`);
        payload = await api(`/api/cards/generate?user_id=${userId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            document_id: activeDocument.id,
            template_key: state.activeTemplateKey,
          }),
        });
      } else {
        throw error;
      }
    }
    state.cards = await loadCardsForActiveCollection(userId);
    let drawnCard =
      pickRandomItem(
        payload.cards.filter((card) => card.template_key === state.activeTemplateKey),
      ) ||
      pickRandomItem(getRandomDrawPool()) ||
      state.cards[0] ||
      null;
    state.activeCardId = drawnCard?.id || null;
    renderWorkspaceHeader();
    renderCards();
    setStatus(
      drawnCard
        ? `已从《${activeDocument.file_name}》整理出 ${payload.cards.length} 张卡片，随机抽到「${drawnCard.title}」。`
        : `已从《${activeDocument.file_name}》整理出 ${payload.cards.length} 张卡片。`,
    );
  } catch (error) {
    setStatus(`随机抽卡失败：${error.message}。请先保证当前集合里已经有合适的正文文档。`);
  } finally {
    setButtonBusy(button, false, "抽卡中...");
  }
}

function renderUserSelect() {
  const overlay = document.getElementById("user-select-overlay");
  const container = document.getElementById("user-buttons");
  if (!overlay || !container) return;

  container.innerHTML = state.users
    .map(
      (user) => `
      <button type="button" class="user-button user-${user.id}" data-user-id="${user.id}">
        ${escapeHtml(user.name)}
      </button>
    `,
    )
    .join("");

  container.querySelectorAll("[data-user-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const userId = Number(button.dataset.userId);
      await handleUserSelected(userId);
    });
  });
}

function renderCurrentUserDisplay() {
  const display = document.getElementById("current-user-display");
  if (!display) return;
  const user = state.users.find((u) => u.id === state.currentUserId);
  display.textContent = user ? user.name : "未选择";
  display.title = "点击切换账号";
}

function switchUser() {
  const overlay = document.getElementById("user-select-overlay");
  if (overlay) {
    overlay.classList.remove("hidden");
  }
  renderUserSelect();
}

async function bootstrap() {
  // First load users
  try {
    state.users = await api("/api/users");
  } catch (error) {
    setStatus(`加载用户列表失败：${error.message}`);
    return;
  }

  // Check for saved user
  const savedUserId = localStorage.getItem("ocdoctor_user_id");
  if (savedUserId && state.users.find((u) => u.id === Number(savedUserId))) {
    await handleUserSelected(Number(savedUserId));
  } else {
    // Show user selection
    renderUserSelect();
  }
}

async function bootstrapWorkspace() {
  try {
    setStatus("正在加载知识库...");
    await loadCollections();
    await refreshWorkspace();

    const generateButton = document.getElementById("generate-button");
    if (generateButton) {
      generateButton.onclick = drawRandomCard;
    }
    const collectionSwitcher = document.getElementById("collection-switcher");
    if (collectionSwitcher) {
      collectionSwitcher.onchange = async (event) => {
        const id = event.target.value;
        if (id) {
          state.activeCollectionId = id;
          state.activeDocumentId = null;
          state.activeCardId = null;
          syncCollectionSelects();
          await refreshWorkspace();
        }
      };
    }

    // User display click to switch
    const userDisplay = document.getElementById("current-user-display");
    if (userDisplay) {
      userDisplay.onclick = switchUser;
    }

    // Register request button
    const registerRequestButton = document.getElementById("register-request-button");
    if (registerRequestButton) {
      registerRequestButton.onclick = openCardRequestModal;
    }

    // My requests button
    const myRequestsBtn = document.getElementById("my-requests-btn");
    if (myRequestsBtn) {
      myRequestsBtn.onclick = openMyRequestsModal;
    }

    // Card request form
    const cardRequestForm = document.getElementById("card-request-form");
    if (cardRequestForm) {
      cardRequestForm.onsubmit = submitCardRequest;
    }

    // Modal close buttons
    document.querySelectorAll(".modal-close, .modal-cancel, .modal-backdrop").forEach((el) => {
      el.addEventListener("click", (e) => {
        if (e.target.closest("#card-request-modal")) {
          closeCardRequestModal();
        }
        if (e.target.closest("#my-requests-modal")) {
          closeMyRequestsModal();
        }
      });
    });

    setStatus("准备就绪，可以开始随机抽卡。");
  } catch (error) {
    setStatus(`初始化失败：${error.message}`);
  }
}

// Card Request functions
function openCardRequestModal() {
  const modal = document.getElementById("card-request-modal");
  if (modal) {
    modal.classList.remove("hidden");
    document.getElementById("requested-name").focus();
  }
}

function closeCardRequestModal() {
  const modal = document.getElementById("card-request-modal");
  if (modal) {
    modal.classList.add("hidden");
    document.getElementById("card-request-form").reset();
  }
}

async function submitCardRequest(event) {
  event.preventDefault();
  const form = event.target;
  const userId = state.currentUserId || 1;

  const requestedName = form.requested_name.value.trim();
  const chapterInfo = form.chapter_info.value.trim();
  const notes = form.notes.value.trim();

  if (!requestedName) {
    setStatus("请输入希望学习的卡片名称。");
    return;
  }

  try {
    setStatus("正在提交登记...");
    const cardRequest = await api("/api/card-requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        requested_name: requestedName,
        chapter_info: chapterInfo || null,
        notes: notes || null,
        collection_id: getActiveCollection()?.primary_collection_id || null,
      }),
    });
    closeCardRequestModal();
    setStatus(`已成功登记「${requestedName}」，我们会尽快处理。`);
  } catch (error) {
    setStatus(`登记失败：${error.message}`);
  }
}

async function loadMyRequests() {
  const userId = state.currentUserId || 1;
  return api(`/api/card-requests?user_id=${userId}`);
}

function renderMyRequests(requests) {
  const container = document.getElementById("my-requests-list");
  if (!container) return;

  if (!requests.length) {
    container.innerHTML = '<div class="empty-requests">暂无缺口登记</div>';
    return;
  }

  container.innerHTML = requests
    .map(
      (req) => `
      <div class="request-item">
        <div class="request-header">
          <span class="request-title">${escapeHtml(req.requested_name)}</span>
          <span class="request-status ${req.status}">${req.status === "pending" ? "待处理" : req.status === "acknowledged" ? "已确认" : "已处理"}</span>
        </div>
        ${req.chapter_info ? `<div class="request-meta">${escapeHtml(req.chapter_info)}</div>` : ""}
        ${req.notes ? `<div class="request-notes">${escapeHtml(req.notes)}</div>` : ""}
        <div class="request-meta">登记时间：${new Date(req.created_at).toLocaleDateString("zh-CN")}</div>
        ${
          req.status === "pending"
            ? `
          <div class="request-actions">
            <button type="button" class="btn-secondary" data-cancel-request="${req.id}">取消登记</button>
          </div>
        `
            : ""
        }
      </div>
    `,
    )
    .join("");

  container.querySelectorAll("[data-cancel-request]").forEach((button) => {
    button.addEventListener("click", async () => {
      const requestId = Number(button.dataset.cancelRequest);
      await cancelCardRequest(requestId);
    });
  });
}

async function cancelCardRequest(requestId) {
  try {
    setStatus("正在取消登记...");
    await api(`/api/card-requests/${requestId}?user_id=${state.currentUserId || 1}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "cancelled" }),
    });
    const requests = await loadMyRequests();
    renderMyRequests(requests);
    setStatus("已取消登记。");
  } catch (error) {
    setStatus(`取消失败：${error.message}`);
  }
}

async function openMyRequestsModal() {
  const modal = document.getElementById("my-requests-modal");
  if (!modal) return;

  try {
    setStatus("正在加载缺口登记...");
    const requests = await loadMyRequests();
    renderMyRequests(requests);
    modal.classList.remove("hidden");
    setStatus("");
  } catch (error) {
    setStatus(`加载失败：${error.message}`);
  }
}

function closeMyRequestsModal() {
  const modal = document.getElementById("my-requests-modal");
  if (modal) {
    modal.classList.add("hidden");
  }
}

bootstrap();
