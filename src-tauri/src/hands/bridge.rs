//! The native-messaging bridge — ADR-662 D15.
//!
//! Chrome starts this binary with the extension's origin as its first argument
//! when the yarnnn extension calls `chrome.runtime.connectNative`. It never
//! opens a window: `main` routes here before Tauri starts. It relays, and does
//! nothing else:
//!   - Chrome → app: native messages on stdin (a 4-byte little-endian length,
//!     then JSON) become JSON lines on the app's socket;
//!   - app → Chrome: JSON lines from the socket become native messages on stdout.
//!
//! The app may not be running, or may restart: the bridge keeps trying the
//! socket every two seconds, and exits when Chrome closes stdin (the extension
//! disconnected, or Chrome quit). Messages from Chrome while the app is away
//! are dropped — an act only ever comes FROM the app, so nothing is lost.

use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::net::UnixStream;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use super::{socket_path, EXTENSION_ORIGIN};

/// True when Chrome launched this process as a native-messaging host.
pub fn requested() -> bool {
    std::env::args().nth(1).map_or(false, |a| a.starts_with("chrome-extension://"))
}

fn read_native(stdin: &mut impl Read) -> Option<Vec<u8>> {
    let mut len = [0u8; 4];
    stdin.read_exact(&mut len).ok()?;
    let mut buf = vec![0u8; u32::from_le_bytes(len) as usize];
    stdin.read_exact(&mut buf).ok()?;
    Some(buf)
}

fn write_native(stdout: &mut impl Write, msg: &[u8]) -> std::io::Result<()> {
    stdout.write_all(&(msg.len() as u32).to_le_bytes())?;
    stdout.write_all(msg)?;
    stdout.flush()
}

pub fn run() -> ! {
    // Only the yarnnn extension may drive the bridge; Chrome enforces the
    // manifest's `allowed_origins`, and this refuses anything else anyway.
    if std::env::args().nth(1).as_deref() != Some(EXTENSION_ORIGIN) {
        std::process::exit(1);
    }
    let app: Arc<Mutex<Option<UnixStream>>> = Arc::new(Mutex::new(None));

    // app → Chrome: (re)connect to the app and pump its lines out.
    let to_chrome = Arc::clone(&app);
    thread::spawn(move || loop {
        match UnixStream::connect(socket_path()) {
            Ok(stream) => {
                let reader = stream.try_clone().expect("socket clone");
                *to_chrome.lock().unwrap() = Some(stream);
                let mut stdout = std::io::stdout();
                // Tell the extension the app is here, so it says hello again.
                let _ = write_native(&mut stdout, br#"{"type":"app"}"#);
                for line in BufReader::new(reader).lines() {
                    let Ok(line) = line else { break };
                    if write_native(&mut stdout, line.as_bytes()).is_err() {
                        std::process::exit(0);
                    }
                }
                *to_chrome.lock().unwrap() = None;
            }
            Err(_) => thread::sleep(Duration::from_secs(2)),
        }
    });

    // Chrome → app, on this thread: exit when Chrome lets go.
    let mut stdin = std::io::stdin();
    while let Some(msg) = read_native(&mut stdin) {
        if let Some(stream) = app.lock().unwrap().as_mut() {
            let _ = stream.write_all(&msg).and_then(|_| stream.write_all(b"\n"));
        }
    }
    std::process::exit(0);
}
