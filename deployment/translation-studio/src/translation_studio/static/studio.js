(function () {
  "use strict";

  const form = document.querySelector("[data-dirty-form]");
  const saveState = document.querySelector("[data-save-state]");
  const banner = document.getElementById("recovery-banner");
  const recoverButton = document.querySelector("[data-recover-draft]");
  const discardButton = document.querySelector("[data-discard-draft]");
  const autosaveUrl = form ? form.getAttribute("data-autosave-url") : null;
  const itemId = form ? form.getAttribute("data-item-id") : null;
  const userId = form ? form.getAttribute("data-user-id") : null;
  const draftKey = itemId && userId ? "lugandagpt-studio-draft-" + userId + "-" + itemId : null;
  let dirty = false;
  let editVersion = 0;
  let timer = null;
  let pendingDraft = null;

  function payloadFromForm() {
    const data = new FormData(form);
    const payload = {};
    for (const [key, value] of data.entries()) {
      payload[key] = value;
    }
    return payload;
  }

  function comparable(payload) {
    const copy = Object.assign({}, payload);
    delete copy.csrf_token;
    return JSON.stringify(copy);
  }

  function storeLocalDraft() {
    if (!draftKey) {
      return;
    }
    try {
      window.localStorage.setItem(
        draftKey,
        JSON.stringify({ payload: payloadFromForm(), savedAt: new Date().toISOString() })
      );
    } catch (error) {
      // Storage can be disabled. The server autosave still runs.
    }
  }

  function clearLocalDraft() {
    if (!draftKey) {
      return;
    }
    try {
      window.localStorage.removeItem(draftKey);
    } catch (error) {
      // Ignore storage errors.
    }
  }

  function setState(text, isError) {
    if (!saveState) {
      return;
    }
    saveState.textContent = text;
    saveState.classList.toggle("muted", Boolean(isError));
  }

  function markDirty() {
    dirty = true;
    editVersion += 1;
    if (saveState && !autosaveUrl) {
      saveState.textContent = "Unsaved changes";
    }
    storeLocalDraft();
    if (autosaveUrl) {
      window.clearTimeout(timer);
      timer = window.setTimeout(runAutosave, 1300);
    }
  }

  async function runAutosave() {
    if (!autosaveUrl || !dirty) {
      return;
    }
    const versionAtStart = editVersion;
    const payload = payloadFromForm();
    setState("Saving...", false);
    try {
      const response = await fetch(autosaveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams(payload).toString()
      });
      const result = await response.json();
      if (!response.ok || result.status !== "saved") {
        setState("Autosave failed. Use Save progress. " + (result.message || ""), true);
        return;
      }
      if (editVersion === versionAtStart) {
        dirty = false;
        clearLocalDraft();
        const when = result.saved_at ? new Date(result.saved_at) : new Date();
        const label = isNaN(when.getTime())
          ? "Saved"
          : "Saved at " + when.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        setState(label + ". Your work is stored.", false);
      } else {
        window.clearTimeout(timer);
        timer = window.setTimeout(runAutosave, 1000);
      }
    } catch (error) {
      setState("Autosave failed. Your text is still on this device. Use Save progress.", true);
    }
  }

  function applyDraft(payload) {
    if (!form || !payload) {
      return;
    }
    for (const [name, value] of Object.entries(payload)) {
      if (name === "csrf_token") {
        continue;
      }
      const field = form.querySelector('[name="' + name.replace(/"/g, '\\"') + '"]');
      if (field && typeof value === "string") {
        field.value = value;
      }
    }
    dirty = true;
    editVersion += 1;
    setState("Unsaved text restored. Review it and save when ready.", false);
  }

  if (form) {
    form.addEventListener("input", markDirty);
    form.addEventListener("change", markDirty);
    form.addEventListener("submit", function () {
      dirty = false;
      clearLocalDraft();
    });

    window.addEventListener("beforeunload", function (event) {
      if (!dirty) {
        return;
      }
      event.preventDefault();
      event.returnValue = "";
    });

    if (draftKey) {
      try {
        const raw = window.localStorage.getItem(draftKey);
        if (raw) {
          const draft = JSON.parse(raw);
          const current = comparable(payloadFromForm());
          if (draft && draft.payload && comparable(draft.payload) !== current && banner) {
            pendingDraft = draft.payload;
            banner.hidden = false;
          }
        }
      } catch (error) {
        // Ignore a malformed local draft.
      }
    }
  }

  if (recoverButton) {
    recoverButton.addEventListener("click", function () {
      if (pendingDraft) {
        applyDraft(pendingDraft);
        pendingDraft = null;
      }
      if (banner) {
        banner.hidden = true;
      }
    });
  }

  if (discardButton) {
    discardButton.addEventListener("click", function () {
      pendingDraft = null;
      clearLocalDraft();
      if (banner) {
        banner.hidden = true;
      }
      setState("No unsaved changes");
    });
  }

  const decision = document.querySelector("[data-review-decision]");
  const commentHint = document.querySelector("[data-comment-hint]");
  if (decision && commentHint) {
    const updateHint = function () {
      if (decision.value === "approved") {
        commentHint.textContent = "Comments are optional for an approval.";
      } else {
        commentHint.textContent = "Please explain your decision. This is required when you request revision or cannot assess the translation.";
      }
    };
    decision.addEventListener("change", updateHint);
    updateHint();
  }
})();
