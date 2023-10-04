# README
Currently this is a prototype of classical chess. With AI and local multiplayer yet to be implemented, one player alternates between playing sides. This will be extended with the above features by including a server and later embedding the multiplayer version on a website. More features are to come once an initial version is fully implemented.

The following project is under active development and some inputs and parts of the README below are outdated and have been moved to embedded site functionality. See the dev-base branch if you wish to test the prototype version where the README is accurate. Otherwise if you understand how to launch Django locally, try this branch. I do not yet share the setup details here. If you wish to test a basic form of local multiplayer try the dev-pygbag branch.

Current the main features include:

- Highlighting squares with right click on and off a square.
- Drawing arrows color coded according to player view by right clicking on a square and dragging and releasing on another square.
- Displaying visuals of available standard or special moves for a selected piece.
- Undoing a move through standard play and during or after pawn promotion.
- Displaying a darkened screen once an endgame position is reached through: 
  - Checkmate or stalemate;
  - Resignation by pressing the "r" key;
  - Drawing by pressing the "d" key;
  - By threefold repetition after checking the last 1000 unique states.
- Algebraic moves are printed to console as the game is played along with end-game algebraic representations.
- Cycling between the themes defined in the `themes.json` file by continuously pressing the "t" key:
  - Note that adjusting the dimensions of the window will break the game as this is not in the current scope but may be added or removed in future versions.
    - All other parameters can be customized to one's liking.
    - Additional themes can be added.
  - Changing the `inverse_view` parameter allows one to play the game from the opposite side/view.

The goal is to have a website running for classical chess first with all the necessary features for this simple version of the game. Then I will implement my personally designed chess variant. Many more features will be added that will be specific to my version such as customizing the specifics of the game and adding personally designed sub-variants.

My version will be called "Joint-Decision Chess", hence the file name, and until then will be worked under branches that focus on the classical game.

## Installation and Usage

1. We recommend using a virtual environment to run the project and isolate dependencies. If you don't have `pipenv` installed, you can install it using pip:

   ```bash
   pip install pipenv
   ```

2. Now, create a virtual environment and install the project's dependencies:

   ```bash
   pipenv install --dev
   ```

   - The dev flag ensures all dependencies including development packages are installed.

3. This will create a virtual environment and install the required packages specified in the `Pipfile.lock`.

4. Activate the virtual environment using the following command:

   ```bash
   pipenv shell
   ```

5. You can now run the application using Python:

   ```bash
   python joint-decision-chess.py
   ```

   - A GUI window should open where you can interact with the pieces.

6. To deactivate the virtual environment when you're finished, simply use the `exit` command or close the terminal.

## Testing

Testing can be run through `pipenv`:

```bash
pipenv run pytest
```

Alternatively, simply by running pytest:

```bash
python -m pytest joint-decision-chess.py
# Or
pytest joint-decision-chess.py
```

Currently the tests only try simple movement logic but will expand into better defined/more useful larger tests once the project is sufficiently developed. 

- These tests were auto-generated by ChatGPT and made functional by me, this explains why they are over-commentated. 

In this sense, I am not following TDD as I do not consider it to be the greatest practice after research and experience.

## Contributing

If you'd like to contribute to this project, please contact the author.

## License

This project is licensed under the GNU General Public License v3.0.
