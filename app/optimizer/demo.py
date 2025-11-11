# demo_optimizer_output.py
"""
Demonstration of the enhanced optimizer output with detailed cutting plans
run by doing the following from repo directory:
    python -m app.optimizer.demo
"""
from app.optimizer.optimizer import optimize_boards


def print_cutting_plan(result, boards):
    """Print human-readable cutting instructions"""
    print("=" * 60)
    print("SHOPPING LIST")
    print("=" * 60)
    for board_idx, quantity in result["board_plan"].items():
        board = boards[board_idx]
        print(f"Buy {quantity}x {board['width']}x{board['height']}x{board['length']}\" "
              f"boards @ ${board['price']} each")

    print(f"\nTotal Cost: ${result['total_cost']}")

    print("\n" + "=" * 60)
    print("CUTTING INSTRUCTIONS")
    print("=" * 60)

    for board_idx, boards_list in result["cut_plan"].items():
        board = boards[board_idx]
        print(f"\n{board['width']}x{board['height']}x{board['length']}\" Boards:")

        for i, cuts_on_board in enumerate(boards_list, 1):
            waste = board['length'] - sum(cuts_on_board)
            cuts_str = " + ".join(f"{c}\"" for c in cuts_on_board)
            print(f"  Board #{i}: {cuts_str} = {sum(cuts_on_board)}\" "
                  f"(waste: {waste}\")")

    print("\n" + "=" * 60)
    print("WASTE SUMMARY")
    print("=" * 60)
    total_waste = 0
    for board_idx, waste in result["waste_summary"].items():
        board = boards[board_idx]
        print(f"{board['width']}x{board['height']}x{board['length']}\": {waste}\" total waste")
        total_waste += waste
    print(f"\nTotal waste: {total_waste}\"")


def example1_simple_project():
    """Simple project: build a small shelf"""
    print("\n\n### EXAMPLE 1: Small Shelf Project ###\n")

    cuts = [
        {"width": 2, "height": 4, "length": 24, "quantity": 3},  # shelves
        {"width": 2, "height": 4, "length": 36, "quantity": 2},  # sides
        {"width": 2, "height": 4, "length": 20, "quantity": 2},  # supports
    ]

    boards = [
        {"width": 2, "height": 4, "length": 96, "price": 8},
        {"width": 2, "height": 4, "length": 72, "price": 6},
    ]

    result = optimize_boards(cuts, boards)
    print_cutting_plan(result, boards)


def example2_deck_project():
    """Larger project: deck joists"""
    print("\n\n### EXAMPLE 2: Deck Joists ###\n")

    cuts = [
        {"width": 2, "height": 6, "length": 120, "quantity": 12},  # main joists
        {"width": 2, "height": 6, "length": 24, "quantity": 8},   # blocking
    ]

    boards = [
        {"width": 2, "height": 6, "length": 144, "price": 22},
        {"width": 2, "height": 6, "length": 96, "price": 16},
    ]

    result = optimize_boards(cuts, boards)
    print_cutting_plan(result, boards)


def example3_mixed_cuts():
    """Project with various cut sizes"""
    print("\n\n### EXAMPLE 3: Mixed Cuts ###\n")

    cuts = [
        {"width": 2, "height": 4, "length": 8, "quantity": 5},
        {"width": 2, "height": 4, "length": 12, "quantity": 3},
        {"width": 2, "height": 4, "length": 16, "quantity": 2},
        {"width": 2, "height": 4, "length": 6, "quantity": 4},
    ]

    boards = [
        {"width": 2, "height": 4, "length": 96, "price": 8},
    ]

    result = optimize_boards(cuts, boards)
    print_cutting_plan(result, boards)


def example4_optimal_choice():
    """Demonstrates optimizer choosing between board sizes"""
    print("\n\n### EXAMPLE 4: Board Size Optimization ###\n")

    cuts = [
        {"width": 2, "height": 4, "length": 30, "quantity": 5},
    ]

    boards = [
        {"width": 2, "height": 4, "length": 96, "price": 8},   # Can fit 3 cuts
        {"width": 2, "height": 4, "length": 72, "price": 6},   # Can fit 2 cuts
        {"width": 2, "height": 4, "length": 60, "price": 5},   # Can fit 2 cuts (tight)
    ]

    result = optimize_boards(cuts, boards)
    print_cutting_plan(result, boards)

    print("\nNote: Optimizer chose the most cost-effective combination!")


if __name__ == "__main__":
    example1_simple_project()
    example2_deck_project()
    example3_mixed_cuts()
    example4_optimal_choice()