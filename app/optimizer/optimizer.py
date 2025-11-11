# app/optimizer/optimizer.py
"""
Enhanced Lumber Optimizer

Function: optimize_boards(cuts, boards)

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

Key Features:

1. Each board’s cuts are tracked individually in cut_plan.
2. Best Fit Decreasing (FFD) bin-packing algorithm efficiently assigns cuts to boards.
3. Waste per board type is calculated and summarized.
4. Chooses the lowest-cost combination of boards that satisfies all cut requirements.
5. Output can be easily converted into human-readable cutting instructions.

Example Usage:

result = optimize_boards(cuts, boards)
print(result["board_plan"])
print(result["cut_plan"])
print(result["total_cost"])
print(result["waste_summary"])
"""

from ortools.linear_solver import pywraplp
from collections import defaultdict
import math


def _pack_cuts_into_boards(cuts_list, board_length, num_boards=None):
    """
    Pack a list of cut lengths into individual boards using Best Fit Decreasing.

    Args:
        cuts_list: List of cut lengths to pack (e.g., [10, 10, 20, 5])
        board_length: Length of each board
        num_boards: Maximum number of boards (None for unlimited)

    Returns:
        List of lists, where each inner list is the cuts for one board
        Example: [[10, 5], [10, 20]] means board 1 has cuts of 10 and 5
    """
    if not cuts_list:
        return []

    # Sort cuts in descending order for better packing (Best Fit Decreasing)
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
            if num_boards is not None and len(boards) >= num_boards:
                total_needed = sum(cuts_list)
                total_available = num_boards * board_length
                raise RuntimeError(
                    f"Cannot fit cuts into {num_boards} boards of length {board_length}. "
                    f"Total cut length: {total_needed}\", Available space: {total_available}\" "
                    f"(bin packing inefficiency: {total_needed/total_available:.1%})"
                )
            boards.append([board_length - cut, [cut]])

    # Return just the cut lists
    return [board[1] for board in boards]


def optimize_boards(cuts, boards):
    """
    Optimize board purchasing and cutting to minimize cost.

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

        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            raise RuntimeError("Could not create solver")

        num_cuts = len(group_cuts)
        num_boards = len(group_boards)

        # Estimate max boards needed with generous buffer for bin packing
        max_needed = []
        for _, b in group_boards:
            board_len = b['length']

            # Calculate worst-case: each cut type might need its own set of boards
            worst_case = 0
            for cut in group_cuts:
                if cut['length'] <= board_len:
                    cuts_per_board = board_len // cut['length']
                    if cuts_per_board > 0:
                        worst_case += math.ceil(cut['quantity'] / cuts_per_board)

            # Also calculate based on total length with 100% buffer for packing inefficiency
            total_length = sum(c['length'] * c['quantity'] for c in group_cuts)
            length_based = math.ceil(total_length / board_len * 2.0)

            # Use the maximum plus safety margin
            max_needed.append(max(worst_case, length_based) + 2)

        # Variables: how many boards of each type to buy
        board_qty = [
            solver.IntVar(0, max_needed[j], f'board_qty_{dim}_{j}')
            for j in range(num_boards)
        ]

        # Variables: assign cut i to board type j
        assign = {}
        for i in range(num_cuts):
            for j in range(num_boards):
                if group_cuts[i]['length'] <= group_boards[j][1]['length']:
                    assign[(i, j)] = solver.IntVar(
                        0,
                        group_cuts[i]['quantity'],
                        f'assign_{dim}_{i}_{j}'
                    )

        # Constraint: Each cut quantity must be satisfied
        for i in range(num_cuts):
            valid_boards = [j for j in range(num_boards) if (i, j) in assign]
            if not valid_boards:
                raise RuntimeError(
                    f"Cut of length {group_cuts[i]['length']} cannot fit on any "
                    f"board for dimension {dim[0]}x{dim[1]}"
                )
            solver.Add(
                sum(assign[(i, j)] for j in valid_boards) == group_cuts[i]['quantity']
            )

        # Constraint: Total cut length must fit (relaxed - doesn't guarantee bin packing works)
        for j in range(num_boards):
            board_len = group_boards[j][1]['length']
            cuts_on_this_board = [i for i in range(num_cuts) if (i, j) in assign]

            if cuts_on_this_board:
                # Total length constraint
                solver.Add(
                    sum(assign[(i, j)] * group_cuts[i]['length'] for i in cuts_on_this_board)
                    <= board_qty[j] * board_len
                )

                # Per-cut-type constraint: can't put more cuts than physically fit
                for i in cuts_on_this_board:
                    cut_len = group_cuts[i]['length']
                    max_per_board = board_len // cut_len
                    if max_per_board > 0:
                        solver.Add(assign[(i, j)] <= board_qty[j] * max_per_board)

        # Objective: minimize cost
        solver.Minimize(
            solver.Sum(
                board_qty[j] * group_boards[j][1]['price']
                for j in range(num_boards)
            )
        )

        status = solver.Solve()
        if status != pywraplp.Solver.OPTIMAL:
            raise RuntimeError(
                f"No optimal solution found for dimension {dim[0]}x{dim[1]}. "
                f"Solver status: {status}"
            )

        # Build detailed cut plan and handle bin packing
        dimension_cost = 0
        for j, (board_idx, board) in enumerate(group_boards):
            # Collect all cuts assigned to this board type
            cuts_for_board_type = []
            for i in range(num_cuts):
                if (i, j) in assign:
                    count = int(assign[(i, j)].solution_value())
                    cuts_for_board_type.extend([group_cuts[i]['length']] * count)

            if cuts_for_board_type:
                board_length = board['length']

                # Pack cuts into boards (without limit to find actual need)
                packed_boards = _pack_cuts_into_boards(
                    cuts_for_board_type,
                    board_length,
                    num_boards=None
                )
                boards_actually_used = len(packed_boards)

                # Record actual boards used
                total_board_plan[board_idx] = total_board_plan.get(board_idx, 0) + boards_actually_used

                # Add to cut plan
                if board_idx not in total_cut_plan:
                    total_cut_plan[board_idx] = []
                total_cut_plan[board_idx].extend(packed_boards)

                # Calculate waste
                total_waste = sum(
                    board_length - sum(cuts) for cuts in packed_boards
                )
                waste_summary[board_idx] = waste_summary.get(board_idx, 0) + total_waste

                # Add to cost
                dimension_cost += boards_actually_used * board['price']

        total_cost += dimension_cost

    return {
        "board_plan": total_board_plan,
        "cut_plan": total_cut_plan,
        "total_cost": total_cost,
        "waste_summary": waste_summary
    }