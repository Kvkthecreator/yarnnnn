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
//!     a frame with no address bar and no back button can only quit);
//!   - the way BACK from that browser: a `yarnnn://` deep link. Without it the
//!     handoff is one-way — the member signs in, the browser holds the session,
//!     and the app never hears about it.
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

use tauri::{Emitter, Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_deep_link::DeepLinkExt;

fn main() {
    tauri::Builder::default()
        // `openExternal` in the web bundle calls window.open(url, '_blank').
        // This plugin is what turns that into the member's own browser rather
        // than a second app window — the whole point of §4.3.
        .plugin(tauri_plugin_opener::init())
        // The return leg of §4.3's handoff. macOS delivers a `yarnnn://` URL
        // to the running app; we forward it to the web layer as an event
        // rather than navigating the window, because the session it carries
        // has to be handed to the Supabase client, not to the router.
        .plugin(tauri_plugin_deep_link::init())
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

            // A deep link can arrive at any time: while the app is running
            // (the member just finished signing in), or as the reason it was
            // launched. Both paths end in the same event, so the web layer has
            // one handler.
            let handle = app.handle().clone();
            app.deep_link().on_open_url(move |event| {
                for url in event.urls() {
                    // Bring the app forward — the member is looking at their
                    // browser, and the act they started finishes here.
                    if let Some(win) = handle.get_webview_window("main") {
                        let _ = win.set_focus();
                    }
                    // Emit APP-WIDE, not to the window. `win.emit` delivers to
                    // that window's own scope; the web layer subscribes with
                    // `listen()`, which is app-scoped, so the two never met —
                    // the host logged the URL and the page never heard it.
                    // Found by instrumenting the host after the link arrived
                    // but nothing navigated.
                    let _ = handle.emit("deep-link", url.to_string());
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running yarnnn");
}
