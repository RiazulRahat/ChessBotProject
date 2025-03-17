import pygame
from sys import exit

pygame.init()   # Always call for pygame

WIDTH, HEIGHT = 550, 600
BOARD_DIMENSION = 500


screen = pygame.display.set_mode((WIDTH,HEIGHT)) # create display window
pygame.display.set_caption("Chess Game Window!")    # set window caption
clock = pygame.time.Clock() # creating a clock to control frame speed


# # Padding for chess board
# padding = pygame.Surface((525,525))
# padding.fill("White")

chess_board = pygame.image.load('assets/chess_board.jpeg')
chess_board = pygame.transform.scale(chess_board, (BOARD_DIMENSION,BOARD_DIMENSION))

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    screen.fill('White')
    screen.blit(chess_board,(25,50))
    # screen.blit(padding, (12.5,35))

    pygame.display.update() # refresh display window
    clock.tick(60)