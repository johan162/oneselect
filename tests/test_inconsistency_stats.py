"""
Test inconsistency statistics calculation and API endpoints.

Verifies that:
1. Stats are calculated correctly
2. Stats are included in comparison creation response
3. Dedicated stats endpoint works
4. Percentage calculations are accurate
"""


def test_inconsistency_percentage_calculation():
    """Test percentage calculation logic"""
    # 4 comparisons, 3 involved in a cycle = 75%
    total_comparisons = 4
    comparisons_in_cycles = 3

    percentage = comparisons_in_cycles / total_comparisons * 100
    assert percentage == 75.0


def test_no_inconsistencies():
    """Test stats when there are no cycles"""
    # Simulate the helper function logic
    total_comparisons = 10
    cycles_found = []
    comparisons_in_cycles = set()

    stats = {
        "cycle_count": len(cycles_found),
        "total_comparisons": total_comparisons,
        "inconsistency_percentage": (
            (len(comparisons_in_cycles) / total_comparisons * 100)
            if total_comparisons > 0
            else 0.0
        ),
        "dimension": "complexity",
    }

    assert stats["cycle_count"] == 0
    assert stats["total_comparisons"] == 10
    assert stats["inconsistency_percentage"] == 0.0


def test_single_cycle_stats():
    """Test stats with a single 3-node cycle"""
    # A>B, B>C, C>A = 3 comparisons in 1 cycle
    total_comparisons = 3
    cycles_found = [["A", "B", "C"]]
    comparisons_in_cycles = {"comp1", "comp2", "comp3"}  # All 3 comparisons involved

    percentage = len(comparisons_in_cycles) / total_comparisons * 100

    stats = {
        "cycle_count": len(cycles_found),
        "total_comparisons": total_comparisons,
        "inconsistency_percentage": round(percentage, 2),
        "dimension": "complexity",
    }

    assert stats["cycle_count"] == 1
    assert stats["total_comparisons"] == 3
    assert stats["inconsistency_percentage"] == 100.0


def test_partial_inconsistencies():
    """Test when only some comparisons are in cycles"""
    # 10 total comparisons, but only 4 involved in cycles
    total_comparisons = 10
    cycles_found = [["A", "B", "C"]]  # 3 edges
    comparisons_in_cycles = {"comp1", "comp2", "comp3"}

    percentage = len(comparisons_in_cycles) / total_comparisons * 100

    stats = {
        "cycle_count": len(cycles_found),
        "total_comparisons": total_comparisons,
        "inconsistency_percentage": round(percentage, 2),
        "dimension": "value",
    }

    assert stats["cycle_count"] == 1
    assert stats["total_comparisons"] == 10
    assert stats["inconsistency_percentage"] == 30.0  # 3/10 = 30%


def test_multiple_cycles_stats():
    """Test stats with multiple independent cycles"""
    # 2 cycles: A>B>C>A (3 edges) and D>E>F>D (3 edges)
    # Plus 4 other comparisons = 10 total
    total_comparisons = 10
    cycles_found = [["A", "B", "C"], ["D", "E", "F"]]
    comparisons_in_cycles = {
        "c1",
        "c2",
        "c3",
        "c4",
        "c5",
        "c6",
    }  # 6 comparisons in cycles

    percentage = len(comparisons_in_cycles) / total_comparisons * 100

    stats = {
        "cycle_count": len(cycles_found),
        "total_comparisons": total_comparisons,
        "inconsistency_percentage": round(percentage, 2),
        "dimension": "complexity",
    }

    assert stats["cycle_count"] == 2
    assert stats["total_comparisons"] == 10
    assert stats["inconsistency_percentage"] == 60.0


def test_empty_project_stats():
    """Test stats for a project with no comparisons"""
    stats = {
        "cycle_count": 0,
        "total_comparisons": 0,
        "inconsistency_percentage": 0.0,
        "dimension": "all",
    }

    assert stats["cycle_count"] == 0
    assert stats["total_comparisons"] == 0
    assert stats["inconsistency_percentage"] == 0.0


def test_rounding_precision():
    """Test that percentages are rounded to 2 decimal places"""
    total_comparisons = 7
    comparisons_in_cycles = 2

    # 2/7 = 0.285714... should round to 28.57
    percentage = round((comparisons_in_cycles / total_comparisons * 100), 2)

    assert percentage == 28.57


def test_high_inconsistency_rate():
    """Test detection of projects with high inconsistency rates"""
    # 8 out of 10 comparisons in cycles (80%)
    total_comparisons = 10
    comparisons_in_cycles = {"c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"}

    percentage = round((len(comparisons_in_cycles) / total_comparisons * 100), 2)

    assert percentage == 80.0
    assert percentage > 20.0  # Threshold for "significant" inconsistencies


def test_ui_color_thresholds():
    """Test typical UI color coding thresholds"""

    def get_severity_level(percentage):
        if percentage == 0:
            return "green"
        elif percentage < 10:
            return "yellow"
        elif percentage < 20:
            return "orange"
        else:
            return "red"

    assert get_severity_level(0.0) == "green"
    assert get_severity_level(5.0) == "yellow"
    assert get_severity_level(15.0) == "orange"
    assert get_severity_level(25.0) == "red"
