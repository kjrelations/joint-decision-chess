import pytest
from helpers import calculate_moves

# Example chess board setup
@pytest.fixture
def chess_board():
    return [
        ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
        ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
        [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
        [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
        [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
        [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
        ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
        ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
    ]

# Will need a print calculated board

# Sub-test 1: Valid Moves
def test_valid_moves(chess_board):
    # TODO captures
    # Sub-section 1: Pawns
    # Example 1: Pawns can move one square forward from their starting position.
    assert (2, 4) in calculate_moves(chess_board, 1, 4, None)[0]  # Black pawn can move one square forward
    assert (5, 4) in calculate_moves(chess_board, 6, 4, None)[0]  # White pawn can move one square forward

    # Example 2: Pawns can move two squares forward from their starting position.
    assert (4, 4) in calculate_moves(chess_board, 6, 4, None)[0]  # White pawn can move two squares forward from starting position
    assert (3, 4) in calculate_moves(chess_board, 1, 4, None)[0]  # Black pawn can move two squares forward from starting position

    # Example 3: Pawns can move one square forward otherwise.
    chess_board[2][4] = 'p'  # Place a black pawn
    chess_board[5][5] = 'P'  # Place a white pawn
    assert (3, 4) in calculate_moves(chess_board, 2, 4, None)[0]  # Black pawn can move one square forward
    assert (4, 5) in calculate_moves(chess_board, 5, 5, None)[0]  # White pawn can move one square forward
    chess_board[2][4] = ' '  # Clear the path
    chess_board[5][5] = ' '  # Clear the path

    # TODO Pawn captures, think the logic is sound though

    # Sub-section 2: Rooks
    # Example 4: Rooks can move horizontally or vertically from a single position.
    chess_board[3][3] = 'r'  # Place a black rook
    assert (3, 0) in calculate_moves(chess_board, 3, 3, None)[0]  # Black Rooks can move horizontally
    assert (3, 7) in calculate_moves(chess_board, 3, 3, None)[0]  # Black Rooks can move horizontally
    assert (2, 3) in calculate_moves(chess_board, 3, 3, None)[0]  # Black Rooks can move vertically
    assert (4, 3) in calculate_moves(chess_board, 3, 3, None)[0]  # Black Rooks can move vertically
    chess_board[3][3] = 'R'  # Place a white rook
    assert (3, 0) in calculate_moves(chess_board, 3, 3, None)[0]  # Rook can move vertically
    assert (3, 7) in calculate_moves(chess_board, 3, 3, None)[0]  # Rook can move vertically
    assert (2, 3) in calculate_moves(chess_board, 3, 3, None)[0]  # Rook can move vertically
    assert (4, 3) in calculate_moves(chess_board, 3, 3, None)[0]  # Rook can move vertically
    chess_board[3][3] = ' '  # Clear the path

    # Example 5: Rooks cannot move diagonally.
    chess_board[3][3] = 'R'  # Place a white rook
    assert (4, 4) not in calculate_moves(chess_board, 3, 3, None)[0]  # White Rook can't move diagonally
    chess_board[3][3] = 'r'  # Place a black rook
    assert (4, 4) not in calculate_moves(chess_board, 3, 3, None)[0]  # Black Rook can't move diagonally
    chess_board[3][3] = ' '  # Clear the path

    # Sub-section 3: Knights
    # Example 6: Knights can only make moves to one of the nearest squares not on the same row, column, or diagonal.
    chess_board[3][3] = 'R'  # Place a white rook
    assert set([(2, 0),(2, 2)]) == set(calculate_moves(chess_board, 0, 1, None)[0])  # Black Knight can move in an L-shape
    assert set([(5, 0),(5, 2)]) == set(calculate_moves(chess_board, 7, 1, None)[0])  # White Knight can move in an L-shape
    chess_board[3][3] = ' '  # Place a white rook

    # Sub-section 4: Bishops
    # Example 7: Bishops can only move diagonally.
    chess_board[3][3] = 'b'  # Place a black bishop
    assert set([(2, 2), (2, 4), (4, 2), (4, 4), (5, 1), (5, 5), (6, 0), (6, 6)]) == \
        set(calculate_moves(chess_board, 3, 3, None)[0])  # Black Bishops can move diagonally
    chess_board[3][3] = 'B'  # Place a white bishop
    assert set([(1, 1), (1, 5), (2, 2), (2, 4), (4, 2), (4, 4), (5, 1), (5, 5)]) == \
        set(calculate_moves(chess_board, 3, 3, None)[0])  # Black Bishops can move diagonally
    chess_board[3][3] = ' '  # Clear the path

    # Sub-section 5: Queens
    # Example 8: Queens can move both horizontally, vertically, and diagonally from a single position.
    chess_board[3][3] = 'q'  # Place a black queen
    assert all(item in calculate_moves(chess_board, 3, 3, None)[0] for item in \
               [(2, 2), (2, 4), (4, 2), (4, 4), (5, 1), (5, 5), (6, 0), (6, 6)]) # Black Queens can move diagonally
    assert (3, 0) in calculate_moves(chess_board, 3, 3, None)[0]  # Black Queens can move horizontally
    assert (3, 7) in calculate_moves(chess_board, 3, 3, None)[0]  # Black Queens can move horizontally
    assert (2, 3) in calculate_moves(chess_board, 3, 3, None)[0]  # Black Queens can move vertically
    assert (4, 3) in calculate_moves(chess_board, 3, 3, None)[0]  # Black Queens can move vertically
    chess_board[3][3] = 'Q'  # Place a white queen
    assert all(item in calculate_moves(chess_board, 3, 3, None)[0] for item in \
               [(1, 1), (1, 5), (2, 2), (2, 4), (4, 2), (4, 4), (5, 1), (5, 5)]) # White Queens can move diagonally
    assert (3, 0) in calculate_moves(chess_board, 3, 3, None)[0]  # White Queens can move horizontally
    assert (3, 7) in calculate_moves(chess_board, 3, 3, None)[0]  # White Queens can move horizontally
    assert (2, 3) in calculate_moves(chess_board, 3, 3, None)[0]  # White Queens can move vertically
    assert (4, 3) in calculate_moves(chess_board, 3, 3, None)[0]  # White Queens can move vertically
    chess_board[3][3] = ' '  # Clear the path

    # Sub-section 6: Kings
    # Example 9: Kings can move one square in any direction.
    chess_board[3][3] = 'k'  # Place a black king
    assert set([(3, 2), (4, 2), (4, 3), (4, 4), (3, 4), (2, 4), (2, 3), (2, 2)]) == set(calculate_moves(chess_board, 3, 3, None)[0])  # Black Kings can move to adjacent squares
    chess_board[3][3] = 'K'  # Place a white king
    assert set([(3, 2), (4, 2), (4, 3), (4, 4), (3, 4), (2, 4), (2, 3), (2, 2)]) == set(calculate_moves(chess_board, 3, 3, None)[0])  # White Kings can move to adjacent squares

# Sub-test 2: Piece Blocking
# These examples may seem redundant at a glance. It may be optimal to have tests that check that pieces on all potential squares limit the total moves. 
# Ehh I could think of more annoying "necessary" tests.
def test_piece_blocking(chess_board):
    # Sub-section 1: Pawn Blocking Pawn
    # Example 1: Place two black pawns of the same color on adjacent squares in a row.
    chess_board[2][4] = 'p'  # Place another black pawn
    assert (2, 4) not in calculate_moves(chess_board, 1, 4, None)[0]  # Pawn can't move forward due to blockage
    chess_board[2][4] = ' '  # Clear the path

    # Example 2: Place two white pawns of the same color on adjacent squares in a row.
    chess_board[5][4] = 'P'  # Place another black pawn
    assert (5, 4) not in calculate_moves(chess_board, 6, 4, None)[0]  # Pawn can't move forward due to blockage
    chess_board[5][4] = ' '  # Clear the path

    # Example 3: Place two pawns of the opposite color on adjacent squares in a row.
    chess_board[2][5] = 'P'  # Place another black pawn diagonally
    assert (2, 5) not in calculate_moves(chess_board, 1, 5, None)[0]  # Black Pawn can't move forward due to blockage
    assert (1, 5) not in calculate_moves(chess_board, 2, 5, None)[0]  # White Pawn can't move forward due to blockage
    chess_board[2][5] = ' '  # Clear the path

    # Sub-section 2: Pawn Blocking Bishop
    # Example 1: Place a pawn and a bishop of the same color on the board.
    chess_board[5][5] = 'B'  # Place a white bishop diagonally
    assert (5, 5) not in calculate_moves(chess_board, 6, 5, None)[0]  # White Pawn can't move forward due to blockage
    assert (6, 5) not in calculate_moves(chess_board, 5, 5, None)[0]  # White Bishop can't move diagonally

    # Sub-section 3: Pawn Blocking Knight
    # Example 1: Place a pawn and a knight of the same color on the board.
    chess_board[5][5] = 'N'  # Place a white knight
    chess_board[4][3] = 'N'  # Place a white knight
    assert (5, 5) not in calculate_moves(chess_board, 6, 5, None)[0]  # White Pawn can't move forward due to blockage
    assert (6, 5) not in calculate_moves(chess_board, 4, 3, None)[0]  # White Pawn can't move diagonally
    chess_board[4][3] = ' '  # Clear the path
    chess_board[5][5] = ' '  # Clear the path

    # Sub-section 4: Rook Blocked by Same-Color Rook
    # Example 1: Place two rooks of the same color on adjacent squares in a row.
    chess_board[3][3] = 'r'  # Place a black rook
    chess_board[3][4] = 'r'  # Place another black rook
    assert (3, 3) not in calculate_moves(chess_board, 3, 4, None)[0]  # Rook can't move horizontally
    assert (3, 4) not in calculate_moves(chess_board, 3, 3, None)[0]  # Rook can't move horizontally
    chess_board[3][3] = ' '  # Clear the path
    chess_board[3][4] = ' '  # Clear the path

    # Sub-section 5: Rook Blocked by Opposite-Color Rook
    # Example 1: Place a rook and an opposing-color rook on the board.
    chess_board[3][3] = 'R'  # Place a white rook
    chess_board[3][4] = 'r'  # Place a black rook
    assert (3, 2) not in calculate_moves(chess_board, 3, 4, None)[0]  # Rook can't move horizontally
    assert (3, 5) not in calculate_moves(chess_board, 3, 3, None)[0]  # Rook can't move horizontally
    chess_board[3][3] = ' '  # Clear the path
    chess_board[3][4] = ' '  # Clear the path

    # Sub-section 6: Bishop Blocked by Same-Color Bishop
    # Example 1: Place two bishops of the same color on the board.
    chess_board[3][3] = 'b'  # Place a black bishop
    chess_board[4][4] = 'b'  # Place a black bishop
    assert (3, 3) not in calculate_moves(chess_board, 4, 4, None)[0]  # Bishop can't move diagonally
    assert (4, 4) not in calculate_moves(chess_board, 3, 3, None)[0]  # Bishop can't move diagonally
    chess_board[3][3] = ' '  # Clear the path
    chess_board[4][4] = ' '  # Clear the path

    # Sub-section 7: Bishop Blocked by Opposite-Color Bishop
    # Example 1: Place a bishop and an opposing-color bishop on the board.
    chess_board[3][3] = 'B'  # Place a white bishop
    chess_board[4][4] = 'b'  # Place a black bishop
    assert (2, 2) not in calculate_moves(chess_board, 4, 4, None)[0]  # Bishop can't move diagonally
    assert (5, 5) not in calculate_moves(chess_board, 3, 3, None)[0]  # Bishop can't move diagonally
    chess_board[3][3] = ' '  # Clear the path
    chess_board[4][4] = ' '  # Clear the path

    # Sub-section 8: Knight Blocked by Same-Color Knight
    # Example 1: Place two knights of the same color on the board.
    chess_board[3][3] = 'n'  # Place a black knight
    chess_board[4][6] = 'n'  # Place another black knight
    assert (3, 3) not in calculate_moves(chess_board, 4, 6, None)[0]  # Knight can't move due to blockage
    assert (4, 6) not in calculate_moves(chess_board, 3, 3, None)[0]  # Knight can't move due to blockage
    chess_board[3][3] = ' '  # Clear the path
    chess_board[4][6] = ' '  # Clear the path

    # Queens need not be checked as it uses moves of bishops and rooks

    # Add more cases if needed

if __name__ == "__main__":
    pytest.main()