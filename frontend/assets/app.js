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
  if (!uploadSelect) {
    return;
  }

  const current = String(state.activeCollectionId || "");
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

function getActiveCollection() {
  return state.collections.find((item) => item.id === state.activeCollectionId) || null;
}

function getActiveCard() {
  return state.cards.find((item) => item.id === state.activeCardId) || null;
}

function getActiveDocument() {
  return state.documents.find((item) => item.id === state.activeDocumentId) || null;
}

function renderSubjects() {
  const select = document.getElementById("subject-select");
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
  document.getElementById("workspace-title").textContent = active
    ? active.title
    : "选择一个集合开始导入 PDF";
  document.getElementById("workspace-subtitle").textContent = active
    ? `${active.subject_display_name} · ${active.description || "上传文档后，选择模板生成卡片。"}`
    : "上传文档后，选择模板生成卡片，每张卡片都会带原文引用。";
  document.getElementById("document-count").textContent = state.documents.length;
  document.getElementById("card-count").textContent = state.cards.length;
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
      renderTemplates();
    });
  });
}

function renderDocuments() {
  const container = document.getElementById("documents-list");
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
  if (!state.cards.length) {
    container.className = "stack-list empty-state";
    container.textContent = "还没有卡片。";
    renderCardDetail();
    return;
  }

  container.className = "stack-list";
  container.innerHTML = state.cards
    .map(
      (card) => `
        <article
          class="list-card ${card.id === state.activeCardId ? "is-active" : ""}"
          data-card-id="${card.id}"
        >
          <div class="list-meta">
            <span class="chip">${escapeHtml(card.subject_display_name)}</span>
            <span>${escapeHtml(card.template_key)}</span>
          </div>
          <h3>${escapeHtml(card.title)}</h3>
          <p>${escapeHtml(card.raw_excerpt || "暂无摘录")}</p>
        </article>
      `,
    )
    .join("");

  container.querySelectorAll("[data-card-id]").forEach((item) => {
    item.addEventListener("click", () => {
      state.activeCardId = Number(item.dataset.cardId);
      renderCards();
      renderCardDetail();
    });
  });

  if (!state.activeCardId && state.cards.length) {
    state.activeCardId = state.cards[0].id;
  }
  renderCardDetail();
}

function renderCardDetail() {
  const container = document.getElementById("card-detail");
  const card = getActiveCard();
  if (!card) {
    container.className = "empty-state";
    container.textContent = "选择一张卡片查看详情。";
    return;
  }

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
      <p class="workspace-kicker">${escapeHtml(card.subject_display_name)}</p>
      <h3>${escapeHtml(card.title)}</h3>
      <p>${escapeHtml(card.source_document_name || "无来源文档")}</p>
    </div>
    <div class="detail-grid">${detailRows}</div>
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

  if (!state.activeDocumentId && state.documents.length) {
    state.activeDocumentId = state.documents[0].id;
  }
  if (!state.cards.find((card) => card.id === state.activeCardId)) {
    state.activeCardId = state.cards[0]?.id || null;
  }
  if (!state.templates.find((template) => template.key === state.activeTemplateKey)) {
    state.activeTemplateKey = state.templates[0]?.key || null;
  }

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
      "这个 PDF 超过当前网页直传限制。请先压缩或拆分到 4 MB 内，再上传到对应集合；200 MB 这类大文件需要改成直传对象存储后再解析。",
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
    setStatus(`已导入文档，生成了 ${payload.chunk_count} 个片段。`);
  } catch (error) {
    setStatus(`导入失败：${error.message}`);
  } finally {
    setButtonBusy(submitButton, false, "导入中...");
  }
}

async function generateCards() {
  const activeDocument = getActiveDocument();
  if (!activeDocument) {
    setStatus("请先选择一个文档。");
    return;
  }
  if (!state.activeTemplateKey) {
    setStatus("请先选择一个模板。");
    return;
  }

  const button = document.getElementById("generate-button");
  try {
    setButtonBusy(button, true, "生成中...");
    setStatus("正在按模板生成卡片...");
    const payload = await api("/api/cards/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: activeDocument.id,
        template_key: state.activeTemplateKey,
      }),
    });
    state.cards = await api(`/api/cards?collection_id=${state.activeCollectionId}`);
    state.activeCardId = payload.cards[0]?.id || state.cards[0]?.id || null;
    renderWorkspaceHeader();
    renderCards();
    setStatus(`已生成 ${payload.cards.length} 张卡片。`);
  } catch (error) {
    setStatus(`生成卡片失败：${error.message}`);
  } finally {
    setButtonBusy(button, false, "生成中...");
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

    document.getElementById("collection-form").addEventListener("submit", createCollection);
    document.getElementById("upload-form").addEventListener("submit", uploadPdf);
    document.getElementById("generate-button").addEventListener("click", generateCards);
    document.getElementById("export-button").addEventListener("click", exportCollection);
    setStatus("准备就绪，可以开始导入 PDF。");
  } catch (error) {
    setStatus(`初始化失败：${error.message}`);
  }
}

bootstrap();
