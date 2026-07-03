# Python 3.11+
# module: model
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum, auto
from itertools import product
from random import randint, choice
from typing import Iterator


@dataclass(frozen=True)
class Cell:
    row: int
    column: int

    def __add__(self, t: tuple[int, int]) -> Cell:
        return Cell(self.row + t[0], self.column + t[1])


class ShotResult(StrEnum):
    HIT = auto()
    MISS = auto()
    SUNK = auto()


class GamePhase(StrEnum):
    PLACEMENT = auto()
    BATTLE = auto()
    VICTORY = auto()


class Winner(StrEnum):
    HUMAN = auto()
    COMPUTER = auto()


class InvalidShipShape(ValueError):
    pass


class ShipOverlapError(ValueError):
    pass


class Board:
    """Represents a player's game board."""

    def __init__(self, size: int, ship_sizes: tuple[int, ...]) -> None:
        self.size = size  # Number of rows and columns on the board.
        self.ship_sizes = ship_sizes  # Sizes of the ships to be placed on the board.
        self._remaining_ship_sizes = list(self.ship_sizes)  # Sizes of the ships that have not yet been placed.
        self._ships: list[Ship] = []  # Ships currently placed on the board.
        self.shots_received: set[Cell] = set()  # Coordinates of all shots fired at this board.

    def __contains__(self, cell: Cell) -> bool:
        """Return True if the specified cell lies within the board."""
        return 0 <= cell.row < self.size and 0 <= cell.column < self.size

    def __iter__(self) -> Iterator[Ship]:
        """Iterate over the ships placed on the board."""
        yield from self._ships

    def add_ship(self, ship: Ship):
        """Add the specified ship to the board if it does not overlap with any existing ship.
        The ship's size is then removed from the list of remaining ship sizes.
        """
        if not ship.can_be_placed_on(self):
            raise ShipOverlapError("The ship overlaps with an already placed ship.")

        if self._remaining_ship_sizes:
            self._ships.append(ship)
            self._remaining_ship_sizes.remove(ship.size)

    def get_cells(self) -> set[Cell]:
        """Return all cells on the board."""
        return {Cell(row_index, column_index) for row_index, column_index in product(range(self.size), repeat=2)}

    def get_cells_available_to_target(self) -> set[Cell]:
        """Return the cells that are not occupied by sunken ships or their surrounding area."""
        return self.get_cells() - {cell for sunken_ship in self.get_sunken_ships()
                                   for cell in sunken_ship.get_occupied_area()}

    def get_ship(self, cell: Cell) -> Ship | None:
        """Return the ship occupying the specified cell, or None if there is no such ship."""
        return next((ship for ship in self if cell in ship), None)

    def get_sunken_ships(self) -> set[Ship]:
        """Return all ships that have been sunk."""
        return {ship for ship in self if ship.is_sunk()}

    def process_shot(self, target_cell: Cell) -> ShotResult:
        """Return the result of firing at the specified cell."""
        self.shots_received.add(target_cell)

        ship = self.get_ship(target_cell)
        if ship is not None:
            return ship.evaluate_shot(target_cell)

        return ShotResult.MISS

    def all_ships_sunk(self) -> bool:
        """Return True if all ships on the board have been sunk."""
        return all(ship.is_sunk() for ship in self)

    def all_ships_placed(self) -> bool:
        """Return True if all ships have been placed on the board."""
        return not self._remaining_ship_sizes


class Ship:
    """Represents a ship on the game board."""

    def __init__(self, cells: set[Cell]):
        if not self.valid_ship_shape(cells):
            raise InvalidShipShape("The provided cells do not form a valid ship.")

        # Maps ship cells to their hit status (True if the segment has been hit).
        self._cells_with_hit_states: dict[Cell, bool] = {cell: False for cell in cells}

    def __repr__(self) -> str:
        return f'{type(self).__name__}({set(self._cells_with_hit_states)})'

    def __str__(self) -> str:
        coords = {(c.row, c.column) for c in self._cells_with_hit_states.keys()}
        return f'{type(self).__name__}({coords})'

    def __contains__(self, cell: Cell) -> bool:
        """Return True if the specified cell is part of the ship."""
        return cell in self._cells_with_hit_states

    @property
    def size(self) -> int:
        return len(self._cells_with_hit_states)

    @property
    def cells(self) -> set[Cell]:
        return set(self._cells_with_hit_states.keys())

    def get_occupied_area(self) -> set[Cell]:
        """Return all cells occupied by the ship, including adjacent buffer zone cells where no other ship may be placed."""
        return self._cells_with_hit_states.keys() | self._get_buffer_cells()

    def has_cells(self, *cells: Cell) -> bool:
        """Return True if all specified cells belong to this ship."""
        return set(cells) <= self._cells_with_hit_states.keys()

    @staticmethod
    def valid_ship_shape(cells: set[Cell]) -> bool:
        """Check whether the cells form a valid contiguous horizontal or vertical ship."""
        if not cells:
            return False

        rows = {cell.row for cell in cells}
        cols = {cell.column for cell in cells}

        is_horizontal = len(rows) == 1  # All cells share the same row index.
        is_vertical = len(cols) == 1  # All cells share the same column index.

        if is_horizontal:
            return max(cols) - min(cols) + 1 == len(cols)  # Columns form a consecutive sequence.
        if is_vertical:
            return max(rows) - min(rows) + 1 == len(rows)  # Rows form a consecutive sequence.
        return False

    def _get_buffer_cells(self) -> set[Cell]:
        """Return the buffer zone cells around the ship where no other ship may be placed."""
        buffer_cells = set()
        for cell in self._cells_with_hit_states:
            for shift in [(-1, -1), (0, -1), (+1, -1), (+1, 0),
                          (+1, +1), (0, +1), (-1, +1), (-1, 0)]:
                neighbor = cell + shift
                if neighbor not in self._cells_with_hit_states:
                    buffer_cells.add(neighbor)
        return buffer_cells

    def can_be_placed_on(self, board: Board) -> bool:
        """Return True if the ship can be placed on the board without overlapping existing ships."""
        return (all(cell in board for cell in self._cells_with_hit_states)
                and not any(self.is_overlapped(_ship) for _ship in board))

    def evaluate_shot(self, target_cell: Cell) -> ShotResult:
        """Evaluate a shot fired at the ship and returns the result (miss, hit, or sunk)."""
        if target_cell not in self._cells_with_hit_states:
            return ShotResult.MISS

        self._cells_with_hit_states[target_cell] = True
        return ShotResult.SUNK if self.is_sunk() else ShotResult.HIT

    def cell_is_damaged(self, cell: Cell) -> bool:
        """Return True if the specified ship cell has been hit."""
        return self._cells_with_hit_states.get(cell, False)

    def is_sunk(self) -> bool:
        """Return True if all segments of the ship have been hit."""
        return all(self._cells_with_hit_states.values())

    def is_overlapped(self, ship: Ship) -> bool:
        """Return True if this ship overlaps or touches another ship (including buffer zones)."""
        return bool(
            self._cells_with_hit_states.keys() & ship._cells_with_hit_states.keys() or
            self._cells_with_hit_states.keys() & ship._get_buffer_cells()
        )


class ComputerFleetFactory:
    """Responsible for generating the computer player's fleet."""

    def __init__(self, computer_board: Board):
        self.board = computer_board

    def _create_ship_cells(self, ship_size: int) -> set[Cell]:
        """Randomly generates a set of cells for a ship of the given size, placed either horizontally or
        vertically within the board boundaries.
        """
        horizontal = choice([True, False])

        if horizontal:
            row_index = randint(0, self.board.size - 1)
            col_index = randint(0, self.board.size - ship_size)  # Column index of the first cell (leftmost).
            return {Cell(row_index, col_index + i) for i in range(ship_size)}
        else:
            row_index = randint(0, self.board.size - ship_size)  # Row index of the first cell (topmost).
            col_index = randint(0, self.board.size - 1)
            return {Cell(row_index + i, col_index) for i in range(ship_size)}

    def produce_ships(self) -> None:
        """Generates the full fleet and places it on the board."""
        for ship_size in self.board.ship_sizes:
            placed = False
            while not placed:
                cells = self._create_ship_cells(ship_size)
                ship = Ship(cells)
                try:
                    self.board.add_ship(ship)
                except ShipOverlapError:
                    continue  # Retry if the ship overlaps with an existing one.
                else:
                    placed = True  # Successful placement.


class ComputerPlayer:
    """Computer player that randomly places ships and fires at the opponent's board."""

    def __init__(self, computer_board: Board):
        self.computer_board = computer_board
        self._human_ship_damaged_cells: list[Cell] = []
        self._cells_already_shot: set[Cell] = set()

    def place_ships(self):
        factory = ComputerFleetFactory(self.computer_board)
        factory.produce_ships()

    def shoot(self, human_board: Board) -> tuple[ShotResult, set[Cell]]:
        """Select a random target cell on the human player's board, avoiding previously fired shots.
        If a ship is hit, the computer continues targeting nearby cells until the ship is sunk.
        Only after sinking the ship does it switch back to random targeting.
        """
        # If no ship segment has been hit yet, choose a random target; otherwise continue targeting the currently hit ship.
        if not self._human_ship_damaged_cells:
            target_cell = self._choose_random_target_cell(human_board)
        else:
            target_cell = self._choose_target_cell_to_sink(human_board)

        shot_result = human_board.process_shot(target_cell)

        if shot_result == ShotResult.HIT:
            self._human_ship_damaged_cells.append(target_cell)
        if shot_result == ShotResult.SUNK:
            self._human_ship_damaged_cells.clear()

        affected_cells = set()

        if shot_result in (ShotResult.MISS, ShotResult.HIT):
            affected_cells = {target_cell}
        elif shot_result == ShotResult.SUNK:
            ship = human_board.get_ship(target_cell)
            assert ship is not None  # If the ship is sunk, the target cell must belong to it.
            affected_cells = set(ship.cells)

        return shot_result, affected_cells

    @staticmethod
    def _choose_random_target_cell(human_board: Board) -> Cell:
        """Choose a random target cell on the human player's board, avoiding previously
        shot cells and buffer zones of sunken ships.
        """
        target_cell = choice(list(human_board.get_cells_available_to_target() - human_board.shots_received))
        return target_cell

    def _choose_target_cell_to_sink(self, human_board: Board) -> Cell:
        """Choose the next target cell in order to sink a partially discovered ship.
        The selection strategy tries to extend the currently hit ship segment in either horizontal or vertical direction.
        """
        potential_target_cells: tuple[Cell, ...] = ()

        if len(self._human_ship_damaged_cells) == 1:
            # If only one segment has been hit, try adjacent cells in all four directions.
            left_cell = self._human_ship_damaged_cells[0] + (-1, 0)
            right_cell = self._human_ship_damaged_cells[0] + (+1, 0)
            top_cell = self._human_ship_damaged_cells[0] + (0, -1)
            bottom_cell = self._human_ship_damaged_cells[0] + (0, +1)
            potential_target_cells = (left_cell, right_cell, top_cell, bottom_cell)

        elif len(self._human_ship_damaged_cells) > 1:
            # If multiple segments are hit, determine ship orientation and target the ends of the detected ship.
            if len({cell.row for cell in self._human_ship_damaged_cells}) == 1:
                # Horizontal ship: target cells left and right of the endpoints.
                left_cell = min(self._human_ship_damaged_cells, key=lambda c: c.column) + (0, -1)
                right_cell = max(self._human_ship_damaged_cells, key=lambda c: c.column) + (0, +1)
                potential_target_cells = (left_cell, right_cell)

            elif len({cell.column for cell in self._human_ship_damaged_cells}) == 1:
                # Vertical ship: target cells above and below the endpoints.
                top_cell = min(self._human_ship_damaged_cells, key=lambda c: c.row) + (-1, 0)
                bottom_cell = max(self._human_ship_damaged_cells, key=lambda c: c.row) + (+1, 0)
                potential_target_cells = (top_cell, bottom_cell)

        # Filter only valid board cells
        selectable_cells = [cell for cell in potential_target_cells if cell in human_board]

        while True:
            target_cell = choice(selectable_cells)
            if target_cell not in human_board.shots_received:
                return target_cell


class HumanFleetFactory:
    """Responsible for creating the human player's fleet."""

    def __init__(self, human_board: Board):
        self.board = human_board
        self.ship_sizes_to_build = list(self.board.ship_sizes)
        self.current_ship_size_to_build: int = self.ship_sizes_to_build[0]

        self._selected_human_ship_cells: list[Cell] = []

    def assemble_ship(self, cell: Cell) -> tuple[bool, bool]:
        """Processes the selection of a cell during human ship placement.
        Determines whether the selected cell can be part of the current ship being assembled.
        If the selection completes a ship, the ship is added to the board and the factory moves on to the next ship size.
        """
        if cell in self._selected_human_ship_cells:
            return False, False

        cell_is_ship_body, ship_completed = False, False

        if not self.board.all_ships_placed():
            self._selected_human_ship_cells.append(cell)
            self.current_ship_size_to_build = self.ship_sizes_to_build[0]

            allowed_cells = self._get_possible_human_ship_cells(self.current_ship_size_to_build,
                                                                *self._selected_human_ship_cells)

            if any(cell in _cells for _cells in allowed_cells):
                cell_is_ship_body = True
                if len(self._selected_human_ship_cells) == self.current_ship_size_to_build:
                    self.board.add_ship(Ship(set(self._selected_human_ship_cells)))
                    ship_completed = True
                    self._selected_human_ship_cells.clear()
                    self.ship_sizes_to_build.pop(0)
            else:
                self._selected_human_ship_cells.pop()

        return cell_is_ship_body, ship_completed

    def _get_possible_human_ship_cells(self, size: int, *cells: Cell) -> tuple[set[Cell], ...]:
        """Return all possible ship cell configurations of the given size that include the specified cells."""
        r0, c0 = cells[0].row, cells[0].column

        # All possible horizontal ship candidates including the anchor cell.
        horizontal_candidates = [ship for i in range(-(size - 1), 1)
                                 if (ship := Ship({Cell(r0, c0 + s + i)
                                                   for s in range(size)
                                                   })).can_be_placed_on(self.board)
                                 ]

        # Horizontal ships that also satisfy all selected constraints.
        valid_horizontal_ships = [ship for ship in horizontal_candidates if ship.has_cells(*cells)]

        # All possible vertical ship candidates including the anchor cell.
        vertical_candidates = [ship for i in range(-(size - 1), 1)
                               if (ship := Ship({Cell(r0 + s + i, c0)
                                                 for s in range(size)
                                                 })).can_be_placed_on(self.board)
                               ]

        # Vertical ships that also satisfy all selected constraints.
        valid_vertical_ships = [ship for ship in vertical_candidates if ship.has_cells(*cells)]

        return tuple(ship.cells for ship in valid_horizontal_ships + valid_vertical_ships)


class GameModel:
    """Core game model that manages the game state, rules, and interactions between the human and computer players.
    It coordinates board state, ship placement, shooting mechanics, and determines the winner of the game.
    """

    def __init__(self, board_size=10):
        self.board_size = board_size if board_size > 10 else 10  # Number of rows and columns.
        self.ship_sizes = (4, 3, 3, 2, 2, 2, 1, 1, 1, 1)  # Sizes of ships to be placed (in number of cells).
        self.current_shipsize_to_build = self.ship_sizes[0]

        # Initialize boards for human and computer players.
        self.human_board = Board(self.board_size, self.ship_sizes)
        self.computer_board = Board(self.board_size, self.ship_sizes)

        # Create the computer player.
        self.computer_player = ComputerPlayer(self.computer_board)
        self.game_phase = GamePhase.PLACEMENT  # Initial phase: ship placement.

        # Let the computer place its ships.
        self.computer_player.place_ships()

        # Create the factory responsible for human ship placement.
        self.human_fleet_factory = HumanFleetFactory(self.human_board)

    def human_make_ship(self, cell: Cell) -> tuple[bool, bool]:
        """Determine whether the selected cell on the human player's board can be part of the currently constructed ship.
        The first return value indicates whether the cell is a valid part of the ship.
        The second indicates whether the ship has been fully completed and placed.
        If all ships have been placed, the game transitions to the battle phase.
        """
        if self.human_board.all_ships_placed():
            self.game_phase = GamePhase.BATTLE
            return False, False

        return self.human_fleet_factory.assemble_ship(cell)

    def human_shoot(self, target_cell: Cell) -> tuple[ShotResult, set[Cell]]:
        """Evaluate a shot fired by the human player at the computer player's board.
        Returns the shot result and the affected cells:
        - If the shot is a miss or hit, returns the target cell.
        - If a ship is sunk, returns all cells occupied by that ship.
        """
        shot_result = self.computer_board.process_shot(target_cell)

        affected_cells = set()
        if shot_result in (ShotResult.MISS, ShotResult.HIT):
            affected_cells = {target_cell}
        elif shot_result == ShotResult.SUNK:
            ship = self.computer_board.get_ship(target_cell)
            assert ship is not None  # If the ship is sunk, the target cell must belong to it.
            affected_cells = set(ship.cells)

        return shot_result, affected_cells

    def computer_shoot(self) -> tuple[ShotResult, set[Cell]]:
        """Evaluate a shot fired by the computer player at the human player's board."""
        return self.computer_player.shoot(self.human_board)

    def check_winner(self) -> Winner | None:
        """Return the winner of the game, if any. Otherwise, returns None."""
        if self.human_board.all_ships_sunk():
            return Winner.COMPUTER
        elif self.computer_board.all_ships_sunk():
            return Winner.HUMAN
        else:
            return None

    def get_undamaged_computer_ship_cells(self) -> set[Cell]:
        """Return all computer ship cells that have not been hit yet."""
        return {cell for ship in self.computer_board for cell in ship.cells if not ship.cell_is_damaged(cell)}

    def get_next_human_ship_size(self) -> int | None:
        """Return the size of the next ship the human player must place. Return None if all ships have already been placed."""
        return next(iter(self.human_fleet_factory.ship_sizes_to_build), None)
