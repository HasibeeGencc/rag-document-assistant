// Talks to the FastAPI backend. All text from the server or the user is put
// on the page with textContent (never innerHTML), so it can't inject HTML.

const $ = (id) => document.getElementById(id);

const dropzone = $("dropzone");
const fileInput = $("file-input");
const uploadStatus = $("upload-status");
const docList = $("doc-list");
const docEmpty = $("doc-empty");
const docCount = $("doc-count");
const askForm = $("ask-form");
const question = $("question");
const askButton = $("ask-button");
const answerArea = $("answer-area");
const answerBox = $("answer");
const sourcesBlock = $("sources-block");
const sourcesList = $("sources");

// Same citation format the backend parses: [file.pdf, p. 3] (or "s." in Turkish).
const CITATION_RE = /\[([^\[\]]+?),\s*(?:p|s)\.\s*(\d+)\]/g;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// Turn a failed response into a readable message.
async function errorMessage(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d) => d.msg).join("; ");
  } catch {
    /* body was not JSON */
  }
  return `Something went wrong (error ${response.status}).`;
}

// ---------------------------------------------------------------- documents

async function loadDocuments() {
  let docs = [];
  try {
    const response = await fetch("/documents");
    if (!response.ok) throw new Error(await errorMessage(response));
    docs = await response.json();
  } catch (err) {
    docEmpty.textContent = `Could not load documents: ${err.message}`;
    docEmpty.hidden = false;
    return;
  }

  docList.replaceChildren(...docs.map(renderDocument));
  docEmpty.textContent = "No documents yet. Upload a PDF to get started.";
  docEmpty.hidden = docs.length > 0;
  docCount.textContent = docs.length ? `(${docs.length})` : "";
}

function renderDocument(doc) {
  const item = el("li", "doc-item");
  item.append(el("span", "doc-icon", "PDF"));
  const name = el("span", "doc-name", doc.filename);
  name.title = doc.filename;
  item.append(name);

  const remove = el("button", "button-delete", "Delete");
  remove.type = "button";
  remove.setAttribute("aria-label", `Delete ${doc.filename}`);
  remove.addEventListener("click", async () => {
    if (!confirm(`Delete "${doc.filename}"? You can upload it again later.`)) return;
    remove.disabled = true;
    try {
      const response = await fetch(`/documents/${encodeURIComponent(doc.doc_id)}`, {
        method: "DELETE",
      });
      if (response.ok || response.status === 404) {
        item.remove(); // gone on the server (or already gone): drop it right away
      } else {
        alert(await errorMessage(response));
      }
    } catch {
      alert("Could not reach the server. Please try again.");
    } finally {
      loadDocuments(); // always re-sync the list with the server
    }
  });
  item.append(remove);
  return item;
}

// ------------------------------------------------------------------ upload

async function uploadFiles(files) {
  for (const file of files) {
    const line = el("li", "status-working", `Uploading ${file.name}…`);
    uploadStatus.prepend(line);

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      line.className = "status-error";
      line.textContent = `${file.name}: only PDF files can be uploaded.`;
      continue;
    }

    const form = new FormData();
    form.append("file", file);
    try {
      const response = await fetch("/documents", { method: "POST", body: form });
      if (!response.ok) {
        line.className = "status-error";
        line.textContent = `${file.name}: ${await errorMessage(response)}`;
        continue;
      }
      const result = await response.json();
      if (result.empty_pages.length) {
        line.className = "status-warn";
        line.textContent =
          `${result.filename} added (${result.page_count} pages). ` +
          `Pages ${result.empty_pages.join(", ")} had no readable text and were skipped.`;
      } else {
        line.className = "status-ok";
        line.textContent = `${result.filename} added (${result.page_count} pages).`;
      }
    } catch {
      line.className = "status-error";
      line.textContent = `${file.name}: could not reach the server.`;
    }
    loadDocuments();
  }
}

fileInput.addEventListener("change", () => {
  uploadFiles([...fileInput.files]);
  fileInput.value = ""; // allow choosing the same file again
});

["dragenter", "dragover"].forEach((type) =>
  dropzone.addEventListener(type, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  })
);
["dragleave", "drop"].forEach((type) =>
  dropzone.addEventListener(type, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
  })
);
dropzone.addEventListener("drop", (event) => uploadFiles([...event.dataTransfer.files]));

// --------------------------------------------------------------------- ask

function showSource(key) {
  const card = sourcesList.querySelector(`[data-key="${CSS.escape(key)}"]`);
  if (!card) return;
  sourcesList.querySelectorAll(".highlight").forEach((c) => c.classList.remove("highlight"));
  card.classList.add("highlight");
  card.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// Replace each [file, p. N] in the answer with a clickable chip, but only if
// that source was returned by the server (unverified citations stay as text).
function renderAnswer(text, sourceKeys) {
  const parts = [];
  let last = 0;
  for (const match of text.matchAll(CITATION_RE)) {
    const [whole, filename, page] = match;
    const key = `${filename.trim()}|${page}`;
    parts.push(document.createTextNode(text.slice(last, match.index)));
    if (sourceKeys.has(key)) {
      const chip = el("button", "cite", `${filename.trim()} · p. ${page}`);
      chip.type = "button";
      chip.setAttribute("aria-label", `Show source: ${filename.trim()}, page ${page}`);
      chip.addEventListener("click", () => showSource(key));
      parts.push(chip);
    } else {
      parts.push(document.createTextNode(whole));
    }
    last = match.index + whole.length;
  }
  parts.push(document.createTextNode(text.slice(last)));
  answerBox.replaceChildren(...parts);
}

function renderSources(sources) {
  sourcesList.replaceChildren(
    ...sources.map((s) => {
      const card = el("li", "source");
      card.dataset.key = `${s.filename}|${s.page}`;
      const head = el("div", "source-head");
      head.append(el("span", "source-file", s.filename), el("span", "source-page", `page ${s.page}`));
      card.append(head, el("p", "source-snippet", s.snippet));
      return card;
    })
  );
  sourcesBlock.hidden = sources.length === 0;
}

askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text) return;

  askButton.disabled = true;
  answerArea.hidden = false;
  answerBox.className = "answer loading";
  answerBox.textContent = "Reading your documents";
  sourcesBlock.hidden = true;

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text }),
    });
    if (!response.ok) {
      answerBox.className = "answer error";
      answerBox.textContent = await errorMessage(response);
      return;
    }
    const result = await response.json();
    answerBox.className = "answer";
    renderSources(result.sources);
    renderAnswer(result.answer, new Set(result.sources.map((s) => `${s.filename}|${s.page}`)));
  } catch {
    answerBox.className = "answer error";
    answerBox.textContent = "Could not reach the server. Is it running?";
  } finally {
    askButton.disabled = false;
  }
});

// Enter submits, Shift+Enter adds a new line.
question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    askForm.requestSubmit();
  }
});

loadDocuments();
