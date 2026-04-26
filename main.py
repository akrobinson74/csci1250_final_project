import logging
import os
from random import choice, randint
import re
import signal
import sys
from typing import Self

PRINTED_EXIT_MESSAGE = False

DASH = '-'
HIT = 'X'
MISS = 'O'
SHIP = 'S'

LOGLEVEL = os.environ.get('LOGLEVEL', 'WARNING').upper()
logging.basicConfig(
    level=LOGLEVEL, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)
LOGGER.debug(f"Logging level set to {LOGLEVEL}")


class GameGrid:
    def __init__(self, rows: int = 4, columns: int = 4):
        self.rows = rows
        self.columns = columns
        self._rows = {}

        self._initialize_rows()
        self._set_battleship_coordinates()
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
        row1, col1, row2, col2 = self.battleship_coordinates
        self._battleship_coordinate_tuple = (
            f"{row1}{col1+1}", f"{row2}{col2+1}")

        if row1 == row2:
            self._rows[row1] = Row.create_row_with_battle_ship(
                cell_count=self.columns, name=row1, battle_ship_indices=(col1, col2))
        else:
            self._rows[row1] = Row.create_row_with_battle_ship(
                cell_count=self.columns, name=row1, battle_ship_indices=(col1, None))
            self._rows[row2] = Row.create_row_with_battle_ship(
                cell_count=self.columns, name=row2, battle_ship_indices=(col2, None))

    def print_grid(self) -> None:
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
                f"{row.name:^3} |{' |'.join([f"{DASH:^3}" if cell.is_empty() else f'{cell.get_value():^3}' for cell in sorted_cells])}", '|')
            print(f"{'----|' * (self.columns + 1)}")


class Row:
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
        LOGGER.debug(
            f"Creating row '{name}' with battleship at indices: {battle_ship_indices}")
        return Row(cell_count=cell_count, name=name, battle_ship_indices=battle_ship_indices)


class Cell:
    def __init__(self, idx: int, is_empty: bool = True, value: str = None):
        self._idx = idx
        self._is_empty = is_empty
        self._is_hit = False
        self._is_miss = False
        self.value = value

    def get_value(self):
        if self.value == SHIP:
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
        return Cell(idx=idx, is_empty=False, value=SHIP)


def game_loop(grid: GameGrid, guess_limit: int = 5) -> None:
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

        is_a_hit = grid.is_a_hit(row, col)
        if is_a_hit:
            print("\nHit at coordinate:", guess)
            hit_count += 1
            if hit_count == 2:
                print("\nCongratulations! You've sunk the battleship!")
                grid.print_grid()
                return
        else:
            print("Miss at coordinate:", guess)

        # increment guess count and log the guess result
        guesses += 1
        LOGGER.info(
            f"Guess {guesses}/{guess_limit}: {guess} - {'Hit' if is_a_hit else 'Miss'}")

    grid.print_grid()
    print("\nGame over! You've used all your guesses.")


def is_valid_input(value: int, valid_range: tuple[int, int]) -> bool:
    return valid_range[0] <= value <= valid_range[1]


def handle_sigs(signum, frame) -> None:
    global PRINTED_EXIT_MESSAGE
    if not PRINTED_EXIT_MESSAGE:
        print(f"\n\nGame terminated with '{signal.Signals(signum).name}'.\n")
        PRINTED_EXIT_MESSAGE = True
    exit(0)


def main() -> None:
    invalid_input = True
    rows, columns, guess_limit = 0, 0, 0
    use_default_values = '-'

    while invalid_input:
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

    game_loop(grid=grid, guess_limit=guesses)


if __name__ == "__main__":

    for sig in [signal.SIGINT, signal.SIGQUIT, signal.SIGTERM]:
        signal.signal(sig, handle_sigs)

    main()
