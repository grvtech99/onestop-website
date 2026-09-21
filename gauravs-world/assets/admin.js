
const API_URL =
  "https://script.google.com/macros/s/AKfycbywnTL4O_EpmdOe3EgYesh-wEAsXMsuus6H1L2n8-rBD2oYWR4v6-3DrUTs8mSTE7f9/exec";

const $ = selector => document.querySelector(selector);

let key = "";
let editingPostId = "";
let saving = false;
let loading = false;


/* =========================================
   HELPERS
========================================= */

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


/* =========================================
   API CALL - GET
========================================= */

async function call(action, data = {}) {
  if (!API_URL.startsWith("https://")) {
    throw new Error("API_URL सेट नहीं है");
  }

  const url = new URL(API_URL);

  url.searchParams.set("action", action);
  url.searchParams.set("adminKey", key);

  Object.entries(data).forEach(([name, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.set(
        name,
        String(value)
      );
    }
  });

  let response;

  try {
    response = await fetch(url.toString(), {
      method: "GET",
      redirect: "follow",
      cache: "no-store"
    });
  } catch (error) {
    console.error("API network error:", error);

    throw new Error(
      "Failed to fetch. Apps Script connection/CORS error."
    );
  }

  let result;

  try {
    result = await response.json();
  } catch (error) {
    console.error("API response was not JSON:", error);

    throw new Error(
      "Apps Script ने JSON के बजाय HTML response दिया। Deployment जाँचें।"
    );
  }

  if (!result.ok) {
    throw new Error(result.error || "Request failed");
  }

  return result.data;
}


/* =========================================
   FORM DATA
========================================= */

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


/* =========================================
   RESET FORM
========================================= */

function reset() {
  editingPostId = "";

  $("#postForm").reset();
  $("#postId").value = "";
  $("#author").value = "Gaurav";

  setMessage("");

  const button = $("#postForm").querySelector(
    '[type="submit"]'
  );

  if (button) {
    button.textContent = "Save Post";
    button.disabled = false;
  }
}


/* =========================================
   EDIT POST
========================================= */

function edit(post) {
  if (!post || !post.id) {
    alert("Post ID missing. Cannot edit.");
    return;
  }

  editingPostId = String(post.id).trim();

  // Keep original ID in hidden field too.
  $("#postId").value = editingPostId;

  const fields = [
    "title",
    "hook",
    "category",
    "status",
    "thumbnail",
    "heroImage",
    "excerpt",
    "content",
    "tags",
    "author"
  ];

  fields.forEach(field => {
    const el = $("#" + field);

    if (el) {
      el.value = post[field] == null
        ? ""
        : post[field];
    }
  });

  const button = $("#postForm").querySelector(
    '[type="submit"]'
  );

  if (button) {
    button.textContent = "Update Post";
  }

  setMessage(
    "Editing existing post. ID: " + editingPostId
  );

  $("#postForm").scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}


/* =========================================
   REFRESH ADMIN LIST
========================================= */

async function refresh() {
  if (loading) return;

  loading = true;

  try {
    const posts = await call("adminList");

    const container = $("#adminPosts");

    if (!container) return;

    container.innerHTML = posts.map(post => `
      <div class="adminpost">
        <div>
          <strong>${esc(post.title)}</strong>
          <small>
            ${esc(post.category)} · ${esc(post.status)}
          </small>
        </div>

        <div>
          <button
            type="button"
            data-edit="${esc(post.id)}"
          >
            Edit
          </button>

          <button
            type="button"
            data-delete="${esc(post.id)}"
          >
            Delete
          </button>
        </div>
      </div>
    `).join("") || "<p>अभी कोई पोस्ट नहीं।</p>";

    container.querySelectorAll("[data-edit]")
      .forEach(button => {
        button.onclick = () => {
          const post = posts.find(
            item =>
              String(item.id) === button.dataset.edit
          );

          edit(post);
        };
      });

    container.querySelectorAll("[data-delete]")
      .forEach(button => {
        button.onclick = async () => {
          const id = button.dataset.delete;

          if (!confirm("यह पोस्ट delete करें?")) {
            return;
          }

          button.disabled = true;

          try {
            await call("delete", { id });

            if (editingPostId === id) {
              reset();
            }

            await refresh();

            setMessage("Post deleted successfully");

          } catch (error) {
            alert(error.message);
            button.disabled = false;
          }
        };
      });

  } finally {
    loading = false;
  }
}


/* =========================================
   LOGIN
========================================= */

async function login() {
  key = $("#adminKey").value;

  try {
    await call("adminList");

    sessionStorage.setItem(
      "gw_admin_key",
      key
    );

    $("#loginPanel").hidden = true;
    $("#editorPanel").hidden = false;

    await refresh();

  } catch (error) {
    $("#loginMsg").textContent = error.message;
    key = "";
  }
}


/* =========================================
   RESTORE SESSION
========================================= */

async function restoreSession() {
  const saved = sessionStorage.getItem(
    "gw_admin_key"
  );

  if (!saved) return;

  key = saved;

  try {
    await call("adminList");

    $("#loginPanel").hidden = true;
    $("#editorPanel").hidden = false;

    await refresh();

  } catch (error) {
    sessionStorage.removeItem("gw_admin_key");
    key = "";
  }
}


/* =========================================
   INITIALIZE
========================================= */

document.addEventListener("DOMContentLoaded", () => {

  /* LOGIN */

  $("#loginForm").onsubmit = async event => {
    event.preventDefault();
    await login();
  };

  restoreSession();


  /* SAVE / UPDATE */

  $("#postForm").onsubmit = async event => {
    event.preventDefault();

    if (saving) return;

    const post = getForm();
    const isUpdate = Boolean(editingPostId);

    if (!post.title || !post.content.trim()) {
      setMessage(
        "Title और Full content भरना जरूरी है।",
        true
      );
      return;
    }

    // Critical: never let an edit lose its ID.
    if (isUpdate && !post.id) {
      setMessage(
        "Update cancelled: Original Post ID missing.",
        true
      );
      return;
    }

    saving = true;

    const button = $("#postForm").querySelector(
      '[type="submit"]'
    );

    if (button) {
      button.disabled = true;
      button.textContent = "Saving...";
    }

    try {
      const action = isUpdate ? "update" : "create";

      const result = await call(action, post);

      setMessage(
        isUpdate
          ? "Post updated successfully."
          : "New post created successfully."
      );

      // Clear form only after confirmed API success.
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
          : "Save Post";
      }
    }
  };


  /* RESET */

  $("#resetBtn").onclick = event => {
    event.preventDefault();
    reset();
  };


  /* LOGOUT */

  $("#logoutBtn").onclick = () => {
    sessionStorage.removeItem("gw_admin_key");
    key = "";
    location.reload();
  };

});
