/* =========================================
   GAURAV'S WORLD — HOMEPAGE & ARTICLE API
   Updated: stable loading, retry, no demo fallback
========================================= */

// Set this to your deployed Apps Script /exec URL.
const API_URL =
  'https://script.google.com/macros/s/AKfycbxPqioJ9nu_znGgoJLInxzi9xRxR35Ex5eLCFzctbpPipyxzoL9vd5B31u3wcecwHF7/exec';

const $ = s => document.querySelector(s);

const state = {
  posts: [],
  category: "All",
  query: "",
  page: 1,
  pageSize: 30,
  sort: "new",
  savedOnly: false,
  loading: false,
  loaded: false,
  loadPromise: null
};


/* =========================================
   HELPERS
========================================= */

function dateText(value) {
  if (!value) return "";

  const d = new Date(value);

  return isNaN(d)
    ? String(value)
    : d.toLocaleDateString("hi-IN", {
        day: "numeric",
        month: "long",
        year: "numeric"
      });
}


function esc(value = "") {
  return String(value).replace(/[&<>"']/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[c]));
}


function imageOrEmpty(src) {
  if (!src || !/^https?:\/\//i.test(src)) {
    return "";
  }

  return `
    <img
      loading="lazy"
      decoding="async"
      src="${esc(src)}"
      alt=""
    >
  `;
}


function setFeedMessage(message) {
  const feed = $("#feed");

  if (feed) {
    feed.innerHTML =
      `<p class="state">${esc(message)}</p>`;
  }
}


/* =========================================
   API REQUEST WITH RETRY — JSONP
   Public read requests only
========================================= */

async function api(action, params = {}) {
  if (!API_URL.startsWith("https://")) {
    throw new Error("Apps Script API URL सेट नहीं है");
  }

  let lastError;

  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const result = await new Promise((resolve, reject) => {
        const callbackName =
          "__gw_public_" +
          Date.now() +
          "_" +
          Math.random().toString(36).slice(2);

        const url = new URL(API_URL);
        url.searchParams.set("action", action);
        url.searchParams.set("callback", callbackName);

        Object.entries(params).forEach(([name, value]) => {
          if (value !== undefined && value !== null) {
            url.searchParams.set(name, String(value));
          }
        });

        if (url.toString().length > 7000) {
          reject(new Error("API request URL बहुत लंबा है"));
          return;
        }

        const script = document.createElement("script");
        let finished = false;
        let timeout;

        function cleanup() {
          clearTimeout(timeout);
          script.onerror = null;
          script.remove();

          try {
            delete window[callbackName];
          } catch (_) {
            window[callbackName] = undefined;
          }
        }

        function finish(error, response) {
          if (finished) return;
          finished = true;
          cleanup();

          if (error) {
            reject(error);
            return;
          }

          if (!response || response.ok !== true) {
            reject(
              new Error(
                response?.error || "Apps Script API error"
              )
            );
            return;
          }

          resolve(response.data);
        }

        window[callbackName] = response => {
          finish(null, response);
        };

        script.onerror = () => {
          finish(new Error("Apps Script JSONP request failed"));
        };

        timeout = setTimeout(() => {
          finish(new Error("Apps Script response timeout"));
        }, 20000);

        script.async = true;
        script.src = url.toString();
        document.head.appendChild(script);
      });

      return result;

    } catch (error) {
      lastError = error;

      console.warn(
        `API ${action}, attempt ${attempt + 1}:`,
        error.message
      );

      if (attempt < 2) {
        await new Promise(resolve =>
          setTimeout(resolve, 700 * (attempt + 1))
        );
      }
    }
  }

  throw lastError || new Error("API request failed");
}


/* =========================================
   CATEGORIES
========================================= */

function categories() {
  const root = $("#categories");

  if (!root) return;

  const cats = [
    "All",
    "Technology",
    "Science",
    "History",
    "Universe",
    "Mystery",
    "Nature",
    "World",
    "AI",
    "Trending"
  ];

  root.innerHTML = cats.map(category => `
    <button
      class="cat ${
        state.category === category ? "active" : ""
      }"
      data-cat="${esc(category)}"
    >
      ${
        category === "All"
          ? "सभी"
          : esc(category)
      }
    </button>
  `).join("");

  root.querySelectorAll("[data-cat]").forEach(button => {
    button.addEventListener("click", () => {
      state.category = button.dataset.cat;
      state.page = 1;
      state.savedOnly = false;

      categories();
      renderFeed();
    });
  });
}


/* =========================================
   FILTER POSTS
========================================= */

function filtered() {
  let posts = state.posts.filter(post =>
    String(post.status || "").toLowerCase() === "published"
  );

  if (state.savedOnly) {
    let savedIds = [];

    try {
      savedIds = JSON.parse(
        localStorage.getItem("gw_saved") || "[]"
      );
    } catch (_) {
      savedIds = [];
    }

    posts = posts.filter(post =>
      savedIds.includes(post.id)
    );
  }

  if (state.category !== "All") {
    posts = posts.filter(post => {
      const category = String(post.category || "")
        .toLowerCase();

      const tags = String(post.tags || "")
        .toLowerCase();

      return (
        category === state.category.toLowerCase() ||
        (
          state.category === "Trending" &&
          tags.includes("trending")
        )
      );
    });
  }

  if (state.query) {
    const query = state.query.toLowerCase();

    posts = posts.filter(post => {
      const searchable = [
        post.title,
        post.hook,
        post.category,
        post.excerpt,
        post.tags
      ].join(" ").toLowerCase();

      return searchable.includes(query);
    });
  }

  posts.sort((a, b) => {
    const dateA = new Date(
      a.publishedAt || a.updatedAt || 0
    ).getTime();

    const dateB = new Date(
      b.publishedAt || b.updatedAt || 0
    ).getTime();

    return state.sort === "old"
      ? dateA - dateB
      : dateB - dateA;
  });

  return posts;
}


/* =========================================
   RENDER HOMEPAGE FEED
========================================= */

function renderFeed() {
  const feed = $("#feed");

  if (!feed) return;

  const posts = filtered();

  const shown = posts.slice(
    0,
    state.page * state.pageSize
  );

  if (!shown.length) {
    feed.innerHTML = `
      <p class="state">
        ${
          state.savedOnly
            ? "आपने अभी कोई लेख सेव नहीं किया है।"
            : "इस खोज में कोई लेख नहीं मिला।"
        }
      </p>
    `;
  } else {
    feed.innerHTML = shown.map((post, index) => `
      <a
        class="story"
        href="article.html?id=${encodeURIComponent(post.id)}"
      >
        <span class="story-num">
          ${String(index + 1).padStart(2, "0")}
        </span>

        <span class="story-copy">
          <span class="story-cat">
            ${esc(post.category || "ARTICLE")}
          </span>

          <span class="story-title">
            ${esc(post.title || "Untitled")}
          </span>

          <span class="story-date">
            ${dateText(post.publishedAt || post.updatedAt)}
          </span>
        </span>

        ${imageOrEmpty(post.thumbnail)}

        <span class="story-arrow">›</span>
      </a>
    `).join("");
  }

  const moreButton = $("#moreBtn");

  if (moreButton) {
    moreButton.hidden = shown.length >= posts.length;
  }
}


/* =========================================
   FEATURED POST
========================================= */

function renderFeatured() {
  const feature = $("#feature");

  if (!feature) return;

  const featured = state.posts.find(post =>
    String(post.status || "").toLowerCase() === "published" &&
    post.heroImage &&
    /^https?:\/\//i.test(post.heroImage)
  );

  if (!featured) return;

  const heading = feature.querySelector("h1");
  const paragraph = feature.querySelector("p");
  const image = $("#featureImg");

  if (heading) {
    heading.textContent = featured.title || "";
  }

  if (paragraph) {
    paragraph.textContent =
      featured.hook ||
      featured.excerpt ||
      "";
  }

  if (image) {
    image.src = featured.heroImage;
    image.hidden = false;
    image.loading = "lazy";
    image.decoding = "async";
  }

  feature.onclick = () => {
    location.href =
      "article.html?id=" +
      encodeURIComponent(featured.id);
  };
}


/* =========================================
   LOAD HOMEPAGE POSTS
   Prevent concurrent duplicate loads
========================================= */

async function loadPosts(force = false) {
  if (state.loadPromise && !force) {
    return state.loadPromise;
  }

  if (state.loaded && !force) {
    return state.posts;
  }

  state.loading = true;

  if ($("#feed")) {
    setFeedMessage("लेख लोड हो रहे हैं...");
  }

  state.loadPromise = (async () => {
    try {
      const result = await api("list");

      if (!Array.isArray(result)) {
        throw new Error(
          "API response में posts की list नहीं मिली।"
        );
      }

      // Only published posts
      state.posts = result.filter(post =>
        String(post.status || "").toLowerCase() === "published"
      );

      state.loaded = true;

      renderFeatured();
      categories();
      renderFeed();

      return state.posts;

    } catch (error) {
      console.error("Homepage load failed:", error);

      // IMPORTANT:
      // Do not show demo/fallback posts.
      // Keep real posts if they were already loaded.
      if (!state.loaded) {
        state.posts = [];

        setFeedMessage(
          "लेख अभी लोड नहीं हो पाए। कृपया कुछ देर बाद Retry करें।"
        );

        const feed = $("#feed");

        if (feed && !$("#retryPostsBtn")) {
          const button = document.createElement("button");

          button.id = "retryPostsBtn";
          button.textContent = "Retry";
          button.className = "cat";

          button.onclick = () => {
            button.disabled = true;
            button.textContent = "लोड हो रहा है...";

            state.loaded = false;
            state.loadPromise = null;

            loadPosts(true).finally(() => {
              button.remove();
            });
          };

          feed.appendChild(button);
        }
      }

      return state.posts;

    } finally {
      state.loading = false;
      state.loadPromise = null;
    }
  })();

  return state.loadPromise;
}


/* =========================================
   ARTICLE PAGE
========================================= */

async function loadArticle() {
  const root = $("#articleRoot");

  if (!root) return;

  const id = new URLSearchParams(
    location.search
  ).get("id");

  if (!id) {
    root.innerHTML = `
      <p class="state">
        लेख ID नहीं मिला।
        <a href="index.html">होम पर लौटें</a>
      </p>
    `;

    return;
  }

  root.innerHTML = `
    <p class="state">लेख लोड हो रहा है...</p>
  `;

  try {
    const post = await api("get", { id });

    if (!post || !post.id) {
      throw new Error("लेख नहीं मिला।");
    }

    if (
      String(post.status || "").toLowerCase() !== "published"
    ) {
      throw new Error("यह लेख प्रकाशित नहीं है।");
    }

    document.title =
      (post.title || "लेख") + " — Gaurav’s World";

    root.innerHTML = `
      <div class="article-cat">
        ${esc(post.category || "ARTICLE")}
      </div>

      <h1>${esc(post.title || "")}</h1>

      <div class="article-meta">
        ${dateText(post.publishedAt || post.updatedAt)}
        · ${esc(post.author || "Gaurav")}
      </div>

      ${
        post.heroImage &&
        /^https?:\/\//i.test(post.heroImage)
          ? `
            <img
              class="article-hero"
              src="${esc(post.heroImage)}"
              alt="${esc(post.title || "")}"
              loading="lazy"
              decoding="async"
            >
          `
          : ""
      }

      ${
        post.hook
          ? `<div class="article-hook">${esc(post.hook)}</div>`
          : ""
      }

      <div class="article-actions">
        <button id="saveArticle">☆ सेव करें</button>
        <button id="shareArticle">↗ शेयर</button>
      </div>

      <article class="article-content">
        ${
          (post.content || post.excerpt || "")
            .split(/\n+/)
            .map(text => text.trim()
              ? `<p>${esc(text)}</p>`
              : ""
            )
            .join("")
        }
      </article>
    `;

    const saveButton = $("#saveArticle");

    if (saveButton) {
      let savedIds = [];

      try {
        savedIds = JSON.parse(
          localStorage.getItem("gw_saved") || "[]"
        );
      } catch (_) {
        savedIds = [];
      }

      if (savedIds.includes(post.id)) {
        saveButton.textContent = "✓ सेव हो गया";
      }

      saveButton.onclick = () => {
        try {
          savedIds = JSON.parse(
            localStorage.getItem("gw_saved") || "[]"
          );
        } catch (_) {
          savedIds = [];
        }

        if (!savedIds.includes(post.id)) {
          savedIds.push(post.id);
        }

        localStorage.setItem(
          "gw_saved",
          JSON.stringify(savedIds)
        );

        saveButton.textContent = "✓ सेव हो गया";
      };
    }

    const shareButton = $("#shareArticle");

    if (shareButton) {
      shareButton.onclick = async () => {
        const shareData = {
          title: post.title || "Gaurav’s World",
          url: location.href
        };

        try {
          if (navigator.share) {
            await navigator.share(shareData);
          } else if (navigator.clipboard) {
            await navigator.clipboard.writeText(
              location.href
            );

            shareButton.textContent = "✓ लिंक कॉपी हुआ";
          }
        } catch (error) {
          console.warn("Share cancelled/failed:", error);
        }
      };
    }

  } catch (error) {
    console.error("Article load failed:", error);

    root.innerHTML = `
      <p class="state">
        ${esc(error.message || "लेख लोड नहीं हो पाया।")}
        <br>
        <a href="index.html">होम पर लौटें</a>
      </p>
    `;
  }
}


/* =========================================
   INITIALIZE PAGE
========================================= */

document.addEventListener("DOMContentLoaded", () => {

  // Search
  const searchButton = $("#searchBtn");
  const searchWrap = $("#searchWrap");
  const searchInput = $("#searchInput");

  if (searchButton && searchWrap) {
    searchButton.onclick = () => {
      searchWrap.classList.toggle("open");

      if (searchWrap.classList.contains("open")) {
        searchInput?.focus();
      }
    };
  }

  if (searchInput) {
    searchInput.oninput = event => {
      state.query = event.target.value;
      state.page = 1;
      state.savedOnly = false;

      renderFeed();
    };
  }

  // Sort
  const sortSelect = $("#sortSelect");

  if (sortSelect) {
    sortSelect.onchange = event => {
      state.sort = event.target.value;
      state.page = 1;

      renderFeed();
    };
  }

  // Load more
  const moreButton = $("#moreBtn");

  if (moreButton) {
    moreButton.onclick = () => {
      state.page++;
      renderFeed();
    };
  }

  // Saved posts
  const savedButton = $("#savedBtn");

  if (savedButton) {
    savedButton.onclick = () => {
      state.savedOnly = !state.savedOnly;
      state.category = "All";
      state.page = 1;

      categories();
      renderFeed();
    };
  }

  // Share homepage
  const shareButton = $("#shareBtn");

  if (shareButton) {
    shareButton.onclick = async () => {
      try {
        if (navigator.share) {
          await navigator.share({
            title: document.title,
            url: location.href
          });
        } else if (navigator.clipboard) {
          await navigator.clipboard.writeText(
            location.href
          );
        }
      } catch (error) {
        console.warn("Share cancelled/failed:", error);
      }
    };
  }

  // Homepage
  if ($("#feed")) {
    categories();
    loadPosts();
  }

  // Article page
  if ($("#articleRoot")) {
    loadArticle();
  }
});


/* Added responsive menu and footer navigation actions */

document.addEventListener("DOMContentLoaded", () => {
  const menuBtn = document.querySelector("#menuBtn");

  if (menuBtn && !document.querySelector("#gwMenuPanel")) {
    const panel = document.createElement("nav");

    panel.id = "gwMenuPanel";
    panel.hidden = true;
    panel.setAttribute("aria-label", "मुख्य मेन्यू");

    panel.innerHTML = `
      <a href="index.html">🏠 होम</a>
      <button type="button" data-gw-menu="categories">▦ सभी कैटेगरी</button>
      <button type="button" data-gw-menu="trending">🔥 ट्रेंडिंग</button>
      <button type="button" data-gw-menu="saved">♧ सेव लेख</button>
      <a href="admin.html">⚙️ Admin</a>`;

    document.querySelector(".topbar")
      ?.insertAdjacentElement("afterend", panel);

    menuBtn.setAttribute("aria-expanded", "false");

    menuBtn.onclick = () => {
      panel.hidden = !panel.hidden;

      menuBtn.setAttribute(
        "aria-expanded",
        String(!panel.hidden)
      );
    };

    panel.addEventListener("click", e => {
      const action =
        e.target.closest("[data-gw-menu]")?.dataset.gwMenu;

      if (!action) return;

      panel.hidden = true;
      menuBtn.setAttribute("aria-expanded", "false");

      if (action === "categories") {
        document.querySelector("#categories")
          ?.scrollIntoView({
            behavior: "smooth",
            block: "start"
          });
      }

      if (action === "trending") {
        setFilter("Trending");
      }

      if (action === "saved") {
        showSaved();
      }
    });
  }

  function setFilter(category) {
    if (typeof state !== "undefined") {
      state.category = category;
      state.savedOnly = false;
      state.page = 1;

      categories();
      renderFeed();
    }

    document.querySelector("#feed")
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
  }

  function showSaved() {
    if (typeof state !== "undefined") {
      state.savedOnly = true;
      state.category = "All";
      state.page = 1;

      categories();
      renderFeed();
    }

    document.querySelector("#feed")
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
  }

  document.querySelectorAll(
    '.bottomnav [data-filter]'
  ).forEach(btn =>
    btn.addEventListener("click", () =>
      setFilter(btn.dataset.filter)
    )
  );

  const myArticles =
    document.querySelector("#myArticlesBtn");

  if (myArticles) {
    myArticles.addEventListener("click", () => {
      const saved = (() => {
        try {
          return JSON.parse(
            localStorage.getItem("gw_saved") || "[]"
          );
        } catch (_) {
          return [];
        }
      })();

      if (typeof state !== "undefined") {
        state.savedOnly = true;
        state.category = "All";
        state.page = 1;

        categories();
        renderFeed();
      }

      const feed = document.querySelector("#feed");

      if (feed && !saved.length) {
        feed.innerHTML =
          '<p class="state">आपने अभी कोई लेख सेव नहीं किया है।</p>';
      }

      feed?.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    });
  }

  const home =
    document.querySelector(".bottomnav a.active");

  if (
    home &&
    location.pathname.endsWith("/article.html")
  ) {
    home.href = "index.html";
  }
});
