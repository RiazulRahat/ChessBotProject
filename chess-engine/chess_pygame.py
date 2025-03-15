# File: chess_pygame.py

import pygame
import chess
from chess_engine import ChessEngine

# Initialize pygame and set up display constants
pygame.init()

WIDTH, HEIGHT = 480, 480        # Board dimensions (8x8 board)
SQUARE_SIZE = WIDTH // 8
INPUT_BOX_HEIGHT = 50           # Space for move input
WINDOW_HEIGHT = HEIGHT + INPUT_BOX_HEIGHT

screen = pygame.display.set_mode((WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Chess Engine - Pygame Version")

# Define colors
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
INPUT_BOX_COLOR = (200, 200, 200)
TEXT_COLOR = (0, 0, 0)
ERROR_COLOR = (255, 0, 0)

# Set up fonts for text input and messages
font = pygame.font.SysFont("Arial", 32)
small_font = pygame.font.SysFont("Arial", 24)

# Create an instance of our chess engine
engine = ChessEngine()

# Load piece images from the assets folder
# Ensure the assets folder contains these images.
piece_images = {}
piece_images['P'] = pygame.image.load("assets/white_pawn.png")
piece_images['N'] = pygame.image.load("assets/white_knight.png")
piece_images['B'] = pygame.image.load("assets/white_bishop.png")
piece_images['R'] = pygame.image.load("assets/white_rook.png")
piece_images['Q'] = pygame.image.load("assets/white_queen.png")
piece_images['K'] = pygame.image.load("assets/white_king.png")
piece_images['p'] = pygame.image.load("assets/black_pawn.png")
piece_images['n'] = pygame.image.load("assets/black_knight.png")
piece_images['b'] = pygame.image.load("assets/black_bishop.png")
piece_images['r'] = pygame.image.load("assets/black_rook.png")
piece_images['q'] = pygame.image.load("assets/black_queen.png")
piece_images['k'] = pygame.image.load("assets/black_king.png")

# Scale all piece images to fit the square dimensions
for key in piece_images:
    piece_images[key] = pygame.transform.scale(piece_images[key], (SQUARE_SIZE, SQUARE_SIZE))

# Variables for user input and error messages
user_text = ""
error_message = ""

clock = pygame.time.Clock()
running = True

while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_BACKSPACE:
                user_text = user_text[:-1]
            elif event.key == pygame.K_RETURN:
                # Attempt to make the move using SAN notation
                valid, message = engine.make_move(user_text)
                if not valid:
                    error_message = message
                else:
                    error_message = ""
                user_text = ""
            else:
                user_text += event.unicode

    # Draw the chess board (8x8 grid with alternating colors)
    for row in range(8):
        for col in range(8):
            square_color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            pygame.draw.rect(screen, square_color, pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    # Draw the pieces using images based on the current board state
    board = engine.board
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            piece_symbol = piece.symbol()
            image = piece_images.get(piece_symbol)
            if image:
                # chess.square_rank returns 0 for rank 1, so we reverse to match pygame's top-down coordinates
                row = 7 - chess.square_rank(square)
                col = chess.square_file(square)
                screen.blit(image, (col * SQUARE_SIZE, row * SQUARE_SIZE))

    # Draw the input box area
    pygame.draw.rect(screen, INPUT_BOX_COLOR, pygame.Rect(0, HEIGHT, WIDTH, INPUT_BOX_HEIGHT))
    input_surface = small_font.render("Move (SAN): " + user_text, True, TEXT_COLOR)
    screen.blit(input_surface, (10, HEIGHT + 10))

    # Optionally display an error message if the move is invalid
    if error_message:
        error_surface = small_font.render(error_message, True, ERROR_COLOR)
        screen.blit(error_surface, (10, HEIGHT + 35))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
