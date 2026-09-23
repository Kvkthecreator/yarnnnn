// ADR-662 D15 / ADR-663 D4 — the questions only the member answers, drawn by
// the extension: may the agent use this SITE (mode=site), and may it use
// Chrome at all (mode=enable, asked when a yarnnn page wants it switched on).
// The page that asked cannot answer either; only a click here can.
const q = new URLSearchParams(location.search);
const host = q.get("host") || "";
const enable = q.get("mode") === "enable";
const t = (k, s) => chrome.i18n.getMessage(k, s);
document.getElementById("title").textContent = enable ? t("enableTitle") : t("consentTitle", [host]);
document.getElementById("body").textContent = enable ? t("enableBody") : t("consentBody");
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
