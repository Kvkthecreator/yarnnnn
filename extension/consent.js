// ADR-662 D15 / ADR-663 D4 — the per-site question, drawn by the extension.
// The page that asked cannot answer it; only a click here can.
const q = new URLSearchParams(location.search);
const host = q.get("host") || "";
const t = (k, s) => chrome.i18n.getMessage(k, s);
document.getElementById("title").textContent = t("consentTitle", [host]);
document.getElementById("body").textContent = t("consentBody");
document.getElementById("later").textContent = t("consentLater");
const answer = (allow) => {
  chrome.runtime.sendMessage({ type: "consent", id: q.get("id"), allow });
  window.close();
};
const allow = document.getElementById("allow");
const deny = document.getElementById("deny");
allow.textContent = t("allow");
deny.textContent = t("deny");
allow.onclick = () => answer(true);
deny.onclick = () => answer(false);
