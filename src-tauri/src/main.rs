// Prevents a console window from opening alongside the app on Windows release
// builds. ADR-661 §7o: one host, built for macOS and Windows; a platform
// difference lives behind a `cfg` here, never as a branch in the web layer.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

//! yarnnn desktop host — ADR-661 §8 step 4, ADR-663.
//! Reference: docs/architecture/desktop-app.md (how the desktop app works now).
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
//! What it does NOT own: anything a member sees. The product is the WEBSITE,
//! loaded into this window (ADR-663 D1) — the installer carries this host and
//! one local page, `bootstrap/index.html`, that opens the website or says it is
//! offline. So the host is the only versioned thing (`Cargo.toml`, ADR-663 D2).
//! A platform difference belongs here as a capability the host fills, never as
//! a branch inside a surface.
//!
//! ⚠️ ADR-663 D4: the page is whatever the website serves NOW. What it may ask
//! of this host is `capabilities/default.json`'s remote roster, and nothing
//! that acts on the member's machine may be added there unless this host
//! itself draws the consent prompt the member answers.
//!
//! §8's constraint, kept on purpose: this stays a HOST with a capability seam,
//! not a thin `WebView::new`. Local hands (ADR-662 D15) live in `hands/`: the
//! app relays the agent's browser acts to the yarnnn Chrome extension, which
//! performs them in the member's own Chrome and draws its own consent. The page
//! reaches the relay only through the commands `build.rs` declares.

mod hands;

use tauri::{Emitter, Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_deep_link::DeepLinkExt;

/// Where the interface comes from (ADR-663 D1). A debug build opens the local
/// dev server, so `cargo tauri dev` runs against `pnpm dev`.
#[cfg(not(debug_assertions))]
const APP_URL: &str = "https://www.yarnnn.com/desktop";
#[cfg(debug_assertions)]
const APP_URL: &str = "http://localhost:3000/desktop";

fn main() {
    // ADR-662 D15 — Chrome launched us as the extension's native-messaging
    // host: relay, and never start the app (no window, no single-instance).
    #[cfg(unix)]
    if hands::bridge::requested() {
        hands::bridge::run();
    }

    tauri::Builder::default()
        // ADR-661 §7o — ONE running app. On Windows a `yarnnn://` link does
        // not reach the running app: the OS starts a SECOND copy with the URL
        // as its argument, and the copy that opened the browser waits for a
        // hand-off that went elsewhere. This plugin forwards the second
        // launch's arguments to the first and exits it; its `deep-link`
        // feature turns them into the same `on_open_url` event macOS delivers
        // natively. It must be registered FIRST, before any plugin that could
        // act on the duplicate launch.
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.unminimize();
                let _ = win.set_focus();
            }
        }))
        // `openExternal` in the web bundle calls window.open(url, '_blank').
        // This plugin is what turns that into the member's own browser rather
        // than a second app window — the whole point of §4.3.
        .plugin(tauri_plugin_opener::init())
        // The return leg of §4.3's handoff. The OS delivers a `yarnnn://` URL
        // to the running app (macOS natively, Windows via the single-instance
        // plugin above); we forward it to the web layer as an event
        // rather than navigating the window, because the session it carries
        // has to be handed to the Supabase client, not to the router.
        .plugin(tauri_plugin_deep_link::init())
        .invoke_handler(tauri::generate_handler![
            hands::hands_status,
            hands::browser_act,
            hands::hands_set_enabled,
        ])
        .manage(hands::Relay::default())
        .setup(|app| {
            // ADR-662 D15 — let Chrome find this app, and listen for the bridge.
            hands::register_with_browsers();
            hands::listen(app.handle());

            // A debug build's page comes from the dev server, which the release
            // roster does not name. Grant it the SAME roster, re-pointed — never
            // a second list, which is how two rosters drift apart.
            #[cfg(debug_assertions)]
            {
                let mut dev: serde_json::Value =
                    serde_json::from_str(include_str!("../capabilities/default.json"))?;
                dev["identifier"] = "dev-server".into();
                dev["remote"]["urls"] = serde_json::json!(["http://localhost:3000/*"]);
                app.add_capability(dev.to_string())?;
            }

            // The window opens the bundled bootstrap, which opens APP_URL once
            // the website answers — or says the app is offline (ADR-663 D1).
            let builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::default())
                .initialization_script(&format!("window.__YARNNN_APP_URL__ = {:?};", APP_URL))
                .title("yarnnn")
                // Roomy enough for the compositor's windows (the product is a
                // desktop metaphor — ADR-297 D17), small enough for a laptop.
                .inner_size(1280.0, 860.0)
                .min_inner_size(900.0, 600.0);

            // ADR-661 §7n — macOS: the traffic lights sit over the app's own
            // chrome rather than in a second title bar above it, so the host
            // does what only it can: overlay the title bar, centre the lights
            // on the app's 56px top bar, and tell the page they are there. The
            // page never detects a platform (§7.6); it reserves
            // `--titlebar-inset` when the host says the title bar is overlaid.
            // The attribute is set before any page script runs, so the first
            // paint is already inset. Without this the lights sat on the
            // wordmark's corner.
            //
            // All of it is macOS-only, and so is Tauri's API for it — these
            // builder methods do not EXIST on Windows, so outside this block
            // the host fails to compile there (§7o). Windows keeps its native
            // frame: the title bar sits above the app's top bar, and the page
            // is never marked, so the inset stays 0.
            #[cfg(target_os = "macos")]
            let builder = builder
                .title_bar_style(tauri::TitleBarStyle::Overlay)
                .hidden_title(true)
                .traffic_light_position(tauri::LogicalPosition::new(18.0, 30.0))
                .initialization_script(
                    r#"(function () {
  var mark = function () {
    var root = document.documentElement;
    if (!root) return false;
    root.setAttribute("data-titlebar", "overlay");
    return true;
  };
  if (!mark()) {
    new MutationObserver(function (_, obs) {
      if (mark()) obs.disconnect();
    }).observe(document, { childList: true });
  }
})();"#,
                );

            let win = builder.build()?;

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
