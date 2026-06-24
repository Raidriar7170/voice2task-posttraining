#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice2task.copy_shadow_scope_policy_design import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROPOSED_POLICY_PATH,
    EXPECTED_CHALLENGE_HASH,
    EXPECTED_POLICY_HASH,
    write_copy_shadow_scope_policy_design_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--proposed-policy-path", type=Path, default=DEFAULT_PROPOSED_POLICY_PATH)
    parser.add_argument("--expected-challenge-hash", default=EXPECTED_CHALLENGE_HASH)
    parser.add_argument("--expected-policy-hash", default=EXPECTED_POLICY_HASH)
    args = parser.parse_args()

    result = write_copy_shadow_scope_policy_design_report(
        args.repo_root,
        output_dir=args.output_dir,
        proposed_policy_path=args.proposed_policy_path,
        expected_challenge_hash=args.expected_challenge_hash,
        expected_policy_hash=args.expected_policy_hash,
    )
    print(
        json.dumps(
            {
                "decision_label": result["summary"]["decision_label"],
                "output_dir": args.output_dir.as_posix(),
                "proposed_policy_path": args.proposed_policy_path.as_posix(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
