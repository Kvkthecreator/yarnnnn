// The member's switch and site lists — this machine's answers (ADR-662 D15).
const t = (k) => chrome.i18n.getMessage(k);
for (const id of ["allowedTitle:allowedSites", "deniedTitle:deniedSites", "neverTitle:neverTitle", "neverBody:neverBody"]) {
  const [el, key] = id.split(":");
  document.getElementById(el).textContent = t(key);
}
async function render() {
  const s = await chrome.storage.local.get({ enabled: true, allowed: [], denied: [] });
  document.getElementById("state").textContent = t(s.enabled ? "popupOn" : "popupOff");
  const toggle = document.getElementById("toggle");
  toggle.textContent = t(s.enabled ? "turnOff" : "turnOn");
  toggle.onclick = async () => {
    await chrome.storage.local.set({ enabled: !s.enabled });
    render();
  };
  for (const list of ["allowed", "denied"]) {
    const ul = document.getElementById(list);
    ul.textContent = "";
    if (!s[list].length) {
      const li = document.createElement("li");
      li.className = "muted";
      li.textContent = t("none");
      ul.append(li);
    }
    for (const host of s[list]) {
      const li = document.createElement("li");
      const name = document.createElement("span");
      name.textContent = host;
      const rm = document.createElement("button");
      rm.textContent = t("remove");
      rm.onclick = async () => {
        await chrome.storage.local.set({ [list]: s[list].filter((h) => h !== host) });
        render();
      };
      li.append(name, rm);
      ul.append(li);
    }
  }
}
render();
