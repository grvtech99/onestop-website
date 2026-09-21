
const API_URL =
  "https://script.google.com/macros/s/AKfycbywnTL4O_EpmdOe3EgYesh-wEAsXMsuus6H1L2n8-rBD2oYWR4v6-3DrUTs8mSTE7f9/exec";

const $ = (selector) => document.querySelector(selector);

let key = "";
let saving = false;
let loading = false;

function esc(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => ({
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

async function call(action, data = {}) {
  if (!API_URL.startsWith("https://")) {
    throw new Error("API_URL सेट नहीं है");
  }

  const payload = {
    ...data,
    action,
    adminKey: key
  };

  let response;

  try {
    response = await fetch(API_URL, {
      method: "POST",
      redirect: "follow",
      headers: {
        "Content-Type": "text/plain;charset=UTF-8"
      },
      body: JSON.stringify(payload)
    });
  } catch (error) {
    console.error("Apps Script network error:", error);

    throw new Error(
      "Failed to fetch: Apps Script connection या browser CORS समस्या।"
    );
  }

  let result;

  try {
    result = await response.json();
  } catch (error) {
    console.error("Invalid API response:", error);

    throw new Error(
      "Apps Script से valid JSON response नहीं मिला। Deployment जाँचें।"
    );
  }

  if (!result.ok) {
    throw new Error(result.error || "Request failed");
  }

  return result.data;
}

function getForm() {
  return {
    id: $("#postId").value.trim(),
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

function reset() {
  $("#postForm").reset();

  $("#postId").value = "";

  $("#author").value = "Gaurav";

  setMessage("");

  const saveButton = $("#postForm button[type='submit']");
  if (saveButton) {
    saveButton.textContent = "Save Post";
    saveButton.disabled = false;
  }
}

function setSavingState(state) {
  const button = $("#postForm button[type='submit']");

  if (!button) return;

  button.disabled = state;

  if (state) {
    button.textContent = "Saving...";
  } else {
    button.textContent = $("#postId").value
      ? "Update Post"
      : "Save Post";
  }
}

async function refresh() {
  if (loading) return;

  loading = true;

  try {
    const posts = await call("adminList");

    const container = $("#adminPosts");

    if (!container) return;

    container.innerHTML = posts.map((post) => `
      <div class="adminpost">
        <div>
          <strong>${esc(post.title)}</strong>
          <small>
            ${esc(post.category)} · ${esc(post.status)}
          </small>
        </div>

        <div>
          <button type="button"
            data-edit="${esc(post.id)}">
            Edit
          </button>

          <button type="button"
            data-delete="${esc(post.id)}">
            Delete
          </button>
        </div>
      </div>
    `).join("") || "<p>अभी कोई पोस्ट नहीं।</p>";

    container.querySelectorAll("[data-edit]").forEach((button) => {
      button.onclick = () => {
        const post = posts.find(
          (item) => item.id === button.dataset.edit
        );

        edit(post);
      };
    });

    container.querySelectorAll("[data-delete]").forEach((button) => {
      button.onclick = async () => {
        const id = button.dataset.delete;

        if (!confirm("यह पोस्ट permanently delete करें?")) {
          return;
        }

        button.disabled = true;

        try {
          await call("delete", { id });

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

function edit(post) {
  if (!post) return;

  const fields = [
    "id",
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

  for (const field of fields) {
    const element = $("#" + field);

    if (element) {
      element.value = post[field] ?? "";
    }
  }

  setMessage("Editing existing post — ID सुरक्षित है।");

  const saveButton = $("#postForm button[type='submit']");

  if (saveButton) {
    saveButton.textContent = "Update Post";
  }

  $("#postForm").scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}

async function login() {
  const input = $("#adminKey");

  key = input.value;

  try {
    await call("adminList");

    sessionStorage.setItem("gw_admin_key", key);

    $("#loginPanel").hidden = true;
    $("#editorPanel").hidden = false;

    await refresh();

  } catch (error) {
    $("#loginMsg").textContent = error.message;
    key = "";
  }
}

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
    sessionStorage.removeItem("gw_admin_key");
    key = "";
  }
}

document.addEventListener("DOMContentLoaded", () => {

  $("#loginForm").onsubmit = async (event) => {
    event.preventDefault();
    await login();
  };

  restoreSession();

  $("#postForm").onsubmit = async (event) => {
    event.preventDefault();

    if (saving) return;

    const post = getForm();

    if (!post.title || !post.content.trim()) {
      setMessage(
        "Title और Full article content जरूरी हैं।",
        true
      );
      return;
    }

    saving = true;
    setSavingState(true);

    try {
      const result = await call("save", post);

      // Keep the returned ID to prevent accidental
      // creation of another post on the next save.
      if (result && result.id) {
        $("#postId").value = result.id;
      }

      setMessage("Post saved successfully");

      await refresh();

      reset();

    } catch (error) {
      console.error("Save error:", error);

      setMessage(error.message, true);

    } finally {
      saving = false;
      setSavingState(false);
    }
  };

  $("#resetBtn").onclick = reset;

  $("#logoutBtn").onclick = () => {
    sessionStorage.removeItem("gw_admin_key");
    key = "";
    location.reload();
  };

});
