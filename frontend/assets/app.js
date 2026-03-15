const state = {
  subjects: [],
  collections: [],
  documents: [],
  cards: [],
  templates: [],
  activeCollectionId: null,
  activeDocumentId: null,
  activeCardId: null,
  activeTemplateKey: null,
};

const MAX_WEB_PDF_UPLOAD_BYTES = 4 * 1024 * 1024;

const fieldLabels = {
  acupoint_name: "穴位名称",
  meridian: "经络",
  location: "定位",
  indication: "主治",
  technique: "刺灸法",
  caution: "注意事项",
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
  const uploadSelect = document.getElementById("upload-collection-select");
  const switcher = document.getElementById("collection-switcher");
  const current = String(state.activeCollectionId || "");

  const optionsHtml = state.collections.length
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

  if (uploadSelect) {
    uploadSelect.innerHTML = state.collections.length
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
  }

  if (switcher) {
    switcher.innerHTML = optionsHtml;
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
    if (/【定位】|定位[：:]/.test(haystack)) score += 4;
    if (/【主治】|主治[：:]/.test(haystack)) score += 4;
    if (/【操作】|刺灸法|操作[：:]/.test(haystack)) score += 3;
    if (/\d+\.[\u4e00-\u9fa5]{1,8}(?:\*|\s)*\(/.test(haystack)) score += 4;
    if (/(LU|LI|ST|SP|HT|SI|BL|KI|PC|SJ|GB|LR|CV|GV)\s?\d+/i.test(haystack)) score += 3;
    if (/腧穴|俞穴|经穴|原穴|络穴|合穴|井穴|荥穴|输穴|郄穴/.test(haystack)) score += 2;
    if (/前置页|目录|前言|编写说明|绪论|总论/.test(haystack)) score -= 6;
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

function renderSubjects() {
  const select = document.getElementById("subject-select");
  if (!select) {
    return;
  }
  select.innerHTML = state.subjects
    .map(
      (subject) => `
        <option value="${escapeHtml(subject.display_name)}">${escapeHtml(subject.display_name)}</option>
      `,
    )
    .join("");
}

function renderCollections() {
  const container = document.getElementById("collections-list");
  if (!container) {
    return;
  }
  if (!state.collections.length) {
    container.className = "stack-list empty-state";
    container.textContent = "先创建一个集合。";
    return;
  }

  container.className = "stack-list";
  container.innerHTML = state.collections
    .map(
      (collection) => `
        <article
          class="list-card ${collection.id === state.activeCollectionId ? "is-active" : ""}"
          data-collection-id="${collection.id}"
        >
          <div class="list-card-top">
            <span class="chip">${escapeHtml(collection.subject_display_name)}</span>
            <button
              type="button"
              class="delete-button"
              data-delete-collection-id="${collection.id}"
            >
              删除
            </button>
          </div>
          <h3>${escapeHtml(collection.title)}</h3>
          <p>${escapeHtml(collection.description || "暂无备注")}</p>
        </article>
      `,
    )
    .join("");

  container.querySelectorAll("[data-collection-id]").forEach((item) => {
    item.addEventListener("click", async () => {
      state.activeCollectionId = Number(item.dataset.collectionId);
      state.activeDocumentId = null;
      state.activeCardId = null;
      syncCollectionSelects();
      await refreshWorkspace();
    });
  });

  container.querySelectorAll("[data-delete-collection-id]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      await deleteCollection(Number(button.dataset.deleteCollectionId));
    });
  });
}

function renderWorkspaceHeader() {
  const active = getActiveCollection();
  const title = document.getElementById("workspace-title");
  if (title) {
    title.textContent = active ? active.title : "选择一个集合";
  }
  const documentCount = document.getElementById("document-count");
  if (documentCount) {
    documentCount.textContent = state.documents.length;
  }
  const cardCount = document.getElementById("card-count");
  if (cardCount) {
    cardCount.textContent = state.cards.length;
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
      renderDocuments();
      renderCards();
    });
  });
}

function renderDocuments() {
  const container = document.getElementById("documents-list");
  if (!container) {
    return;
  }
  if (!state.documents.length) {
    container.className = "stack-list empty-state";
    container.textContent = "还没有导入文档。";
    return;
  }

  container.className = "stack-list";
  container.innerHTML = state.documents
    .map(
      (document) => `
        <article
          class="list-card ${document.id === state.activeDocumentId ? "is-active" : ""}"
          data-document-id="${document.id}"
        >
          <div class="list-card-top">
            <div class="list-meta">
              <span class="chip">${escapeHtml(document.type.toUpperCase())}</span>
              ${
                getDocumentTemplateScore(
                  document,
                  state.activeTemplateKey,
                  getActiveCollection()?.subject_key,
                ) > 0
                  ? '<span class="chip">可抽卡</span>'
                  : ""
              }
              <span>${document.page_count} 页 / ${document.chunk_count} 段</span>
            </div>
            <button
              type="button"
              class="delete-button"
              data-delete-document-id="${document.id}"
            >
              删除
            </button>
          </div>
          <h3>${escapeHtml(document.file_name)}</h3>
          <p>${escapeHtml(document.preview || "暂无摘要")}</p>
        </article>
      `,
    )
    .join("");

  container.querySelectorAll("[data-document-id]").forEach((item) => {
    item.addEventListener("click", () => {
      state.activeDocumentId = Number(item.dataset.documentId);
      renderDocuments();
    });
  });

  container.querySelectorAll("[data-delete-document-id]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      await deleteDocument(Number(button.dataset.deleteDocumentId));
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
        <div class="draw-count" title="随机抽到次数">
          <span class="draw-star">★</span>
          <strong>${escapeHtml(card.draw_count || 0)}</strong>
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
  renderCardDetail();
}

function renderCardDetail() {
  const container = document.getElementById("card-detail");
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

async function refreshWorkspace() {
  renderCollections();
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
    renderDocuments();
    renderCards();
    return;
  }

  state.documents = await api(`/api/documents?collection_id=${active.id}`);
  state.cards = await api(`/api/cards?collection_id=${active.id}`);
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
  renderDocuments();
  renderCards();
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
    await api("/api/collections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    formElement.reset();
    await loadCollections();
    await refreshWorkspace();
    setStatus(`已创建集合：${payload.title}`);
  } catch (error) {
    setStatus(`创建集合失败：${error.message}`);
  } finally {
    setButtonBusy(submitButton, false, "创建中...");
  }
}

async function deleteCollection(collectionId) {
  try {
    setStatus("正在删除集合...");
    await api(`/api/collections/${collectionId}`, { method: "DELETE" });
    if (state.activeCollectionId === collectionId) {
      state.activeCollectionId = null;
      state.activeDocumentId = null;
      state.activeCardId = null;
    }
    await loadCollections();
    await refreshWorkspace();
    setStatus("集合已删除。");
  } catch (error) {
    setStatus(`删除集合失败：${error.message}`);
  }
}

async function uploadPdf(event) {
  event.preventDefault();
  const collectionSelect = document.getElementById("upload-collection-select");
  const targetCollectionId = Number(collectionSelect.value);
  if (!targetCollectionId) {
    setStatus("请先创建或选择一个集合。");
    return;
  }

  const formElement = event.currentTarget;
  const submitButton = formElement.querySelector('button[type="submit"]');
  const fileInput = document.getElementById("pdf-input");
  const file = fileInput.files?.[0];

  if (!file) {
    setStatus("请先选择一个 PDF。");
    return;
  }
  if (file.size > MAX_WEB_PDF_UPLOAD_BYTES) {
    setStatus(
      "这个 PDF 超过当前网页文档上传限制。请先压缩或拆分到 4 MB 内；200 MB 这类扫描版教材建议拆分后再用本地导入工具回传。",
    );
    return;
  }

  const formData = new FormData();
  formData.append("collection_id", String(targetCollectionId));
  formData.append("file", file);

  try {
    setButtonBusy(submitButton, true, "导入中...");
    setStatus("正在解析 PDF...");
    const payload = await api("/api/import/pdf", {
      method: "POST",
      body: formData,
    });
    fileInput.value = "";
    state.activeCollectionId = targetCollectionId;
    await refreshWorkspace();
    state.activeDocumentId = payload.document_id;
    renderDocuments();
    setStatus(`已导入文档，整理出 ${payload.chunk_count} 个片段，可以直接随机抽卡。`);
  } catch (error) {
    setStatus(`导入失败：${error.message}`);
  } finally {
    setButtonBusy(submitButton, false, "导入中...");
  }
}

async function recordCardDraw(cardId) {
  const updatedCard = await api(`/api/cards/${cardId}/draw`, { method: "POST" });
  state.cards = state.cards.map((card) => (card.id === updatedCard.id ? updatedCard : card));
  state.activeCardId = updatedCard.id;
  return updatedCard;
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
      const updatedCard = await recordCardDraw(drawnCard.id);
      renderCards();
      setStatus(`已随机抽到「${updatedCard.title}」。`);
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
      renderDocuments();
    }

    setStatus("正在整理内容并随机抽卡...");
    let payload;
    try {
      payload = await api("/api/cards/generate", {
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
        renderDocuments();
        setStatus(`当前文档不适合该模板，已自动改用《${activeDocument.file_name}》继续抽卡...`);
        payload = await api("/api/cards/generate", {
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
    state.cards = await api(`/api/cards?collection_id=${state.activeCollectionId}`);
    let drawnCard =
      pickRandomItem(
        payload.cards.filter((card) => card.template_key === state.activeTemplateKey),
      ) ||
      pickRandomItem(getRandomDrawPool()) ||
      state.cards[0] ||
      null;
    if (drawnCard) {
      drawnCard = await recordCardDraw(drawnCard.id);
    }
    state.activeCardId = drawnCard?.id || null;
    renderWorkspaceHeader();
    renderDocuments();
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

async function exportCollection() {
  const active = getActiveCollection();
  if (!active) {
    setStatus("请先选择一个集合。");
    return;
  }

  const button = document.getElementById("export-button");
  try {
    setButtonBusy(button, true, "导出中...");
    setStatus("正在导出 Markdown...");
    const payload = await api(`/api/collections/${active.id}/export`);
    const blob = new Blob([payload.content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = payload.filename;
    link.click();
    URL.revokeObjectURL(url);
    setStatus("导出完成。");
  } catch (error) {
    setStatus(`导出失败：${error.message}`);
  } finally {
    setButtonBusy(button, false, "导出中...");
  }
}

async function deleteDocument(documentId) {
  try {
    setStatus("正在删除文档...");
    await api(`/api/documents/${documentId}`, { method: "DELETE" });
    if (state.activeDocumentId === documentId) {
      state.activeDocumentId = null;
      state.activeCardId = null;
    }
    await refreshWorkspace();
    setStatus("文档已删除。");
  } catch (error) {
    setStatus(`删除文档失败：${error.message}`);
  }
}

async function bootstrap() {
  try {
    setStatus("正在加载知识库...");
    await loadSubjects();
    await loadCollections();
    await refreshWorkspace();

    const collectionForm = document.getElementById("collection-form");
    if (collectionForm) {
      collectionForm.addEventListener("submit", createCollection);
    }
    const uploadForm = document.getElementById("upload-form");
    if (uploadForm) {
      uploadForm.addEventListener("submit", uploadPdf);
    }
    const generateButton = document.getElementById("generate-button");
    if (generateButton) {
      generateButton.addEventListener("click", drawRandomCard);
    }
    const exportButton = document.getElementById("export-button");
    if (exportButton) {
      exportButton.addEventListener("click", exportCollection);
    }
    const collectionSwitcher = document.getElementById("collection-switcher");
    if (collectionSwitcher) {
      collectionSwitcher.addEventListener("change", async (event) => {
        const id = Number(event.target.value);
        if (id) {
          state.activeCollectionId = id;
          state.activeDocumentId = null;
          state.activeCardId = null;
          syncCollectionSelects();
          await refreshWorkspace();
        }
      });
    }
    setStatus("准备就绪，可以开始随机抽卡。");
  } catch (error) {
    setStatus(`初始化失败：${error.message}`);
  }
}

bootstrap();
