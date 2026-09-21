/* GAURAV'S WORLD — ADMIN.JS
   Long-article POST build
   IMPORTANT: Requires the matching Apps Script backend below.
*/
const API_URL = "https://script.google.com/macros/s/AKfycbxPqioJ9nu_znGgoJLInxzi9xRxR35Ex5eLCFzctbpPipyxzoL9vd5B31u3wcecwHF7/exec";
const $ = selector => document.querySelector(selector);

let key = "";
let editingPostId = "";
let saving = false;
let loading = false;

function esc(value = "") {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
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

/* POST JSON as text/plain to avoid a browser preflight request.
   Browser CORS policy may still block reading Apps Script's response.
   If that occurs, a same-origin proxy/backend is required. */
async function call(action, data = {}) {
  if (!API_URL.startsWith("https://")) throw new Error("API_URL सेट नहीं है।");
  const payload = { ...data, action, adminKey: key };

  let response;
  try {
    response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify(payload),
      redirect: "follow",
      cache: "no-store"
    });
  } catch (e) {
    throw new Error("POST request browser CORS/network policy से ब्लॉक हुई। Apps Script को same-origin proxy से जोड़ना होगा।");
  }

  if (!response.ok) throw new Error(`Server error: HTTP ${response.status}`);
  let result;
  try { result = await response.json(); }
  catch (_) { throw new Error("Server ने readable JSON response नहीं दिया। Apps Script deployment/CORS जाँचें।"); }
  if (!result || result.ok !== true) throw new Error(result?.error || "Apps Script request failed.");
  return result.data;
}

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
  if (button) { button.textContent = "Save Post"; button.disabled = false; }
}
function edit(post) {
  if (!post || !post.id) { alert("Post ID missing. Cannot edit."); return; }
  editingPostId = String(post.id).trim();
  const postId = $("#postId");
  if (postId) postId.value = editingPostId;
  ["title","hook","category","status","thumbnail","heroImage","excerpt","content","tags","author"].forEach(field => {
    const el = $("#" + field);
    if (el) el.value = post[field] == null ? "" : post[field];
  });
  const button = $("#postForm")?.querySelector('[type="submit"]');
  if (button) button.textContent = "Update Post";
  setMessage("Editing existing post. ID: " + editingPostId);
  $("#postForm")?.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function refresh() {
  if (loading) return;
  loading = true;
  const container = $("#adminPosts");
  if (container) container.setAttribute("aria-busy", "true");
  try {
    const posts = await call("adminList");
    if (!Array.isArray(posts)) throw new Error("API ne posts ki valid list nahi bheji.");
    if (!container) return;
    container.innerHTML = posts.map(post => `
      <div class="adminpost">
        <div><strong>${esc(post.title || "Untitled")}</strong>
        <small>${esc(post.category || "")} · ${esc(post.status || "")}</small></div>
        <div><button type="button" data-edit="${esc(post.id || "")}">Edit</button>
        <button type="button" data-delete="${esc(post.id || "")}">Delete</button></div>
      </div>`).join("") || "<p>अभी कोई पोस्ट नहीं।</p>";
    container.querySelectorAll("[data-edit]").forEach(button => {
      button.onclick = () => {
        const post = posts.find(item => String(item.id) === button.dataset.edit);
        if (!post) return alert("Post nahi mili. List refresh karein.");
        edit(post);
      };
    });
    container.querySelectorAll("[data-delete]").forEach(button => {
      button.onclick = async () => {
        const id = button.dataset.delete;
        if (!id) return alert("Post ID missing.");
        if (!confirm("यह पोस्ट delete करें?")) return;
        button.disabled = true;
        try {
          await call("delete", { id });
          if (editingPostId === id) reset();
          setMessage("Post deleted successfully.");
          await refresh();
        } catch (error) {
          alert(error.message); button.disabled = false;
        }
      };
    });
  } finally {
    loading = false;
    if (container) container.removeAttribute("aria-busy");
  }
}
async function login() {
  const input = $("#adminKey");
  const enteredKey = input ? input.value.trim() : "";
  if (!enteredKey) return setLoginMessage("Admin key भरें।");
  key = enteredKey;
  const button = $("#loginForm")?.querySelector('[type="submit"]');
  if (button) { button.disabled = true; button.textContent = "Connecting..."; }
  setLoginMessage("", false);
  try {
    await call("adminList");
    sessionStorage.setItem("gw_admin_key", key);
    $("#loginPanel").hidden = true;
    $("#editorPanel").hidden = false;
    await refresh();
  } catch (error) {
    key = ""; sessionStorage.removeItem("gw_admin_key");
    setLoginMessage(error.message);
  } finally {
    if (button) { button.disabled = false; button.textContent = "Continue"; }
  }
}
async function restoreSession() {
  const saved = sessionStorage.getItem("gw_admin_key");
  if (!saved) return;
  key = saved;
  try {
    await call("adminList");
    $("#loginPanel").hidden = true; $("#editorPanel").hidden = false;
    await refresh();
  } catch (_) {
    sessionStorage.removeItem("gw_admin_key"); key = "";
    $("#loginPanel").hidden = false; $("#editorPanel").hidden = true;
    setLoginMessage("Session verify nahi hua. Dobara login karein.");
  }
}
document.addEventListener("DOMContentLoaded", () => {
  const loginForm = $("#loginForm");
  const postForm = $("#postForm");
  const resetBtn = $("#resetBtn");
  const logoutBtn = $("#logoutBtn");
  if (loginForm) loginForm.onsubmit = async event => { event.preventDefault(); await login(); };
  restoreSession();

  if (postForm) postForm.onsubmit = async event => {
    event.preventDefault();
    if (saving) return;
    const post = getForm();
    const isUpdate = Boolean(editingPostId);
    if (!post.title || !post.content.trim()) return setMessage("Title और Full content भरना जरूरी है।", true);
    if (isUpdate && !post.id) return setMessage("Update cancelled: Original Post ID missing.", true);
    saving = true;
    const button = postForm.querySelector('[type="submit"]');
    const originalText = button ? button.textContent : "Save Post";
    if (button) { button.disabled = true; button.textContent = isUpdate ? "Updating..." : "Saving..."; }
    setMessage("");
    try {
      await call(isUpdate ? "update" : "create", post);
      setMessage(isUpdate ? "Post updated successfully." : "New post created successfully.");
      reset();
      await refresh();
    } catch (error) {
      console.error("Save failed:", error);
      setMessage(error.message, true);
    } finally {
      saving = false;
      if (button) { button.disabled = false; button.textContent = editingPostId ? "Update Post" : originalText; }
    }
  };
  if (resetBtn) resetBtn.onclick = event => { event.preventDefault(); if (!saving) reset(); };
  if (logoutBtn) logoutBtn.onclick = () => {
    sessionStorage.removeItem("gw_admin_key"); key = ""; editingPostId = ""; location.reload();
  };
});
