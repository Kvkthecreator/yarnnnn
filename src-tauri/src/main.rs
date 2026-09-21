// Prevents a console window from opening alongside the app on Windows release
// builds. ADR-661 §7.6: the shell ships macOS first but is not written against
// one platform, and this is the one line that would otherwise assume it.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

//! yarnnn desktop host — ADR-661 §8 step 4.
//!
//! What this file owns, and deliberately nothing more:
//!   - a window, with the size and chrome a desktop app has and a tab cannot;
//!   - the system-browser handoff, so an OAuth consent screen or a checkout
//!     page never navigates the app's own window (§4.3 — a member stranded in
//!     a frame with no address bar and no back button can only quit).
//!
//! What it does NOT own: anything a member sees. The product is the exported
//! web app it serves from disk, one codebase with the web build (D4). A
//! platform difference belongs here as a capability the host fills, never as a
//! branch inside a surface.
//!
//! §8's constraint, kept on purpose: this stays a HOST with a capability seam,
//! not a thin `WebView::new`. Step 6 (local hands, §5/§6) would add a command
//! here — behind a per-act permission the member grants — and that must not
//! require reopening the packaging decision.

use tauri::{WebviewUrl, WebviewWindowBuilder};

fn main() {
    tauri::Builder::default()
        // `openExternal` in the web bundle calls window.open(url, '_blank').
        // This plugin is what turns that into the member's own browser rather
        // than a second app window — the whole point of §4.3.
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let win = WebviewWindowBuilder::new(app, "main", WebviewUrl::default())
                .title("yarnnn")
                // Roomy enough for the compositor's windows (the product is a
                // desktop metaphor — ADR-297 D17), small enough for a laptop.
                .inner_size(1280.0, 860.0)
                .min_inner_size(900.0, 600.0)
                // macOS: the traffic lights sit over the app's own chrome
                // rather than a second title bar above it. The shell already
                // draws its own top bar.
                .title_bar_style(tauri::TitleBarStyle::Overlay)
                .hidden_title(true)
                .build()?;

            // A window that opens behind whatever the member was doing reads
            // as "nothing happened".
            let _ = win.set_focus();
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running yarnnn");
}
