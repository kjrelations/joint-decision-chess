# README
## Introduction

Currently this is a deployed public site prototype of classical chess. Multiplayer has been enabled. 

The project is available at https://decisionchess.com

The goal is to have a website running for classical chess first with all the necessary features for this simple version of the game. Then I will implement my personally designed chess variant. Many more features will be added that will be specific to my version such as customizing the specifics of the game and adding personally designed sub-variants. 

The site is being deployed off of the `dev-pre-alpha` branch but it should be noted that the active default branch has many other features and pages already enabled. 

My version will be called "Joint-Decision Chess", and until then will be worked under branches that focus on the classical game.

More features are to come now that an initial version is public and working, including an AI opponent and live chat. Stay tuned...

## Description

The following project is under active development and some parts of the README below or on other branches may be outdated. 

See the dev-base branch if you wish to test the prototype version where the README is accurate and local testing can easily be performed with no connection or major setup and an early version of the game can be played.

Otherwise, if you understand how to launch Django locally, you may try this branch. Know that you will need a PostgreSQL database setup and to configure it in Django's settings as well as server connection details. Contact me for these. 

If you wish to test a basic form of local multiplayer try the dev-pygbag branch.

Current the main gameplay features include:

- Highlighting squares with right click on and off a square.
- Drawing arrows color coded according to player view by right clicking on a square and dragging and releasing on another square.
- Displaying visuals of available standard or special moves for a selected piece.
- Undoing a move through standard play and during or after pawn promotion through undo offers.
  - An offer must be accepted by the opponent but they can reject your proposed offer as well.

- Allowing for a draw offer that ends the game in a tie that has UI/UX just like the undo offer.
- Allowing for a player to resign at any time.
- Displaying a darkened screen once an endgame position is reached through: 
  - Checkmate or stalemate;
  - Resignation;
  - Drawing;
  - By threefold repetition after checking the last 500 unique states.
- Algebraic moves are displayed as the game is played in the command center.
- Cycling between the themes defined in the `themes.json` file by continuously pressing the "t" key or through the web "Cycle Theme" button:
  - Note that adjusting the dimensions of the window of this file may break the game as this was not in the initial scope and it resizes itself in the browser but may be customized or removed in future versions after handling an existing display bug.
    - All other parameters can be customized to one's liking.
    - Additional themes can be added.
- Cycling between player perspectives by pressing the "f" key or through the web "Flip" button.
  - This only changes perspective and not player color, you still have to wait your turn.


## Installation and Usage

The site is public for testing but a local environment of just the game can easily be set up. However, to not abuse the servers the right values for `host` and `lobby` in `pygbag_net.py` should be used. Contact the author for details, we give the setup details here regardless. I do not detail how to setup a local Django site here.

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

5. You can now run the application using Pygbag which should have been installed:

   ```bash
   python -m pygbag main.py
   ```

   - This will allow your game to be available at localhost:8000.

6. The game requires a game id to connect to the server in order to load, this is retrieved from the browser sessionStorage. Open a browser dev console and run the following before the ready button is clicked 

   - `sessionStorage.setItem("current_game_id", "<non-0-number>")`.
   - If the game loads with a black screen simply reload the page. If an error box occurs then clear the site cache and re-run the above.

7. Repeat step 6 once the board is loaded on a new tab to open a second client as the opponent.

8. Play a game!

9. To deactivate the virtual environment when you're finished, simply use the `exit` command or close the terminal.

## Testing

Testing can be run through `pipenv`:

```bash
pipenv run pytest
```

Alternatively, simply by running pytest:

```bash
python -m pytest test_chess.py
# Or
pytest test_chess.py
```

Currently the tests only try simple movement logic but will expand into better defined/more useful larger tests once the project is sufficiently developed. 

- These tests were auto-generated by ChatGPT and made functional by me, this explains why they are over-commentated. 

An additional test that I think should be added in the future is ensuring all the web actions work as expected as they took time to design and get just right and are easily testable now through a mock setup.

- If this were a production application I would develop the tests for these immediately but this is a hobby project.

## Contributing

If you'd like to contribute to this project, please contact the author.

## License

This project is licensed under the GNU General Public License v3.0.
