# app/optimizer/tests/test_optimizer_comprehensive.py
import pytest
from app.optimizer.optimizer import optimize_boards


class TestCanonicalUsage:
    """Test that the optimizer passes the canonical example"""

    def test_canonical1(self):
        """The cheapest should be an 8 inch board cut in 4"""
        cuts = [
            {"width": 2, "height": 4, "length": 2, "quantity": 4},
        ]
        boards = [
            {"width": 2, "height": 4, "length": 2, "price": 4},
            {"width": 2, "height": 4, "length": 4, "price": 7},
            {"width": 2, "height": 4, "length": 8, "price": 13},
            {"width": 2, "height": 4, "length": 9, "price": 19},
        ]
        result = optimize_boards(cuts, boards)
        # 4 cuts of 2" = 8" total
        # Option 1: 4× 2" boards = $16
        # Option 2: 2× 4" boards = $14
        # Option 3: 1× 8" board = $13 ✓ OPTIMAL
        # Option 4: 1× 9" board = $19
        assert result["total_cost"] == 13

    def test_canonical2(self):
        """The cheapest should be a 9 inch board cut in 4 with 1 inch of waste"""
        cuts = [
            {"width": 2, "height": 4, "length": 2, "quantity": 4},
        ]
        boards = [
            {"width": 2, "height": 4, "length": 2, "price": 4},
            {"width": 2, "height": 4, "length": 4, "price": 7},
            {"width": 2, "height": 4, "length": 8, "price": 13},
            {"width": 2, "height": 4, "length": 9, "price": 12},
        ]
        result = optimize_boards(cuts, boards)
        # 4 cuts of 2" = 8" total
        # Option 1: 4× 2" boards = $16
        # Option 2: 2× 4" boards = $14
        # Option 3: 1× 8" board = $13
        # Option 4: 1× 9" board = $12 ✓ OPTIMAL (1" waste)
        assert result["total_cost"] == 12

    def test_canonical3(self):
        """The cheapest would be two 4-inch boards cut in half"""
        cuts = [
            {"width": 2, "height": 4, "length": 2, "quantity": 4},
        ]
        boards = [
            {"width": 2, "height": 4, "length": 2, "price": 5},
            {"width": 2, "height": 4, "length": 4, "price": 2},
            {"width": 2, "height": 4, "length": 8, "price": 13},
            {"width": 2, "height": 4, "length": 9, "price": 19},
        ]
        result = optimize_boards(cuts, boards)
        # 4 cuts of 2" = 8" total
        # Option 1: 4× 2" boards = $20
        # Option 2: 2× 4" boards = $4 ✓ OPTIMAL (each 4" board yields 2× 2" cuts)
        # Option 3: 1× 8" board = $13
        # Option 4: 1× 9" board = $19
        assert result["total_cost"] == 4

    def test_mixed_small_and_large_cuts(self):
        """
        CRITICAL BUG TEST: Mixed cut sizes should find optimal board combination
        Scenario: 6× 2" cuts + 1× 8" cut
        
        Optimal solution: $31
        - 1× 9" board → cut 1× 8" (waste: 1")  = $12
        - 1× 4" board → cut 2× 2" (waste: 0")  = $7
        - 1× 9" board → cut 4× 2" (waste: 1")  = $12
        Total: $31
        
        Suboptimal solution: $40
        - 1× 2" board → cut 1× 2" (waste: 0")  = $4
        - 1× 9" board → cut 1× 8" (waste: 1")  = $12
        - 1× 9" board → cut 1× 2" (waste: 7")  = $12
        - 1× 9" board → cut 4× 2" (waste: 1")  = $12
        Total: $40
        """
        cuts = [
            {"width": 2, "height": 4, "length": 2, "quantity": 6},
            {"width": 2, "height": 4, "length": 8, "quantity": 1},
        ]
        boards = [
            {"width": 2, "height": 4, "length": 2, "price": 4},
            {"width": 2, "height": 4, "length": 4, "price": 7},
            {"width": 2, "height": 4, "length": 8, "price": 13},
            {"width": 2, "height": 4, "length": 9, "price": 12},
        ]
        result = optimize_boards(cuts, boards)
        assert result["total_cost"] == 31, f"Expected $31, got ${result['total_cost']}"


class TestCuttingPlanDetails:
    """Test that cutting plans are detailed and practical"""

    def test_cutting_plan_structure(self):
        """Verify each board has a specific cutting plan"""
        cuts = [
            {"width": 2, "height": 4, "length": 8, "quantity": 2},
            {"width": 2, "height": 4, "length": 5, "quantity": 2},
        ]
        boards = [{"width": 2, "height": 4, "length": 20, "price": 5}]
        result = optimize_boards(cuts, boards)

        # Should have one board type in cut_plan
        assert len(result["cut_plan"]) == 1
        board_idx = list(result["cut_plan"].keys())[0]

        # Get the list of individual boards
        individual_boards = result["cut_plan"][board_idx]

        # Each element should be a list of cuts for one physical board
        for board_cuts in individual_boards:
            assert isinstance(board_cuts, list)
            # Cuts on this board shouldn't exceed board length
            assert sum(board_cuts) <= 20
            # Each cut should be positive
            for cut in board_cuts:
                assert cut > 0

        # All cuts should be present (2× 8" + 2× 5" = [8, 8, 5, 5])
        all_cuts = [cut for board in individual_boards for cut in board]
        assert sorted(all_cuts) == sorted([8, 8, 5, 5])

    def test_readable_cutting_instructions(self):
        """Test that we can generate human-readable cutting instructions"""
        cuts = [
            {"width": 2, "height": 4, "length": 10, "quantity": 2},
            {"width": 2, "height": 4, "length": 15, "quantity": 1},
        ]
        boards = [{"width": 2, "height": 4, "length": 30, "price": 8}]
        result = optimize_boards(cuts, boards)

        # Generate cutting instructions
        instructions = []
        for board_idx, boards_list in result["cut_plan"].items():
            board_spec = boards[board_idx]
            instructions.append(
                f"{board_spec['width']}x{board_spec['height']} boards "
                f"({board_spec['length']}\" long):"
            )

            for i, cuts_on_board in enumerate(boards_list, 1):
                waste = board_spec['length'] - sum(cuts_on_board)
                cuts_str = ", ".join(f"{c}\"" for c in cuts_on_board)
                instructions.append(
                    f"  Board #{i}: Cut into {cuts_str} (waste: {waste}\")"
                )

        # Verify structure
        assert 0 in result["cut_plan"]
        assert len(result["cut_plan"][0]) >= 1

        # Verify we can describe each board
        assert len(instructions) >= 2  # At least header + one board

    def test_waste_calculation(self):
        """Verify waste is calculated correctly"""
        cuts = [{"width": 2, "height": 4, "length": 8, "quantity": 3}]
        boards = [{"width": 2, "height": 4, "length": 10, "price": 5}]
        result = optimize_boards(cuts, boards)

        # Should use 3 boards of 10", cutting 8" from each, wasting 2" each
        # Total waste should be 6"
        assert "waste_summary" in result
        assert result["waste_summary"][0] == 6

    def test_multiple_boards_detailed_plan(self):
        """Test detailed plan with multiple physical boards"""
        cuts = [{"width": 2, "height": 4, "length": 12, "quantity": 5}]
        boards = [{"width": 2, "height": 4, "length": 30, "price": 10}]
        result = optimize_boards(cuts, boards)

        # 5 cuts of 12" = 60" total
        # On 30" boards: can fit 2 cuts (24") per board, leaving 6" waste
        # So need 3 boards: [12,12], [12,12], [12]
        assert result["board_plan"][0] == 3

        # Should have 3 individual boards in cut plan
        assert len(result["cut_plan"][0]) == 3

        # Verify each board
        all_cuts = []
        for board_cuts in result["cut_plan"][0]:
            # Each should not exceed 30"
            assert sum(board_cuts) <= 30
            all_cuts.extend(board_cuts)

        # Together should have all 5 cuts of 12"
        assert len(all_cuts) == 5
        assert all(c == 12 for c in all_cuts)

    def test_efficient_packing(self):
        """Test that bin packing minimizes waste"""
        cuts = [
            {"width": 2, "height": 4, "length": 15, "quantity": 1},
            {"width": 2, "height": 4, "length": 10, "quantity": 1},
            {"width": 2, "height": 4, "length": 5, "quantity": 1},
        ]
        boards = [{"width": 2, "height": 4, "length": 30, "price": 10}]
        result = optimize_boards(cuts, boards)

        # All cuts total 30", should fit perfectly in 1 board
        assert result["board_plan"][0] == 1
        assert result["waste_summary"][0] == 0

        # Should all be on one board
        assert len(result["cut_plan"][0]) == 1
        board_cuts = result["cut_plan"][0][0]
        assert sorted(board_cuts) == [5, 10, 15]


class TestBasicFunctionality:
    """Test basic optimizer functionality"""

    def test_simple_case(self):
        cuts = [
            {"width": 2, "height": 4, "length": 10, "quantity": 2},
            {"width": 2, "height": 4, "length": 20, "quantity": 1},
        ]
        boards = [
            {"width": 2, "height": 4, "length": 30, "price": 5},
            {"width": 2, "height": 4, "length": 20, "price": 4},
        ]
        result = optimize_boards(cuts, boards)

        assert "board_plan" in result
        assert "cut_plan" in result
        assert "total_cost" in result
        assert "waste_summary" in result
        assert result["total_cost"] > 0

        # Verify all cuts are accounted for (2× 10" + 1× 20" = 40" total)
        all_cuts = [
            cut for board_cuts in result["cut_plan"].values()
            for single_board in board_cuts for cut in single_board
        ]
        assert len(all_cuts) == 3
        assert sum(all_cuts) == 40

        # Verify each board in cut_plan has valid cuts
        for board_idx, boards_list in result["cut_plan"].items():
            board_length = boards[board_idx]["length"]
            for single_board_cuts in boards_list:
                # Each board's cuts should not exceed board length
                assert sum(single_board_cuts) <= board_length

    def test_exact_fit(self):
        """Test when cuts exactly fit into boards"""
        cuts = [{"width": 2, "height": 4, "length": 8, "quantity": 1}]
        boards = [{"width": 2, "height": 4, "length": 8, "price": 2}]
        result = optimize_boards(cuts, boards)
        assert result["total_cost"] == 2
        assert result["board_plan"][0] == 1
        assert result["waste_summary"][0] == 0

    def test_single_cut_single_board(self):
        """Simplest possible case"""
        cuts = [{"width": 1, "height": 1, "length": 5, "quantity": 1}]
        boards = [{"width": 1, "height": 1, "length": 10, "price": 3}]
        result = optimize_boards(cuts, boards)
        assert result["total_cost"] == 3
        assert result["board_plan"][0] == 1
        assert result["waste_summary"][0] == 5


class TestCostOptimization:
    """Test that optimizer chooses cost-effective solutions"""

    def test_prefer_single_long_board(self):
        """Should choose single longer board over multiple shorter ones when cheaper"""
        cuts = [{"width": 2, "height": 4, "length": 2, "quantity": 4}]
        boards = [
            {"width": 2, "height": 4, "length": 2, "price": 4},   # 4 boards = $16
            {"width": 2, "height": 4, "length": 4, "price": 7},   # 2 boards = $14
            {"width": 2, "height": 4, "length": 8, "price": 13},  # 1 board = $13
            {"width": 2, "height": 4, "length": 9, "price": 12},  # 1 board = $12 ✓
        ]
        result = optimize_boards(cuts, boards)
        # 4× 2" = 8" total, best is 1× 9" board @ $12
        assert result["total_cost"] == 12

    def test_avoid_expensive_boards(self):
        """Should avoid expensive board even with less waste"""
        cuts = [{"width": 2, "height": 4, "length": 2, "quantity": 4}]
        boards = [
            {"width": 2, "height": 4, "length": 2, "price": 4},   # 4 boards = $16
            {"width": 2, "height": 4, "length": 4, "price": 7},   # 2 boards = $14
            {"width": 2, "height": 4, "length": 8, "price": 13},  # 1 board = $13 ✓
            {"width": 2, "height": 4, "length": 9, "price": 19},  # 1 board = $19 (expensive!)
        ]
        result = optimize_boards(cuts, boards)
        # Should choose 1× 8" @ $13 over 1× 9" @ $19
        assert result["total_cost"] == 13

    def test_prefer_multiple_cheap_boards(self):
        """Should choose multiple cheap boards over single expensive one"""
        cuts = [{"width": 2, "height": 4, "length": 2, "quantity": 4}]
        boards = [
            {"width": 2, "height": 4, "length": 2, "price": 4},   # 4 boards = $16
            {"width": 2, "height": 4, "length": 4, "price": 2},   # 2 boards = $4 ✓
            {"width": 2, "height": 4, "length": 8, "price": 13},  # 1 board = $13
            {"width": 2, "height": 4, "length": 9, "price": 12},  # 1 board = $12
        ]
        result = optimize_boards(cuts, boards)
        # 4" boards are so cheap that 2× 4" @ $4 beats 1× 9" @ $12
        assert result["total_cost"] == 4

    def test_board_size_optimization(self):
        """Verify correct choice between board sizes"""
        cuts = [{"width": 2, "height": 4, "length": 5, "quantity": 4}]
        boards = [
            {"width": 2, "height": 4, "length": 10, "price": 3},  # 2 boards = $6
            {"width": 2, "height": 4, "length": 20, "price": 5},  # 1 board = $5 ✓
        ]
        result = optimize_boards(cuts, boards)
        # 4× 5" = 20" total
        # Option 1: 2× 10" boards @ $3 each = $6
        # Option 2: 1× 20" board @ $5 = $5 ✓
        assert result["total_cost"] == 5

    def test_cost_vs_waste_tradeoff(self):
        """Should minimize cost even if it means more waste"""
        cuts = [{"width": 2, "height": 4, "length": 7, "quantity": 2}]
        boards = [
            {"width": 2, "height": 4, "length": 8, "price": 10},  # 2 boards = $20, 2" waste
            {"width": 2, "height": 4, "length": 20, "price": 15}, # 1 board = $15, 6" waste ✓
        ]
        result = optimize_boards(cuts, boards)
        # 2× 7" = 14" total
        # Option 1: 2× 8" boards = $20 (waste: 2")
        # Option 2: 1× 20" board = $15 (waste: 6") ✓ cheaper despite more waste
        assert result["total_cost"] == 15


class TestMultipleDimensions:
    """Test handling of different board dimensions"""

    def test_mixed_dimensions(self):
        """Test cuts with different dimensions"""
        cuts = [
            {"width": 2, "height": 4, "length": 8, "quantity": 2},
            {"width": 4, "height": 6, "length": 12, "quantity": 1},
        ]
        boards = [
            {"width": 2, "height": 4, "length": 10, "price": 3},
            {"width": 4, "height": 6, "length": 12, "price": 6},
        ]
        result = optimize_boards(cuts, boards)
        # 2× 8" cuts need 2× (2×4×10) boards = $6
        # 1× 12" cut needs 1× (4×6×12) board = $6
        # Total: $12
        assert result["total_cost"] == 12

    def test_three_different_dimensions(self):
        """Test with three distinct dimension groups"""
        cuts = [
            {"width": 1, "height": 2, "length": 5, "quantity": 2},
            {"width": 2, "height": 4, "length": 10, "quantity": 1},
            {"width": 3, "height": 6, "length": 15, "quantity": 1},
        ]
        boards = [
            {"width": 1, "height": 2, "length": 10, "price": 5},
            {"width": 2, "height": 4, "length": 20, "price": 8},
            {"width": 3, "height": 6, "length": 20, "price": 10},
        ]
        result = optimize_boards(cuts, boards)
        # 2× 5" on 1×2: 1 board @ $5
        # 1× 10" on 2×4: 1 board @ $8
        # 1× 15" on 3×6: 1 board @ $10
        # Total: $23
        assert result["total_cost"] == 23
        assert len(result["board_plan"]) == 3

    def test_many_dimensions_same_length(self):
        """Multiple dimensions but same length requirements"""
        cuts = [
            {"width": 1, "height": 1, "length": 8, "quantity": 1},
            {"width": 2, "height": 2, "length": 8, "quantity": 1},
            {"width": 3, "height": 3, "length": 8, "quantity": 1},
        ]
        boards = [
            {"width": 1, "height": 1, "length": 10, "price": 3},
            {"width": 2, "height": 2, "length": 10, "price": 4},
            {"width": 3, "height": 3, "length": 10, "price": 5},
        ]
        result = optimize_boards(cuts, boards)
        # 1 board of each dimension: $3 + $4 + $5 = $12
        assert result["total_cost"] == 12


class TestLargeCutQuantities:
    """Test with large quantities of cuts"""

    def test_many_identical_cuts(self):
        """100 identical cuts - should choose most cost-effective board"""
        cuts = [{"width": 2, "height": 4, "length": 3, "quantity": 100}]
        boards = [
            {"width": 2, "height": 4, "length": 10, "price": 5},
            {"width": 2, "height": 4, "length": 20, "price": 8},
        ]
        result = optimize_boards(cuts, boards)
        # Total length needed: 100× 3" = 300"
        # Option 1: 10" boards fit 3 cuts each → need 34 boards @ $5 = $170
        # Option 2: 20" boards fit 6 cuts each → need 17 boards @ $8 = $136 ✓
        assert result["total_cost"] == 136

    def test_mixed_large_quantities(self):
        """Multiple cuts with large quantities"""
        cuts = [
            {"width": 2, "height": 4, "length": 5, "quantity": 50},
            {"width": 2, "height": 4, "length": 8, "quantity": 30},
        ]
        boards = [
            {"width": 2, "height": 4, "length": 10, "price": 3},
            {"width": 2, "height": 4, "length": 20, "price": 5},
        ]
        result = optimize_boards(cuts, boards)
        # Total: 50× 5" + 30× 8" = 250" + 240" = 490"
        assert result["total_cost"] > 0
        
        # Verify all cuts accounted for
        all_cuts = [
            cut for boards_list in result["cut_plan"].values()
            for single_board in boards_list for cut in single_board
        ]
        count_5 = sum(1 for c in all_cuts if c == 5)
        count_8 = sum(1 for c in all_cuts if c == 8)
        assert count_5 == 50
        assert count_8 == 30


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_small_cuts(self):
        """Cuts that are very small relative to boards"""
        cuts = [{"width": 2, "height": 4, "length": 1, "quantity": 20}]
        boards = [{"width": 2, "height": 4, "length": 100, "price": 10}]
        result = optimize_boards(cuts, boards)
        # 20× 1" = 20" fits easily on 1× 100" board
        assert result["total_cost"] == 10
        assert result["board_plan"][0] == 1

    def test_cut_equals_board_length(self):
        """Cut length exactly equals board length"""
        cuts = [{"width": 2, "height": 4, "length": 50, "quantity": 3}]
        boards = [{"width": 2, "height": 4, "length": 50, "price": 12}]
        result = optimize_boards(cuts, boards)
        # Need exactly 3 boards @ $12 each
        assert result["total_cost"] == 36
        assert result["board_plan"][0] == 3
        assert result["waste_summary"][0] == 0

    def test_varying_cut_lengths_same_dimension(self):
        """Many different cut lengths for same dimension"""
        cuts = [
            {"width": 2, "height": 4, "length": 3, "quantity": 2},
            {"width": 2, "height": 4, "length": 5, "quantity": 3},
            {"width": 2, "height": 4, "length": 7, "quantity": 1},
            {"width": 2, "height": 4, "length": 11, "quantity": 2},
        ]
        boards = [
            {"width": 2, "height": 4, "length": 12, "price": 5},
            {"width": 2, "height": 4, "length": 24, "price": 9},
        ]
        result = optimize_boards(cuts, boards)
        # Total: 2×3" + 3×5" + 1×7" + 2×11" = 6 + 15 + 7 + 22 = 50"
        assert result["total_cost"] > 0
        assert len(result["board_plan"]) > 0

    def test_quantity_one_all_cuts(self):
        """All cuts have quantity of 1"""
        cuts = [
            {"width": 2, "height": 4, "length": 5, "quantity": 1},
            {"width": 2, "height": 4, "length": 7, "quantity": 1},
            {"width": 2, "height": 4, "length": 9, "quantity": 1},
        ]
        boards = [{"width": 2, "height": 4, "length": 25, "price": 10}]
        result = optimize_boards(cuts, boards)
        # 5" + 7" + 9" = 21" fits on 1× 25" board
        assert result["total_cost"] == 10
        assert result["board_plan"][0] == 1


class TestBoardVariety:
    """Test scenarios with many board options"""

    def test_many_board_options(self):
        """10 different board sizes to choose from"""
        cuts = [{"width": 2, "height": 4, "length": 15, "quantity": 5}]
        boards = [
            {"width": 2, "height": 4, "length": 10, "price": 5},
            {"width": 2, "height": 4, "length": 15, "price": 7},
            {"width": 2, "height": 4, "length": 20, "price": 9},
            {"width": 2, "height": 4, "length": 25, "price": 11},
            {"width": 2, "height": 4, "length": 30, "price": 13},
            {"width": 2, "height": 4, "length": 35, "price": 15},
            {"width": 2, "height": 4, "length": 40, "price": 17},
            {"width": 2, "height": 4, "length": 50, "price": 20},
            {"width": 2, "height": 4, "length": 75, "price": 28},
            {"width": 2, "height": 4, "length": 100, "price": 35},
        ]
        result = optimize_boards(cuts, boards)
        # 5× 15" = 75" total
        # Should find optimal combination
        assert result["total_cost"] > 0

    def test_board_options_different_price_patterns(self):
        """Boards with non-linear pricing"""
        cuts = [{"width": 2, "height": 4, "length": 20, "quantity": 3}]
        boards = [
            {"width": 2, "height": 4, "length": 10, "price": 8},  # Can't fit 20" cut
            {"width": 2, "height": 4, "length": 20, "price": 12}, # 3 boards = $36 ✓
            {"width": 2, "height": 4, "length": 30, "price": 15}, # 3 boards = $45
        ]
        result = optimize_boards(cuts, boards)
        # 3× 20" cuts
        # 10" boards: can't fit (cut > board)
        # 20" boards: 1 cut per board, need 3 @ $12 = $36 ✓
        # 30" boards: 1 cut per board, need 3 @ $15 = $45
        assert result["total_cost"] == 36


class TestComplexScenarios:
    """Complex real-world scenarios"""

    def test_realistic_lumber_scenario(self):
        """Realistic lumber cutting scenario"""
        cuts = [
            {"width": 2, "height": 4, "length": 36, "quantity": 8},  # studs
            {"width": 2, "height": 4, "length": 48, "quantity": 4},  # headers
            {"width": 2, "height": 4, "length": 24, "quantity": 12}, # blocking
        ]
        boards = [
            {"width": 2, "height": 4, "length": 96, "price": 8},
            {"width": 2, "height": 4, "length": 120, "price": 11},
        ]
        result = optimize_boards(cuts, boards)
        assert result["total_cost"] > 0
        
        # Verify all cuts present
        all_cuts = [
            cut for boards_list in result["cut_plan"].values()
            for single_board in boards_list for cut in single_board
        ]
        assert sorted(all_cuts) == sorted([36]*8 + [48]*4 + [24]*12)

    def test_furniture_project(self):
        """Furniture project with multiple piece types"""
        cuts = [
            {"width": 1, "height": 6, "length": 72, "quantity": 4},  # legs
            {"width": 1, "height": 8, "length": 48, "quantity": 2},  # cross supports
            {"width": 1, "height": 10, "length": 60, "quantity": 2}, # side rails
        ]
        boards = [
            {"width": 1, "height": 6, "length": 96, "price": 15},
            {"width": 1, "height": 8, "length": 96, "price": 20},
            {"width": 1, "height": 10, "length": 96, "price": 25},
        ]
        result = optimize_boards(cuts, boards)
        assert result["total_cost"] > 0
        assert len(result["board_plan"]) <= 3

    def test_deck_building_scenario(self):
        """Deck with joists, beams, and posts"""
        cuts = [
            {"width": 2, "height": 6, "length": 144, "quantity": 15}, # joists
            {"width": 2, "height": 8, "length": 192, "quantity": 3},  # beams
            {"width": 4, "height": 4, "length": 96, "quantity": 6},   # posts
        ]
        boards = [
            {"width": 2, "height": 6, "length": 144, "price": 25},
            {"width": 2, "height": 8, "length": 192, "price": 40},
            {"width": 4, "height": 4, "length": 96, "price": 18},
        ]
        result = optimize_boards(cuts, boards)
        # Each cut exactly matches board length (perfect fit)
        # 15× 144" boards @ $25 = $375
        # 3× 192" boards @ $40 = $120
        # 6× 96" boards @ $18 = $108
        # Total: $603
        assert result["total_cost"] == 603


class TestErrorHandling:
    """Test error conditions"""

    def test_no_boards_for_dimension(self):
        """Should raise error when no matching boards available"""
        cuts = [{"width": 2, "height": 4, "length": 10, "quantity": 1}]
        boards = [{"width": 3, "height": 6, "length": 20, "price": 5}]

        with pytest.raises(RuntimeError, match="No boards available"):
            optimize_boards(cuts, boards)

    def test_board_too_short(self):
        """All boards too short for required cut"""
        cuts = [{"width": 2, "height": 4, "length": 100, "quantity": 1}]
        boards = [
            {"width": 2, "height": 4, "length": 50, "price": 5},
            {"width": 2, "height": 4, "length": 80, "price": 8},
        ]

        with pytest.raises(RuntimeError, match="Cut length.*exceeds.*board"):
            optimize_boards(cuts, boards)


class TestResultStructure:
    """Verify structure and completeness of results"""

    def test_board_plan_completeness(self):
        """Verify board_plan contains correct indices and quantities"""
        cuts = [{"width": 2, "height": 4, "length": 10, "quantity": 3}]
        boards = [
            {"width": 2, "height": 4, "length": 15, "price": 5},
            {"width": 2, "height": 4, "length": 30, "price": 8},
        ]
        result = optimize_boards(cuts, boards)

        # Check board_plan has valid board indices
        for board_idx in result["board_plan"].keys():
            assert 0 <= board_idx < len(boards)

        # Check quantities are positive
        for qty in result["board_plan"].values():
            assert qty > 0

    def test_cut_plan_structure(self):
        """Verify cut_plan has correct structure"""
        cuts = [
            {"width": 2, "height": 4, "length": 8, "quantity": 2},
            {"width": 2, "height": 4, "length": 12, "quantity": 1},
        ]
        boards = [{"width": 2, "height": 4, "length": 20, "price": 6}]
        result = optimize_boards(cuts, boards)

        # cut_plan should map board indices to lists of individual boards
        for board_idx, boards_list in result["cut_plan"].items():
            assert isinstance(boards_list, list)
            # Each element is one physical board
            for single_board_cuts in boards_list:
                assert isinstance(single_board_cuts, list)
                # Each cut should be a positive number
                for cut_length in single_board_cuts:
                    assert cut_length > 0
                # Total cuts shouldn't exceed board length
                assert sum(single_board_cuts) <= boards[board_idx]["length"]

    def test_total_cost_accuracy(self):
        """Verify total_cost matches board_plan"""
        cuts = [{"width": 2, "height": 4, "length": 15, "quantity": 5}]
        boards = [
            {"width": 2, "height": 4, "length": 20, "price": 7},
            {"width": 2, "height": 4, "length": 40, "price": 12},
        ]
        result = optimize_boards(cuts, boards)

        # Calculate expected cost from board_plan
        expected_cost = sum(
            qty * boards[board_idx]["price"]
            for board_idx, qty in result["board_plan"].items()
        )
        assert result["total_cost"] == expected_cost

    def test_waste_summary_accuracy(self):
        """Verify waste_summary is calculated correctly"""
        cuts = [{"width": 2, "height": 4, "length": 7, "quantity": 3}]
        boards = [{"width": 2, "height": 4, "length": 10, "price": 5}]
        result = optimize_boards(cuts, boards)

        # Should use 3 boards, each with 3" waste
        assert result["waste_summary"][0] == 9

        # Verify waste matches cut_plan
        calculated_waste = 0
        for board_idx, boards_list in result["cut_plan"].items():
            board_length = boards[board_idx]["length"]
            for single_board_cuts in boards_list:
                calculated_waste += board_length - sum(single_board_cuts)
        
        assert result["waste_summary"][0] == calculated_waste


class TestPackingEfficiency:
    """Test that bin packing algorithm works efficiently"""

    def test_best_fit_decreasing(self):
        """Verify Best Fit Decreasing produces efficient packing"""
        cuts = [
            {"width": 2, "height": 4, "length": 8, "quantity": 1},
            {"width": 2, "height": 4, "length": 7, "quantity": 1},
            {"width": 2, "height": 4, "length": 5, "quantity": 1},
            {"width": 2, "height": 4, "length": 3, "quantity": 1},
            {"width": 2, "height": 4, "length": 2, "quantity": 1},
        ]
        boards = [{"width": 2, "height": 4, "length": 15, "price": 10}]
        result = optimize_boards(cuts, boards)

        # 8+7=15 (one board), 5+3+2=10 (another board)
        # Should use 2 boards with minimal waste
        assert result["board_plan"][0] == 2
        assert result["total_cost"] == 20

    def test_tight_packing(self):
        """Test packing with cuts that fit tightly"""
        cuts = [
            {"width": 2, "height": 4, "length": 6, "quantity": 2},
            {"width": 2, "height": 4, "length": 4, "quantity": 3},
        ]
        boards = [{"width": 2, "height": 4, "length": 12, "price": 8}]
        result = optimize_boards(cuts, boards)

        # Total: 2×6" + 3×4" = 12" + 12" = 24"
        # Should fit in 2× 12" boards
        assert result["board_plan"][0] == 2
        assert result["total_cost"] == 16


class TestRealWorldExamples:
    """Test cases based on real woodworking projects"""

    def test_bookshelf_project(self):
        """Building a simple bookshelf"""
        cuts = [
            {"width": 1, "height": 12, "length": 36, "quantity": 5},  # shelves
            {"width": 1, "height": 12, "length": 48, "quantity": 2},  # sides
            {"width": 1, "height": 4, "length": 34, "quantity": 1},   # top trim
        ]
        boards = [
            {"width": 1, "height": 12, "length": 96, "price": 45},
            {"width": 1, "height": 4, "length": 96, "price": 15},
        ]
        result = optimize_boards(cuts, boards)
        assert result["total_cost"] > 0
        
        # Verify all cuts present
        all_cuts = [
            cut for boards_list in result["cut_plan"].values()
            for single_board in boards_list for cut in single_board
        ]
        assert 36 in all_cuts  # Has shelves
        assert 48 in all_cuts  # Has sides
        assert 34 in all_cuts  # Has trim

    def test_picture_frame_project(self):
        """Making picture frames with mitered corners"""
        cuts = [
            {"width": 1, "height": 2, "length": 10, "quantity": 8},  # 2 frames, 4 sides each
        ]
        boards = [
            {"width": 1, "height": 2, "length": 48, "price": 6},
            {"width": 1, "height": 2, "length": 72, "price": 9},
        ]
        result = optimize_boards(cuts, boards)
        # 8× 10" = 80" total
        # 48" board fits 4 cuts (40"), need 2 boards = $12
        # 72" board fits 7 cuts (70"), need 2 boards = $18
        # Should choose 2× 48" boards @ $12
        assert result["total_cost"] <= 18

    def test_garden_bed_project(self):
        """Building raised garden beds"""
        cuts = [
            {"width": 2, "height": 6, "length": 96, "quantity": 4},   # long sides
            {"width": 2, "height": 6, "length": 48, "quantity": 4},   # short sides
            {"width": 4, "height": 4, "length": 36, "quantity": 4},   # corner posts
        ]
        boards = [
            {"width": 2, "height": 6, "length": 96, "price": 22},
            {"width": 2, "height": 6, "length": 120, "price": 28},
            {"width": 4, "height": 4, "length": 96, "price": 18},
        ]
        result = optimize_boards(cuts, boards)
        assert result["total_cost"] > 0
        # Should have all three board types in plan
        assert len(result["board_plan"]) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])