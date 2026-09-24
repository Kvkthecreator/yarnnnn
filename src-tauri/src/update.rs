//! The host keeps itself current — ADR-663 D6.
//!
//! The interface is the website and is always current (D1); the HOST is the
//! installed thing that ages. This module is the whole of its updater, and it
//! runs in the host, never on the page's say-so:
//!
//!   - **check** at launch (after the window is up) and every six hours, against
//!     `plugins.updater.endpoints` in `tauri.conf.json` — our own
//!     `www.yarnnn.com/download/latest.json`, which `scripts/publish-desktop-release.sh`
//!     writes last, after the files it names;
//!   - **download** in the background. Tauri's updater verifies the bytes against
//!     the public key compiled into this host (`plugins.updater.pubkey`) — a
//!     manifest or file that was not signed with the operator's key is refused,
//!     whoever serves it;
//!   - **install at quit** (`install_on_exit`) — the Claude desktop / VS Code
//!     convention: the member is never interrupted, and the next launch is new;
//!   - or **now**, when the member presses *Restart to update* in the page's
//!     `UpdateNotice` (`update_restart`).
//!
//! ADR-663 D4: the page is whatever the website serves, so what it may ask here
//! is bounded. It can learn that an update is ready (`update_ready`) and choose
//! WHEN it installs (`update_restart`) — never WHAT: the file is the one this
//! host downloaded and verified. A compromised page can at worst restart the app
//! a little early into the same signed update.

use std::sync::Mutex;
use std::time::Duration;

use tauri::{AppHandle, Emitter, Manager, State};
use tauri_plugin_updater::{Update, UpdaterExt};

/// Long enough that the window and the website are up before any network work.
const FIRST_CHECK: Duration = Duration::from_secs(20);
const EVERY: Duration = Duration::from_secs(6 * 60 * 60);

/// The event the page's `UpdateNotice` listens for (`web/lib/shell/host.ts`).
const READY_EVENT: &str = "update-ready";

/// A downloaded, verified update waiting to be installed.
#[derive(Default)]
pub struct Pending(Mutex<Option<(Update, Vec<u8>)>>);

/// Start the check loop. Release builds only: a debug host runs against the dev
/// server and must not pull a published build over itself.
pub fn start(app: &AppHandle) {
    if cfg!(debug_assertions) {
        return;
    }
    let app = app.clone();
    tauri::async_runtime::spawn(async move {
        tokio::time::sleep(FIRST_CHECK).await;
        loop {
            if let Err(e) = check(&app).await {
                // Offline, or nothing published yet: try again next round.
                eprintln!("[update] check failed: {e}");
            }
            tokio::time::sleep(EVERY).await;
        }
    });
}

async fn check(app: &AppHandle) -> tauri_plugin_updater::Result<()> {
    // One update at a time: a newer one is picked up after this one installs.
    if app.state::<Pending>().0.lock().unwrap().is_some() {
        return Ok(());
    }
    let Some(update) = app.updater()?.check().await? else {
        return Ok(());
    };
    let bytes = update.download(|_, _| {}, || {}).await?;
    let version = update.version.clone();
    *app.state::<Pending>().0.lock().unwrap() = Some((update, bytes));
    // App-wide, like `deep-link`: the page listens with `listen()`.
    let _ = app.emit(READY_EVENT, version);
    Ok(())
}

/// The version downloaded and waiting, if any — asked by the page on mount,
/// since the event may have fired before the website loaded.
#[tauri::command]
pub fn update_ready(pending: State<'_, Pending>) -> Option<String> {
    pending.0.lock().unwrap().as_ref().map(|(u, _)| u.version.clone())
}

/// *Restart to update*: install the waiting update now and relaunch into it.
/// On Windows the installer closes this process and reopens the app itself.
#[tauri::command]
pub fn update_restart(app: AppHandle, pending: State<'_, Pending>) -> Result<(), String> {
    let Some((update, bytes)) = pending.0.lock().unwrap().take() else {
        return Err("no update is waiting".into());
    };
    update.install(bytes).map_err(|e| e.to_string())?;
    app.restart();
}

/// The member quit with an update waiting: install it on the way out, and do
/// NOT reopen the app they just closed.
pub fn install_on_exit(app: &AppHandle) {
    let Some((update, bytes)) = app.state::<Pending>().0.lock().unwrap().take() else {
        return;
    };
    if let Err(e) = update.restart_after_install(false).install(bytes) {
        eprintln!("[update] install at quit failed: {e}");
    }
}
