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

#[derive(Default)]
pub struct Relay {
    #[cfg(unix)]
    writer: Mutex<Option<tokio::net::unix::OwnedWriteHalf>>,
    #[cfg(not(unix))]
    writer: Mutex<Option<()>>,
    pending: Mutex<HashMap<u64, oneshot::Sender<Value>>>,
    extension_version: Mutex<Option<String>>,
    next: AtomicU64,
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
            *handle.state::<Relay>().writer.lock().await = Some(write);
            let handle = handle.clone();
            tauri::async_runtime::spawn(async move {
                let relay = handle.state::<Relay>();
                let mut lines = tokio::io::BufReader::new(read).lines();
                while let Ok(Some(line)) = lines.next_line().await {
                    let Ok(msg) = serde_json::from_str::<Value>(&line) else { continue };
                    match msg.get("type").and_then(Value::as_str) {
                        Some("hello") => {
                            *relay.extension_version.lock().await =
                                msg.get("version").and_then(Value::as_str).map(str::to_string);
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
                // The bridge went away (Chrome closed, the extension reloaded).
                *relay.writer.lock().await = None;
                *relay.extension_version.lock().await = None;
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
    let connected = relay.writer.lock().await.is_some();
    let version = relay.extension_version.lock().await.clone();
    json!({ "extension": connected, "version": version })
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
    let mut writer = relay.writer.lock().await;
    let Some(w) = writer.as_mut() else { return Err(NOT_CONNECTED) };
    if w.write_all(line.as_bytes()).await.is_err() {
        *writer = None;
        return Err("The connection to Chrome dropped before the act was sent. Nothing was done.");
    }
    Ok(())
}

#[cfg(not(unix))]
async fn send(_relay: &Relay, _line: &str) -> Result<(), &'static str> {
    Err(NOT_CONNECTED)
}
