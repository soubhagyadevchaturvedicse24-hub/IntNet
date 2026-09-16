"""
Subprocess Worker Entry Point for CRIMENET Observation Engine (Slice 7).
Executes E01 observation inside an isolated operating system process to guarantee
that any native C-level exceptions or crashes in libewf/pytsk3 will not terminate
the primary FastAPI server.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path so imports resolve cleanly when invoked as standalone script
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.observation.e01_engine import E01ForensicObservationEngine


def main():
    parser = argparse.ArgumentParser(description="CRIMENET E01 Observation Subprocess Worker")
    parser.add_argument("--image-path", required=True, help="Path to primary E01 forensic image")
    parser.add_argument("--output-dir", required=True, help="Directory to save artifacts and contract")
    parser.add_argument("--case-id", required=True, help="Case identifier")
    parser.add_argument("--evidence-id", required=True, help="Evidence identifier")
    parser.add_argument("--job-id", required=True, help="Processing job identifier")
    parser.add_argument("--max-artifacts", type=int, default=250, help="Maximum representative files to extract")
    parser.add_argument("--max-file-size", type=int, default=100 * 1024 * 1024, help="Maximum individual file size in bytes")
    parser.add_argument("--priority-targets", nargs="*", default=["autopsy.db"], help="Priority target filenames to extract first")

    args = parser.parse_args()

    image_path = Path(args.image_path)
    output_dir = Path(args.output_dir)

    try:
        engine = E01ForensicObservationEngine(
            max_artifacts=args.max_artifacts,
            max_file_size=args.max_file_size,
            priority_targets=args.priority_targets
        )

        contract_v1, observed_filesystem = engine.process(
            image_path=image_path,
            output_dir=output_dir,
            case_id=args.case_id,
            evidence_id=args.evidence_id,
            job_id=args.job_id
        )

        result_payload = {
            "status": "SUCCESS",
            "observed_filesystem": observed_filesystem,
            "artifacts_count": len(contract_v1.get("observed_artifacts", [])),
            "contract_file": str(output_dir / f"evidence_contract_{args.job_id}.json")
        }

        print(json.dumps(result_payload))
        sys.exit(0)

    except Exception as exc:
        error_payload = {
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        }
        print(json.dumps(error_payload), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
