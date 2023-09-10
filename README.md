# README
 A chess variant with simultaneous play

See the `dev-classical` branch for current development...

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

Testing can be run through pipenv:

```bash
pipenv run pytest
```

Alternatively, simply by running pytest:

```bash
python -m pytest joint-decision-chess.py
# Or
pytest joint-decision-chess.py
```

## Contributing

If you'd like to contribute to this project, please contact the author.

## License

This project is licensed under the GNU General Public License v3.0.
