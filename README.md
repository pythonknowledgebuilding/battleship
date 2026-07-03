# Battleship Game
Battleship is one of the best-known board games and has long been adapted into numerous digital versions that let players compete against a computer-controlled opponent. 
## How to Play
This application is a computer implementation of the classic Battleship game, in which you compete against the computer. The game follows the traditional rules: both players place their fleets on separate 10×10 boards and then take turns trying to sink each other's ships.
### Getting Started
When the program starts, two game boards are displayed. The board on the left represents your fleet, while the board on the right represents the computer's hidden fleet. At the beginning of the game, the program displays the size of the ship you need to place next.
### Placing Your Ships
Ships are placed by clicking cells on your own board. The program always indicates the size of the next ship to be placed. You build a ship by selecting its cells one by one.
After each click, the program checks whether the currently selected cells can still form a valid ship. As a result, it is impossible to select a cell that would make the ship placement invalid.
The program enforces the standard Battleship placement rules:
- Ships may be placed only horizontally or vertically. 
-	A ship must occupy consecutive cells with no gaps. 
-	Ships may not touch each other, not even at the corners. 

When a ship has been completed, an audible notification is played and the program automatically prompts you to place the next ship.
Once all ships have been placed, the game automatically enters the battle phase.
### Battle Phase
During the battle phase, fire at the opponent by left-clicking a cell on the board on the right.
The result of each shot is displayed immediately:
-	Small black dot: the shot missed. 
-	Red X on a gray background: the shot hit a ship, but it has not yet sunk. 
-	Black cell: the entire ship has been sunk.

Each shot fired by the human player is automatically followed by the computer's move, which is displayed on your own board using the same visual indicators.
### End of the Game
The game continues until all ships belonging to one player have been sunk. The program then displays a message announcing the winner.
### Revealing the Opponent's Undamaged Ships
Once the battle phase has begun, you can right-click the opponent's board to reveal the locations of the computer player's ship cells that have not yet been hit.
This feature is useful after losing a game, as it lets you see where the remaining enemy ships were located and which cells you would still have needed to find in order to win.

## Screenshots
The following screenshots illustrate several key stages of the game, including ship placement, the battle phase, and the end of the game.

<img src="images/example.png" width="300" />
