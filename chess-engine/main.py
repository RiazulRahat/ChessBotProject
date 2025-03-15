from chess_engine import ChessEngine

def main():
    engine = ChessEngine()

    print("Welcome to the Chess Engine Terminal Game!")
    print("Enter your moves in SAN notation (e.g., e4, Nf3, O-O, etc.)")

    # Game Loop
    while not engine.is_game_over():
        # Display current state of Board
        print("\nCurrent Board: ")
        print(engine.display_board())

        user_move = input("Enter your move: ")
        valid, message = engine.make_move(user_move)

        if not valid:
            print("Error: " + message)
        else:
            print(message)

    print("\n Game is Over!")
    print("\n Final Board: ")
    print(engine.display_board())
    print("\n Results: ")
    print(engine.get_result())


if __name__ == "__main__":
    main()