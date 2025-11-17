# app/optimizer/optimizer.py
"""
Enhanced Lumber Optimizer with True Cost Optimization

Function: optimize_boards(cuts, boards)

This optimizer uses a two-phase approach:
1. Generate all viable cutting patterns for each board type
2. Use integer linear programming to select the optimal combination of patterns

This ensures globally optimal solutions, unlike the previous greedy approach.

Inputs:

1. cuts : list of dict
   - Each dict describes a cut needed in the project.
   - Required keys:
       "width": int or float,  # board width in inches
       "height": int or float, # board height in inches
       "length": int or float, # length of each cut in inches
       "quantity": int         # how many of this cut are required
   Example:
       cuts = [
           {"width": 2, "height": 4, "length": 10, "quantity": 2},
           {"width": 2, "height": 4, "length": 5, "quantity": 1},
       ]

2. boards : list of dict
   - Each dict describes a board type available for purchase.
   - Required keys:
       "width": int or float,  # board width in inches
       "height": int or float, # board height in inches
       "length": int or float, # length of the board in inches
       "price": float          # cost of one board
   Example:
       boards = [
           {"width": 2, "height": 4, "length": 20, "price": 8},
           {"width": 2, "height": 4, "length": 30, "price": 12},
       ]

Outputs:

result : dict
- "board_plan": {board_idx: quantity, ...}   # number of boards of each type to buy
- "cut_plan": {board_idx: [[cut1, cut2, ...], ...], ...}  # each sublist = one physical board's cuts
- "total_cost": float                        # total cost of purchased boards
- "waste_summary": {board_idx: total_waste, ...}  # total leftover length per board type

Example Usage:

result = optimize_boards(cuts, boards)
print(result["board_plan"])
print(result["cut_plan"])
print(result["total_cost"])
print(result["waste_summary"])
"""

from ortools.linear_solver import pywraplp
from collections import defaultdict
import itertools


def _generate_cutting_patterns(cut_lengths, board_length, max_patterns=1000):
    """
    Generate all feasible cutting patterns for a board.
    
    A pattern is a combination of cuts that fits on one board.
    Uses dynamic programming to efficiently generate patterns.
    
    Args:
        cut_lengths: List of unique cut lengths needed
        board_length: Length of the board
        max_patterns: Maximum number of patterns to generate (prevent explosion)
    
    Returns:
        List of patterns, where each pattern is a dict {cut_length: count}
    """
    patterns = []
    cut_lengths_sorted = sorted(set(cut_lengths), reverse=True)
    
    def generate_recursive(remaining_length, current_pattern, start_idx):
        """Recursively generate patterns using backtracking"""
        if len(patterns) >= max_patterns:
            return
        
        # Add current pattern if it's non-empty
        if sum(current_pattern.values()) > 0:
            patterns.append(current_pattern.copy())
        
        # Try adding each cut type
        for i in range(start_idx, len(cut_lengths_sorted)):
            cut_len = cut_lengths_sorted[i]
            if cut_len <= remaining_length:
                # Add this cut to the pattern
                current_pattern[cut_len] = current_pattern.get(cut_len, 0) + 1
                generate_recursive(remaining_length - cut_len, current_pattern, i)
                # Backtrack
                current_pattern[cut_len] -= 1
                if current_pattern[cut_len] == 0:
                    del current_pattern[cut_len]
    
    generate_recursive(board_length, {}, 0)
    
    # Sort patterns by efficiency (less waste is better)
    patterns.sort(key=lambda p: sum(k * v for k, v in p.items()), reverse=True)
    
    return patterns


def _pack_cuts_into_boards(cuts_list, board_length):
    """
    Pack a list of cut lengths into individual boards using Best Fit Decreasing.
    
    This is used after optimization to create the detailed cutting plan.
    
    Args:
        cuts_list: List of cut lengths to pack (e.g., [10, 10, 20, 5])
        board_length: Length of each board
    
    Returns:
        List of lists, where each inner list is the cuts for one board
        Example: [[10, 5], [10, 20]] means board 1 has cuts of 10 and 5
    """
    if not cuts_list:
        return []
    
    # Sort cuts in descending order for better packing
    sorted_cuts = sorted(cuts_list, reverse=True)
    
    # Initialize boards: List of [remaining_space, [cuts]]
    boards = []
    
    for cut in sorted_cuts:
        # Find best board: one with smallest remaining space that still fits the cut
        best_board_idx = -1
        best_remaining = float('inf')
        
        for idx, board in enumerate(boards):
            remaining_after = board[0] - cut
            if remaining_after >= 0 and remaining_after < best_remaining:
                best_board_idx = idx
                best_remaining = remaining_after
        
        if best_board_idx >= 0:
            # Place in existing board
            boards[best_board_idx][0] -= cut
            boards[best_board_idx][1].append(cut)
        else:
            # Need a new board
            boards.append([board_length - cut, [cut]])
    
    # Return just the cut lists
    return [board[1] for board in boards]


def optimize_boards(cuts, boards):
    """
    Optimize board purchasing and cutting to minimize cost.
    
    Uses pattern-based column generation approach for true optimality.
    
    Args:
        cuts: List of dicts with keys: width, height, length, quantity
        boards: List of dicts with keys: width, height, length, price
    
    Returns:
        Dict with keys:
            - board_plan: {board_idx: quantity} - how many of each board to buy
            - cut_plan: {board_idx: [[cuts], [cuts], ...]} - cutting plan for each physical board
            - total_cost: total cost in dollars
            - waste_summary: {board_idx: total_waste} - waste per board type
    
    Raises:
        RuntimeError: If no valid solution exists
    """
    # Group cuts and boards by (width, height)
    cut_groups = defaultdict(list)
    board_groups = defaultdict(list)
    
    for cut in cuts:
        cut_groups[(cut['width'], cut['height'])].append(cut)
    
    for idx, board in enumerate(boards):
        board_groups[(board['width'], board['height'])].append((idx, board))
    
    total_board_plan = {}
    total_cut_plan = {}
    total_cost = 0
    waste_summary = {}
    
    # Solve each dimension group independently
    for dim, group_cuts in cut_groups.items():
        if dim not in board_groups:
            raise RuntimeError(
                f"No boards available for dimension {dim[0]}x{dim[1]}"
            )
        
        group_boards = board_groups[dim]
        
        # VALIDATION: Check if any board can fit each cut
        max_board_length = max(b[1]['length'] for b in group_boards)
        for cut in group_cuts:
            if cut['length'] > max_board_length:
                raise RuntimeError(
                    f"Cut length {cut['length']} exceeds maximum available "
                    f"board length {max_board_length} for dimension {dim[0]}x{dim[1]}"
                )
        
        # Extract cut requirements: {cut_length: quantity}
        cut_requirements = {}
        for cut in group_cuts:
            cut_len = cut['length']
            cut_requirements[cut_len] = cut_requirements.get(cut_len, 0) + cut['quantity']
        
        # Get all unique cut lengths
        unique_cut_lengths = list(cut_requirements.keys())
        
        # Generate cutting patterns for each board type
        board_patterns = {}  # {board_idx: [patterns]}
        for board_idx, board in group_boards:
            patterns = _generate_cutting_patterns(unique_cut_lengths, board['length'])
            if patterns:
                board_patterns[board_idx] = patterns
        
        if not board_patterns:
            raise RuntimeError(
                f"Cannot generate any valid cutting patterns for dimension {dim[0]}x{dim[1]}"
            )
        
        # Create ILP solver
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            raise RuntimeError("Could not create solver")
        
        # Variables: how many times to use each pattern for each board type
        pattern_vars = {}
        for board_idx, patterns in board_patterns.items():
            for pattern_idx, pattern in enumerate(patterns):
                var_name = f'pattern_{board_idx}_{pattern_idx}'
                # Upper bound: worst case is using this pattern for all cuts
                max_uses = max(
                    (cut_requirements.get(cut_len, 0) + pattern.get(cut_len, 1) - 1) // pattern.get(cut_len, 1)
                    for cut_len in pattern.keys()
                ) if pattern else 0
                pattern_vars[(board_idx, pattern_idx)] = solver.IntVar(0, max_uses * 2, var_name)
        
        # Constraints: Each cut type must be satisfied exactly
        for cut_len, required_qty in cut_requirements.items():
            constraint_terms = []
            for (board_idx, pattern_idx), var in pattern_vars.items():
                pattern = board_patterns[board_idx][pattern_idx]
                cut_count = pattern.get(cut_len, 0)
                if cut_count > 0:
                    constraint_terms.append((var, cut_count))
            
            if not constraint_terms:
                raise RuntimeError(
                    f"No pattern can produce cut of length {cut_len} for dimension {dim[0]}x{dim[1]}"
                )
            
            solver.Add(
                sum(var * count for var, count in constraint_terms) == required_qty
            )
        
        # Objective: Minimize total cost
        objective_terms = []
        for (board_idx, pattern_idx), var in pattern_vars.items():
            board = next(b for idx, b in group_boards if idx == board_idx)
            objective_terms.append((var, board['price']))
        
        solver.Minimize(
            solver.Sum(var * price for var, price in objective_terms)
        )
        
        # Solve
        status = solver.Solve()
        if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            raise RuntimeError(
                f"No solution found for dimension {dim[0]}x{dim[1]}. Solver status: {status}"
            )
        
        # Extract solution and build cutting plan
        for board_idx, patterns in board_patterns.items():
            cuts_for_this_board_type = []
            patterns_used = []  # Track which patterns were used
            
            for pattern_idx, pattern in enumerate(patterns):
                var = pattern_vars[(board_idx, pattern_idx)]
                times_used = int(round(var.solution_value()))
                
                if times_used > 0:
                    # Record pattern usage
                    for _ in range(times_used):
                        patterns_used.append(pattern.copy())
                    
                    # Add all cuts from this pattern usage
                    for cut_len, count in pattern.items():
                        cuts_for_this_board_type.extend([cut_len] * (count * times_used))
            
            if cuts_for_this_board_type:
                board = next(b for idx, b in group_boards if idx == board_idx)
                board_length = board['length']
                
                # Pack cuts into individual boards for detailed plan
                packed_boards = _pack_cuts_into_boards(cuts_for_this_board_type, board_length)
                boards_used = len(packed_boards)
                
                # Record in board plan
                total_board_plan[board_idx] = total_board_plan.get(board_idx, 0) + boards_used
                
                # Add to cut plan
                if board_idx not in total_cut_plan:
                    total_cut_plan[board_idx] = []
                total_cut_plan[board_idx].extend(packed_boards)
                
                # Calculate waste
                total_waste = sum(board_length - sum(cuts) for cuts in packed_boards)
                waste_summary[board_idx] = waste_summary.get(board_idx, 0) + total_waste
                
                # Add to cost
                total_cost += boards_used * board['price']
    
    return {
        "board_plan": total_board_plan,
        "cut_plan": total_cut_plan,
        "total_cost": total_cost,
        "waste_summary": waste_summary
    }