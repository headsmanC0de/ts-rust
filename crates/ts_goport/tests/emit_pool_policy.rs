//! Exercise the real pool admission policy in fresh processes: its env is read once.
use std::process::Command;

use ts_goport::core::enter_program;
use ts_goport::options::Tristate;
use ts_goport::program::{available_cores, emit_pool_enabled, release_program, try_load_version};

const CASE: &str = "EMIT_POOL_POLICY_CASE";
const CONFIG: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/tests/fixtures/emit_pool/tsconfig.json"
);

#[test]
fn emit_pool_policy_respects_process_capabilities() {
    if let Ok(case) = std::env::var(CASE) {
        let program = try_load_version(CONFIG, |options| {
            if case == "single-threaded" {
                options.single_threaded = Tristate::True;
            }
        })
        .expect("load the existing emit fixture");
        {
            let _scope = enter_program(Some(program));
            let high_core = case == "default-high-core" || case == "explicit-zero";
            assert_eq!(available_cores(), if high_core { 8 } else { 1 });
            let enabled = emit_pool_enabled();
            println!(
                "emit-pool-policy case={case} cores={} enabled={enabled}",
                available_cores()
            );
            assert_eq!(
                enabled,
                case == "positive-override" || case == "default-high-core"
            );
        }
        release_program(program);
        return;
    }
    for (case, cores, override_value) in [
        ("default-low-core", "1", None),
        ("default-high-core", "8", None),
        ("positive-override", "1", Some("1")),
        ("explicit-zero", "8", Some("0")),
        ("single-threaded", "1", Some("1")),
    ] {
        let mut child = Command::new(std::env::current_exe().expect("current test executable"));
        child
            .env_clear()
            .env(CASE, case)
            .env("GOMAXPROCS", cores)
            .args([
                "--exact",
                "emit_pool_policy_respects_process_capabilities",
                "--nocapture",
            ]);
        #[cfg(windows)]
        if let Some(system_root) = std::env::var_os("SystemRoot") {
            child.env("SystemRoot", system_root);
        }
        if let Some(value) = override_value {
            child.env("GOPORT_EMIT_THREADS", value);
        }
        let status = child.status().expect("start isolated policy process");
        assert!(status.success(), "pool policy case {case}: {status}");
    }
}
