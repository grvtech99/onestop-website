
const API_URL = "https://script.google.com/macros/s/AKfycbywnTL4O_EpmdOe3EgYesh-wEAsXMsuus6H1L2n8-rBD2oYWR4v6-3DrUTs8mSTE7f9/exec";

const $ = s => document.querySelector(s);

let key = "";


/* ================================
   HTML ESCAPE
================================ */

function esc(s = "") {
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[c]));
}


/* ================================
   API CALL
================================ */

async function call(action, data = {}) {
  if (!API_URL.startsWith("https://")) {
    throw Error("API_URL सेट नहीं है");
  }

  const url = new URL(API_URL);

  url.searchParams.set("action", action);
  url.searchParams.set("adminKey", key);

  Object.entries(data).forEach(([k, v]) => {
    url.searchParams.set(
      k,
      typeof v === "string"
        ? v
        : JSON.stringify(v)
    );
  });

  const response = await fetch(url.toString(), {
    method: "GET"
  });

  const result = await response.json();

  if (!result.ok) {
    throw Error(result.error || "Request failed");
  }

  return result.data;
}


/* ================================
   FORM DATA
================================ */

function getForm() {
  return {
    id: $("#postId").value,

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


/* ================================
   RESET FORM
================================ */

function reset() {
  $("#postForm").reset();

  // Clear existing ID so next save creates a new post
  $("#postId").value = "";

  $("#author").value = "Gaurav";

  $("#saveMsg").textContent = "";

  const saveBtn = $(
    "#postForm button[type='submit']"
  );

  if (saveBtn) {
    saveBtn.textContent = "Save Post";
  }
}


/* ================================
   LOAD ADMIN POSTS
================================ */

async function refresh() {
  const posts = await call("adminList");

  $("#adminPosts").innerHTML = posts.map(p => `
    <div class="adminpost">
      <div>
        <strong>${esc(p.title)}</strong>
        <small>
          ${esc(p.category)} · ${esc(p.status)}
        </small>
      </div>

      <div>
        <button
          type="button"
          data-edit="${esc(p.id)}"
        >
          Edit
        </button>

        <button
          type="button"
          data-delete="${esc(p.id)}"
        >
          Delete
        </button>
      </div>
    </div>
  `).join("") || "<p>अभी कोई पोस्ट नहीं।</p>";


  // EDIT BUTTONS

  $("#adminPosts")
    .querySelectorAll("[data-edit]")
    .forEach(button => {
      button.onclick = () => {
        const post = posts.find(
          p => String(p.id) === button.dataset.edit
        );

        edit(post);
      };
    });


  // DELETE BUTTONS

  $("#adminPosts")
    .querySelectorAll("[data-delete]")
    .forEach(button => {
      button.onclick = async () => {
        if (!confirm("यह पोस्ट delete करें?")) {
          return;
        }

        try {
          await call("delete", {
            id: button.dataset.delete
          });

          await refresh();

          // If deleted post was being edited, clear form
          if (
            $("#postId").value === button.dataset.delete
          ) {
            reset();
          }

        } catch (error) {
          alert(error.message);
        }
      };
    });
}


/* ================================
   EDIT EXISTING POST
================================ */

function edit(p) {
  if (!p) {
    return;
  }

  // CRITICAL FIX:
  // The HTML uses #postId, not #id.
  // Load the original ID to update the existing row.
  $("#postId").value = p.id || "";


  // Load every editable field

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
    const element = $("#" + field);

    if (element) {
      element.value = p[field] ?? "";
    }
  });


  // Update button label

  const saveBtn = $(
    "#postForm button[type='submit']"
  );

  if (saveBtn) {
    saveBtn.textContent = "Update Post";
  }


  // Show editing message

  const saveMsg = $("#saveMsg");

  if (saveMsg) {
    saveMsg.textContent =
      "Editing existing post: " + (p.title || "");
  }


  // Scroll to editor

  window.scrollTo({
    top: 0,
    behavior: "smooth"
  });
}


/* ================================
   INITIALIZE ADMIN
================================ */

document.addEventListener("DOMContentLoaded", () => {

  /* ---------- LOGIN ---------- */

  $("#loginForm").onsubmit = async e => {
    e.preventDefault();

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
  };


  /* ---------- RESTORE SESSION ---------- */

  const saved = sessionStorage.getItem(
    "gw_admin_key"
  );

  if (saved) {
    key = saved;

    call("adminList")
      .then(() => {
        $("#loginPanel").hidden = true;

        $("#editorPanel").hidden = false;

        return refresh();
      })
      .catch(() => {
        sessionStorage.removeItem(
          "gw_admin_key"
        );

        key = "";

        $("#loginPanel").hidden = false;

        $("#editorPanel").hidden = true;
      });
  }


  /* ---------- SAVE / UPDATE POST ---------- */

  $("#postForm").onsubmit = async e => {
    e.preventDefault();

    const post = getForm();

    // Prevent empty title/content
    if (!post.title || !post.content.trim()) {
      $("#saveMsg").textContent =
        "Title और Full article content भरें।";

      return;
    }

    // Remember whether this is an update
    const isUpdate = Boolean(post.id);

    try {
      $("#saveMsg").textContent =
        isUpdate
          ? "Updating post..."
          : "Saving post...";

      await call("save", post);

      $("#saveMsg").textContent =
        isUpdate
          ? "Post updated successfully"
          : "Post saved successfully";

      reset();

      await refresh();

    } catch (error) {
      $("#saveMsg").textContent = error.message;
    }
  };


  /* ---------- CLEAR FORM ---------- */

  $("#resetBtn").onclick = e => {
    e.preventDefault();
    reset();
  };


  /* ---------- LOGOUT ---------- */

  $("#logoutBtn").onclick = () => {
    sessionStorage.removeItem(
      "gw_admin_key"
    );

    key = "";

    location.reload();
  };

});
