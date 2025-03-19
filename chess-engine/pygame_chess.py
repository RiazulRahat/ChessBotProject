import pygame
from sys import exit
import chess
from chess_engine import ChessEngine
from utils import scale_and_resize

# -------------------------
# Initialize Pygame & Engine
# -------------------------
pygame.init()
engine = ChessEngine()

# ---------------------------------
# --- Board Coordinates Mapping ---
# ---------------------------------
# This dictionary maps each chess square to its pixel coordinates
board_coord = {"A1":(83, 508), "A2":(83, 455), "A3":(83, 400), "A4":(83, 345), 
               "A5":(83, 290), "A6":(83, 237), "A7":(83, 181), "A8":(83, 127),
               "B1":(138, 508), "B2":(138, 455), "B3":(138, 400), "B4":(138, 345), 
               "B5":(138, 290), "B6":(138, 237), "B7":(138, 181), "B8":(138, 127),
               "C1":(193, 508), "C2":(193, 455), "C3":(193, 400), "C4":(193, 345), 
               "C5":(193, 290), "C6":(193, 237), "C7":(193, 181), "C8":(193, 127),
               "D1":(247, 506), "D2":(247, 455), "D3":(247, 400), "D4":(247, 345), 
               "D5":(247, 290), "D6":(247, 237), "D7":(247, 181), "D8":(247, 127),
               "E1":(302, 506), "E2":(302, 455), "E3":(302, 400), "E4":(302, 345), 
               "E5":(302, 290), "E6":(302, 237), "E7":(302, 181), "E8":(302, 127),
               "F1":(356, 508), "F2":(356, 455), "F3":(356, 400), "F4":(356, 345), 
               "F5":(356, 290), "F6":(356, 237), "F7":(356, 181), "F8":(356, 127),
               "G1":(411, 508), "G2":(411, 455), "G3":(411, 400), "G4":(411, 345), 
               "G5":(411, 290), "G6":(411, 237), "G7":(411, 181), "G8":(411, 127),
               "H1":(465, 508), "H2":(465, 455), "H3":(465, 400), "H4":(465, 345), 
               "H5":(465, 290), "H6":(465, 237), "H7":(465, 181), "H8":(465, 127)
               }
# ---------------------------------
# --- Window and Board Settings ---
# ---------------------------------
WIDTH, HEIGHT = 550, 600    # Window Dimensions
BOARD_DIMENSION = 500       # Displayed chess board area (in pixels)

# Calculate the size of each square on the board.
# The board image is 1274 pixels in total with 1110 pixels representing the checkered area.
# Divide the checkered area by 8 to get the square size.
SQUARE_SIZE = int(((BOARD_DIMENSION / 1274) * 1110 ) / 8 )   # size of each square

# Create the display window and set caption
screen = pygame.display.set_mode((WIDTH,HEIGHT)) 
pygame.display.set_caption("Chess Game Window!")

# Creating a clock object to control frame rate
clock = pygame.time.Clock() 

# -----------------------------
# --- Load and Scale Images ---
# -----------------------------
# Load and scale the Chess Board image to fit the board dimension.
chess_board = pygame.image.load('assets/chess_board.png')
chess_board = pygame.transform.scale(chess_board, (BOARD_DIMENSION,BOARD_DIMENSION))

# Load and scale each chess piece using the helper function from utils.py

# Stored in a dictionary which maps the piece symbols to its images
piece_images = {
    # White Pieces
    "P": scale_and_resize(pygame.image.load('assets/pawn_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    "R": scale_and_resize(pygame.image.load('assets/rook_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    "N": scale_and_resize(pygame.image.load('assets/knight_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    "B": scale_and_resize(pygame.image.load('assets/bishop_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    "Q": scale_and_resize(pygame.image.load('assets/queen_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    "K": scale_and_resize(pygame.image.load('assets/king_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    # Black Pieces
    "p": scale_and_resize(pygame.image.load('assets/pawn_black.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    "r": scale_and_resize(pygame.image.load('assets/rook_black.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    "n": scale_and_resize(pygame.image.load('assets/knight_black.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    "b": scale_and_resize(pygame.image.load('assets/bishop_black.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    "q": scale_and_resize(pygame.image.load('assets/queen_black.png'), (SQUARE_SIZE, SQUARE_SIZE)),
    "k": scale_and_resize(pygame.image.load('assets/king_black.png'), (SQUARE_SIZE, SQUARE_SIZE))
}

# --------------------------------------
# Global Variables for Movement Handling
# --------------------------------------
selected_square = None  # Stores the currently selected square coordinate (i.e - "A1")
legal_destinations = [] # List of square coordinates from selected piece

# ------------------------
# --- Helper Functions ---
# ------------------------
def draw_piece(piece_image, square_label):
    """
    Draws the given piece image on the board, aligning its midbottom with the
    coordinate specified for the given chess square.
    
    Parameters:
      piece_image (pygame.Surface): The image of the chess piece.
      square_label (str): The board square (e.g., "E1") where the piece will be anchored.
    """
    # Get the target coordinate from the board mapping
    target_coord = board_coord[square_label]
    # Create a rectangle for the piece with midbottom anchored at target_coord
    piece_rect = piece_image.get_rect(midbottom=target_coord)
    # Draw (blit) the piece image onto the screen using its rectangle
    screen.blit(piece_image, piece_rect)

def get_square_rect(square_label):
    """
    Returns a pygame.Rect for the square. We compute the top-left corner
    from the board_coord which holds the midbottom.
    """
    midbottom = board_coord[square_label]
    # Compute top-left coordinates from midbottom:
    x = midbottom[0] - SQUARE_SIZE // 2
    y = midbottom[1] - SQUARE_SIZE
    return pygame.Rect(x, y, SQUARE_SIZE, SQUARE_SIZE)

def highlight_square(square_label, color = (0, 255, 0 ,100)):
    """
    Highlights the given square by drawing a semi-transparent rectangle over it.
    """
    # Create a surface with per-pixel alpha for transparency
    highlight = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
    highlight.fill(color)
    rect = get_square_rect(square_label)
    screen.blit(highlight, rect.topleft)

def square_from_mouse(pos):
    """
    Given a mouse position, return the square label if the click is within any board square.
    If no square is found, return None.
    """
    for square, coord in board_coord.items():
        rect = get_square_rect(square)
        if rect.collidepoint(pos):
            return square
    return None

# --- Main Game Loop ---
running = True
while running:
    # Process events (keyboard, mouse, window close, etc.)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        # Handle mouse clicks
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            clicked_square = square_from_mouse(pos)
            if clicked_square:
                # If no square is currently selected, try to select a piece
                if selected_square is None:
                    # Convert clicked_square to lower-case (for python-chess API)
                    sq_index = chess.parse_square(clicked_square.lower())
                    piece = engine.board.piece_at(sq_index)
                    # Only select if there is a piece at the square and it belongs to the side to move.
                    if piece and piece.color == engine.board.turn:
                        selected_square = clicked_square
                        # Filter legal moves for moves originating from this square.
                        legal_destinations = []
                        for move in engine.board.legal_moves:
                            if move.from_square == sq_index:
                                dest_label = chess.square_name(move.to_square).upper()
                                legal_destinations.append(dest_label)
                else:
                    # A square is already selected. Check if clicked_square is a legal destination.
                    if clicked_square in legal_destinations:
                        # Construct the move in SAN by using python-chess Move object.
                        from_sq = chess.parse_square(selected_square.lower())
                        to_sq = chess.parse_square(clicked_square.lower())
                        # Find the move among legal moves.
                        move_found = None
                        for move in engine.board.legal_moves:
                            if move.from_square == from_sq and move.to_square == to_sq:
                                move_found = move
                                break
                        if move_found:
                            # Apply the move to the engine's board.
                            engine.board.push(move_found)
                    # Clear the selection whether or not a legal move was made.
                    selected_square = None
                    legal_destinations = []


    # -------------------
    # Drawing Section
    # -------------------
    # Fill the background with white
    screen.fill('White')

    # Blit (draw) the chess board image on the screen at positiom (25, 50)
    screen.blit(chess_board,(25,50))

    # Highlight selected square and legal destination squares, if any.
    if selected_square:
        highlight_square(selected_square, color=(255, 255, 0, 150))  # Yellow for selection
        for dest in legal_destinations:
            highlight_square(dest, color=(0, 255, 0, 150))  # Green for legal moves

    # Draw all pieces dynamically from engine board state.
    # Iterate all squares and draw it if piece is there
    for square in chess.SQUARES:
        piece = engine.board.piece_at(square)
        if piece:
            # Convert square index to square label (to uppercase "E1")
            square_label = chess.square_name(square).upper()
            # Get the image for this piece using its symbol
            img = piece_images.get(piece.symbol())
            if img:
                draw_piece(img, square_label)

    # Update the display window to show the new frame
    pygame.display.update()

    # Control the frame rate (60 frames per second)
    clock.tick(60)