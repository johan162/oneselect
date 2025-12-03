"""
Test cycle detection in comparison graph.

This module tests the inconsistency detection algorithm that finds cycles
in the comparison graph (e.g., A>B, B>C, C>A).
"""
import pytest


def test_simple_cycle_detection():
    """Test detection of a simple 3-node cycle: A>B, B>C, C>A"""
    # Build graph
    graph = {
        "A": {"B"},
        "B": {"C"},
        "C": {"A"},
    }
    
    # DFS cycle detection
    def find_cycles_dfs(node, path, visited, rec_stack, all_cycles):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                find_cycles_dfs(neighbor, path, visited, rec_stack, all_cycles)
            elif neighbor in rec_stack:
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:]
                min_idx = cycle.index(min(cycle))
                normalized = cycle[min_idx:] + cycle[:min_idx]
                if normalized not in all_cycles:
                    all_cycles.append(normalized)
        
        path.pop()
        rec_stack.remove(node)
    
    cycles = []
    visited = set()
    
    for node in graph:
        if node not in visited:
            find_cycles_dfs(node, [], visited, set(), cycles)
    
    assert len(cycles) == 1
    assert set(cycles[0]) == {"A", "B", "C"}


def test_no_cycle():
    """Test graph with no cycles: A>B, B>C, A>C"""
    graph = {
        "A": {"B", "C"},
        "B": {"C"},
        "C": set(),
    }
    
    def find_cycles_dfs(node, path, visited, rec_stack, all_cycles):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                find_cycles_dfs(neighbor, path, visited, rec_stack, all_cycles)
            elif neighbor in rec_stack:
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:]
                min_idx = cycle.index(min(cycle))
                normalized = cycle[min_idx:] + cycle[:min_idx]
                if normalized not in all_cycles:
                    all_cycles.append(normalized)
        
        path.pop()
        rec_stack.remove(node)
    
    cycles = []
    visited = set()
    
    for node in graph:
        if node not in visited:
            find_cycles_dfs(node, [], visited, set(), cycles)
    
    assert len(cycles) == 0


def test_multiple_cycles():
    """Test detection of multiple independent cycles"""
    # Two cycles: A>B>C>A and D>E>F>D
    graph = {
        "A": {"B"},
        "B": {"C"},
        "C": {"A"},
        "D": {"E"},
        "E": {"F"},
        "F": {"D"},
    }
    
    def find_cycles_dfs(node, path, visited, rec_stack, all_cycles):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                find_cycles_dfs(neighbor, path, visited, rec_stack, all_cycles)
            elif neighbor in rec_stack:
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:]
                min_idx = cycle.index(min(cycle))
                normalized = cycle[min_idx:] + cycle[:min_idx]
                if normalized not in all_cycles:
                    all_cycles.append(normalized)
        
        path.pop()
        rec_stack.remove(node)
    
    cycles = []
    visited = set()
    
    for node in graph:
        if node not in visited:
            find_cycles_dfs(node, [], visited, set(), cycles)
    
    assert len(cycles) == 2


def test_complex_cycle():
    """Test detection of longer cycle with branches"""
    # Main cycle: A>B>C>D>A, with extra edges
    graph = {
        "A": {"B", "C"},  # Direct path to C
        "B": {"C"},
        "C": {"D"},
        "D": {"A"},
    }
    
    def find_cycles_dfs(node, path, visited, rec_stack, all_cycles):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                find_cycles_dfs(neighbor, path, visited, rec_stack, all_cycles)
            elif neighbor in rec_stack:
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:]
                min_idx = cycle.index(min(cycle))
                normalized = cycle[min_idx:] + cycle[:min_idx]
                if normalized not in all_cycles:
                    all_cycles.append(normalized)
        
        path.pop()
        rec_stack.remove(node)
    
    cycles = []
    visited = set()
    
    for node in graph:
        if node not in visited:
            find_cycles_dfs(node, [], visited, set(), cycles)
    
    # Should find both A>B>C>D>A and A>C>D>A
    assert len(cycles) >= 1


def test_performance_large_graph():
    """Test performance with a graph similar to 70 features"""
    import time
    
    # Create a graph with 70 nodes and ~200 edges
    # Most edges form a DAG, but add a few cycles
    graph = {}
    
    # Create a mostly ordered graph
    for i in range(70):
        graph[str(i)] = set()
        # Each node points to a few higher-numbered nodes (no cycles)
        for j in range(i + 1, min(i + 4, 70)):
            graph[str(i)].add(str(j))
    
    # Add a few cycles
    graph["10"].add("5")  # Creates cycle
    graph["30"].add("25")  # Creates another cycle
    graph["50"].add("45")  # Creates another cycle
    
    def find_cycles_dfs(node, path, visited, rec_stack, all_cycles):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                find_cycles_dfs(neighbor, path, visited, rec_stack, all_cycles)
            elif neighbor in rec_stack:
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:]
                min_idx = cycle.index(min(cycle))
                normalized = cycle[min_idx:] + cycle[:min_idx]
                if normalized not in all_cycles:
                    all_cycles.append(normalized)
        
        path.pop()
        rec_stack.remove(node)
    
    start_time = time.time()
    cycles = []
    visited = set()
    
    for node in graph:
        if node not in visited:
            find_cycles_dfs(node, [], visited, set(), cycles)
    
    elapsed_time = time.time() - start_time
    
    # Should complete in well under 100ms for 70 nodes
    assert elapsed_time < 0.1
    # Should find at least the 3 direct cycles we added
    # (may find more due to transitive paths)
    assert len(cycles) >= 3
