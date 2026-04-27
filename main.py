import logging
import os
from random import choice, randint
import re
import signal
import sys
from typing import Self

# don't print out the exit message more than once since multiple signals
# might be emitted
PRINTED_EXIT_MESSAGE = False

# Cell value constants
# I don't really like strings since I'm prone to typos this way reduces the
# risk of that type of mistake
DASH = '-'
HIT = 'X'
MISS = 'O'
SHIP = 'S'

# logging for debugging
LOGLEVEL = os.environ.get('LOGLEVEL', 'WARNING').upper()
logging.basicConfig(
    level=LOGLEVEL, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)
LOGGER.debug(f"Logging level set to {LOGLEVEL}")


class GameGrid:
    def __init__(self, rows: int = 4, columns: int = 4):
        """
        Class that models our game grid. It is composed of Row objects
        which in turn are composed of a set of Cell objects. At construction,
        the grid sets the location of the battleship in two adjacent cells.

        Arguments:
            rows: the number of rows of which the grid consists - 4 by default

            columns: the number of columns in each row - 4 by default
        """
        self.rows = rows
        self.columns = columns
        self._rows = {}

        # creates empty rows and cells that make up the grid
        self._initialize_rows()

        # randomly determines the location of the battleship
        self._set_battleship_coordinates()

        # updates the model with the newly determined battleship coordinates
        self.set_battle_ship_location()
        LOGGER.debug(
            f"Battle ship coordinates: {self._battleship_coordinate_tuple}")

    def _set_battleship_coordinates(self):
        battle_ship_row1 = chr(65 + randint(0, self.rows - 1))
        battle_ship_orientation = choice(['horizontal', 'vertical'])

        match battle_ship_orientation:
            case 'horizontal':
                idx1 = randint(0, self.columns - 1)
                idx2 = idx1 + 1
                if idx1 > 0:
                    idx2 = idx1 + choice([-1, 1])
                self.battleship_coordinates = (battle_ship_row1, idx1, battle_ship_row1, idx2) if idx2 > idx1 else (
                    battle_ship_row1, idx2, battle_ship_row1, idx1)
            case 'vertical':
                row1_int = ord(battle_ship_row1)
                battle_ship_row2 = chr(row1_int + 1) if row1_int == 65 else choice(
                    [chr(row1_int + 1), chr(row1_int - 1)])
                idx = randint(0, self.columns - 1)
                self.battleship_coordinates = (battle_ship_row1, idx, battle_ship_row2, idx) if row1_int < ord(
                    battle_ship_row2) else (battle_ship_row2, idx, battle_ship_row1, idx)

    def _initialize_rows(self):
        for i in range(self.rows):
            name = chr(65 + i)
            self._rows[name] = Row(cell_count=self.columns, name=name)

    def check_for_hit(self, row: str, col: int) -> bool:
        coordinate_tuple = f"{row}{col}"
        return coordinate_tuple in self._battleship_coordinate_tuple

    def grid_range(self) -> tuple[str, str]:
        min_row, max_row = min(self._rows.keys()), max(self._rows.keys())
        min_col, max_col = 1, self.columns
        return f"{min_row}{min_col}", f"{max_row}{max_col}"

    def is_a_hit(self, row: str, col: int) -> bool:
        is_hit = self.check_for_hit(row, col)
        LOGGER.debug(
            f"Coordinate ({row}, {col}) is a {'hit' if is_hit else 'miss'}")

        if is_hit:
            self._rows[row].cells = {cell.mark_as_hit(
            ) if cell.get_index() == (col-1) else cell for cell in self._rows[row].cells}
        else:
            self._rows[row].cells = {cell.mark_as_miss(
            ) if cell.get_index() == (col-1) else cell for cell in self._rows[row].cells}

        return is_hit

    def is_out_of_range(self, row: str, col: int) -> bool:
        if col is None:
            return False
        return row not in self._rows or col < 1 or col > self.columns

    def set_battle_ship_location(self) -> None:
        """
        Method that updates the grid model with the location of the battleship.
        Recreates Row object(s) that contain the battleship pieces
        """
        row1, col1, row2, col2 = self.battleship_coordinates
        self._battleship_coordinate_tuple = (
            f"{row1}{col1+1}", f"{row2}{col2+1}")

        # we have a horizontal battleship, no need to update two rows
        if row1 == row2:
            self._rows[row1] = Row.create_row_with_battle_ship(
                cell_count=self.columns, name=row1, battle_ship_indices=(col1, col2))
        # vertical battleship, it lives in two separate rows
        else:
            self._rows[row1] = Row.create_row_with_battle_ship(
                cell_count=self.columns, name=row1, battle_ship_indices=(col1, None))
            self._rows[row2] = Row.create_row_with_battle_ship(
                cell_count=self.columns, name=row2, battle_ship_indices=(col2, None))

    def print_grid(self, reveal_battleship: bool = False) -> None:
        """
        Produces the visual representation of the grid on the console. Not the
        most elegant solution - I was in a hurry to just generate something that
        I could test quickly :)
        """
        print_header = True
        for row in self._rows.values():
            if print_header:
                print(
                    f"    |{' |'.join([f"{i:3d}" for i in range(1, self.columns + 1)])}", '|')
                print(f"{'----|' * (self.columns + 1)}")
                print_header = False
            sorted_cells = sorted(row.cells, key=lambda c: c.get_index())
            LOGGER.debug(
                f"Printing row '{row.name}' with cells: {[(cell.get_index(), cell.is_empty(), cell.get_value()) for cell in sorted_cells]}")
            print(
                f"{row.name:^3} |{' |'.join([f"{DASH:^3}" if cell.is_empty() else f'{cell.get_value(reveal_battleship):^3}' for cell in sorted_cells])}", '|')
            print(f"{'----|' * (self.columns + 1)}")


class Row:
    """
    Class that represents a row in the game grid. Each row has an alphabetic
    name from A-Z. Each row contains a set of cells that contain a
    representation of each content holder in the row.

    Arguments:
        cell_count: the number of cells in the row. This is 4 by default, 
            otherwise, it's determined by the user

        name: the alphabetic name of the row from A-Z

        battle_ship_indices: the index in our virtual array of cells that contains a
            piece of the battleship
    """

    def __init__(self, cell_count: int, name: str, battle_ship_indices: tuple[int, int] = None):
        self.cell_count = cell_count
        self.name = name
        self.battle_ship_indices = battle_ship_indices
        self.cells = set()

        for i in range(0, cell_count):
            if battle_ship_indices is None or i not in battle_ship_indices:
                self.cells.add(Cell(i))
            else:
                LOGGER.debug(
                    f"Adding battleship cell at index {i} for row '{name}'")
                self.cells.add(Cell.battleship_cell(i))

        if battle_ship_indices is not None:
            sorted_cells = sorted(self.cells, key=lambda c: c.get_index())
            LOGGER.debug(
                f"Current cells for row '{self.name}': {[(cell.get_index(), cell.is_empty(), cell.get_value()) for cell in sorted_cells]}")

    def is_not_empty(self) -> bool:
        return any(not cell.is_empty() for cell in self.cells)

    @staticmethod
    def create_row_with_battle_ship(cell_count: int, name: str, battle_ship_indices: tuple[int, int]) -> Self:
        """
        Method called after the battleship coordinates have been determined to
        locate the battleship piece(s) in the row

        Arguments:
            cell_count: because we're recreating a new row (easier to do than 
                updating an existing row) we need to know how many cells to create

            name: as in the constructor above, the alphabetic name of the row from A-Z

            battle_ship_indices: the index in our virtual array of cells that contains a
                piece (or pieces) of the battleship

        N.B.
        Since we're assigning the result of this call to the row dictionary
        in the GameGrid class, this method needs to return an object hence
        the return type of Self and the static method because this is more
        coherent with our choice of assigning a new Row object
        """
        LOGGER.debug(
            f"Creating row '{name}' with battleship at indices: {battle_ship_indices}")
        return Row(cell_count=cell_count, name=name, battle_ship_indices=battle_ship_indices)


class Cell:
    """
    A class to represent an individual cell in the game grid

    Arguments:
        idx: the index of the cell in its row. Since we're using a set to store
            the cells we need this to get the cells out in sorted order

        is_empty: by default each cell is empty but this value should be updated
            if the cell represents coordinates where the battleship is located

        value: the string representation of the cell's contents. In the course
            of game this will be either '-' for untargeted, 'X' for a hit, 'O'
            for a miss. If the game is lost, the battleship location is revealed
            with an 'S'
    """

    def __init__(self, idx: int, is_empty: bool = True, value: str = None):
        self._idx = idx
        self._is_empty = is_empty
        self._is_hit = False
        self._is_miss = False
        self.value = value

    def get_value(self, reveal_battleship: bool = False) -> str:
        if self.value == SHIP:
            if reveal_battleship:
                return SHIP

            if self._is_hit:
                return HIT
            else:
                return DASH
        return self.value

    def get_index(self) -> int:
        return self._idx

    def is_empty(self) -> bool:
        return self._is_empty

    def is_miss(self) -> bool:
        return self._is_miss

    def mark_as_hit(self) -> Self:
        self._is_empty = False
        self._is_hit = True
        return self

    def mark_as_miss(self) -> Self:
        self._is_miss = True
        self._is_empty = False
        self.value = MISS
        return self

    @staticmethod
    def battleship_cell(idx: int) -> Self:
        """
        An alternate way of constructing a cell that we know contains a piece of the battleship. 

        Arguments:
            idx: the index of the cell in its row. Necessary to retrieve the
                cell objects in the sorted order to be printed

            is_empty: since again, we know this cell contains a piece of the
                battleship, we know is_empty should be false

            value: it's a battleship cell, so what does it contain other than
                a SHIP? Perhaps would have been more sensible to call this
                SHIP_PIECE or something...

        Frankly, I don't know the best solution for implementing multiple
        constructors in Python, but this seemed more intuitive than
        @classmethod and, again, Python doesn't support constructor overloading
        """
        return Cell(idx=idx, is_empty=False, value=SHIP)


def game_loop(grid: GameGrid, guess_limit: int = 5) -> None:
    """
    Function that executes gameplay given a grid and guess limit.

    Arguments:
        grid: the GameGrid - the game grid object that defines the space in
            which the game is played and the location of the battleship

        guess_limit: the maximum number of guesses allowed

    The function will loop until either the guess limit is reached or the battleship is sunk.
    On each iteration, the grid will is printed to reflect the state of the game
    """
    guesses, hit_count = 0, 0
    min_coord, max_coord = grid.grid_range()
    coord_range = f"{min_coord}-{max_coord}"
    guessed_coordinates = set()

    while guesses < guess_limit:
        grid.print_grid()

        # catch input exceptions that don't satisfy our regex
        try:
            guess = input(
                f"Enter a coordinate in the range {coord_range}: ").upper()
            row = re.findall(r'[a-zA-Z]+', guess)[0]
            col = int(re.findall(r'\d+', guess)[0])

            # validate that the user-supplied coordinate is in the grid
            if grid.is_out_of_range(row, col):
                print(
                    f"\nCoordinate '{guess}' is not in range {coord_range}. Please try again.")
                continue
        except (IndexError, ValueError):
            print(
                f"\nInvalid input '{guess}'. Please enter a valid coordinate in the range {coord_range}.")
            continue

        # prevent duplicate guesses
        if guess in guessed_coordinates:
            print(
                f"\nYou've already guessed '{guess}'. Try a different coordinate.")
            continue
        guessed_coordinates.add(guess)

        # compare the user-supplied coordinate to the battleship coordinates
        # print the result and update the grid
        is_a_hit = grid.is_a_hit(row, col)
        if is_a_hit:
            print("\nHit at coordinate:", guess)
            hit_count += 1

            # you've sunk my battleship!
            if hit_count == 2:
                print("\nCongratulations! You've sunk the battleship!")
                grid.print_grid()
                return
        else:
            print("\nMiss at coordinate:", guess)

        # increment guess count and log the guess result
        guesses += 1
        LOGGER.info(
            f"Guess {guesses}/{guess_limit}: {guess} - {'Hit' if is_a_hit else 'Miss'}")

    # game over :( - show the location of the battleship
    grid.print_grid(True)
    print("\nGame over! You've used all your guesses.")


def is_valid_input(value: int, valid_range: tuple[int, int]) -> bool:
    """
    Simple function to check whether a user input value falls within the
    expeceted range
    """
    return valid_range[0] <= value <= valid_range[1]


def handle_sigs(signum, frame) -> None:
    """Our noble signal handler - it works, kinda'"""
    global PRINTED_EXIT_MESSAGE
    if not PRINTED_EXIT_MESSAGE:
        print(f"\n\nGame terminated with '{signal.Signals(signum).name}'.\n")
        PRINTED_EXIT_MESSAGE = True
    exit(0)


def main() -> None:
    """Program entry point where grid size and guess limit are set and input is validated"""
    invalid_input = True
    rows, columns, guess_limit = 0, 0, 0
    use_default_values = '-'

    # loop until we have valid input for each grid dimension and guess limit
    # save state in rows, columns and guess_limit so we can resume where we
    # left off in case of invalid input
    while invalid_input:
        # wrap in try block in case there is an unexpected error
        try:
            if use_default_values == '-':
                use_default_values = input(
                    "Enter 'n' to not accept the default values of a 4x4 grid and 5 guesses? (n): ").lower()
                if use_default_values not in ['n', '']:
                    print(
                        f"Invalid input '{use_default_values}'. Please enter 'y' for yes or 'n' for no.")
                    use_default_values = '-'
                    continue

                if use_default_values == '':
                    break

            if rows <= 0:
                while not is_valid_input(rowz := int(input("Enter the number of rows for the game grid 4-26: ")), (4, 26)):
                    print(
                        f"Invalid input '{rowz}'. Please enter a number between 4 and 26.")
                rows = rowz

            if columns <= 0:
                while not is_valid_input(cols := int(input("Enter the number of columns for the game grid 4-26: ")), (4, 26)):
                    print(
                        f"Invalid input '{cols}'. Please enter a number between 4 and 26.")
                columns = cols

            if guess_limit <= 0:
                while not is_valid_input(limit := int(input("Enter the number of guesses allowed 5-16: ")), (5, 16)):
                    print(
                        f"Invalid input '{limit}'. Please enter a number between 5 and 16.")
                guess_limit = limit

            if rows > 0 and columns > 0 and guess_limit > 0:
                invalid_input = False

        except ValueError as ve:
            print(f"Invalid input! Please enter a valid number.")

    grid, guesses = (GameGrid(), 5) if use_default_values == '' else (
        GameGrid(rows=rows, columns=columns), guess_limit)

    print("""

#################################################
# Key:                                          #
#    '-' = Untargeted cell                      #
#    'X' = Hit                                  #
#    'O' = Miss                                 #
#    'S' = Battleship (at end of losing game)   #
#################################################

""")

    # start of game logic loop where we iterate asking for coordinates until
    # either the guess limit is reach or the battleship is sunk
    game_loop(grid=grid, guess_limit=guesses)


if __name__ == "__main__":
    # try to exit gracefully if one of these signals is emitted
    for sig in [signal.SIGINT, signal.SIGQUIT, signal.SIGTERM]:
        signal.signal(sig, handle_sigs)

    main()
