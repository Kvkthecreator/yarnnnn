/**
 * Behavioural replay — the stale-pin heal reloads exactly once (ADR-499 + the
 * 2026-07-29 workspace-binding audit).
 *
 * WHY A REPLAY AND NOT A GREP. A text gate can prove the word "reload" appears
 * in `client.ts`; it cannot prove the reload FIRES, fires ONCE across a fan-out
 * of parallel calls, or fires AFTER the healed retry resolves. Those are the
 * three things that can actually be wrong, so they get executed.
 *
 * The heal logic is re-stated here rather than imported (client.ts is a browser
 * module with Supabase + Next imports). That is a real limitation: this asserts
 * the ALGORITHM is right, not that client.ts contains this exact algorithm —
 * the companion text gate covers the wiring. Keep the two in sync.
 *
 * Run: node scripts/verify-heal-reload.mjs
 */

let failures = 0;
const ok = (cond, msg) => {
  console.log(`  ${cond ? "✓" : "✗"} ${msg}`);
  if (!cond) failures += 1;
};

// --- the harness: a fake browser + API -------------------------------------

function makeWorld({ pinnedWorkspaceRevoked }) {
  const world = {
    pin: "revoked-workspace-id",
    reloads: 0,
    requests: [],
    reloadScheduled: false,
    timers: [],
  };
  world.setTimeout = (fn, ms) => world.timers.push({ fn, ms });
  world.flushTimers = () => {
    const t = world.timers.sort((a, b) => a.ms - b.ms);
    world.timers = [];
    t.forEach(({ fn }) => fn());
  };

  // The server: 403s a revoked pin fail-closed; succeeds with no pin.
  world.serverCall = (sentPin) => {
    world.requests.push(sentPin);
    if (sentPin && pinnedWorkspaceRevoked) {
      return { ok: false, status: 403, detail: `No active grant into workspace ${sentPin}` };
    }
    return { ok: true, status: 200 };
  };

  // The request() heal path, transcribed from lib/api/client.ts.
  world.request = async (retried = false) => {
    const res = world.serverCall(world.pin);
    if (!res.ok) {
      const stale =
        res.status === 403 &&
        typeof res.detail === "string" &&
        res.detail.startsWith("No active grant into workspace") &&
        !!world.pin;
      if (stale && !retried) {
        world.pin = null; // clearActiveWorkspace()
        const healed = world.request(true);
        if (!world.reloadScheduled) {
          world.reloadScheduled = true;
          void healed.finally(() =>
            world.setTimeout(() => {
              world.reloads += 1;
            }, 150),
          );
        }
        return healed;
      }
      throw new Error(`APIError ${res.status}`);
    }
    return res;
  };
  return world;
}

// --- the cases --------------------------------------------------------------

async function testHealsAndReloadsOnce() {
  console.log("\nA revoked pin heals, then reloads exactly once");
  const w = makeWorld({ pinnedWorkspaceRevoked: true });
  const res = await w.request();
  ok(res.ok, "the call that triggered the heal still RESOLVES (caller sees success)");
  ok(w.pin === null, "the stale pin is cleared");
  ok(w.requests.length === 2, `heals in exactly 2 calls (got ${w.requests.length})`);
  ok(w.requests[1] === null, "the retry goes out with NO pin");
  ok(w.reloads === 0, "the reload has NOT fired before timers run (retry resolves first)");
  w.flushTimers();
  ok(w.reloads === 1, `reloads exactly once (got ${w.reloads})`);
}

async function testParallelFanOutReloadsOnce() {
  console.log("\nA page-load fan-out reloads ONCE, not N times");
  const w = makeWorld({ pinnedWorkspaceRevoked: true });
  // 8 parallel calls, exactly what a page load does — every one 403s + heals.
  await Promise.all(Array.from({ length: 8 }, () => w.request()));
  w.flushTimers();
  ok(w.reloads === 1, `8 parallel heals → 1 reload (got ${w.reloads})`);
}

async function testHealthyPinNeverReloads() {
  console.log("\nA VALID pin is left alone");
  const w = makeWorld({ pinnedWorkspaceRevoked: false });
  const res = await w.request();
  w.flushTimers();
  ok(res.ok, "the call succeeds first try");
  ok(w.requests.length === 1, "no retry");
  ok(w.pin === "revoked-workspace-id", "the pin is NOT cleared");
  ok(w.reloads === 0, "no reload — a working session is never interrupted");
}

async function testOrdinary403NeverReloads() {
  console.log("\nAn ordinary 403 (owner-only verb) still throws");
  const w = makeWorld({ pinnedWorkspaceRevoked: true });
  w.serverCall = (sentPin) => {
    w.requests.push(sentPin);
    return { ok: false, status: 403, detail: "Only the owner may clear this workspace" };
  };
  let threw = false;
  try {
    await w.request();
  } catch {
    threw = true;
  }
  w.flushTimers();
  ok(threw, "it surfaces to the caller");
  ok(w.pin === "revoked-workspace-id", "the pin is NOT cleared");
  ok(w.reloads === 0, "no reload — this is not a binding problem");
}

const run = async () => {
  console.log("Stale-pin heal — behavioural replay");
  console.log("=".repeat(60));
  await testHealsAndReloadsOnce();
  await testParallelFanOutReloadsOnce();
  await testHealthyPinNeverReloads();
  await testOrdinary403NeverReloads();
  console.log("\n" + "=".repeat(60));
  if (failures) {
    console.log(`FAIL: ${failures} check(s)`);
    process.exit(1);
  }
  console.log("PASS");
};

run();
