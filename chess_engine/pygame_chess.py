import pygame
from sys import exit
import chess
from .chess_engine import ChessEngine
from .utils import scale_and_resize
from bot.chess_bot import ChessBotAgent

# =============================================================================
# Global Configuration & Initialization
# =============================================================================

# Global variables that will be initialized in main()
screen = None
clock = None

# Window and Board Settings
WIDTH, HEIGHT = 800, 600                # Window Dimensions
BOARD_DIMENSION = 500                   # Chess board display area in pixels
SQUARE_SIZE = int(((BOARD_DIMENSION / 1274) * 1110) / 8)  # Size of each square

# -----------------------------------------------------------------
# Board Coordinates Mapping (for piece placement using midbottom)
# -----------------------------------------------------------------
board_coord = {
    "A1": (83, 508), "A2": (83, 455), "A3": (83, 400), "A4": (83, 345),
    "A5": (83, 290), "A6": (83, 237), "A7": (83, 181), "A8": (83, 127),
    "B1": (138, 508), "B2": (138, 455), "B3": (138, 400), "B4": (138, 345),
    "B5": (138, 290), "B6": (138, 237), "B7": (138, 181), "B8": (138, 127),
    "C1": (193, 508), "C2": (193, 455), "C3": (193, 400), "C4": (193, 345),
    "C5": (193, 290), "C6": (193, 237), "C7": (193, 181), "C8": (193, 127),
    "D1": (247, 506), "D2": (247, 455), "D3": (247, 400), "D4": (247, 345),
    "D5": (247, 290), "D6": (247, 237), "D7": (247, 181), "D8": (247, 127),
    "E1": (302, 506), "E2": (302, 455), "E3": (302, 400), "E4": (302, 345),
    "E5": (302, 290), "E6": (302, 237), "E7": (302, 181), "E8": (302, 127),
    "F1": (356, 508), "F2": (356, 455), "F3": (356, 400), "F4": (356, 345),
    "F5": (356, 290), "F6": (356, 237), "F7": (356, 181), "F8": (356, 127),
    "G1": (411, 508), "G2": (411, 455), "G3": (411, 400), "G4": (411, 345),
    "G5": (411, 290), "G6": (411, 237), "G7": (411, 181), "G8": (411, 127),
    "H1": (465, 508), "H2": (465, 455), "H3": (465, 400), "H4": (465, 345),
    "H5": (465, 290), "H6": (465, 237), "H7": (465, 181), "H8": (465, 127)
}

# Global variables for movement and logging
selected_square = None   # Currently selected square label (e.g., "A1")
legal_destinations = []  # List of available destination square labels
move_history = []        # List of moves in SAN notation

# =============================================================================
# Initialization Functions
# =============================================================================

def init_pygame():
    """Initializes Pygame and returns the screen and clock objects."""
    pygame.init()
    s = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Chess Game Window!")
    c = pygame.time.Clock()
    return s, c

def load_images():
    """
    Loads and scales the chess board and piece images.
    Returns a tuple: (chess_board, piece_images)
    """
    # Load and scale board image
    board_img = pygame.image.load('assets/chess_board.png')
    board_img = pygame.transform.scale(board_img, (BOARD_DIMENSION, BOARD_DIMENSION))
    
    # Load and scale piece images; stored in a dictionary mapping piece symbols
    piece_imgs = {
        "P": scale_and_resize(pygame.image.load('assets/pawn_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "R": scale_and_resize(pygame.image.load('assets/rook_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "N": scale_and_resize(pygame.image.load('assets/knight_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "B": scale_and_resize(pygame.image.load('assets/bishop_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "Q": scale_and_resize(pygame.image.load('assets/queen_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "K": scale_and_resize(pygame.image.load('assets/king_white.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "p": scale_and_resize(pygame.image.load('assets/pawn_black.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "r": scale_and_resize(pygame.image.load('assets/rook_black.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "n": scale_and_resize(pygame.image.load('assets/knight_black.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "b": scale_and_resize(pygame.image.load('assets/bishop_black.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "q": scale_and_resize(pygame.image.load('assets/queen_black.png'), (SQUARE_SIZE, SQUARE_SIZE)),
        "k": scale_and_resize(pygame.image.load('assets/king_black.png'), (SQUARE_SIZE, SQUARE_SIZE))
    }
    return board_img, piece_imgs

# =============================================================================
# Drawing Functions
# =============================================================================

def get_square_rect(square_label):
    """
    Given a square label (e.g., "E1"), returns a pygame.Rect for that square.
    Uses board_coord (midbottom positions) and adjusts to calculate the top-left corner.
    """
    midbottom = board_coord[square_label]
    x = midbottom[0] - SQUARE_SIZE // 2
    y = (midbottom[1] + 10) - SQUARE_SIZE  # Add back the offset for piece centering
    return pygame.Rect(x, y, SQUARE_SIZE, SQUARE_SIZE)

def draw_piece(piece_image, square_label):
    """
    Draws a piece on the board with its midbottom aligned to the coordinate from board_coord.
    """
    target_coord = board_coord[square_label]
    piece_rect = piece_image.get_rect(midbottom=target_coord)
    screen.blit(piece_image, piece_rect)

def highlight_square(square_label, color=(255, 255, 0, 150)):
    """
    Highlights a square by drawing a semi-transparent rectangle.
    """
    overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
    overlay.fill(color)
    rect = get_square_rect(square_label)
    screen.blit(overlay, rect.topleft)

def highlight_move_circle(square_label, color=(128, 128, 128)):
    """
    Draws a grey circle in the center of a square to indicate an available move.
    """
    rect = get_square_rect(square_label)
    center = rect.center
    radius = SQUARE_SIZE // 6
    pygame.draw.circle(screen, color, center, radius)

def draw_move_history():
    """
    Draws the move history panel on the right side of the window.
    Displays a header and lists moves for White and Black in two columns.
    """
    history_rect = pygame.Rect(525, 50, 250, 500)
    pygame.draw.rect(screen, (230, 230, 230), history_rect)
    pygame.draw.rect(screen, (0, 0, 0), history_rect, 2)
    
    font_history = pygame.font.SysFont(None, 24)
    header = font_history.render("Move History", True, (0, 0, 0))
    screen.blit(header, (history_rect.x + 10, history_rect.y + 10))
    
    white_header = font_history.render("White", True, (0, 0, 0))
    black_header = font_history.render("Black", True, (0, 0, 0))
    screen.blit(white_header, (history_rect.x + 10, history_rect.y + 40))
    screen.blit(black_header, (history_rect.x + history_rect.width // 2 + 10, history_rect.y + 40))
    
    y_offset = history_rect.y + 70
    row_height = 24
    total_moves = len(move_history)
    for i in range(0, total_moves, 2):
        row_number = i // 2 + 1
        row_text = font_history.render(f"{row_number}.", True, (0, 0, 0))
        screen.blit(row_text, (history_rect.x + 10, y_offset))
        white_move = move_history[i]
        white_text = font_history.render(white_move, True, (0, 0, 0))
        screen.blit(white_text, (history_rect.x + 40, y_offset))
        black_move = move_history[i+1] if i+1 < total_moves else ""
        black_text = font_history.render(black_move, True, (0, 0, 0))
        screen.blit(black_text, (history_rect.x + history_rect.width // 2 + 10, y_offset))
        y_offset += row_height

# =============================================================================
# Event & Interaction Functions
# =============================================================================

def square_from_mouse(pos):
    """
    Returns the square label corresponding to the given mouse position, or None if not on any square.
    """
    for square in board_coord:
        rect = get_square_rect(square)
        if rect.collidepoint(pos):
            return square
    return None

def promotion_prompt_vertical(color, target_coord, background_surf):
    """
    Displays a vertical promotion prompt near the promotion square.
    Returns the chosen promotion piece type.
    Parameters:
      color: chess.WHITE or chess.BLACK.
      target_coord: Pixel coordinate (from board_coord) near the promotion square.
      background_surf: A copy of the current screen to use as the background.
    """
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
    option_size = SQUARE_SIZE
    gap = 5
    offset_x = 10
    offset_y = -2 * SQUARE_SIZE
    start_x = target_coord[0] + offset_x
    start_y = target_coord[1] + offset_y

    option_rects = []
    for i, _ in enumerate(options):
        rect = pygame.Rect(start_x, start_y + i * (option_size + gap), option_size, option_size)
        option_rects.append(rect)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                for i, (piece_symbol, _) in enumerate(options):
                    if option_rects[i].collidepoint(mx, my):
                        if piece_symbol.upper() == "Q":
                            return chess.QUEEN
                        elif piece_symbol.upper() == "R":
                            return chess.ROOK
                        elif piece_symbol.upper() == "B":
                            return chess.BISHOP
                        elif piece_symbol.upper() == "N":
                            return chess.KNIGHT

        # Draw the promotion prompt overlay (board remains visible in background)
        screen.blit(background_surf, (0, 0))
        for rect in option_rects:
            small_overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            small_overlay.fill((0, 0, 0, 120))
            screen.blit(small_overlay, rect.topleft)
        for (piece_symbol, image), rect in zip(options, option_rects):
            pygame.draw.rect(screen, (255, 255, 255), rect, 2)
            image_rect = image.get_rect(center=rect.center)
            screen.blit(image, image_rect)
        pygame.display.update()
        clock.tick(30)

def get_game_over_message(board):
    """
    Returns a string describing the game result if game over.
    """
    if not board.is_game_over():
        return None
    if board.is_checkmate():
        return "Black Wins by Checkmate!" if board.turn == chess.WHITE else "White Wins by Checkmate!"
    if board.is_stalemate():
        return "Draw by Stalemate!"
    if board.is_insufficient_material():
        return "Draw by Insufficient Material!"
    if board.is_seventyfive_moves():
        return "Draw by 75-Move Rule!"
    if board.is_fivefold_repetition():
        return "Draw by Fivefold Repetition!"
    return "Game is a Draw!"

def show_game_over_prompt(result_text, background_surf):
    """
    Displays a Game Over prompt with the given result text along with "Play Again" and "Exit" buttons.
    Returns the user's choice.
    """
    font_title = pygame.font.SysFont(None, 48)
    font_button = pygame.font.SysFont(None, 32)
    text_surface = font_title.render(result_text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    play_again_surface = font_button.render("Play Again", True, (255, 255, 255))
    exit_surface = font_button.render("Exit", True, (255, 255, 255))
    button_padding = (20, 10)
    play_again_rect = play_again_surface.get_rect()
    exit_rect = exit_surface.get_rect()
    spacing = 20
    play_again_rect.center = (WIDTH // 2, HEIGHT // 2 + 10)
    exit_rect.center = (WIDTH // 2, play_again_rect.bottom + exit_rect.height // 2 + spacing)
    play_again_rect.inflate_ip(*button_padding)
    exit_rect.inflate_ip(*button_padding)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "exit"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                if play_again_rect.collidepoint(mx, my):
                    return "play_again"
                if exit_rect.collidepoint(mx, my):
                    return "exit"
        screen.blit(background_surf, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        screen.blit(text_surface, text_rect)
        pygame.draw.rect(screen, (150, 150, 150), play_again_rect)
        pygame.draw.rect(screen, (255, 255, 255), play_again_rect, 2)
        screen.blit(play_again_surface, play_again_surface.get_rect(center=play_again_rect.center))
        pygame.draw.rect(screen, (150, 150, 150), exit_rect)
        pygame.draw.rect(screen, (255, 255, 255), exit_rect, 2)
        screen.blit(exit_surface, exit_surface.get_rect(center=exit_rect.center))
        pygame.display.update()
        clock.tick(30)

# =============================================================================
# Main Game Loop
# =============================================================================

def main():
    global screen, clock, selected_square, legal_destinations, background_surf, piece_images, move_history

    screen, clock = init_pygame()
    chess_board, piece_imgs = load_images()
    piece_images = piece_imgs  # assign to global variable

    engine = ChessEngine()

    # Initialize chess bot (as Black for self play)
    chess_bot = ChessBotAgent(exploration_rate=0.1)
    
    running = True
    while running:
        # -----------------
        # Event Handling
        # -----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                clicked_square = square_from_mouse(pos)
                if clicked_square:
                    if selected_square is None:
                        # Select a piece if it belongs to the side to move
                        sq_index = chess.parse_square(clicked_square.lower())
                        piece = engine.board.piece_at(sq_index)
                        if piece and piece.color == engine.board.turn:
                            selected_square = clicked_square
                            legal_destinations = []
                            for move in engine.board.legal_moves:
                                if move.from_square == sq_index:
                                    dest_label = chess.square_name(move.to_square).upper()
                                    legal_destinations.append(dest_label)
                    else:
                        if clicked_square in legal_destinations:
                            from_sq = chess.parse_square(selected_square.lower())
                            to_sq = chess.parse_square(clicked_square.lower())
                            move_found = None
                            for move in engine.board.legal_moves:
                                if move.from_square == from_sq and move.to_square == to_sq:
                                    move_found = move
                                    break
                            if move_found:
                                piece = engine.board.piece_at(from_sq)
                                # Handle pawn promotion
                                if piece and piece.piece_type == chess.PAWN and (chess.square_rank(to_sq) in [0, 7]):
                                    background_surf = screen.copy()
                                    promotion_piece = promotion_prompt_vertical(piece.color, board_coord[chess.square_name(to_sq).upper()], background_surf)
                                    move_found = chess.Move(from_sq, to_sq, promotion=promotion_piece)
                                # Record move and update board
                                san_move = engine.board.san(move_found)
                                engine.board.push(move_found)
                                move_history.append(san_move)
                                
                                pygame.display.update()
                                #pygame.time.wait(500)
                                
                                # Check for game over
                                if engine.board.is_game_over():
                                    result_text = get_game_over_message(engine.board)
                                    if result_text:
                                        background_surf = screen.copy()
                                        choice = show_game_over_prompt(result_text, background_surf)
                                        if choice == "play_again":
                                            engine.board.reset()
                                            selected_square = None
                                            legal_destinations = []
                                            move_history.clear()
                                            continue
                                        elif choice == "exit":
                                            running = False
                                            break
                        selected_square = None
                        legal_destinations = []
        
        # -----------------
        # Drawing Section
        # -----------------
        screen.fill('White')
        screen.blit(chess_board, (25, 50))
        
        if selected_square:
            highlight_square(selected_square, color=(255, 255, 0, 150))
            for dest in legal_destinations:
                highlight_move_circle(dest, color=(128, 128, 128))
        
        for square in chess.SQUARES:
            piece = engine.board.piece_at(square)
            if piece:
                square_label = chess.square_name(square).upper()
                img = piece_images.get(piece.symbol())
                if img:
                    draw_piece(img, square_label)
        
        draw_move_history()
        
        pygame.display.update()
        clock.tick(60)

if __name__ == "__main__":
    main()
