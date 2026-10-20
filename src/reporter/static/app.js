"use strict";

// Local dashboard client. Sends only the approved actions (generate, retry
// delivery, delivery test, schedule) and never receives a bot token or a
// filesystem path from the server.

function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function getJSON(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  const data = await response.json().catch(() => ({ ok: false, error: "bad JSON" }));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Reporter-Client": "local",
      Accept: "application/json",
    },
    body: JSON.stringify(payload || {}),
  });
  const data = await response.json().catch(() => ({ ok: false, error: "bad JSON" }));
  return { status: response.status, data };
}

function setStatus(elementId, label, kind) {
  const el = document.getElementById(elementId);
  el.textContent = label;
  el.className = "badge" + (kind ? " " + kind : "");
}

function listOrNone(items, render) {
  if (!items || items.length === 0) {
    return "<p class='hint'>None recorded.</p>";
  }
  return "<ul>" + items.map(render).join("") + "</ul>";
}

function scheduleLastResult(result) {
  if (!result) return "never";
  const delivery = result.delivery_ok;
  return (
    (result.ok ? "ok" : "failed") +
    (result.report_id ? ", report " + result.report_id : "") +
    (result.generated === false ? ", not generated" : "") +
    (delivery === true
      ? ", delivered"
      : delivery === false
        ? ", delivery failed"
        : result.reason
          ? ", " + result.reason
          : "") +
    (result.error ? ", error: " + result.error : "")
  );
}

function renderReporting(reporting) {
  const lastReport = reporting.last_report;
  const lastDelivery = reporting.last_delivery;
  const pending = reporting.awaiting_delivery;
  const rows = [];

  rows.push(
    "<li>Latest saved report: " +
    (reporting.latest_saved_report_id
      ? "<code>" + esc(reporting.latest_saved_report_id) + "</code> (" +
        esc(String(reporting.saved_report_count)) + " saved)"
      : "none saved yet") +
    "</li>"
  );

  if (lastReport) {
    rows.push(
      "<li>Last generation: " +
      (lastReport.ok === false
        ? "<span class='error-text'>failed" +
          (lastReport.error ? ": " + esc(lastReport.error) : "") +
          "</span>"
        : esc(lastReport.report_id || "unknown") +
          " (" + esc(lastReport.source || "") + ", " + esc(lastReport.at || "") + ")") +
      "</li>"
    );
  } else {
    rows.push("<li>Last generation: no run recorded in this process.</li>");
  }

  if (lastDelivery) {
    const parts = lastDelivery.parts_total
      ? ", parts " + esc(String(lastDelivery.parts_sent)) + "/" +
        esc(String(lastDelivery.parts_total))
      : "";
    rows.push(
      "<li>Last delivery: " +
      (lastDelivery.ok
        ? "<span class='ok-text'>delivered</span> report " +
          esc(lastDelivery.report_id || "") +
          " at " + esc(lastDelivery.at || "")
        : "<span class='error-text'>failed</span> report " +
          esc(lastDelivery.report_id || "") +
          " at " + esc(lastDelivery.at || "") +
          ": " + esc(lastDelivery.error || lastDelivery.reason || "unknown error")) +
      parts +
      " (source: " + esc(lastDelivery.source || "") + ")</li>"
    );
  } else {
    rows.push("<li>Last delivery: none recorded.</li>");
  }

  if (pending) {
    rows.push(
      "<li><span class='error-text'>Awaiting delivery: report " +
      esc(pending.report_id || "") + " since " + esc(pending.since || "") +
      " (" + esc(pending.attempts || "?") + " attempt(s)): " +
      esc(pending.last_error || "unknown error") +
      "</span></li>"
    );
  } else {
    rows.push("<li>Awaiting delivery: none.</li>");
  }

  rows.push(
    "<li>Delivery test passed: " +
    (reporting.delivery_test_passed ? "yes" : "no") +
    "</li>"
  );
  document.getElementById("reporting-block").innerHTML = "<ul>" + rows.join("") + "</ul>";
}

function renderOverview(overview) {
  document.getElementById("model-status").textContent = overview.model_status || "";
  document.getElementById("generated-at").textContent =
    "Dashboard data collected at " + (overview.generated_at || "unknown");

  const schedule = overview.schedule || {};
  setStatus(
    "schedule-badge",
    "schedule: " + (schedule.enabled ? "ENABLED" : "disabled"),
    schedule.enabled ? "ok" : "warn"
  );
  const telegram = overview.telegram || {};
  setStatus(
    "telegram-badge",
    "telegram: " + (telegram.delivery_test_passed ? "test passed" : "test not passed"),
    telegram.delivery_test_passed ? "ok" : "warn"
  );

  const repo = overview.repo || {};
  const phase = (overview.phase || {}).current;
  document.getElementById("status-list").innerHTML =
    "<dt>Repository</dt><dd>" +
    (repo.available ? esc(repo.branch || "unknown") + " (readable)" : "Git unavailable") +
    "</dd>" +
    "<dt>Working tree</dt><dd>" +
    (repo.available
      ? repo.clean
        ? "clean"
        : esc(String(repo.changed_file_count)) + " uncommitted change(s)"
      : "unavailable") +
    "</dd>" +
    "<dt>Current phase</dt><dd>" +
    (phase
      ? "Phase " + esc(phase.number) + ": " + esc(phase.title) + " (" + esc(phase.status) + ")"
      : "not determinable from records") +
    "</dd>" +
    "<dt>Test records</dt><dd>" + esc((overview.tests || {}).status || "unavailable") + "</dd>" +
    "<dt>Experiments</dt><dd>" + esc((overview.experiments || {}).status || "unavailable") + "</dd>";

  const head = repo.head;
  document.getElementById("git-block").innerHTML = repo.available
    ? "<p>Latest commit: <code>" +
      esc(String(head ? head.sha.slice(0, 12) : "")) +
      "</code> " +
      esc(head ? head.subject : "") +
      "<br><span class='evidence'>" +
      esc(head ? head.author + " " + head.authored_at : "") +
      "</span></p><p>" +
      esc(
        repo.clean
          ? "Working tree clean."
          : repo.changed_file_count + " uncommitted change(s)."
      ) +
      "</p>"
    : "<p class='error-text'>Git unavailable: " + esc(repo.error || "") + "</p>";

  const spending = overview.api_spending || {};
  document.getElementById("spending-block").innerHTML =
    spending.status === "available"
      ? "<p>" +
        esc(String(spending.spend_usd)) +
        " USD<br><span class='evidence'>source: " +
        esc(spending.source || "") +
        ", retrieved " +
        esc(spending.retrieved_at || "") +
        "</span></p>"
      : "<p>Unavailable</p><p class='evidence'>" +
        esc(spending.reason || "no verified billing data") +
        "</p><p class='hint'>No zero or estimate is assumed.</p>";

  document.getElementById("telegram-block").innerHTML =
    "<ul>" +
    "<li>Bot token configured: " + (telegram.token_configured ? "yes" : "no") + "</li>" +
    "<li>Destination chat id configured: " + (telegram.chat_id_configured ? "yes" : "no") + "</li>" +
    "<li>Destination: " + esc(telegram.chat_id_masked || "not set") + "</li>" +
    "<li>Verified bot: " + esc(telegram.bot_username ? "@" + telegram.bot_username : "not verified yet") + "</li>" +
    "<li>Delivery test passed: " + (telegram.delivery_test_passed ? "yes" : "no") + "</li>" +
    "</ul><p class='hint'>The token is never returned by the server.</p>";

  document.getElementById("schedule-block").innerHTML =
    "<ul>" +
    "<li>Enabled: " + (schedule.enabled ? "yes" : "no") + "</li>" +
    "<li>Interval: " + esc(String(schedule.interval_hours)) + " hours (" +
    esc(schedule.slots_eat || "") + ")</li>" +
    "<li>Timezone: " + esc(schedule.timezone || "") + "</li>" +
    "<li>Next run: " + esc(schedule.next_run_at || "not scheduled") + "</li>" +
    "<li>Last attempt: " + esc(schedule.last_attempt_at || "never") + "</li>" +
    "<li>Last result: " + esc(scheduleLastResult(schedule.last_result)) + "</li>" +
    "<li>Runs in this process only; no system task was created.</li>" +
    "</ul>";

  renderReporting(overview.reporting || {});

  const tests = overview.tests || {};
  document.getElementById("tests-block").innerHTML =
    tests.status === "available"
      ? listOrNone(tests.runs, (run) =>
          "<li><code>" +
          esc(run.file || run.id || "record") +
          "</code>: " +
          esc(run.summary || run.command || "recorded") +
          " <span class='evidence'>" +
          esc(run.recorded_at || "") +
          "</span></li>"
        )
      : "<p>Unavailable</p><p class='evidence'>" + esc(tests.reason || "") + "</p>";

  const experiments = overview.experiments || {};
  document.getElementById("experiments-block").innerHTML =
    experiments.status === "available"
      ? listOrNone(experiments.entries, (entry) =>
          "<li>" + esc(entry.id) + ": " + esc(entry.title) + "</li>"
        )
      : "<p>Unavailable</p><p class='evidence'>" +
        esc(experiments.reason || "") +
        "</p><p class='hint'>No experiment is claimed as run.</p>";

  document.getElementById("blockers-block").innerHTML = listOrNone(
    overview.blockers,
    (item) =>
      "<li>" +
      esc(item.text || item.title || item.id) +
      "<br><span class='evidence'>" +
      esc(item.evidence || "") +
      "</span></li>"
  );

  document.getElementById("milestones-block").innerHTML = listOrNone(
    overview.milestones,
    (item) =>
      "<li>Phase " + esc(item.number) + ": " + esc(item.title) +
      " (" + esc(item.status) + ")</li>"
  );

  document.getElementById("timeline-block").innerHTML = listOrNone(
    overview.timeline,
    (event) =>
      "<li>" +
      esc(event.label || event.id) +
      "<br><span class='evidence'>" +
      esc(event.kind || "") +
      " / " +
      esc(event.evidence || "") +
      (event.previously_reported ? " / previously reported" : "") +
      "</span></li>"
  );

  const reports = overview.reports || [];
  const renderReport = (item) =>
    "<li><code>" +
    esc(item.report_id) +
    "</code><br><span class='evidence'>" +
    esc(item.activity || "") +
    "</span> " +
    (item.has_markdown
      ? "<a href='/api/report/" + esc(item.report_id) + "/markdown'>markdown</a>"
      : "") +
    "</li>";
  document.getElementById("reports-block").innerHTML = listOrNone(
    reports.slice(0, 5),
    renderReport
  );
  document.getElementById("history-block").innerHTML = listOrNone(reports, renderReport);

  document.getElementById("public-block").innerHTML =
    "<p class='hint'>" + esc((overview.public_drafts || {}).status || "") + "</p>" +
    "<p class='hint'>Public posting requires human approval and is not implemented.</p>";

  const log = overview.delivery_log || [];
  document.getElementById("delivery-block").innerHTML = listOrNone(log, (line) =>
    "<li class='evidence'>" + esc(line) + "</li>"
  );
}

async function refresh() {
  try {
    const data = await getJSON("/api/overview");
    renderOverview(data.overview);
  } catch (error) {
    document.getElementById("action-result").innerHTML =
      "<span class='error-text'>Could not load overview: " + esc(error.message) + "</span>";
  }
}

function showActionResult(text, isError) {
  document.getElementById("action-result").innerHTML = isError
    ? "<span class='error-text'>" + esc(text) + "</span>"
    : esc(text);
}

function bindActions() {
  document.getElementById("btn-generate").addEventListener("click", async () => {
    const button = document.getElementById("btn-generate");
    button.disabled = true;
    try {
      const { status, data } = await postJSON("/api/report/generate", {});
      if (data.ok) {
        showActionResult(
          "Report " + data.result.report_id +
          (data.result.created ? " created." : " already existed; not overwritten.") +
          " " + data.result.activity_note
        );
      } else {
        showActionResult("Generate failed (HTTP " + status + "): " + data.error, true);
      }
    } catch (error) {
      showActionResult("Generate failed: " + error.message, true);
    } finally {
      button.disabled = false;
      refresh();
    }
  });

  document.getElementById("btn-deliver").addEventListener("click", async () => {
    const button = document.getElementById("btn-deliver");
    button.disabled = true;
    try {
      const { status, data } = await postJSON("/api/report/deliver", {});
      if (data.ok) {
        const result = data.result || {};
        showActionResult(
          result.duplicate
            ? "Report " + result.report_id + " was already delivered; nothing was sent again."
            : "Report " + result.report_id + " delivered" +
              (result.parts_total
                ? " (parts " + result.parts_sent + " of " + result.parts_total + ")"
                : "") + "."
        );
      } else {
        showActionResult(
          "Delivery failed (HTTP " + status + "): " +
          (data.result ? data.result.reason || data.result.error || "" : data.error),
          true
        );
      }
    } catch (error) {
      showActionResult("Delivery failed: " + error.message, true);
    } finally {
      button.disabled = false;
      refresh();
    }
  });

  document.getElementById("btn-telegram-test").addEventListener("click", async () => {
    const button = document.getElementById("btn-telegram-test");
    button.disabled = true;
    try {
      const { status, data } = await postJSON("/api/telegram/test", {});
      if (data.ok) {
        showActionResult(
          "Delivery test passed: bot @" +
          (data.result.bot_username || "?") +
          ", message id " + data.result.message_id
        );
      } else {
        const detail = data.result
          ? (data.result.stage || "") + ": " +
            (data.result.error || (data.result.problems || []).join("; "))
          : data.error;
        showActionResult("Delivery test failed (HTTP " + status + "): " + detail, true);
      }
    } catch (error) {
      showActionResult("Delivery test failed: " + error.message, true);
    } finally {
      button.disabled = false;
      refresh();
    }
  });

  document.getElementById("btn-enable").addEventListener("click", async () => {
    try {
      const { status, data } = await postJSON("/api/schedule", { enabled: true });
      if (data.ok) {
        showActionResult("Automatic reporting enabled.");
      } else {
        showActionResult(
          "Enable refused (HTTP " + status + "): " + (data.result.reason || data.error),
          true
        );
      }
    } catch (error) {
      showActionResult("Enable failed: " + error.message, true);
    }
    refresh();
  });

  document.getElementById("btn-disable").addEventListener("click", async () => {
    try {
      const { data } = await postJSON("/api/schedule", { enabled: false });
      showActionResult(data.ok ? "Automatic reporting disabled." : "Disable failed.");
    } catch (error) {
      showActionResult("Disable failed: " + error.message, true);
    }
    refresh();
  });
}

bindActions();
refresh();
setInterval(refresh, 60000);
