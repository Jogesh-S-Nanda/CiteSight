const indexForm = document.querySelector("#indexForm");
const searchForm = document.querySelector("#searchForm");
const clearButton = document.querySelector("#clearButton");
const indexButton = document.querySelector("#indexButton");
const indexBadge = document.querySelector("#indexBadge");
const emptyState = document.querySelector("#emptyState");
const resultsList = document.querySelector("#resultsList");
const resultsTitle = document.querySelector("#resultsTitle");
const resultsMeta = document.querySelector("#resultsMeta");
const message = document.querySelector("#message");
const resultTemplate = document.querySelector("#resultTemplate");

function setSearchEnabled(enabled) {
  searchForm.querySelectorAll("input, button").forEach((element) => {
    element.disabled = !enabled;
  });
}

function showMessage(text, type = "error") {
  message.textContent = text;
  message.className = type === "success" ? "message success" : "message";
  message.hidden = false;
}

function hideMessage() {
  message.hidden = true;
}

function setBusy(element, busy, busyText, normalText) {
  element.disabled = busy;
  element.classList.toggle("loading", busy);
  const label = element.querySelector("span");
  if (label) label.textContent = busy ? busyText : normalText;
}

async function parseResponse(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

function renderResults(data) {
  resultsList.replaceChildren();
  emptyState.hidden = data.results.length > 0;
  resultsTitle.textContent = data.results.length
    ? `${data.count} document${data.count === 1 ? "" : "s"} found`
    : "No matching documents";
  resultsMeta.textContent = `${data.indexed_count} indexed • ${data.folder}`;

  if (!data.results.length) {
    emptyState.querySelector("h3").textContent = "No results found";
    emptyState.querySelector("p").textContent = "Try a shorter term or clear the advanced filters.";
    return;
  }

  data.results.forEach((record) => {
    const card = resultTemplate.content.cloneNode(true);
    card.querySelector(".result-title").textContent = record.title;
    card.querySelector(".result-file").textContent = record.file_name;
    card.querySelector(".result-path").textContent = record.relative_path;
    card.querySelector(".result-path").title = record.path;

    const copyButton = card.querySelector(".copy-button");
    copyButton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(record.path);
        copyButton.querySelector("span").textContent = "Copied";
        setTimeout(() => {
          copyButton.querySelector("span").textContent = "Copy path";
        }, 1400);
      } catch {
        showMessage(`Could not copy. Path: ${record.path}`);
      }
    });

    resultsList.append(card);
  });
}

indexForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideMessage();
  setBusy(indexButton, true, "Indexing…", "Index PDFs");

  try {
    const response = await fetch("/api/index", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder: indexForm.elements.folder.value }),
    });
    const data = await parseResponse(response);

    indexBadge.textContent = `${data.count} indexed`;
    indexBadge.classList.add("ready");
    setSearchEnabled(true);
    resultsTitle.textContent = "Library indexed";
    resultsMeta.textContent = `${data.count} PDFs • ${data.folder}`;
    emptyState.querySelector("h3").textContent = "Your library is ready";
    emptyState.querySelector("p").textContent = "Enter a term above or search with an empty field to show all PDFs.";
    showMessage(data.message, "success");
    document.querySelector("#query").focus();
  } catch (error) {
    showMessage(error.message);
  } finally {
    setBusy(indexButton, false, "Indexing…", "Index PDFs");
  }
});

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideMessage();

  const params = new URLSearchParams();
  new FormData(searchForm).forEach((value, key) => {
    if (value.trim()) params.set(key, value.trim());
  });

  try {
    const response = await fetch(`/api/search?${params.toString()}`);
    renderResults(await parseResponse(response));
  } catch (error) {
    showMessage(error.message);
  }
});

clearButton.addEventListener("click", () => {
  searchForm.reset();
  document.querySelector("#query").focus();
});
