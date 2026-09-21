/* =========================================
   GAURAV'S WORLD — ADMIN.JS
   JSONP-compatible build
========================================= */

const API_URL =
  "https://script.google.com/macros/s/AKfycbxPqioJ9nu_znGgoJLInxzi9xRxR35Ex5eLCFzctbpPipyxzoL9vd5B31u3wcecwHF7/exec";

const $ = selector => document.querySelector(selector);

let key = "";
let editingPostId = "";
let saving = false;
let loading = false;

/* HELPERS */

function esc(value = "") {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[char]);
}

function setMessage(message, isError = false) {
  const el = $("#saveMsg");
  if (!el) return;
  el.textContent = message;
  el.style.color = isError ? "#b91c1c" : "";
}

function setLoginMessage(message, isError = true) {
  const el = $("#loginMsg");
  if (!el) return;
  el.textContent = message;
  el.style.color = isError ? "#b91c1c" : "";
}

/* API CALL — JSONP */

function call(action, data = {}) {
  return new Promise((resolve, reject) => {
    if (!API_URL.startsWith("https://")) {
      reject(new Error("API_URL सेट नहीं है।"));
      return;
    }

    const callbackName =
      "__gwcb_" + Date.now() + "_" +
      Math.random().toString(36).slice(2);

    const url = new URL(API_URL);
    url.searchParams.set("action", action);
    url.searchParams.set("adminKey", key);
    url.searchParams.set("callback", callbackName);

    Object.entries(data).forEach(([name, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(name, String(value));
      }
    });

    if (url.toString().length > 7000) {
      reject(new Error(
        "Article data URL ke liye bahut lamba hai. Save nahi bheja gaya. " +
        "Is setup mein JSONP URL limit hai; large articles ke liye POST-based " +
        "same-origin/restricted admin backend chahiye."
      ));
      return;
    }

    const script = document.createElement("script");
    let finished = false;
    let timer;

    function cleanup() {
      clearTimeout(timer);
      try {
        delete window[callbackName];
      } catch (_) {
        window[callbackName] = undefined;
      }
      script.onerror = null;
      script.remove();
    }

    function finish(error, result) {
      if (finished) return;
      finished = true;
      cleanup();

      if (error) {
        reject(error);
        return;
      }

      if (!result || result.ok !== true) {
        reject(new Error(result?.error || "Apps Script request failed."));
        return;
      }

      resolve(result.data);
    }

    window[callbackName] = result => finish(null, result);

    script.onerror = () => finish(new Error(
      "Apps Script JSONP load failed. API URL, deployment aur access settings check karein."
    ));

    timer = setTimeout(() => finish(new Error(
      "Apps Script response timeout. Deployment URL ya access check karein."
    )), 30000);

    script.async = true;
    script.src = url.toString();
    document.head.appendChild(script);
  });
}

/* FORM DATA */

function getForm() {
  return {
    id: editingPostId || "",
    title: $("#title").value.trim(),
    hook: $("#hook").value.trim(),
    category: $("#category").value,
    status: $("#status").value,
    thumbnail: $("#thumbnail").value.trim(),
    heroImage: $("#heroImage").value.trim(),
    excerpt: $("#excerpt").value.trim(),
    content: $("#content").value,
    tags: $("#tags").value,
    author: $("#author").value.trim()
  };
}

/* RESET */

function reset() {
  editingPostId = "";

  const form = $("#postForm");
  if (form) form.reset();

  const postId = $("#postId");
  if (postId) postId.value = "";

  const author = $("#author");
  if (author) author.value = "Gaurav";

  setMessage("");

  const button = form?.querySelector('[type="submit"]');
  if (button) {
    button.textContent = "Save Post";
    button.disabled = false;
  }
}

/* EDIT */

function edit(post) {
  if (!post || !post.id) {
    alert("Post ID missing. Cannot edit.");
    return;
  }

  editingPostId = String(post.id).trim();

  const postId = $("#postId");
  if (postId) postId.value = editingPostId;

  [
    "title", "hook", "category", "status",
    "thumbnail", "heroImage", "excerpt",
    "content", "tags", "author"
  ].forEach(field => {
    const el = $("#" + field);
    if (el) el.value = post[field] == null ? "" : post[field];
  });

  const button = $("#postForm").querySelector('[type="submit"]');
  if (button) button.textContent = "Update Post";

  setMessage("Editing existing post. ID: " + editingPostId);

  $("#postForm").scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}

/* REFRESH POSTS */

async function refresh() {
  if (loading) return;
  loading = true;

  const container = $("#adminPosts");
  if (container) container.setAttribute("aria-busy", "true");

  try {
    const posts = await call("adminList");

    if (!Array.isArray(posts)) {
      throw new Error("API ne posts ki valid list nahi bheji.");
    }

    if (!container) return;

    container.innerHTML = posts.map(post => `
      <div class="adminpost">
        <div>
          <strong>${esc(post.title || "Untitled")}</strong>
          <small>${esc(post.category || "")} · ${esc(post.status || "")}</small>
        </div>
        <div>
          <button type="button" data-edit="${esc(post.id || "")}">Edit</button>
          <button type="button" data-delete="${esc(post.id || "")}">Delete</button>
        </div>
      </div>
    `).join("") || "<p>अभी कोई पोस्ट नहीं।</p>";

    container.querySelectorAll("[data-edit]").forEach(button => {
      button.onclick = () => {
        const post = posts.find(item =>
          String(item.id) === button.dataset.edit
        );

        if (!post) {
          alert("Post nahi mili. List refresh karein.");
          return;
        }

        edit(post);
      };
    });

    container.querySelectorAll("[data-delete]").forEach(button => {
      button.onclick = async () => {
        const id = button.dataset.delete;

        if (!id) {
          alert("Post ID missing.");
          return;
        }

        if (!confirm("यह पोस्ट delete करें?")) return;

        button.disabled = true;

        try {
          await call("delete", { id });

          if (editingPostId === id) reset();

          setMessage("Post deleted successfully.");
          await refresh();

        } catch (error) {
          console.error("Delete failed:", error);
          alert(error.message);
          button.disabled = false;
        }
      };
    });

  } catch (error) {
    console.error("Posts refresh failed:", error);
    throw error;

  } finally {
    loading = false;
    if (container) container.removeAttribute("aria-busy");
  }
}

/* LOGIN */

async function login() {
  const input = $("#adminKey");
  const enteredKey = input ? input.value.trim() : "";

  if (!enteredKey) {
    setLoginMessage("Admin key भरें।");
    return;
  }

  key = enteredKey;

  const loginButton = $("#loginForm")?.querySelector('[type="submit"]');

  if (loginButton) {
    loginButton.disabled = true;
    loginButton.textContent = "Connecting...";
  }

  setLoginMessage("", false);

  try {
    await call("adminList");
    sessionStorage.setItem("gw_admin_key", key);

    $("#loginPanel").hidden = true;
    $("#editorPanel").hidden = false;

    await refresh();

  } catch (error) {
    console.error("Login failed:", error);

    key = "";
    sessionStorage.removeItem("gw_admin_key");
    setLoginMessage(error.message);

  } finally {
    if (loginButton) {
      loginButton.disabled = false;
      loginButton.textContent = "Continue";
    }
  }
}

/* RESTORE SESSION */

async function restoreSession() {
  const saved = sessionStorage.getItem("gw_admin_key");
  if (!saved) return;

  key = saved;

  try {
    await call("adminList");

    $("#loginPanel").hidden = true;
    $("#editorPanel").hidden = false;

    await refresh();

  } catch (error) {
    console.error("Session restore failed:", error);

    sessionStorage.removeItem("gw_admin_key");
    key = "";

    $("#loginPanel").hidden = false;
    $("#editorPanel").hidden = true;

    setLoginMessage("Session verify nahi hua. Dobara login karein.");
  }
}

/* INITIALIZE */

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = $("#loginForm");
  const postForm = $("#postForm");
  const resetBtn = $("#resetBtn");
  const logoutBtn = $("#logoutBtn");

  if (loginForm) {
    loginForm.onsubmit = async event => {
      event.preventDefault();
      await login();
    };
  }

  restoreSession();

  if (postForm) {
    postForm.onsubmit = async event => {
      event.preventDefault();

      if (saving) return;

      const post = getForm();
      const isUpdate = Boolean(editingPostId);

      if (!post.title || !post.content.trim()) {
        setMessage("Title और Full content भरना जरूरी है।", true);
        return;
      }

      if (isUpdate && !post.id) {
        setMessage("Update cancelled: Original Post ID missing.", true);
        return;
      }

      saving = true;

      const button = postForm.querySelector('[type="submit"]');
      const originalButtonText = button
        ? button.textContent
        : "Save Post";

      if (button) {
        button.disabled = true;
        button.textContent = isUpdate ? "Updating..." : "Saving...";
      }

      setMessage("");

      try {
        await call(isUpdate ? "update" : "create", post);

        setMessage(isUpdate
          ? "Post updated successfully."
          : "New post created successfully."
        );

        reset();
        await refresh();

      } catch (error) {
        console.error("Save failed:", error);
        setMessage(error.message, true);

      } finally {
        saving = false;

        if (button) {
          button.disabled = false;
          button.textContent = editingPostId
            ? "Update Post"
            : originalButtonText;
        }
      }
    };
  }

  if (resetBtn) {
    resetBtn.onclick = event => {
      event.preventDefault();
      if (!saving) reset();
    };
  }

  if (logoutBtn) {
    logoutBtn.onclick = () => {
      sessionStorage.removeItem("gw_admin_key");
      key = "";
      editingPostId = "";
      location.reload();
    };
  }
});
