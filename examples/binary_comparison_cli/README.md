# Binary Comparison CLI Example

A terminal-based interactive tool that demonstrates the OneSelect API for pairwise feature comparisons using **binary mode** (A wins, B wins, or tie).

## Overview

This example:
1. Loads features from a CSV file
2. Creates a project via the OneSelect API
3. Guides the user through comparisons in two dimensions:
   - **Complexity** - How difficult is this feature to implement?
   - **Value** - How much value does this feature provide to users?
4. Displays real-time statistics after each comparison:
   - Progress percentage toward target certainty
   - Effective confidence level
   - Estimated remaining comparisons
   - Inconsistency detection (cycles)
5. Shows final ranked results when done

## Prerequisites

1. OneSelect API server running locally:
   ```bash
   cd /path/to/oneselect
   make run
   ```

2. Default admin credentials (or customize):
   - Username: `admin`
   - Password: `admin`

## Installation

```bash
# From the example directory
cd examples/binary_comparison_cli

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies (now isolated in the venv)
pip install -r requirements.txt

# Run the example
python compare.py

# When done, deactivate the venv
deactivate
```


## Usage

### Basic Usage (with sample features)

```bash
python compare.py
```

### Custom CSV File

```bash
python compare.py --csv my_features.csv
```

### All Options

```bash
python compare.py \
    --csv features.csv \
    --api-url http://localhost:8000 \
    --username admin \
    --password admin \
    --target-certainty 0.90 \
    --project-name "My Project"
```

## CSV Format

The CSV file should have two columns:
- `name` (required): Feature name
- `description` (optional): Feature description

Example:
```csv
name,description
User Authentication,Implement secure login and registration
Dashboard,Create main dashboard with metrics
Search,Full-text search with filters
```

## Interactive Controls

During comparisons:
- `A` - Feature A is more complex/valuable
- `B` - Feature B is more complex/valuable
- `T` - They are equal (tie)
- `Q` - Quit and show current results

## Example Session

```
============================================================
  ONESELECT - Binary Comparison Mode
  Dimension: COMPLEXITY | Comparison #1
============================================================

Compare these two features:

  [A] User Authentication
      Implement secure login and registration system

  [B] Dashboard Overview
      Create main dashboard with key metrics

------------------------------------------------------------
Statistics:
  • Progress: 12.5%
  • Confidence: 45%
  • Comparisons done: 3
  • Est. remaining for 90%: ~21
  • ✓ No inconsistencies detected
------------------------------------------------------------

Which feature is MORE COMPLEX to implement?
  [A] Feature A
  [B] Feature B
  [T] Equal / Tie
  [Q] Quit and show results

Your choice (A/B/T/Q): A
```

## Output

After completing comparisons (or quitting early), you'll see ranked results:

```
============================================================
  FINAL RESULTS
============================================================

Rank  Feature                            Score     Confidence
------------------------------------------------------------
1     User Authentication                +1.24     85%
2     Search Functionality               +0.89     78%
3     Dashboard Overview                 +0.45     72%
...
```

## Notes

- The project is created fresh each run
- You can choose to delete or preserve the project when done
- Comparisons are submitted to the API in real-time
- Statistics update after each comparison
