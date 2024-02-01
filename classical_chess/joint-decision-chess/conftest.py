import pytest

def pytest_exception_interact(node, call, report):
    if report.failed:
        if "chess_board" in node.fixturenames:
            chess_board = node.funcargs["chess_board"]
            print("\nChess Board State:")
            for row in chess_board:
                print(" ".join(row))
