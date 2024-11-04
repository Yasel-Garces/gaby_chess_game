import pygame as p
import sys
import pyttsx3
from flask import Flask
import os

app = Flask(__name__)

p.init()
# Conditionally initialize mixer if not on Heroku
if os.getenv('HEROKU'):
    print("Running on Heroku, skipping audio initialization.")
else:
    p.mixer.init()

# Initialize the text-to-speech engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)  # Adjust speaking rate

# Game Constants
WIDTH = HEIGHT = 1000  # Increased window size for larger elements
DIMENSION = 8  # Chessboard dimensions are 8x8
SQ_SIZE = HEIGHT // DIMENSION
MAX_FPS = 15  # For animations
IMAGES = {}

# Load Images
def load_images():
    pieces = ['bK', 'bQ', 'bR', 'bB', 'bN', 'bP',
              'wK', 'wQ', 'wR', 'wB', 'wN', 'wP']
    for piece in pieces:
        IMAGES[piece] = p.transform.smoothscale(
            p.image.load("images/" + piece + ".png"), (SQ_SIZE, SQ_SIZE))

# Load Sounds
move_sound = p.mixer.Sound('sounds/move.wav')
capture_sound = p.mixer.Sound('sounds/capture.wav')

# Main Driver
def main():
    screen = p.display.set_mode((WIDTH, HEIGHT), p.SRCALPHA)

    clock = p.time.Clock()
    screen.fill(p.Color("white"))
    load_images()
    gs = GameState(screen)
    running = True
    game_over = False  # Flag to check if the game is over
    selected_sq = ()  # No square is selected initially
    player_clicks = []  # Tracks player clicks

    while running:
        for e in p.event.get():
            if e.type == p.QUIT:
                running = False
                p.quit()
                sys.exit()

            elif e.type == p.KEYDOWN:
                if e.key == p.K_ESCAPE:
                    running = False
                if game_over:
                    if e.key == p.K_r:
                        reset_game(gs)
                        game_over = False
                        selected_sq = ()
                        player_clicks = []
                    elif e.key == p.K_ESCAPE:
                        running = False
            elif not game_over and e.type == p.MOUSEBUTTONDOWN:
                location = p.mouse.get_pos()  # x, y position of mouse
                col = location[0] // SQ_SIZE
                row = location[1] // SQ_SIZE

                if selected_sq == ():  # No piece selected yet
                    if gs.board[row][col] != '--':
                        piece_color = gs.board[row][col][0]
                        if (piece_color == 'w' and gs.white_to_move) or (piece_color == 'b' and not gs.white_to_move):
                            selected_sq = (row, col)
                            player_clicks.append(selected_sq)
                else:
                    player_clicks.append((row, col))
                    move = Move(player_clicks[0], player_clicks[1], gs.board)
                    if gs.make_move(move):
                        # Check for checkmate or stalemate
                        if gs.in_checkmate():
                            tts_engine.say("Checkmate!")
                            tts_engine.runAndWait()
                            display_message(screen, "Checkmate! Press 'R' to play again or 'Esc' to quit.")
                            game_over = True  # Set game_over flag
                        elif gs.in_stalemate():
                            tts_engine.say("Stalemate!")
                            tts_engine.runAndWait()
                            display_message(screen, "Stalemate! Press 'R' to play again or 'Esc' to quit.")
                            game_over = True  # Set game_over flag
                    else:
                        display_message(screen, "Invalid move!")
                    selected_sq = ()  # Reset user clicks
                    player_clicks = []

        draw_game_state(screen, gs, selected_sq)
        if game_over:
            display_game_over_message(screen)
        clock.tick(MAX_FPS)
        p.display.flip()

# Draw the current game state
def draw_game_state(screen, gs, selected_sq):
    draw_board(screen)
    highlight_movable_pieces(screen, gs)
    if selected_sq != ():
        highlight_squares(screen, gs, selected_sq)
    draw_pieces(screen, gs.board)

# Draw the chessboard
def draw_board(screen):
    colors = [p.Color(235, 235, 208), p.Color(119, 148, 85)]  # Light and dark squares
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            color = colors[((r + c) % 2)]
            p.draw.rect(screen, color, p.Rect(
                c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))

# Highlight pieces that can move
def highlight_movable_pieces(screen, gs):
    movable_pieces = get_movable_pieces(gs)
    s = p.Surface((SQ_SIZE, SQ_SIZE))
    s.set_alpha(100)  # Transparency value
    s.fill(p.Color('blue'))  # Blue color for movable pieces
    for (row, col) in movable_pieces:
        screen.blit(s, (col * SQ_SIZE, row * SQ_SIZE))

# Get all pieces that can move for the current player
def get_movable_pieces(gs):
    """Returns a list of pieces that can move for the current player."""
    movable_pieces = []
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = gs.board[r][c]
            if piece != '--':
                color = piece[0]
                if (color == 'w' and gs.white_to_move) or (color == 'b' and not gs.white_to_move):
                    valid_moves = get_valid_moves(gs, r, c)
                    if valid_moves:
                        movable_pieces.append((r, c))
    return movable_pieces

# Highlight possible moves
def highlight_squares(screen, gs, selected_sq):
    valid_moves = get_valid_moves(gs, *selected_sq)
    s = p.Surface((SQ_SIZE, SQ_SIZE))
    s.set_alpha(100)  # Transparency value
    s.fill(p.Color('yellow'))
    for move in valid_moves:
        screen.blit(s, (move[1] * SQ_SIZE, move[0] * SQ_SIZE))

# Draw the pieces on the board
def draw_pieces(screen, board):
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != '--':
                screen.blit(IMAGES[piece], p.Rect(
                    c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))

# Game State class to store the state of the game
class GameState:
    def __init__(self, screen):
        # Standard chess starting position
        self.board = [
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bP", "bP", "bP", "bP", "bP", "bP", "bP", "bP"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["wP", "wP", "wP", "wP", "wP", "wP", "wP", "wP"],
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]
        ]
        self.white_to_move = True
        self.screen = screen

    def make_move(self, move):
        # Check if the move is valid
        valid_moves = get_valid_moves(self, move.start_row, move.start_col)
        if (move.end_row, move.end_col) in valid_moves:
            # Move the piece
            if self.board[move.end_row][move.end_col] != '--':
                capture_sound.play()
            else:
                move_sound.play()
            self.board[move.start_row][move.start_col] = '--'
            self.board[move.end_row][move.end_col] = move.piece_moved

            # Generate move narration and provide audio narration
            move_narration = move.get_move_narration()
            print(f"Move: {move_narration}")
            display_message(self.screen, f"Move: {move_narration}")

            # Speak the move using TTS
            tts_engine.say(move_narration)
            tts_engine.runAndWait()

            self.white_to_move = not self.white_to_move
            return True
        else:
            return False

    def in_check(self, color):
        """Check if the player's king is in check."""
        king_pos = self.find_king(color)
        opponent_color = 'b' if color == 'w' else 'w'
        opponent_moves = self.get_all_possible_moves(opponent_color)
        return king_pos in opponent_moves

    def in_checkmate(self):
        """Check for checkmate."""
        color = 'w' if self.white_to_move else 'b'
        if self.in_check(color) and not self.has_valid_moves(color):
            return True
        return False

    def in_stalemate(self):
        """Check for stalemate."""
        color = 'w' if self.white_to_move else 'b'
        if not self.in_check(color) and not self.has_valid_moves(color):
            return True
        return False

    def has_valid_moves(self, color):
        """Check if the player has any valid moves."""
        for row in range(DIMENSION):
            for col in range(DIMENSION):
                if self.board[row][col].startswith(color):
                    valid_moves = get_valid_moves(self, row, col)
                    if valid_moves:
                        return True
        return False

    def get_all_possible_moves(self, color):
        """Get all possible moves for the specified color."""
        moves = []
        for row in range(DIMENSION):
            for col in range(DIMENSION):
                if self.board[row][col].startswith(color):
                    moves.extend(get_possible_moves(self, row, col))
        return moves

    def find_king(self, color):
        """Find the position of the king."""
        for row in range(DIMENSION):
            for col in range(DIMENSION):
                if self.board[row][col] == color + 'K':
                    return (row, col)
        return None

# Move class to handle piece moves
class Move:
    ranks_to_rows = {str(r + 1): 7 - r for r in range(8)}
    rows_to_ranks = {v: k for k, v in ranks_to_rows.items()}
    files_to_cols = {chr(c + 97): c for c in range(8)}
    cols_to_files = {v: k for k, v in files_to_cols.items()}

    def __init__(self, start_sq, end_sq, board):
        self.start_row = start_sq[0]
        self.start_col = start_sq[1]
        self.end_row = end_sq[0]
        self.end_col = end_sq[1]
        self.piece_moved = board[self.start_row][self.start_col]
        self.piece_captured = board[self.end_row][self.end_col]

    def get_chess_notation(self):
        """ Returns the move in standard chess notation, e.g. 'Qe5' """
        piece = self.piece_moved[1]
        if piece == 'P':  # Pawn moves don't have the piece letter
            piece = ''
        return f"{piece}{self.cols_to_files[self.end_col].upper()}{self.rows_to_ranks[self.end_row]}"

    def get_move_narration(self):
        """ Returns the move as narration, e.g. 'White Queen to D3' """
        color = 'White' if self.piece_moved[0] == 'w' else 'Black'
        piece_name = {
            'K': 'King',
            'Q': 'Queen',
            'R': 'Rook',
            'B': 'Bishop',
            'N': 'Knight',
            'P': 'Pawn'
        }.get(self.piece_moved[1], '')
        return f"{color} {piece_name} to {self.cols_to_files[self.end_col].upper()}{self.rows_to_ranks[self.end_row]}"

# Get valid moves for a piece at (row, col)
def get_valid_moves(gs, row, col):
    """Generates valid moves for a piece, ensuring the king is not left in check."""
    piece = gs.board[row][col]
    color = piece[0]
    possible_moves = get_possible_moves(gs, row, col)
    valid_moves = []
    for move in possible_moves:
        # Make a temporary copy of the board
        temp_board = [r.copy() for r in gs.board]
        # Make the move on the temporary board
        temp_board[row][col] = '--'
        temp_board[move[0]][move[1]] = piece
        # Create a temporary GameState with the new board
        temp_gs = GameState(gs.screen)
        temp_gs.board = temp_board
        temp_gs.white_to_move = gs.white_to_move  # Keep the same player's turn
        # Check if the player's own king is in check after the move
        if not temp_gs.in_check(color):
            valid_moves.append(move)
    return valid_moves

# Get possible moves for a piece at (row, col)
def get_possible_moves(gs, row, col):
    possible_moves = []
    piece = gs.board[row][col]
    if piece == '--':
        return possible_moves
    color = piece[0]
    piece_type = piece[1]
    directions = []
    if piece_type == 'P':  # Pawn moves
        if color == 'w':
            # Forward move
            if row > 0 and gs.board[row - 1][col] == '--':
                possible_moves.append((row - 1, col))
                # Double move from starting position
                if row == 6 and gs.board[row - 2][col] == '--':
                    possible_moves.append((row - 2, col))
            # Captures
            if row > 0 and col > 0 and gs.board[row - 1][col - 1].startswith('b'):
                possible_moves.append((row - 1, col - 1))
            if row > 0 and col < 7 and gs.board[row - 1][col + 1].startswith('b'):
                possible_moves.append((row - 1, col + 1))
        else:
            # Forward move
            if row < 7 and gs.board[row + 1][col] == '--':
                possible_moves.append((row + 1, col))
                # Double move from starting position
                if row == 1 and gs.board[row + 2][col] == '--':
                    possible_moves.append((row + 2, col))
            # Captures
            if row < 7 and col > 0 and gs.board[row + 1][col - 1].startswith('w'):
                possible_moves.append((row + 1, col - 1))
            if row < 7 and col < 7 and gs.board[row + 1][col + 1].startswith('w'):
                possible_moves.append((row + 1, col + 1))
    elif piece_type == 'R':  # Rook moves
        directions = [(-1, 0), (0, -1), (1, 0), (0, 1)]
    elif piece_type == 'B':  # Bishop moves
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    elif piece_type == 'Q':  # Queen moves
        directions = [(-1, 0), (0, -1), (1, 0), (0, 1),
                      (-1, -1), (-1, 1), (1, -1), (1, 1)]
    elif piece_type == 'K':  # King moves
        directions = [(-1, -1), (-1, 0), (-1, 1),
                      (0, -1),         (0, 1),
                      (1, -1),  (1, 0),  (1, 1)]
        for d in directions:
            end_row = row + d[0]
            end_col = col + d[1]
            if 0 <= end_row < DIMENSION and 0 <= end_col < DIMENSION:
                end_piece = gs.board[end_row][end_col]
                if end_piece == '--' or end_piece[0] != color:
                    possible_moves.append((end_row, end_col))
        return possible_moves
    elif piece_type == 'N':  # Knight moves
        knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                        (1, -2),  (1, 2),  (2, -1),  (2, 1)]
        for m in knight_moves:
            end_row = row + m[0]
            end_col = col + m[1]
            if 0 <= end_row < DIMENSION and 0 <= end_col < DIMENSION:
                end_piece = gs.board[end_row][end_col]
                if end_piece == '--' or end_piece[0] != color:
                    possible_moves.append((end_row, end_col))
        return possible_moves
    # Handle sliding pieces (Rook, Bishop, Queen)
    for d in directions:
        for i in range(1, DIMENSION):
            end_row = row + d[0] * i
            end_col = col + d[1] * i
            if 0 <= end_row < DIMENSION and 0 <= end_col < DIMENSION:
                end_piece = gs.board[end_row][end_col]
                if end_piece == '--':
                    possible_moves.append((end_row, end_col))
                elif end_piece[0] != color:
                    possible_moves.append((end_row, end_col))
                    break
                else:
                    break
            else:
                break
    return possible_moves

# Display positive feedback messages
def display_message(screen, text):
    font = p.font.SysFont('Arial', 32, True, False)
    text_object = font.render(text, True, p.Color('Black'))
    text_location = p.Rect(0, 0, WIDTH, HEIGHT).move(
        WIDTH / 2 - text_object.get_width() / 2, HEIGHT / 2 - text_object.get_height() / 2)
    screen.blit(text_object, text_location)
    p.display.flip()

# Display game over message
def display_game_over_message(screen):
    font = p.font.SysFont('Arial', 36, True, False)
    message = "Game Over! Press 'R' to play again or 'Esc' to quit."
    text_object = font.render(message, True, p.Color('Red'))
    text_location = p.Rect(0, 0, WIDTH, HEIGHT).move(
        WIDTH / 2 - text_object.get_width() / 2, HEIGHT / 2 - text_object.get_height() / 2)
    screen.blit(text_object, text_location)
    p.display.flip()

# Reset the game to start a new game
def reset_game(gs):
    gs.__init__(gs.screen)

if __name__ == "__main__":
    main()