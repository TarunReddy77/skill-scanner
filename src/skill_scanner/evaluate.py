"""Run the scanner over the labeled skills in skills/ as a Langfuse dataset experiment.

Usage: uv run python -m skill_scanner.evaluate [--model MODEL_ID] [--run-name NAME]
"""

import argparse
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Import Langfuse only after load_dotenv() so it picks up the credentials from .env.
from langfuse import Evaluation, get_client  # noqa: E402

from skill_scanner.agent import DEFAULT_MODEL_ID, scan_skill  # noqa: E402

DATASET_NAME = "skill-scanner"
SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
LABELS = ("benign", "malicious")


def sync_dataset() -> int:
    """Create or update the Langfuse dataset from skills/<label>/<name>/SKILL.md.

    Item ids are derived from the skill name, so re-running updates items instead of duplicating them.
    """
    langfuse = get_client()
    langfuse.create_dataset(
        name=DATASET_NAME,
        description="Labeled agent skills (benign / malicious). The label is the expected output.",
    )
    count = 0
    for label in LABELS:
        for skill_md in sorted((SKILLS_DIR / label).glob("*/SKILL.md")):
            name = skill_md.parent.name
            langfuse.create_dataset_item(
                dataset_name=DATASET_NAME,
                id=f"skill-{name}",
                input={"skill_name": name, "skill_md": skill_md.read_text()},
                expected_output=label,
            )
            count += 1
    return count


def make_task(model_id: str):
    def task(*, item, **kwargs) -> dict:
        # Write the skill to a neutral temp path so the label (the folder name) cannot leak to the agent.
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / item.input["skill_name"]
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(item.input["skill_md"])
            return scan_skill(str(skill_dir / "SKILL.md"), model_id=model_id).model_dump()

    return task


def correct(*, output, expected_output, **kwargs) -> Evaluation:
    """Item-level score: 1 if the verdict matches the label."""
    hit = output["verdict"] == expected_output
    return Evaluation(
        name="correct",
        value=1.0 if hit else 0.0,
        comment=f"predicted {output['verdict']} ({output['confidence']:.2f}), expected {expected_output}",
    )


def make_run_evaluator(total_items: int):
    def summarize(*, item_results, **kwargs) -> list[Evaluation]:
        """Run-level scores. Items whose scan failed are missing from item_results and count as wrong."""
        expected = {r.item.expected_output for r in item_results}
        by_label = {label: [r for r in item_results if r.item.expected_output == label] for label in expected}

        hits = sum(r.output["verdict"] == r.item.expected_output for r in item_results)
        missed = sum(r.output["verdict"] == "benign" for r in by_label.get("malicious", []))
        flagged = sum(r.output["verdict"] == "malicious" for r in by_label.get("benign", []))

        # Denominators come from the full dataset, so failed scans cannot hide behind a smaller sample.
        all_items = get_client().get_dataset(DATASET_NAME).items
        n_malicious = sum(i.expected_output == "malicious" for i in all_items)
        n_benign = sum(i.expected_output == "benign" for i in all_items)
        failures = total_items - len(item_results)

        return [
            Evaluation(name="accuracy", value=hits / total_items, comment=f"{hits}/{total_items} correct"),
            Evaluation(
                name="false_negative_rate",
                value=missed / n_malicious if n_malicious else 0.0,
                comment=f"{missed}/{n_malicious} malicious skills classified as benign",
            ),
            Evaluation(
                name="false_positive_rate",
                value=flagged / n_benign if n_benign else 0.0,
                comment=f"{flagged}/{n_benign} benign skills classified as malicious",
            ),
            Evaluation(name="scan_failure_rate", value=failures / total_items, comment=f"{failures} scans failed"),
        ]

    return summarize


def print_item_table(item_results) -> None:
    print("\nPer-skill results:")
    for r in sorted(item_results, key=lambda r: (r.item.expected_output, r.item.input["skill_name"])):
        mark = "ok   " if r.output["verdict"] == r.item.expected_output else "WRONG"
        print(
            f"  {mark} {r.item.input['skill_name']:28} expected {r.item.expected_output:10} "
            f"got {r.output['verdict']:10} ({r.output['confidence']:.2f})"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the skill scanner on the labeled dataset.")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID, help="Bedrock model id to scan with")
    parser.add_argument("--run-name", help="Name for this run (default: <model>-<timestamp>)")
    parser.add_argument("--concurrency", type=int, default=5, help="Skills to scan in parallel")
    args = parser.parse_args()

    langfuse = get_client()
    n = sync_dataset()
    print(f"Synced {n} skills to dataset '{DATASET_NAME}'")

    dataset = langfuse.get_dataset(DATASET_NAME)
    run_name = args.run_name or f"{args.model}-{datetime.now():%Y%m%d-%H%M%S}"
    result = dataset.run_experiment(
        name="skill-scanner-eval",
        run_name=run_name,
        description=f"Scan every labeled skill with {args.model}",
        task=make_task(args.model),
        evaluators=[correct],
        run_evaluators=[make_run_evaluator(len(dataset.items))],
        max_concurrency=args.concurrency,
        metadata={"model_id": args.model},
    )
    print(result.format())
    print_item_table(result.item_results)
    langfuse.flush()


if __name__ == "__main__":
    main()
