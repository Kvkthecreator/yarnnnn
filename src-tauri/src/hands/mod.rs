//! Local hands in the desktop app — ADR-662 D15.
//!
//! The browser tools are performed by the yarnnn **Chrome extension**, in the
//! member's own Chrome, with their sign-ins (`extension/`). The desktop app does
//! not act on any page itself: `browser_act` hands the act to the extension and
//! returns its answer. The extension draws the per-site consent (ADR-663 D4 —
//! the executor asks the member, the page never can), so the host holds no
//! switch, no window and no page routine of its own.
//!
//! How the two meet — Chrome's native messaging:
//!   1. At startup the app registers itself as the native-messaging host
//!      `com.yarnnn.desktop` with every Chromium browser it finds
//!      (`register_with_browsers`), allowing only the yarnnn extension.
//!   2. The extension connects; Chrome launches THIS binary in bridge mode
//!      (`bridge.rs`), which relays between Chrome's stdio and a private socket.
//!   3. The running app listens on that socket (`listen`): one bridge at a
//!      time, owner-only permissions. An act is one JSON line out, its result
//!      one JSON line back, matched by id.
//!
//! Nothing here touches the pointer, the keyboard, the screen or the clipboard.
//! Windows is owed: its native messaging is a registry key and a named pipe;
//! until then `browser_act` there says the desktop app cannot reach Chrome.

#[cfg(unix)]
pub mod bridge;

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

use serde_json::{json, Value};
use tauri::{AppHandle, Manager, Runtime};
use tokio::sync::{oneshot, Mutex};

/// The native-messaging host name the extension connects to.
pub const HOST_NAME: &str = "com.yarnnn.desktop";
/// The only extension allowed to connect (its id is fixed by its manifest key).
pub const EXTENSION_ORIGIN: &str = "chrome-extension://flkcmnbfjjkglgaakihlcdfocecfaccb/";
/// One act's bound — the extension's consent question (up to 120 s) plus a
/// page load. The server fails the act closed at the same bound.
const ACT_TIMEOUT: Duration = Duration::from_secs(150);

/// The private socket between the bridge and the app. Both compute it from
/// HOME alone, because the bridge runs without Tauri.
pub fn socket_path() -> PathBuf {
    let home = std::env::var_os("HOME").map(PathBuf::from).unwrap_or_default();
    #[cfg(target_os = "macos")]
    let base = home.join("Library/Application Support/com.yarnnn.desktop");
    #[cfg(not(target_os = "macos"))]
    let base = home.join(".config/com.yarnnn.desktop");
    base.join("hands.sock")
}

#[cfg(unix)]
type Writer = tokio::net::unix::OwnedWriteHalf;
#[cfg(not(unix))]
type Writer = ();

/// The one bridge connection, and which one it is. Every accepted connection
/// gets a new `id`; a connection that ends clears the link ONLY if the link is
/// still its own. Without the id, a connection that closed after a newer one
/// attached wiped the newer one — the app then said "not connected" with the
/// bridge attached (reproduced 2026-09-23: a transient client came and went,
/// and the operator's turns got no browser).
struct Link<W> {
    id: u64,
    writer: Option<W>,
    version: Option<String>,
}

pub struct Relay {
    link: Mutex<Link<Writer>>,
    pending: Mutex<HashMap<u64, oneshot::Sender<Value>>>,
    next: AtomicU64,
}

impl Default for Relay {
    fn default() -> Self {
        Relay {
            link: Mutex::new(Link { id: 0, writer: None, version: None }),
            pending: Mutex::new(HashMap::new()),
            next: AtomicU64::new(0),
        }
    }
}

impl<W> Link<W> {
    /// A new connection becomes the link; the one it replaces is dropped
    /// (its writer's shutdown tells that bridge to reconnect). Returns its id.
    fn attach(&mut self, writer: W) -> u64 {
        self.id += 1;
        self.writer = Some(writer);
        self.version = None;
        self.id
    }

    /// A connection ended: clear the link only if it is still this one.
    fn detach(&mut self, id: u64) {
        if self.id == id {
            self.writer = None;
            self.version = None;
        }
    }

    fn hello(&mut self, id: u64, version: Option<String>) {
        if self.id == id {
            self.version = version;
        }
    }
}

/// Where each Chromium browser looks for native-messaging hosts (macOS).
#[cfg(target_os = "macos")]
fn host_dirs() -> Vec<PathBuf> {
    let home = std::env::var_os("HOME").map(PathBuf::from).unwrap_or_default();
    let support = home.join("Library/Application Support");
    [
        "Google/Chrome",
        "Google/Chrome Beta",
        "Google/Chrome Canary",
        "Chromium",
        "Microsoft Edge",
        "BraveSoftware/Brave-Browser",
        "Arc/User Data",
    ]
    .iter()
    .map(|b| support.join(b))
    .filter(|b| b.exists())
    .map(|b| b.join("NativeMessagingHosts"))
    .collect()
}

#[cfg(not(target_os = "macos"))]
fn host_dirs() -> Vec<PathBuf> {
    Vec::new()
}

/// Tell every installed Chromium browser that this binary is the yarnnn
/// native-messaging host, reachable by the yarnnn extension only. Rewritten at
/// every start, so a moved or updated app keeps pointing at itself.
pub fn register_with_browsers() {
    let Ok(exe) = std::env::current_exe() else { return };
    let manifest = json!({
        "name": HOST_NAME,
        "description": "yarnnn desktop app — relays the agent's browser acts to the yarnnn extension",
        "path": exe,
        "type": "stdio",
        "allowed_origins": [EXTENSION_ORIGIN],
    })
    .to_string();
    for dir in host_dirs() {
        let _ = std::fs::create_dir_all(&dir);
        let _ = std::fs::write(dir.join(format!("{HOST_NAME}.json")), &manifest);
    }
}

/// Listen for the bridge. One at a time: a new one replaces the old.
#[cfg(unix)]
pub fn listen<R: Runtime>(app: &AppHandle<R>) {
    use std::os::unix::fs::PermissionsExt;
    use tokio::io::AsyncBufReadExt;

    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        let path = socket_path();
        if let Some(dir) = path.parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        let _ = std::fs::remove_file(&path);
        let Ok(listener) = tokio::net::UnixListener::bind(&path) else { return };
        // Owner-only: another account on this machine cannot pose as the bridge.
        let _ = std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600));
        loop {
            let Ok((stream, _)) = listener.accept().await else { continue };
            let (read, write) = stream.into_split();
            let id = handle.state::<Relay>().link.lock().await.attach(write);
            let handle = handle.clone();
            tauri::async_runtime::spawn(async move {
                let relay = handle.state::<Relay>();
                let mut lines = tokio::io::BufReader::new(read).lines();
                while let Ok(Some(line)) = lines.next_line().await {
                    let Ok(msg) = serde_json::from_str::<Value>(&line) else { continue };
                    match msg.get("type").and_then(Value::as_str) {
                        Some("hello") => {
                            let version = msg.get("version").and_then(Value::as_str).map(str::to_string);
                            relay.link.lock().await.hello(id, version);
                        }
                        Some("result") => {
                            let id = msg.get("id").and_then(Value::as_u64).unwrap_or(0);
                            if let Some(tx) = relay.pending.lock().await.remove(&id) {
                                let _ = tx.send(msg.get("result").cloned().unwrap_or(Value::Null));
                            }
                        }
                        _ => {}
                    }
                }
                // This connection went away (Chrome closed, the extension
                // reloaded, or a newer connection replaced it) — clear the link
                // only if it is still this one.
                relay.link.lock().await.detach(id);
            });
        }
    });
}

#[cfg(not(unix))]
pub fn listen<R: Runtime>(_app: &AppHandle<R>) {}

fn refusal(receipt: &str) -> Value {
    json!({
        "success": false,
        "receipt": receipt,
        "record": { "act": "refused", "subject": "", "changed": false },
    })
}

/// Whether the yarnnn extension in Chrome is connected to this app. Reads only.
#[tauri::command]
pub async fn hands_status<R: Runtime>(app: AppHandle<R>) -> Value {
    let relay = app.state::<Relay>();
    let link = relay.link.lock().await;
    json!({ "extension": link.writer.is_some(), "version": link.version })
}

/// Hand one act to the yarnnn extension and return what it answered.
#[tauri::command]
pub async fn browser_act<R: Runtime>(app: AppHandle<R>, tool: String, args: Value) -> Value {
    let relay = app.state::<Relay>();
    let id = relay.next.fetch_add(1, Ordering::Relaxed) + 1;
    let (tx, rx) = oneshot::channel();
    relay.pending.lock().await.insert(id, tx);
    let line = json!({ "type": "act", "id": id, "tool": tool, "args": args }).to_string() + "\n";
    if let Err(why) = send(&relay, &line).await {
        relay.pending.lock().await.remove(&id);
        return refusal(why);
    }
    match tokio::time::timeout(ACT_TIMEOUT, rx).await {
        Ok(Ok(result)) => result,
        _ => {
            relay.pending.lock().await.remove(&id);
            refusal("Chrome did not answer in time — nothing is known to have changed.")
        }
    }
}

const NOT_CONNECTED: &str = "The desktop app cannot reach Chrome: the yarnnn extension is not connected. \
     Nothing was done. Ask the member to add the yarnnn extension to Chrome (Settings → Desktop app) and keep Chrome open.";

#[cfg(unix)]
async fn send(relay: &Relay, line: &str) -> Result<(), &'static str> {
    use tokio::io::AsyncWriteExt;
    let mut link = relay.link.lock().await;
    let id = link.id;
    let Some(w) = link.writer.as_mut() else { return Err(NOT_CONNECTED) };
    if w.write_all(line.as_bytes()).await.is_err() {
        link.detach(id);
        return Err("The connection to Chrome dropped before the act was sent. Nothing was done.");
    }
    Ok(())
}

#[cfg(not(unix))]
async fn send(_relay: &Relay, _line: &str) -> Result<(), &'static str> {
    Err(NOT_CONNECTED)
}

#[cfg(test)]
mod tests {
    use super::Link;

    fn link() -> Link<&'static str> {
        Link { id: 0, writer: None, version: None }
    }

    #[test]
    fn a_connection_that_ends_clears_only_itself() {
        let mut l = link();
        let old = l.attach("old");
        let new = l.attach("new");
        l.detach(old); // the old one closes AFTER the new one attached
        assert_eq!(l.writer, Some("new"), "the newer connection must survive");
        l.detach(new);
        assert_eq!(l.writer, None);
    }

    #[test]
    fn a_hello_counts_only_from_the_current_connection() {
        let mut l = link();
        let old = l.attach("old");
        let new = l.attach("new");
        l.hello(old, Some("stale".into()));
        assert_eq!(l.version, None);
        l.hello(new, Some("0.1.0".into()));
        assert_eq!(l.version.as_deref(), Some("0.1.0"));
    }
}
