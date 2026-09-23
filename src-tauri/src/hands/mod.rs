//! Local hands, the browser first — ADR-662 D6/D13/D14.
//!
//! The agent works in a BROWSER PANE this host owns: a second window, labelled
//! `browser`, that the member can watch while they keep using their machine.
//! Nothing here touches another app, the pointer, the keyboard, the screen or
//! the clipboard (D1, D2): every act runs inside the pane's own page, through
//! `page.js`, and reads its effect back (D3).
//!
//! The boundary, in three parts:
//!   - **The pane holds no capability.** `capabilities/default.json` names the
//!     `main` window only, so a page loaded here — any site on the internet —
//!     can ask this host for nothing.
//!   - **Only the host asks for consent** (ADR-663 D4). The website may call
//!     `hands_enable`, but the answer comes from a native dialog this host
//!     draws, and it is remembered on this machine only. `browser_act` refuses
//!     until the member said yes (`require_enabled`).
//!   - **The model never writes a script** (D13). An act is `page.js` plus one
//!     call whose arguments are JSON-encoded here (`call`).

use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde_json::{json, Value};
use tauri::{AppHandle, Manager, Runtime, WebviewUrl, WebviewWindow, WebviewWindowBuilder};
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};

/// The pane's window label. Never named in any capability.
pub const PANE: &str = "browser";

/// The page routines, ONE copy shared with the Chrome extension (ADR-662 D15).
const PAGE_JS: &str = include_str!("../../../extension/page.js");

/// How long a page may take to load before the act reports that it did not.
const LOAD_TIMEOUT: Duration = Duration::from_secs(30);
/// How long after a click or a submit a new page may take to START loading.
const NAV_GRACE: Duration = Duration::from_millis(1500);
/// How long one script may take to answer.
const EVAL_TIMEOUT: Duration = Duration::from_secs(10);
const POLL: Duration = Duration::from_millis(200);
const POLL_EVAL: Duration = Duration::from_millis(1500);

/// Whether the member switched the browser on — this machine's answer,
/// kept beside the app's other state, never in the workspace (ADR-662 D4).
pub struct Consent(pub Mutex<bool>);

fn consent_file<R: Runtime>(app: &AppHandle<R>) -> Option<PathBuf> {
    app.path().app_config_dir().ok().map(|d| d.join("hands.json"))
}

pub fn load_consent<R: Runtime>(app: &AppHandle<R>) -> bool {
    consent_file(app)
        .and_then(|p| std::fs::read_to_string(p).ok())
        .and_then(|s| serde_json::from_str::<Value>(&s).ok())
        .and_then(|v| v.get("browser").and_then(Value::as_bool))
        .unwrap_or(false)
}

fn save_consent<R: Runtime>(app: &AppHandle<R>, on: bool) {
    if let Some(path) = consent_file(app) {
        if let Some(dir) = path.parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        let _ = std::fs::write(path, json!({ "browser": on }).to_string());
    }
}

fn require_enabled<R: Runtime>(app: &AppHandle<R>) -> Result<(), Value> {
    let on = *app.state::<Consent>().0.lock().unwrap();
    if on {
        Ok(())
    } else {
        Err(json!({
            "success": false,
            "error": "browser_off",
            "receipt": "The browser is switched off in this app's settings, so nothing was done. Ask the member to switch it on in Settings → Desktop app.",
            "record": { "act": "refused", "subject": "", "changed": false },
        }))
    }
}

/// Whether the browser is on in this app. Reads only.
#[tauri::command]
pub fn hands_status<R: Runtime>(app: AppHandle<R>) -> Value {
    json!({ "browser": *app.state::<Consent>().0.lock().unwrap() })
}

/// Switch the browser on. The page may ask; the answer is the member's, in a
/// dialog this host draws (ADR-663 D4) — never a flag the page can set.
#[tauri::command]
pub async fn hands_enable<R: Runtime>(app: AppHandle<R>) -> bool {
    let allowed = app
        .dialog()
        .message(
            "Your agent will be able to open web pages in a yarnnn browser window, read them, \
             press buttons and fill in fields for you. You can watch every step, and keep \
             using your computer while it works.\n\nWhat it sees on those pages is sent to the \
             AI model you chose for the conversation. It only uses sites you are signed in to \
             inside that window.",
        )
        .title("Let your agent use a browser?")
        .kind(MessageDialogKind::Info)
        .buttons(MessageDialogButtons::OkCancelCustom(
            "Allow".into(),
            "Not now".into(),
        ))
        .blocking_show();
    *app.state::<Consent>().0.lock().unwrap() = allowed;
    save_consent(&app, allowed);
    allowed
}

/// Switch the browser off, and close the pane.
#[tauri::command]
pub fn hands_disable<R: Runtime>(app: AppHandle<R>) -> bool {
    *app.state::<Consent>().0.lock().unwrap() = false;
    save_consent(&app, false);
    if let Some(win) = app.get_webview_window(PANE) {
        let _ = win.close();
    }
    false
}

/// Perform one browser act and say what changed (ADR-662 D3).
#[tauri::command]
pub async fn browser_act<R: Runtime>(app: AppHandle<R>, tool: String, args: Value) -> Value {
    if let Err(refusal) = require_enabled(&app) {
        return refusal;
    }
    match act(&app, &tool, &args).await {
        Ok(v) => v,
        Err(why) => failure(&why, "failed", ""),
    }
}

fn failure(receipt: &str, act: &str, subject: &str) -> Value {
    json!({
        "success": false,
        "receipt": receipt,
        "record": { "act": act, "subject": subject, "changed": false },
    })
}

/// The pane, opened beside the app the first time it is needed. It opens
/// without taking focus: the member keeps working where they were (D1).
fn pane<R: Runtime>(app: &AppHandle<R>) -> Result<WebviewWindow<R>, String> {
    if let Some(win) = app.get_webview_window(PANE) {
        return Ok(win);
    }
    WebviewWindowBuilder::new(app, PANE, WebviewUrl::External("about:blank".parse().unwrap()))
        .title("yarnnn — your agent's browser")
        .inner_size(1100.0, 800.0)
        .min_inner_size(600.0, 400.0)
        .focused(false)
        .build()
        .map_err(|e| format!("The browser window could not open: {e}"))
}

/// `page.js`, then one call. Arguments are JSON values encoded HERE, so text
/// from the model reaches the page as a string, never as code.
fn call(routine: &str, args: &[Value]) -> String {
    let encoded: Vec<String> = args
        .iter()
        .map(|a| serde_json::to_string(a).unwrap_or_else(|_| "null".into()))
        .collect();
    format!("{PAGE_JS}\nwindow.__yarnnnHands.{routine}({})", encoded.join(","))
}

/// Run a routine and parse the JSON string it returns. The webview hands the
/// host the script's value JSON-encoded, so a string comes back quoted: two
/// decodes.
async fn eval<R: Runtime>(win: &WebviewWindow<R>, routine: &str, args: &[Value]) -> Result<Value, String> {
    eval_within(win, routine, args, EVAL_TIMEOUT).await
}

async fn eval_within<R: Runtime>(
    win: &WebviewWindow<R>,
    routine: &str,
    args: &[Value],
    limit: Duration,
) -> Result<Value, String> {
    let (tx, mut rx) = tauri::async_runtime::channel::<String>(1);
    win.eval_with_callback(call(routine, args), move |raw| {
        let _ = tx.try_send(raw);
    })
    .map_err(|e| format!("The page could not be reached: {e}"))?;
    let raw = tokio::time::timeout(limit, rx.recv())
        .await
        .map_err(|_| "The page did not answer in time.".to_string())?
        .ok_or_else(|| "The page did not answer.".to_string())?;
    let outer: Value = serde_json::from_str(&raw).map_err(|_| "The page answered in a shape I could not read.".to_string())?;
    match outer {
        Value::String(inner) => serde_json::from_str(&inner).map_err(|_| "The page answered in a shape I could not read.".to_string()),
        // A page that is mid-navigation answers null; the caller polls again.
        other => Ok(other),
    }
}

/// A mark unique to one act, left on the page so a NEW document is
/// recognisable by its absence.
fn nonce() -> String {
    static COUNT: AtomicU64 = AtomicU64::new(0);
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!("{now:x}-{:x}", COUNT.fetch_add(1, Ordering::Relaxed))
}

/// Wait for the page to be a NEW document (the mark we left is gone) that has
/// finished loading. `grace` bounds how long we wait for the navigation to
/// START; None means one was certainly started (open, back).
async fn settle<R: Runtime>(win: &WebviewWindow<R>, mark: &str, grace: Option<Duration>) -> Result<(bool, Value), String> {
    let started = Instant::now();
    let mut navigated = false;
    loop {
        // A document being torn down may never answer; poll briefly.
        let state = eval_within(win, "state", &[], POLL_EVAL).await.unwrap_or(Value::Null);
        let still_ours = state.get("mark").and_then(Value::as_str) == Some(mark);
        if !still_ours && !state.is_null() {
            navigated = true;
            if state.get("ready").and_then(Value::as_str) != Some("loading") {
                return Ok((true, state));
            }
        }
        if still_ours {
            if let Some(g) = grace {
                if started.elapsed() > g {
                    return Ok((false, state));
                }
            }
        }
        if started.elapsed() > LOAD_TIMEOUT {
            return if navigated {
                Ok((true, state))
            } else {
                Err("The page did not load within 30 seconds.".into())
            };
        }
        tokio::time::sleep(POLL).await;
    }
}

fn host_of(url: &str) -> String {
    url.parse::<tauri::Url>()
        .ok()
        .and_then(|u| u.host_str().map(str::to_string))
        .unwrap_or_default()
}

fn title_of(state: &Value) -> String {
    state.get("title").and_then(Value::as_str).unwrap_or("").to_string()
}

async fn act<R: Runtime>(app: &AppHandle<R>, tool: &str, args: &Value) -> Result<Value, String> {
    let win = pane(app)?;
    match tool {
        "BrowserOpen" => {
            let raw = args.get("url").and_then(Value::as_str).unwrap_or("").trim();
            let url: tauri::Url = raw.parse().map_err(|_| format!("“{raw}” is not a web address."))?;
            if url.scheme() != "http" && url.scheme() != "https" {
                return Ok(failure("Only http and https addresses can be opened.", "refused", raw));
            }
            let mark = nonce();
            let _ = eval(&win, "mark", &[json!(mark)]).await;
            win.navigate(url.clone()).map_err(|e| format!("The page could not be opened: {e}"))?;
            let (_, state) = settle(&win, &mark, None).await?;
            let title = title_of(&state);
            let host = host_of(state.get("url").and_then(Value::as_str).unwrap_or(raw));
            Ok(json!({
                "success": true,
                "title": title,
                "url": state.get("url"),
                "receipt": format!("Opened “{title}” ({host})."),
                "record": { "act": "opened", "subject": if title.is_empty() { host.clone() } else { title.clone() }, "changed": true },
            }))
        }
        "BrowserRead" => {
            let page = eval(&win, "read", &[]).await?;
            let n = page.get("elements").and_then(Value::as_array).map(|a| a.len()).unwrap_or(0);
            let title = title_of(&page);
            let mut out = page.clone();
            out["success"] = json!(true);
            out["receipt"] = json!(format!("Read “{title}” — {n} things to act on."));
            out["record"] = json!({ "act": "read", "subject": title, "changed": false });
            Ok(out)
        }
        "BrowserClick" | "BrowserFill" => {
            let reference = args.get("ref").and_then(Value::as_i64).ok_or("A ref from BrowserRead is needed.")?;
            let before = eval(&win, "state", &[]).await.unwrap_or(Value::Null);
            let mark = nonce();
            let _ = eval(&win, "mark", &[json!(mark)]).await;
            let done = if tool == "BrowserClick" {
                eval(&win, "click", &[json!(reference)]).await?
            } else {
                let text = args.get("text").and_then(Value::as_str).unwrap_or("");
                let submit = args.get("submit").and_then(Value::as_bool).unwrap_or(false);
                eval(&win, "fill", &[json!(reference), json!(text), json!(submit)]).await?
            };
            let label = done.get("label").and_then(Value::as_str).unwrap_or("").to_string();
            if done.get("error").and_then(Value::as_str) == Some("stale_ref") {
                return Ok(failure("That element is no longer on the page — read the page again for fresh refs.", "failed", ""));
            }
            if done.get("error").and_then(Value::as_str) == Some("not_a_field") {
                return Ok(failure(&format!("“{label}” is not a field that takes text."), "failed", &label));
            }
            if done.get("error").and_then(Value::as_str) == Some("no_such_option") {
                return Ok(failure(&format!("“{label}” has no option with that text."), "failed", &label));
            }
            let submitted = done.get("submitted").and_then(Value::as_bool).unwrap_or(false);
            let (navigated, after) = if tool == "BrowserClick" || submitted {
                settle(&win, &mark, Some(NAV_GRACE)).await?
            } else {
                (false, eval(&win, "state", &[]).await.unwrap_or(Value::Null))
            };
            let changed = navigated || before.get("sig") != after.get("sig");
            let title = title_of(&after);
            if tool == "BrowserClick" {
                let receipt = if navigated {
                    format!("Pressed “{label}” — now on “{title}”.")
                } else if changed {
                    format!("Pressed “{label}” — the page changed.")
                } else {
                    format!("Pressed “{label}” — no change observed.")
                };
                Ok(json!({
                    "success": true, "changed": changed, "title": title, "url": after.get("url"),
                    "receipt": receipt,
                    "record": { "act": "pressed", "subject": label, "changed": changed },
                }))
            } else {
                let matches = done.get("matches").and_then(Value::as_bool).unwrap_or(false);
                let mut receipt = if matches {
                    format!("Filled “{label}”; its value reads back as entered.")
                } else {
                    format!("Tried to fill “{label}”, but its value did not read back as entered — no change observed.")
                };
                if submitted {
                    receipt.push_str(&if navigated { format!(" Sent the form — now on “{title}”.") } else { " Sent the form.".to_string() });
                }
                Ok(json!({
                    "success": matches, "changed": matches || navigated, "title": title, "url": after.get("url"),
                    "receipt": receipt,
                    "record": { "act": "filled", "subject": label, "changed": matches },
                }))
            }
        }
        "BrowserBack" => {
            let mark = nonce();
            let _ = eval(&win, "mark", &[json!(mark)]).await;
            let _ = eval(&win, "back", &[]).await;
            let (navigated, state) = settle(&win, &mark, Some(NAV_GRACE)).await?;
            let title = title_of(&state);
            Ok(json!({
                "success": navigated,
                "receipt": if navigated { format!("Went back to “{title}”.") } else { "There was no earlier page to go back to — no change observed.".into() },
                "record": { "act": "back", "subject": title, "changed": navigated },
            }))
        }
        other => Ok(failure(&format!("{other} is not a browser act this app performs."), "refused", "")),
    }
}
