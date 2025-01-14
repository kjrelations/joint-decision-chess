# README
## Introduction

This project is a multiplayer enabled game for classic chess as well as the variant called **Decision chess** which allows for simultaneous play. 

The project is available at https://decisionchess.com

![home](/images/home.jpg)

![play](/images/play.jpg)

![play](/images/lessons.png)

Play against a live opponent or basic AI in a chess variant where the first move doesn't dictate an advantage and surprise is around every corner. Many more features have been added will be specific to the variant such as sub-variants, timed modes, leaderboards, a board editor, saved games under a user profile, and more. 

The full title is called "Joint-Decision Chess".

## Description

See the dev-base branch if you wish to test the prototype version where the README is accurate and local testing can easily be performed with no connection or major setup and an early version of the game can be played.

Otherwise, if you understand how to launch Django locally, you may try this branch, you will need a PostgreSQL database setup and to configure it in Django's settings as well as server connection details.

If you wish to test a basic form of local multiplayer without Django try the dev-pygbag branch.

Currently the main gameplay features include:

- Highlighting squares with right click on and off a square.
- Drawing arrows color coded according to player view by right clicking on a square and dragging and releasing on another square.
  - Allowing for the sharing of arrows between players with a toggle button.

- Resetting the game to the initial stage of the previous play with a reset button on subvariants with the Decision mode enabled.
- Displaying visuals of available standard or special moves for a selected piece.
- Undoing a move through standard play and during or after pawn promotion through undo offers.
  - An offer must be accepted by the opponent in live games but they can reject your proposed offer as well.
- Allowing for a draw offer that ends the game in a tie that has UI/UX just like the undo offer.
- Allowing for a player to resign at any time.
- Displaying a visual check or checkmate indicator
- A game is completed under the following conditions: 
  - Checkmate or stalemate;
  - Resignation;
  - Drawing;
  - By threefold repetition after checking the last 500 unique states.
- Algebraic moves are displayed as the game is played in the command center with figurine algebraic notation.
- Cycling between the themes defined in the `themes.json` file by continuously pressing the "t" key or through the web "Cycle Theme" button:
  - A selection of a subset of themes can be made in the user settings including the active theme.
- Cycling between player perspectives by pressing the "f" key or through the web "Flip" button.
  - This only changes perspective and not player color, you still have to wait your turn.


## Installation and Usage

The site is public for testing but a local environment of just the game can easily be set up. However, to not abuse the servers the values for `host` and `lobby` in `pygbag_net.py` are not given. Contact the author for details, we give the setup details here regardless and they work for the AI and solo game without connection details. I do not detail how to setup a local Django site here for full local site deployment, just the game in browser.

1. We recommend using a virtual environment to run the project and isolate dependencies. If you don't have `pipenv` installed, you can install it using pip:

   ```bash
   pip install pipenv
   ```

2. Now, create a virtual environment and install the project's dependencies:

   ```bash
   pipenv install --dev
   ```

   - The dev flag ensures all dependencies including development packages are installed.
   - This will create a virtual environment and install the required packages specified in the `Pipfile.lock`.

3. Activate the virtual environment using the following command:

   ```bash
   pipenv shell
   ```

4. You can now run the application using Pygbag which should have been installed. This should be done from the `join-decision-chess` file for the live game, the `simple_ai` folder for the AI game, and `solo_play` for a game against yourself:

   ```bash
   python -m pygbag main.py
   ```

   - This will allow your game to be available at localhost:8000.

5. The live game requires a game id to connect to the server in order to load, this is retrieved from the browser sessionStorage. Open a browser dev console and run the following before the ready button is clicked.

   - `sessionStorage.setItem("current_game_id", "<non-0-number>")`.
   - If the game loads with a black screen simply reload the page. If an error box occurs then clear the site cache and re-run the above.

6. For the live game repeat step 5 once the board is loaded on a new tab to open a second client as the opponent.

7. Play a game!

8. To deactivate the virtual environment when you're finished, simply use the `exit` command or close the terminal.

## Contributing

If you'd like to contribute to this project, please contact the author.

## License

This project is licensed under the MIT License.
