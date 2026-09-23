// ADR-662 D13/D15 — the routines that run inside a web page the agent works in.
//
// ONE copy, two executors: the yarnnn Chrome extension injects this file into
// its tab (`background.js`, `chrome.scripting` — the extension's isolated
// world), and the desktop host's browser pane evaluates it (`src-tauri/src/
// hands/mod.rs` include_str!s this path). The model never writes a line of it:
// an act is this file plus ONE call whose arguments the executor JSON-encoded,
// so a model's text reaches the page only as a string value, never as code.
//
// Every routine is synchronous and returns a JSON string: an executor hands
// back the value of the script's last expression and does not wait for a
// promise.
//
// Idempotent: a page keeps what an earlier act installed, and a new page
// installs it again.
(function () {
  var Y = (window.__yarnnnHands = window.__yarnnnHands || {});

  var ACTIONABLE =
    'a[href], button, input:not([type="hidden"]), textarea, select, summary,' +
    ' [role="button"], [role="link"], [role="tab"], [role="menuitem"],' +
    ' [role="checkbox"], [role="option"], [contenteditable=""], [contenteditable="true"]';
  var MAX_ELEMENTS = 250;
  var MAX_TEXT = 12000;
  var MAX_LABEL = 80;

  function clip(s, n) {
    s = (s || "").replace(/\s+/g, " ").trim();
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  }

  function shown(el) {
    var r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return false;
    var st = window.getComputedStyle(el);
    return st.visibility !== "hidden" && st.display !== "none";
  }

  function labelOf(el) {
    var aria = el.getAttribute("aria-label");
    if (aria) return clip(aria, MAX_LABEL);
    if (el.labels && el.labels.length) return clip(el.labels[0].innerText, MAX_LABEL);
    var by = el.getAttribute("aria-labelledby");
    if (by) {
      var ref = document.getElementById(by.split(" ")[0]);
      if (ref) return clip(ref.innerText, MAX_LABEL);
    }
    return clip(
      el.getAttribute("placeholder") ||
        el.innerText ||
        (el.tagName === "INPUT" && /^(submit|button|reset)$/i.test(el.type) ? el.value : "") ||
        el.getAttribute("title") ||
        el.getAttribute("alt") ||
        // A link or button that is only an image is named by the image.
        (el.querySelector("img[alt]") || { getAttribute: function () { return ""; } }).getAttribute("alt") ||
        el.getAttribute("name") ||
        "",
      MAX_LABEL,
    );
  }

  function kindOf(el) {
    var tag = el.tagName;
    var role = el.getAttribute("role");
    if (tag === "A" || role === "link") return "link";
    if (tag === "SELECT") return "dropdown";
    if (tag === "TEXTAREA" || el.isContentEditable) return "text field";
    if (tag === "INPUT") {
      var t = (el.type || "text").toLowerCase();
      if (t === "checkbox" || t === "radio") return t;
      if (/^(submit|button|reset|image)$/.test(t)) return "button";
      return t === "password" ? "password field" : "text field";
    }
    if (role === "checkbox") return "checkbox";
    return "button";
  }

  function fillable(el) {
    var k = kindOf(el);
    return k === "text field" || k === "password field" || k === "dropdown";
  }

  // A cheap fingerprint of what the member would see, so "nothing changed"
  // is a measurement, not a guess (ADR-662 D3).
  function signature() {
    var body = document.body;
    return location.href + "#" + (body ? body.innerText.length : 0);
  }

  Y.state = function () {
    return JSON.stringify({
      url: location.href,
      title: document.title,
      ready: document.readyState,
      mark: window.__yarnnnMark || null,
      sig: signature(),
    });
  };

  Y.mark = function (m) {
    window.__yarnnnMark = m;
    return Y.state();
  };

  Y.read = function () {
    var els = [];
    var out = [];
    var nodes = document.querySelectorAll(ACTIONABLE);
    for (var i = 0; i < nodes.length && out.length < MAX_ELEMENTS; i++) {
      var el = nodes[i];
      if (el.disabled || !shown(el)) continue;
      var item = { ref: els.length, kind: kindOf(el), label: labelOf(el) };
      if (fillable(el)) {
        // A password's value never leaves the page.
        if (item.kind !== "password field") item.value = clip(el.value || el.innerText || "", MAX_LABEL);
        if (el.tagName === "SELECT") {
          item.options = Array.prototype.slice
            .call(el.options, 0, 30)
            .map(function (o) { return clip(o.text, 40); });
        }
      }
      if (item.kind === "checkbox" || item.kind === "radio") item.checked = !!el.checked;
      if (item.kind === "link") item.href = clip(el.getAttribute("href") || "", 120);
      els.push(el);
      out.push(item);
    }
    Y.els = els;
    var text = document.body ? document.body.innerText : "";
    return JSON.stringify({
      ok: true,
      title: document.title,
      url: location.href,
      text: clip(text, MAX_TEXT),
      text_truncated: text.length > MAX_TEXT,
      elements: out,
      elements_truncated: nodes.length > out.length && out.length >= MAX_ELEMENTS,
    });
  };

  function element(ref) {
    var el = Y.els && Y.els[ref];
    return el && el.isConnected ? el : null;
  }

  Y.click = function (ref) {
    var el = element(ref);
    if (!el) return JSON.stringify({ ok: false, error: "stale_ref" });
    var label = labelOf(el);
    el.scrollIntoView({ block: "center", inline: "nearest" });
    // A link that opens a NEW tab is followed in this one: a click with no
    // user gesture behind it cannot open a tab (the browser blocks it as a
    // popup), and the agent works in one tab (driven, 2026-09-23).
    if (el.tagName === "A" && el.target === "_blank" && /^https?:/.test(el.href)) {
      location.assign(el.href);
      return JSON.stringify({ ok: true, label: label });
    }
    el.click();
    return JSON.stringify({ ok: true, label: label });
  };

  function setValue(el, text) {
    // The prototype's own setter, so a framework that watches the property
    // (React, Vue) sees the change as if typed.
    var proto =
      el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype :
      el.tagName === "SELECT" ? HTMLSelectElement.prototype :
      HTMLInputElement.prototype;
    var setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, text);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  Y.fill = function (ref, text, submit) {
    var el = element(ref);
    if (!el) return JSON.stringify({ ok: false, error: "stale_ref" });
    if (!fillable(el)) return JSON.stringify({ ok: false, error: "not_a_field", label: labelOf(el) });
    var label = labelOf(el);
    el.focus();
    var matches;
    if (el.tagName === "SELECT") {
      var want = String(text).trim().toLowerCase();
      var hit = null;
      for (var i = 0; i < el.options.length; i++) {
        var o = el.options[i];
        if (o.text.trim().toLowerCase() === want || o.value.toLowerCase() === want) { hit = o; break; }
      }
      if (!hit) return JSON.stringify({ ok: false, error: "no_such_option", label: label });
      setValue(el, hit.value);
      matches = el.value === hit.value;
    } else if (el.isContentEditable) {
      el.textContent = text;
      el.dispatchEvent(new InputEvent("input", { bubbles: true }));
      matches = el.textContent === text;
    } else {
      setValue(el, text);
      matches = el.value === text;
    }
    var submitted = false;
    if (submit) {
      var form = el.form;
      if (form) {
        if (form.requestSubmit) form.requestSubmit(); else form.submit();
        submitted = true;
      } else {
        var opts = { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true };
        el.dispatchEvent(new KeyboardEvent("keydown", opts));
        el.dispatchEvent(new KeyboardEvent("keyup", opts));
        submitted = true;
      }
    }
    return JSON.stringify({ ok: matches, label: label, matches: matches, submitted: submitted });
  };

  Y.back = function () {
    history.back();
    return JSON.stringify({ ok: true });
  };
})();
