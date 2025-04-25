import pygame, chess, statistics
from . import pygame_chess as pgc
from .chess_engine import ChessEngine
from bot.chess_bot import ChessBotAgent
from .pygame_chess import (WIDTH, HEIGHT, BOARD_DIMENSION, SQUARE_SIZE,
                           board_coord, load_images, get_square_rect, draw_piece,
                           highlight_square, highlight_move_circle,
                           draw_move_history, promotion_prompt_vertical,
                           get_game_over_message, show_game_over_prompt)

# globals shared with helper funcs
screen = clock = None
selected_square = None
legal_destinations = []
move_history     = []
game_history     = []   # [(fen_before_move, white_to_move)]

def init():
    global screen, clock
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Play vs. TD-Bot")
    clock  = pygame.time.Clock()
    pgc.screen = screen
    pgc.clock  = clock

def square_from_mouse(pos):
    for sq in board_coord:
        if get_square_rect(sq).collidepoint(pos):
            return sq
    return None

# ────────────────────────────────────────────────────────────────────────
def main():
    global selected_square, legal_destinations, move_history, game_history
    init()
    board_img, piece_images = load_images()
    pgc.piece_images = piece_images
    engine = ChessEngine()

    human_color = chess.WHITE
    bot   = ChessBotAgent(exploration_rate=0.0, learning_rate=0.0,
                          save_interval=50, table_path="bot/eval_table_zobrist.pkl", 
                          search_depth=3, positional_weight=0.8, mobility_weight=0.05,
                          use_quiescence=True, use_policy=True)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                  and engine.board.turn == human_color):
                pos = pygame.mouse.get_pos()
                clicked = square_from_mouse(pos)
                if not clicked:
                    continue
                if selected_square is None:
                    idx = chess.parse_square(clicked.lower())
                    piece = engine.board.piece_at(idx)
                    if piece and piece.color == human_color:
                        selected_square = clicked
                        legal_destinations = [
                            chess.square_name(m.to_square).upper()
                            for m in engine.board.legal_moves
                            if m.from_square == idx]
                else:
                    if clicked in legal_destinations:
                        _apply_move(engine, selected_square, clicked)
                    selected_square, legal_destinations = None, []

        # bot move
        if engine.board.turn != human_color and not engine.board.is_game_over():
            mv = mv = bot.choose_move_timed(engine.board, time_per_move=2.0)
            if mv:
                game_history.append((engine.board.fen(), engine.board.turn == chess.WHITE))
                move_history.append(engine.board.san(mv))
                engine.board.push(mv)

        # draw
        screen.fill("White")
        screen.blit(board_img, (25, 50))
        if selected_square:
            highlight_square(selected_square)
            for d in legal_destinations:
                highlight_move_circle(d)
        for sq in chess.SQUARES:
            p = engine.board.piece_at(sq)
            if p:
                draw_piece(piece_images[p.symbol()], chess.square_name(sq).upper())
        draw_move_history()
        pygame.display.update()
        clock.tick(60)

        # game over?
        if engine.board.is_game_over():
            bot.update_evaluation(game_history, engine.board.result())
            print("table size:", len(bot.evaluation_table),
                  "stdev:", statistics.pstdev(bot.evaluation_table.values()))
            result = get_game_over_message(engine.board)
            if show_game_over_prompt(result, screen.copy()) == "play_again":
                engine.board.reset()
                move_history.clear()
                game_history.clear()
            else:
                running = False
    pygame.quit()

def _apply_move(engine, frm, to):
    from_sq = chess.parse_square(frm.lower())
    to_sq   = chess.parse_square(to.lower())
    for mv in engine.board.legal_moves:
        if mv.from_square == from_sq and mv.to_square == to_sq:
            if (engine.board.piece_at(from_sq).piece_type == chess.PAWN and
                chess.square_rank(to_sq) in (0, 7)):
                mv = chess.Move(from_sq, to_sq,
                                promotion=promotion_prompt_vertical(
                                    engine.board.turn, board_coord[to], screen.copy()))
            game_history.append((engine.board.fen(), engine.board.turn == chess.WHITE))
            move_history.append(engine.board.san(mv))
            engine.board.push(mv)
            break

if __name__ == "__main__":
    main()
