#!/usr/bin/env python3
"""
Binary Comparison CLI Example

A terminal-based tool that demonstrates the OneSelect API for pairwise
feature comparisons using binary mode (A wins, B wins, or tie).

Features are loaded from a CSV file, and the user interactively compares
them in each dimension (complexity, then value) sequentially.

Usage:
    # Start a new comparison session with features from CSV
    python compare.py [--csv features.csv] [--api-url http://localhost:8000]

    # View results for an existing project and exit
    python compare.py --project-id <PROJECT_UUID>
"""

import argparse
import csv
import sys
from typing import Optional

import requests


class OneSelectClient:
    """Client for interacting with the OneSelect API."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/v1"
        self.token: Optional[str] = None
        self._login(username, password)

    def _login(self, username: str, password: str) -> None:
        """Authenticate and store the access token."""
        response = requests.post(
            f"{self.api_url}/auth/login",
            data={"username": username, "password": password},
        )
        if response.status_code != 200:
            raise RuntimeError(f"Login failed: {response.text}")
        self.token = response.json()["access_token"]

    @property
    def headers(self) -> dict:
        """Return authorization headers."""
        return {"Authorization": f"Bearer {self.token}"}

    def create_project(self, name: str, description: str) -> dict:
        """Create a new project in binary comparison mode."""
        response = requests.post(
            f"{self.api_url}/projects/",
            headers=self.headers,
            json={
                "name": name,
                "description": description,
                "comparison_mode": "binary",
            },
        )
        response.raise_for_status()
        return response.json()

    def add_features(self, project_id: str, features: list[dict]) -> dict:
        """Bulk add features to a project."""
        response = requests.post(
            f"{self.api_url}/projects/{project_id}/features/bulk",
            headers=self.headers,
            json=features,  # API expects a list directly, not wrapped
        )
        response.raise_for_status()
        return response.json()

    def get_next_pair(
        self, project_id: str, dimension: str, target_certainty: float = 0.90
    ) -> Optional[dict]:
        """Get the next pair of features to compare."""
        response = requests.get(
            f"{self.api_url}/projects/{project_id}/comparisons/next",
            headers=self.headers,
            params={
                "dimension": dimension,
                "target_certainty": str(target_certainty),
                "include_progress": "true",
            },
        )
        if response.status_code == 204:
            return None  # No more comparisons needed
        response.raise_for_status()
        return response.json()

    def submit_comparison(
        self,
        project_id: str,
        feature_a_id: str,
        feature_b_id: str,
        choice: str,
        dimension: str,
    ) -> dict:
        """Submit a binary comparison result."""
        response = requests.post(
            f"{self.api_url}/projects/{project_id}/comparisons/binary",
            headers=self.headers,
            json={
                "feature_a_id": feature_a_id,
                "feature_b_id": feature_b_id,
                "choice": choice,
                "dimension": dimension,
            },
        )
        response.raise_for_status()
        return response.json()

    def get_progress(
        self, project_id: str, dimension: str, target_certainty: float = 0.90
    ) -> dict:
        """Get comparison progress for a dimension."""
        response = requests.get(
            f"{self.api_url}/projects/{project_id}/comparisons/progress",
            headers=self.headers,
            params={"dimension": dimension, "target_certainty": str(target_certainty)},
        )
        response.raise_for_status()
        return response.json()

    def get_estimates(self, project_id: str, dimension: str) -> dict:
        """Get estimated comparisons needed for certainty thresholds."""
        response = requests.get(
            f"{self.api_url}/projects/{project_id}/comparisons/estimates",
            headers=self.headers,
            params={"dimension": dimension},
        )
        response.raise_for_status()
        return response.json()

    def get_inconsistency_stats(self, project_id: str, dimension: str) -> dict:
        """Get inconsistency statistics for a dimension."""
        response = requests.get(
            f"{self.api_url}/projects/{project_id}/comparisons/inconsistency-stats",
            headers=self.headers,
            params={"dimension": dimension},
        )
        response.raise_for_status()
        return response.json()

    def get_results(self, project_id: str, sort_by: str = "ratio") -> list:
        """Get ranked results."""
        response = requests.get(
            f"{self.api_url}/projects/{project_id}/results",
            headers=self.headers,
            params={"sort_by": sort_by},
        )
        response.raise_for_status()
        return response.json()

    def delete_project(self, project_id: str) -> None:
        """Delete a project."""
        response = requests.delete(
            f"{self.api_url}/projects/{project_id}",
            headers=self.headers,
        )
        response.raise_for_status()


def load_features_from_csv(filepath: str) -> list[dict]:
    """Load features from a CSV file with 'name' and 'description' columns."""
    features = []
    with open(filepath, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            features.append(
                {
                    "name": row["name"].strip(),
                    "description": row.get("description", "").strip(),
                }
            )
    return features


def clear_screen() -> None:
    """Clear the terminal screen."""
    print("\033[2J\033[H", end="")


def print_header(dimension: str, comparison_num: int) -> None:
    """Print the comparison header."""
    print("=" * 60)
    print("  ONESELECT - Binary Comparison Mode")
    print(f"  Dimension: {dimension.upper()} | Comparison #{comparison_num}")
    print("=" * 60)
    print()


def print_features(feature_a: dict, feature_b: dict) -> None:
    """Print the two features being compared."""
    print("Compare these two features:\n")
    print(f"  [A] {feature_a['name']}")
    if feature_a.get("description"):
        print(f"      {feature_a['description']}")
    print()
    print(f"  [B] {feature_b['name']}")
    if feature_b.get("description"):
        print(f"      {feature_b['description']}")
    print()


def print_stats(progress: dict, inconsistency: dict, estimates: dict, target_certainty: float = 0.90) -> None:
    """Print current statistics."""
    print("-" * 60)
    print("Statistics:")
    print(f"  • Progress: {progress.get('progress_percent', 0):.1f}%")
    print(f"  • Confidence: {progress.get('effective_confidence', 0):.1%}")
    print(f"  • Comparisons done: {progress.get('total_comparisons_done', 0)}")

    # Estimated remaining comparisons
    remaining = progress.get("comparisons_remaining", "?")
    target_pct = f"{int(target_certainty * 100)}%"
    if remaining is not None and remaining != "?":
        print(f"  • Est. remaining for {target_pct}: {remaining}")
    else:
        # Fall back to estimates endpoint
        est_target = estimates.get("estimates", {}).get(target_pct, "?")
        done = progress.get("total_comparisons_done", 0)
        if est_target != "?" and est_target is not None:
            remaining = max(0, est_target - done)
            print(f"  • Est. remaining for {target_pct}: ~{remaining}")

    # Inconsistency
    cycle_count = inconsistency.get("cycle_count", 0)
    inconsistency_pct = inconsistency.get("inconsistency_percentage", 0)
    if cycle_count > 0:
        print(
            f"  • ⚠️  Inconsistencies: {cycle_count} cycles ({inconsistency_pct:.1f}%)"
        )
    else:
        print("  • ✓ No inconsistencies detected")
    print("-" * 60)


def get_user_choice() -> Optional[str]:
    """Get the user's choice from keyboard input."""
    print("\nWhich is MORE {dimension}?")
    print("  [A] Feature A is more")
    print("  [B] Feature B is more")
    print("  [T] They are equal (tie)")
    print("  [Q] Quit and show results")
    print()

    while True:
        try:
            choice = input("Your choice (A/B/T/Q): ").strip().upper()
            if choice in ("A", "B", "T", "Q"):
                return choice
            print("Invalid choice. Please enter A, B, T, or Q.")
        except (KeyboardInterrupt, EOFError):
            return "Q"


def run_comparison_session(
    client: OneSelectClient,
    project_id: str,
    dimension: str,
    target_certainty: float = 0.90,
) -> bool:
    """
    Run an interactive comparison session for one dimension.

    Returns True if completed normally, False if user quit early.
    """
    comparison_num = 0

    while True:
        comparison_num += 1

        # Get next pair
        next_pair = client.get_next_pair(project_id, dimension, target_certainty)

        if next_pair is None:
            clear_screen()
            print(f"\n✓ {dimension.upper()} comparisons complete!")
            print(f"  Target certainty of {target_certainty:.0%} reached.\n")
            return True

        # Get current stats
        progress = client.get_progress(project_id, dimension, target_certainty)
        inconsistency = client.get_inconsistency_stats(project_id, dimension)
        estimates = client.get_estimates(project_id, dimension)

        # Display UI
        clear_screen()
        print_header(dimension, comparison_num)
        print_features(next_pair["feature_a"], next_pair["feature_b"])
        print_stats(progress, inconsistency, estimates, target_certainty)

        # Show dimension-specific prompt
        if dimension == "complexity":
            print("\nWhich feature is MORE COMPLEX to implement?")
        else:
            print("\nWhich feature provides MORE VALUE to users?")

        print("  [A] Feature A")
        print("  [B] Feature B")
        print("  [T] Equal / Tie")
        print("  [Q] Quit and show results")

        # Get choice
        while True:
            try:
                choice = input("\nYour choice (A/B/T/Q): ").strip().upper()
                if choice in ("A", "B", "T", "Q"):
                    break
                print("Invalid choice. Please enter A, B, T, or Q.")
            except (KeyboardInterrupt, EOFError):
                choice = "Q"
                break

        if choice == "Q":
            return False

        # Map choice to API format
        choice_map = {"A": "feature_a", "B": "feature_b", "T": "tie"}

        # Submit comparison
        client.submit_comparison(
            project_id,
            next_pair["feature_a"]["id"],
            next_pair["feature_b"]["id"],
            choice_map[choice],
            dimension,
        )


def print_final_results(client: OneSelectClient, project_id: str) -> None:
    """Print the final ranked results."""
    clear_screen()
    print("=" * 60)
    print("  FINAL RESULTS")
    print("=" * 60)
    print()

    results = client.get_results(project_id, sort_by="ratio")

    if not results:
        print("No results available yet.")
        return

    print(f"{'Rank':<6}{'Feature':<35}{'Score':<10}{'Uncertainty'}")
    print("-" * 60)

    for i, item in enumerate(results, 1):
        feature = item.get("feature", {})
        name = feature.get("name", "Unknown")[:33]
        score = item.get("score", 0)
        variance = item.get("variance", 1.0)
        # Show sigma (standard deviation) as uncertainty measure
        # Lower sigma = higher confidence in the score
        sigma = variance**0.5

        print(f"{i:<6}{name:<35}{score:>+.2f}     ±{sigma:.2f}")

    print()
    print("Note: Lower uncertainty (±) indicates higher confidence in the score.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Binary Comparison CLI - Interactive feature prioritization"
    )
    parser.add_argument(
        "--csv",
        default="sample_features.csv",
        help="Path to CSV file with features (columns: name, description)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="OneSelect API base URL",
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="API username for authentication",
    )
    parser.add_argument(
        "--password",
        default="admin",
        help="API password for authentication",
    )
    parser.add_argument(
        "--target-certainty",
        type=float,
        default=0.85,
        help="Target certainty threshold (0.0-1.0)",
    )
    parser.add_argument(
        "--project-name",
        default="CLI Comparison Example",
        help="Name for the created project",
    )
    parser.add_argument(
        "--project-id",
        help="Existing project ID - print results and exit (skips comparison session)",
    )

    args = parser.parse_args()

    # If project-id is provided, just print results and exit
    if args.project_id:
        print("=" * 60)
        print("  ONESELECT - View Project Results")
        print("=" * 60)
        print()
        print(f"Connecting to API: {args.api_url}")

        try:
            client = OneSelectClient(args.api_url, args.username, args.password)
            print("✓ Authenticated successfully")
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            sys.exit(1)

        print_final_results(client, args.project_id)
        return

    print("=" * 60)
    print("  ONESELECT - Binary Comparison CLI")
    print("=" * 60)
    print()
    print(f"Loading features from: {args.csv}")
    print(f"Connecting to API: {args.api_url}")
    print()

    # Load features
    try:
        features = load_features_from_csv(args.csv)
        print(f"✓ Loaded {len(features)} features")
    except FileNotFoundError:
        print(f"✗ Error: CSV file not found: {args.csv}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error loading CSV: {e}")
        sys.exit(1)

    # Connect to API
    try:
        client = OneSelectClient(args.api_url, args.username, args.password)
        print("✓ Authenticated successfully")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        print("\nMake sure the API server is running:")
        print("  cd /path/to/oneselect && make run")
        sys.exit(1)

    # Create project
    try:
        project = client.create_project(
            args.project_name,
            f"Created via CLI with {len(features)} features",
        )
        project_id = project["id"]
        print(f"✓ Created project: {project['name']}")
    except Exception as e:
        print(f"✗ Failed to create project: {e}")
        sys.exit(1)

    # Add features
    try:
        result = client.add_features(project_id, features)
        print(f"✓ Added {result['count']} features")
    except Exception as e:
        print(f"✗ Failed to add features: {e}")
        client.delete_project(project_id)
        sys.exit(1)

    print()
    print("Starting comparison session...")
    print("You will compare features in two dimensions:")
    print("  1. COMPLEXITY - How difficult is this to implement?")
    print("  2. VALUE - How much value does this provide to users?")
    print()
    input("Press Enter to begin...")

    try:
        # Phase 1: Complexity comparisons
        print("\n" + "=" * 60)
        print("  PHASE 1: COMPLEXITY COMPARISONS")
        print("=" * 60)
        input("\nPress Enter to start complexity comparisons...")

        completed = run_comparison_session(
            client, project_id, "complexity", args.target_certainty
        )

        if completed:
            # Phase 2: Value comparisons
            print("\n" + "=" * 60)
            print("  PHASE 2: VALUE COMPARISONS")
            print("=" * 60)
            input("\nPress Enter to start value comparisons...")

            run_comparison_session(client, project_id, "value", args.target_certainty)

        # Show final results
        print_final_results(client, project_id)

        # Ask about cleanup
        print()
        cleanup = input("Delete this project? (y/N): ").strip().lower()
        if cleanup == "y":
            client.delete_project(project_id)
            print("✓ Project deleted")
        else:
            print(f"Project preserved. ID: {project_id}")

    except KeyboardInterrupt:
        print("\n\nSession interrupted.")
        print_final_results(client, project_id)
        cleanup = input("\nDelete this project? (y/N): ").strip().lower()
        if cleanup == "y":
            client.delete_project(project_id)
            print("✓ Project deleted")


if __name__ == "__main__":
    main()
