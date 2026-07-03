# Python 3.11+
# module: main

from __future__ import annotations
import tkinter as tk
from itertools import product
import winsound
from typing import cast, Callable
from model import Cell, GameModel, ShotResult, GamePhase, Winner


class BoardView(tk.Frame):
    """Displays a game board and defines methods shared by the human and computer player boards."""

    def __init__(self, master, board_size: int) -> None:
        super().__init__(master)

        self._board_size = board_size if board_size > 10 else 10  # The classic game uses a minimum board size of 10×10.
        self._cell_canvases: dict[Cell, tk.Canvas] = {}  # Maps each board cell to its corresponding canvas widget.
        self._create_cell_grid()

    def _create_cell_grid(self) -> None:
        """Creates and displays the cells of the game board."""
        for row_index, column_index in product(range(self._board_size), repeat=2):
            grid_cell = Cell(row_index, column_index)
            cell_canvas = tk.Canvas(self, width='1.2c', height='1.2c', bg="#B3F0FF", bd=1, highlightthickness=0)
            cell_canvas.grid(row=row_index, column=column_index, padx=1, pady=1)
            self._cell_canvases[grid_cell] = cell_canvas

    def bind_cell_event(self, tk_event_descriptor: str, handler: Callable[[tk.Event], None]) -> None:
        """Binds the specified event and event handler to all board cells."""
        for cell_widget in self._cell_canvases.values():
            cell_widget.bind(tk_event_descriptor, handler)

    def update_on_shot(self, affected_cells: set[Cell], shot_result: ShotResult) -> None:
        """Updates the appearance of the specified board cells based on the shot result.
        If the shot is a miss, the first argument contains a single cell, and a small black dot is drawn on it.
        If the shot is a hit but the ship is not sunk, the first argument contains a single cell, which is
        colored gray and marked with a red X.
        If the shot sinks a ship, the first argument contains one or more cells, all of which are colored black.
        """
        match shot_result:
            case ShotResult.MISS:
                self._update_miss(affected_cells.pop())

            case ShotResult.HIT:
                self._update_hit(affected_cells.pop())

            case ShotResult.SUNK:
                self._update_sunk(affected_cells)

    def _update_miss(self, cell: Cell) -> None:
        """Draws a small black dot on the specified cell."""
        canvas = self._cell_canvases[cell]
        cnv_width, cnv_height = canvas.winfo_width(), canvas.winfo_height()
        canvas.create_oval(cnv_width * 0.4, cnv_height * 0.4, cnv_width * 0.6, cnv_height * 0.6, fill="black")

    def _update_hit(self, cell: Cell) -> None:
        """Colors the specified cell gray and marks it with a red X."""
        canvas = self._cell_canvases[cell]
        cnv_width, cnv_height = canvas.winfo_width(), canvas.winfo_height()
        canvas.config(bg='grey75')
        canvas.create_line(0, 0, cnv_width, cnv_height, fill="red", width=4)
        canvas.create_line(0, cnv_height, cnv_width, 0, fill="red", width=4)

    def _update_sunk(self, cells: set[Cell]) -> None:
        """Colors the specified cells black."""
        for cell in cells:
            canvas = self._cell_canvases[cell]
            canvas.delete('all')
            canvas.config(bg='black')


class HumanBoardView(BoardView):
    """Panel for displaying the human player's board."""

    def mark_as_ship_cell(self, cell: Cell):
        """Highlights the specified cell as part of a ship."""
        self._cell_canvases[cell].config(bg="SeaGreen3")

    @staticmethod
    def play_ship_placement_sound() -> None:
        """Plays a sound prompting the player to place the next ship."""
        winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)


class ComputerBoardView(BoardView):
    """Panel for displaying the computer player's board."""

    def mark_as_revealed_ship_cell(self, cell: Cell) -> None:
        """Highlights the specified cell belonging to an undamaged enemy ship."""
        self._cell_canvases[cell].config(bg='yellow')


class MessageView(tk.Frame):
    """Panel for displaying status messages."""

    def __init__(self, master, control_variable: tk.StringVar) -> None:
        super().__init__(master)
        message_lbl = tk.Label(self, textvariable=control_variable, bg='white', fg='red', font=('Tahoma', 14, 'bold'))
        message_lbl.pack(fill='both', expand=True)


class BattleshipGame(tk.Tk):
    """Main controller of the application, which also represents the main GUI window.
    It is responsible for creating the model and views, registering event handlers, and coordinating the game flow.
    """

    def __init__(self, board_size: int = 10) -> None:
        super().__init__()

        self.title("Battleship")
        self.resizable(False, False)

        # Create the game model.
        self._game_model = GameModel(board_size)

        # Create and arrange the display panels.
        human_board_title = tk.Label(self, text="Human Player's Board", font=('Tahoma', 12, 'bold'))
        computer_board_title = tk.Label(self, text="Computer Player's Board", font=('Tahoma', 12, 'bold'))
        human_board_title.grid(row=0, column=0, padx=10, pady=(10, 0), sticky='news')
        computer_board_title.grid(row=0, column=1, padx=10, pady=(10, 0), sticky='news')

        self.human_board = HumanBoardView(self, board_size)
        self.computer_board = ComputerBoardView(self, board_size)

        self.human_board.grid(row=1, column=0, padx=10, pady=10)
        self.computer_board.grid(row=1, column=1, padx=10, pady=10)

        self.message = tk.StringVar(self, '')
        MessageView(self, self.message).grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky='news')

        # Specify which user-generated events the board cells should respond to and the corresponding event handlers.
        self.human_board.bind_cell_event("<Button-1>", self._place_human_ship)
        self.computer_board.bind_cell_event("<Button-1>", self._process_shot_on_computer_board)
        self.computer_board.bind_cell_event("<Button-3>", self._reveal_undamaged_computer_ship_cells)

        # Initial message prompting the player to place the first ship.
        self.message.set(f'Place a ship of length {self._game_model.get_next_human_ship_size()}.')

    # ----------------------------------- EVENT HANDLERS --------------------------------

    def _place_human_ship(self, event: tk.Event) -> None:
        """Handles ship placement on the human player's board.
        If the selected cell belongs to the ship being placed, its appearance is updated accordingly.
        Once a ship has been completed, a sound is played and the player is prompted to place the next ship.
        After all ships have been placed, the game enters the battle phase.
        """
        cell_canvas = cast(tk.Canvas, event.widget)
        clicked_cell: Cell = Cell(cell_canvas.grid_info()['row'], cell_canvas.grid_info()['column'])

        if self._game_model.game_phase == GamePhase.PLACEMENT:
            cell_is_ship_body, ship_completed = self._game_model.human_make_ship(clicked_cell)

            if cell_is_ship_body:
                # Visually indicate that the selected cell is part of a ship.
                self.human_board.mark_as_ship_cell(clicked_cell)

            if self._game_model.get_next_human_ship_size():
                if ship_completed:
                    # Notify the player to place the next ship.
                    self.human_board.play_ship_placement_sound()
                    self.message.set(f'Place a ship of length {self._game_model.get_next_human_ship_size()}.')
            else:
                # All ships have been placed, so the game enters the battle phase.
                self._game_model.game_phase = GamePhase.BATTLE
                self.message.set("Fire at the opponent's board.")

    def _process_shot_on_computer_board(self, event: tk.Event) -> None:
        """Processes the human player's shot at the computer's board.
        The shot result is displayed on the computer's board. If all ships are sunk, the game ends.
        """
        cell_canvas = cast(tk.Canvas, event.widget)
        clicked_cell: Cell = Cell(cell_canvas.grid_info()['row'], cell_canvas.grid_info()['column'])

        if self._game_model.game_phase == GamePhase.BATTLE:
            shot_result, affected_cells = self._game_model.human_shoot(clicked_cell)
            self.computer_board.update_on_shot(affected_cells, shot_result)
            self._notify_upon_victory()

            # After the human player's turn, the computer takes its shot.
            self._computer_shoot()

    def _reveal_undamaged_computer_ship_cells(self, event: tk.Event) -> None:
        """Reveals the cells of the computer's ships that have not been hit.
        Has no effect during the ship placement phase.
        """
        if self._game_model.game_phase != GamePhase.PLACEMENT:
            for cell in self._game_model.get_undamaged_computer_ship_cells():
                self.computer_board.mark_as_revealed_ship_cell(cell)

    # ------------------------------------- HELPER METHODS ------------------------------

    def _computer_shoot(self) -> None:
        """Processes the computer player's shot at the human player's board.
        The shot result is displayed on the human player's board. If all ships are sunk, the game ends.
        """
        if self._game_model.game_phase != GamePhase.VICTORY:
            shot_result, affected_cells = self._game_model.computer_shoot()
            self.human_board.update_on_shot(affected_cells, shot_result)
            self._notify_upon_victory()

    def _notify_upon_victory(self) -> None:
        """Displays the winner and switches the game to the victory phase."""
        if (winner := self._game_model.check_winner()) is not None:
            text = "You win!" if winner == Winner.HUMAN else "The computer wins!"
            self.message.set(text)
            self._game_model.game_phase = GamePhase.VICTORY

    def run(self) -> None:
        """Starts the game."""
        self.mainloop()


if __name__ == '__main__':
    battleship_game = BattleshipGame()
    battleship_game.run()
