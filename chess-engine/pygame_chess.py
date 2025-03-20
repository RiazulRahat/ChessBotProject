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
    y = (midbottom[1] + 10) - SQUARE_SIZE
    return pygame.Rect(x, y, SQUARE_SIZE, SQUARE_SIZE)

def highlight_square(square_label, color = (128, 128, 128)):
    """
    Highlights the given square by drawing a semi-transparent rectangle over it.
    """
    # Create a surface with per-pixel alpha for transparency
    highlight = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
    highlight.fill(color)
    rect = get_square_rect(square_label)
    screen.blit(highlight, rect.topleft)

def highlight_move_circle(square_label, color=(128, 128, 128)):
    """
    Draws a grey circle to indicate an available move on the given square.
    
    Parameters:
      square_label (str): The square to highlight (e.g., "E4").
      color (tuple): The RGB color for the circle. Default is grey.
    """
    rect = get_square_rect(square_label)
    # Calculate the center of the square
    center = rect.center
    # Choose a radius that's a fraction of the square size
    radius = SQUARE_SIZE // 6
    pygame.draw.circle(screen, color, center, radius)

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

def promotion_prompt_vertical(color, target_coord):
    """
    Displays a vertical promotion prompt near the pawn's promotion square.
    Returns the chosen promotion piece type (chess.QUEEN, chess.ROOK, etc.).
    
    Parameters:
      color (bool): True for white, False for black.
      target_coord (tuple): The pixel coordinate (x, y) near which the prompt should appear.
      
    Returns:
      int: The promotion piece type from chess (e.g., chess.QUEEN, chess.ROOK, etc.)
    """
    # Define which piece symbols to show for white vs black
    if color == chess.WHITE:
        options = [
            ("Q", piece_images["Q"]),
            ("R", piece_images["R"]),
            ("B", piece_images["B"]),
            ("N", piece_images["N"])
        ]
    else:
        options = [
            ("q", piece_images["q"]),
            ("r", piece_images["r"]),
            ("b", piece_images["b"]),
            ("n", piece_images["n"])
        ]

    # Each option will have the same box size as SQUARE_SIZE (or you can choose smaller).
    option_size = SQUARE_SIZE
    gap = 5  # Gap between each option box

    # Let's place the prompt so its top-left corner is slightly to the right of the target square.
    # For instance, place the first option 10 pixels to the right, and 2 squares above the target_coord.
    # Adjust these offsets to your liking.
    offset_x = 10
    offset_y = -2 * SQUARE_SIZE

    # The top-left of the first option box:
    start_x = target_coord[0] + offset_x
    start_y = target_coord[1] + offset_y

    # Precompute rectangles for each option
    option_rects = []
    for i, (piece_symbol, image) in enumerate(options):
        rect_x = start_x
        rect_y = start_y + i * (option_size + gap)
        option_rects.append(pygame.Rect(rect_x, rect_y, option_size, option_size))


    # We'll run a mini-loop to let the user click one of the promotion options.
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                # Check each option's bounding box
                for i, (piece_symbol, image) in enumerate(options):
                    rect_x = start_x
                    rect_y = start_y + i * (option_size + gap)
                    rect = pygame.Rect(rect_x, rect_y, option_size, option_size)
                    if rect.collidepoint(mx, my):
                        # Return the corresponding promotion piece type.
                        if piece_symbol.upper() == "Q":
                            return chess.QUEEN
                        elif piece_symbol.upper() == "R":
                            return chess.ROOK
                        elif piece_symbol.upper() == "B":
                            return chess.BISHOP
                        elif piece_symbol.upper() == "N":
                            return chess.KNIGHT

        # --- Drawing Section ---
        # 1. Restore the background so the board remains visible
        screen.blit(background_surf, (0, 0))

        # 2. Optionally, draw a small semi-transparent overlay behind just the options
        #    (instead of the whole screen).
        for rect in option_rects:
            small_overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            small_overlay.fill((0, 0, 0, 120))  # 120 alpha for partial transparency
            screen.blit(small_overlay, rect.topleft)

        # 3. Draw each option box and piece image
        for (piece_symbol, image), rect in zip(options, option_rects):
            # Draw a border for clarity
            pygame.draw.rect(screen, (255, 255, 255), rect, 2)

            # Center the piece image in the box
            image_rect = image.get_rect(center=rect.center)
            screen.blit(image, image_rect)

        pygame.display.update()
        clock.tick(30)

def get_game_over_message(board):
    """
    Returns a string describing the game result if the board is in a game-over state.
    Possible outcomes: checkmate, stalemate, insufficient material, etc.
    """
    if not board.is_game_over():
        return None  # The game isn't actually over yet

    # Check for checkmate
    if board.is_checkmate():
        # If it's checkmate, the side that just moved delivered the mate.
        # 'board.turn' indicates who moves next, so the side that delivered mate is the opposite.
        if board.turn == chess.WHITE:
            return "Black Wins by Checkmate!"
        else:
            return "White Wins by Checkmate!"

    # Other draw conditions
    if board.is_stalemate():
        return "Draw by Stalemate!"
    if board.is_insufficient_material():
        return "Draw by Insufficient Material!"
    if board.is_seventyfive_moves():
        return "Draw by 75-Move Rule!"
    if board.is_fivefold_repetition():
        return "Draw by Fivefold Repetition!"

    # If we reach here, it's probably a 50-move rule or threefold repetition recognized as game_over
    return "Game is a Draw!"

def show_game_over_prompt(result_text, background_surf):
    """
    Displays a Game Over prompt with the given result_text (e.g., "White Wins by Checkmate!")
    on top of the current board (background_surf), along with "Play Again" and "Exit" buttons.
    
    Returns:
      str: "play_again" if user chooses to play again, "exit" if user chooses to exit.
    """
    # Choose a font
    font_title = pygame.font.SysFont(None, 48)
    font_button = pygame.font.SysFont(None, 32)

    # Render the result text
    text_surface = font_title.render(result_text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))

    # Define button labels
    play_again_surface = font_button.render("Play Again", True, (255, 255, 255))
    exit_surface = font_button.render("Exit", True, (255, 255, 255))

    # Create button rectangles
    # The button width is based on the text width plus some padding.
    button_padding_x = 20
    button_padding_y = 10

    play_again_rect = play_again_surface.get_rect()
    exit_rect = exit_surface.get_rect()

    # Position the buttons (for example, below the result text)
    spacing = 20
    play_again_rect.center = (WIDTH // 2, HEIGHT // 2 + 10)
    exit_rect.center = (WIDTH // 2, play_again_rect.bottom + exit_rect.height // 2 + spacing)

    # Expand the rect to allow some padding around the text
    play_again_rect.inflate_ip(button_padding_x, button_padding_y)
    exit_rect.inflate_ip(button_padding_x, button_padding_y)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "exit"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                # Check if user clicked one of the buttons
                if play_again_rect.collidepoint(mx, my):
                    return "play_again"
                if exit_rect.collidepoint(mx, my):
                    return "exit"

        # Draw the background so the board is visible behind the text
        screen.blit(background_surf, (0, 0))

        # Draw a semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Draw the result text
        screen.blit(text_surface, text_rect)

        # Draw the buttons (background + text)
        # Play Again Button
        pygame.draw.rect(screen, (150, 150, 150), play_again_rect)  # grey background
        pygame.draw.rect(screen, (255, 255, 255), play_again_rect, 2)  # white border
        text_rect_pa = play_again_surface.get_rect(center=play_again_rect.center)
        screen.blit(play_again_surface, text_rect_pa)

        # Exit Button
        pygame.draw.rect(screen, (150, 150, 150), exit_rect)  # grey background
        pygame.draw.rect(screen, (255, 255, 255), exit_rect, 2)  # white border
        text_rect_exit = exit_surface.get_rect(center=exit_rect.center)
        screen.blit(exit_surface, text_rect_exit)

        pygame.display.update()
        clock.tick(30)


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
                        from_sq = chess.parse_square(selected_square.lower())
                        to_sq = chess.parse_square(clicked_square.lower())
                        move_found = None
                        for move in engine.board.legal_moves:
                            if move.from_square == from_sq and move.to_square == to_sq:
                                move_found = move
                                break
                        if move_found:
                            # Check if this move is a pawn promotion
                            piece = engine.board.piece_at(from_sq)
                            if piece and piece.piece_type == chess.PAWN and (chess.square_rank(to_sq) in [0, 7]):
                                # The coordinate for the promotion square can be found from board_coord:
                                # This is the midbottom coordinate for the to_sq label, so just do:
                                to_sq_label = chess.square_name(to_sq).upper()
                                target_coord = board_coord[to_sq_label]

                                # Capture the current screen as background
                                background_surf = screen.copy()
                            
                                # Show the vertical prompt near the promotion square
                                promotion_piece = promotion_prompt_vertical(piece.color, target_coord)
                                move_found = chess.Move(from_sq, to_sq, promotion=promotion_piece)
                            engine.board.push(move_found)

                            # After detecting game over:
                            if engine.board.is_game_over():
                                result_text = get_game_over_message(engine.board)
                                if result_text:
                                    background_surf = screen.copy()
                                    choice = show_game_over_prompt(result_text, background_surf)

                                    if choice == "play_again":
                                        # Reset the board
                                        engine.board.reset()
                                        selected_square = None
                                        legal_destinations = []
                                        # Continue the main loop with a fresh game
                                        continue
                                    elif choice == "exit":
                                        running = False
                                        break
                    # Clear selection whether move was legal or not.
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
            highlight_move_circle(dest, color=(128, 128, 128))  # Grey for legal moves

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