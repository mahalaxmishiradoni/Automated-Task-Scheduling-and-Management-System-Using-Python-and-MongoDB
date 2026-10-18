const featuredSlot = document.querySelector("#featured-content");
const newsGrid = document.querySelector("#news-grid");
const resultsMessage = document.querySelector("#results-message");
const articleCount = document.querySelector("#article-count");
const sidebarCount = document.querySelector("#sidebar-count");
const searchInput = document.querySelector("#search-input");
const refreshButton = document.querySelector("#refresh-button");
const categoryButtons = [...document.querySelectorAll(".topic-chip")];

const state = {
  category: "",
  search: "",
  requestId: 0,
  debounceTimer: null,
  controller: null,
};

document.querySelector("#today-date").textContent = new Intl.DateTimeFormat(
  undefined,
  { weekday: "long", month: "short", day: "numeric" },
).format(new Date());

function formatDate(value) {
  if (!value) return "Date unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(parsed);
}

function textElement(tagName, className, text) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = text || "";
  return element;
}

function createMetadata(article) {
  const metadata = document.createElement("div");
  metadata.className = "article-meta";

  if (article.category) {
    metadata.append(textElement("span", "category-label", article.category));
  }

  if (article.source) {
    const divider = document.createElement("span");
    divider.className = "meta-divider";
    divider.setAttribute("aria-hidden", "true");
    metadata.append(divider, textElement("span", "article-source", article.source));
  }

  const date = article.publication_date || article.collected_at;
  if (date) {
    const divider = document.createElement("span");
    divider.className = "meta-divider";
    divider.setAttribute("aria-hidden", "true");
    metadata.append(divider, textElement("time", "article-date", formatDate(date)));
  }

  return metadata;
}

function createReadLink(url, featured = false) {
  const link = document.createElement("a");
  link.className = featured ? "featured-action" : "read-link";
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = featured ? "Read the full story" : "Read article";

  const arrow = document.createElement("span");
  arrow.setAttribute("aria-hidden", "true");
  arrow.textContent = "→";
  link.append(arrow);
  return link;
}

function renderFeatured(article) {
  if (!article) {
    featuredSlot.replaceChildren();
    return;
  }

  const card = document.createElement("article");
  card.className = "featured-card";

  const content = document.createElement("div");
  content.className = "featured-content";
  content.append(createMetadata(article));
  content.append(textElement("h3", "featured-title", article.title || "Untitled story"));
  content.append(
    textElement(
      "p",
      "featured-description",
      article.description || "No description was provided for this story.",
    ),
  );
  if (article.url) content.append(createReadLink(article.url, true));

  const art = document.createElement("div");
  art.className = "featured-art";
  art.setAttribute("aria-hidden", "true");
  const orbital = document.createElement("div");
  orbital.className = "orbital";
  const core = document.createElement("div");
  core.className = "orbital-core";
  const pointOne = document.createElement("span");
  pointOne.className = "orbital-point orbital-point-one";
  const pointTwo = document.createElement("span");
  pointTwo.className = "orbital-point orbital-point-two";
  art.append(orbital, core, pointOne, pointTwo);

  card.append(content, art);
  featuredSlot.replaceChildren(card);
}

function createNewsCard(article, index) {
  const card = document.createElement("article");
  card.className = "news-card";
  card.style.animationDelay = `${Math.min(index * 45, 270)}ms`;
  card.append(createMetadata(article));
  card.append(textElement("h3", "card-title", article.title || "Untitled story"));
  card.append(
    textElement(
      "p",
      "card-description",
      article.description || "No description was provided for this story.",
    ),
  );

  const footer = document.createElement("div");
  footer.className = "card-footer";
  footer.append(
    textElement("span", "card-source", article.source || "Source unavailable"),
  );
  if (article.url) footer.append(createReadLink(article.url));
  card.append(footer);
  return card;
}

function showMessage(title, description, canRetry = false) {
  resultsMessage.replaceChildren();
  resultsMessage.append(textElement("strong", "", title));
  resultsMessage.append(document.createTextNode(description));

  if (canRetry) {
    const retry = textElement("button", "retry-button", "Try again");
    retry.type = "button";
    retry.addEventListener("click", () => loadNews());
    resultsMessage.append(document.createElement("br"), retry);
  }

  resultsMessage.hidden = false;
}

function showSkeletons() {
  resultsMessage.hidden = true;
  featuredSlot.replaceChildren();
  const featuredSkeleton = document.createElement("div");
  featuredSkeleton.className = "featured-skeleton skeleton";
  featuredSlot.append(featuredSkeleton);

  newsGrid.replaceChildren();
  for (let index = 0; index < 4; index += 1) {
    const skeleton = document.createElement("div");
    skeleton.className = "news-skeleton skeleton";
    newsGrid.append(skeleton);
  }
  articleCount.textContent = "Loading stories";
  sidebarCount.textContent = "—";
}

async function loadNews() {
  const requestId = ++state.requestId;
  if (state.controller) state.controller.abort();
  state.controller = new AbortController();
  refreshButton.classList.add("is-loading");
  refreshButton.disabled = true;
  showSkeletons();

  const params = new URLSearchParams({ limit: "100" });
  if (state.search) params.set("search", state.search);
  if (state.category) params.set("category", state.category);

  try {
    const response = await fetch(`/api/news?${params.toString()}`, {
      headers: { Accept: "application/json" },
      signal: state.controller.signal,
    });
    if (!response.ok) {
      let message = `The news service returned an error (${response.status}).`;
      try {
        const errorBody = await response.json();
        if (typeof errorBody.detail === "string") message = errorBody.detail;
      } catch {
        // Keep the clear status-based message if the error is not JSON.
      }
      throw new Error(message);
    }

    const articles = await response.json();
    if (!Array.isArray(articles)) {
      throw new Error("The news service returned an unexpected response.");
    }
    if (requestId !== state.requestId) return;

    const [featured, ...remaining] = articles;
    renderFeatured(featured);
    newsGrid.replaceChildren(
      ...remaining.map((article, index) => createNewsCard(article, index)),
    );
    articleCount.textContent = `${articles.length} ${articles.length === 1 ? "story" : "stories"} loaded`;
    sidebarCount.textContent = String(articles.length);
    resultsMessage.hidden = true;

    if (articles.length === 0) {
      showMessage(
        "No stories found",
        "Try another topic or adjust your search to see more of the signal.",
      );
    }
  } catch (error) {
    if (error.name === "AbortError" || requestId !== state.requestId) return;
    renderFeatured(null);
    newsGrid.replaceChildren();
    articleCount.textContent = "Stories unavailable";
    sidebarCount.textContent = "—";
    showMessage(
      "We couldn't load the briefing",
      error instanceof Error
        ? error.message
        : "Please check your connection and try again.",
      true,
    );
  } finally {
    if (requestId === state.requestId) {
      refreshButton.classList.remove("is-loading");
      refreshButton.disabled = false;
    }
  }
}

searchInput.addEventListener("input", () => {
  window.clearTimeout(state.debounceTimer);
  state.debounceTimer = window.setTimeout(() => {
    state.search = searchInput.value.trim();
    loadNews();
  }, 280);
});

categoryButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.category = button.dataset.category || "";
    categoryButtons.forEach((chip) => {
      const isActive = chip === button;
      chip.classList.toggle("is-active", isActive);
      chip.setAttribute("aria-pressed", String(isActive));
    });
    loadNews();
  });
});

refreshButton.addEventListener("click", () => loadNews());

document.addEventListener("keydown", (event) => {
  if (
    event.key === "/" &&
    !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)
  ) {
    event.preventDefault();
    searchInput.focus();
  }
  if (event.key === "Escape" && document.activeElement === searchInput) {
    searchInput.value = "";
    state.search = "";
    searchInput.blur();
    loadNews();
  }
});

loadNews();
