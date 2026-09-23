// ADR-663 D4 — the app's own commands are declared here, so each one gets a
// permission (`allow-<command>`) and NOTHING reaches the website's origin
// unless `capabilities/default.json` names it. Without a manifest, Tauri's
// ACL would still refuse a remote page — this makes the roster explicit and
// readable by the gates.
fn main() {
    tauri_build::try_build(
        tauri_build::Attributes::new().app_manifest(
            tauri_build::AppManifest::new().commands(&[
                // ADR-662 D15 — local hands: the relay to the yarnnn extension.
                "hands_status",
                "browser_act",
            ]),
        ),
    )
    .expect("failed to run tauri-build");
}
