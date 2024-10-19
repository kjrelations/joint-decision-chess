# Checkmate & Stalemate

If it is impossible to get out of check as there are no legal moves then the king is under **checkmate** and the opponent has won.

If there are no legal moves available and the king is not under check then the game ends in a **stalemate**. *This is a draw*. This usually occurs because any move would place the king under a check.

There are a few other ways that a draw can be reached through play: 

1. **Threefold repetition**: If the same board position and state has been reached 3 times then it is a draw.
2. **Fifty move rule**: If there has been no capture or pawn move in the last fifty moves by each player, and if the last move was not a checkmate.
3. **Dead position**: A *dead position* is defined as a position where neither player can checkmate their opponent's king by any sequence of legal moves. 

There are two kinds of dead positions:

- **Insufficient Material**: Positions with only the following pieces make checkmate impossible.
  - King against king;
  - King against king and bishop;
  - King against king and knight;
  - King and bishop against king and bishop, with both bishops on squares of the same color.
- Other positions in which checkmate is impossible by any sequence of legal moves. This can occur in blocked positions where it is impossible for either side to make a capture. If this is not immediately recognized as a dead position the fifty move rule will eventually apply.

In the following the king will move into the corner. If the queen moves to g1 then it would be stalemate. Perform a checkmate by moving the queen to a8.