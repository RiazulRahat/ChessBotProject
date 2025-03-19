import pygame
from sys import exit
from utils import scale_and_resize

pygame.init()   # Always call for pygame

board_coord = {"A1":(73, 476), "A2":(73, 422), "A3":(73, 367), "A4":(73, 312), 
               "A5":(73, 257), "A6":(73, 204), "A7":(73, 148), "A8":(73, 94),
               "B1":(128, 476), "B2":(128, 422), "B3":(128, 367), "B4":(128, 312), 
               "B5":(128, 257), "B6":(128, 204), "B7":(128, 148), "B8":(128, 94),
               "C1":(183, 476), "C2":(183, 422), "C3":(183, 367), "C4":(183, 312), 
               "C5":(183, 257), "C6":(183, 204), "C7":(183, 148), "C8":(183, 94),
               "D1":(237, 476), "D2":(237, 422), "D3":(237, 367), "D4":(237, 312), 
               "D5":(237, 257), "D6":(237, 204), "D7":(237, 148), "D8":(237, 94),
               "E1":(292, 476), "E2":(292, 422), "E3":(292, 367), "E4":(292, 312), 
               "E5":(292, 257), "E6":(292, 204), "E7":(292, 148), "E8":(292, 94),
               "F1":(346, 476), "F2":(346, 422), "F3":(346, 367), "F4":(346, 312), 
               "F5":(346, 257), "F6":(346, 204), "F7":(348, 148), "F8":(346, 94),
               "G1":(401, 476), "G2":(401, 422), "G3":(401, 367), "G4":(401, 312), 
               "G5":(401, 257), "G6":(401, 204), "G7":(401, 148), "G8":(401, 94),
               "H1":(455, 476), "H2":(455, 422), "H3":(455, 367), "H4":(455, 312), 
               "H5":(455, 257), "H6":(455, 204), "H7":(455, 148), "H8":(455, 94)}

WIDTH, HEIGHT = 550, 600
BOARD_DIMENSION = 500
SQUARE_SIZE = int(((BOARD_DIMENSION / 1274) * 1110 ) / 8 )   # size of each square


screen = pygame.display.set_mode((WIDTH,HEIGHT)) # create display window
pygame.display.set_caption("Chess Game Window!")    # set window caption
clock = pygame.time.Clock() # creating a clock to control frame speed

# Load and scale the Chess Board
chess_board = pygame.image.load('assets/chess_board.png')
chess_board = pygame.transform.scale(chess_board, (BOARD_DIMENSION,BOARD_DIMENSION))

# Load and scale the pieces

### WHITE PIECES ###
white_pawn = pygame.image.load('assets/pawn_white.png')
white_pawn = scale_and_resize(white_pawn, (SQUARE_SIZE, SQUARE_SIZE))

white_rook = pygame.image.load('assets/rook_white.png')
white_rook = scale_and_resize(white_rook, (SQUARE_SIZE, SQUARE_SIZE))

white_knight = pygame.image.load('assets/knight_white.png')
white_knight = scale_and_resize(white_knight, (SQUARE_SIZE, SQUARE_SIZE))

white_bishop = pygame.image.load('assets/bishop_white.png')
white_bishop = scale_and_resize(white_bishop, (SQUARE_SIZE, SQUARE_SIZE))

white_queen = pygame.image.load('assets/queen_white.png')
white_queen = scale_and_resize(white_queen, (SQUARE_SIZE, SQUARE_SIZE))

white_king = pygame.image.load('assets/king_white.png')
white_king = scale_and_resize(white_king, (SQUARE_SIZE, SQUARE_SIZE))

### BLACK PIECES ###
black_pawn = pygame.image.load('assets/pawn_black.png')
black_pawn = scale_and_resize(black_pawn, (SQUARE_SIZE, SQUARE_SIZE))

black_rook = pygame.image.load('assets/rook_black.png')
black_rook = scale_and_resize(black_rook, (SQUARE_SIZE, SQUARE_SIZE))

black_knight = pygame.image.load('assets/knight_black.png')
black_knight = scale_and_resize(black_knight, (SQUARE_SIZE, SQUARE_SIZE))

black_bishop = pygame.image.load('assets/bishop_black.png')
black_bishop = scale_and_resize(black_bishop, (SQUARE_SIZE, SQUARE_SIZE))

black_queen = pygame.image.load('assets/queen_black.png')
black_queen = scale_and_resize(black_queen, (SQUARE_SIZE, SQUARE_SIZE))

black_king = pygame.image.load('assets/king_black.png')
black_king = scale_and_resize(black_king, (SQUARE_SIZE, SQUARE_SIZE))


running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    screen.fill('White')
    screen.blit(chess_board,(25,50))

    ### PRINT WHITE PIECES
    screen.blit(white_rook, board_coord["A1"])
    screen.blit(white_knight, board_coord["B1"])
    screen.blit(white_bishop, board_coord["C1"])
    screen.blit(white_queen, board_coord["D1"])
    screen.blit(white_king, board_coord["E1"])
    screen.blit(white_bishop, board_coord["F1"])
    screen.blit(white_knight, board_coord["G1"])
    screen.blit(white_rook, board_coord["H1"])

    screen.blit(white_pawn, board_coord["A2"])
    screen.blit(white_pawn, board_coord["B2"])
    screen.blit(white_pawn, board_coord["C2"])
    screen.blit(white_pawn, board_coord["D2"])
    screen.blit(white_pawn, board_coord["E2"])
    screen.blit(white_pawn, board_coord["F2"])
    screen.blit(white_pawn, board_coord["G2"])
    screen.blit(white_pawn, board_coord["H2"])

    ### PRINT BLACK PIECES
    screen.blit(black_rook, board_coord["A8"])
    screen.blit(black_knight, board_coord["B8"])
    screen.blit(black_bishop, board_coord["C8"])
    screen.blit(black_queen, board_coord["D8"])
    screen.blit(black_king, board_coord["E8"])
    screen.blit(black_bishop, board_coord["F8"])
    screen.blit(black_knight, board_coord["G8"])
    screen.blit(black_rook, board_coord["H8"])

    screen.blit(black_pawn, board_coord["A7"])
    screen.blit(black_pawn, board_coord["B7"])
    screen.blit(black_pawn, board_coord["C7"])
    screen.blit(black_pawn, board_coord["D7"])
    screen.blit(black_pawn, board_coord["E7"])
    screen.blit(black_pawn, board_coord["F7"])
    screen.blit(black_pawn, board_coord["G7"])
    screen.blit(black_pawn, board_coord["H7"])

    pygame.display.update() # refresh display window
    clock.tick(60)