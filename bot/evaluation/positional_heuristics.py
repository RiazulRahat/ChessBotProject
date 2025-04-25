import chess

# Piece-Square Tables (in centipawns)
# Tables represent values for White; for Black, values are negated automatically.

PAWN_TABLE = [
     0,   0,   0,   0,   0,   0,   0,   0,
    50,  50,  50,  50,  50,  50,  50,  50,
    10,  10,  20,  30,  30,  20,  10,  10,
     5,   5,  10,  25,  25,  10,   5,   5,
     0,   0,   0,  20,  20,   0,   0,   0,
     5,  -5, -10,   0,   0, -10,  -5,   5,
     5,  10,  10, -20, -20,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0,
]

KNIGHT_TABLE = [
   -50, -40, -30, -30, -30, -30, -40, -50,
   -40, -20,   0,   0,   0,   0, -20, -40,
   -30,   0,  10,  15,  15,  10,   0, -30,
   -30,   5,  15,  20,  20,  15,   5, -30,
   -30,   0,  15,  20,  20,  15,   0, -30,
   -30,   5,  10,  15,  15,  10,   5, -30,
   -40, -20,   0,   5,   5,   0, -20, -40,
   -50, -40, -30, -30, -30, -30, -40, -50,
]

BISHOP_TABLE = [
   -20, -10, -10, -10, -10, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,  10,  10,   5,   0, -10,
   -10,   5,   5,  10,  10,   5,   5, -10,
   -10,   0,  10,  10,  10,  10,   0, -10,
   -10,  10,  10,  10,  10,  10,  10, -10,
   -10,   5,   0,   0,   0,   0,   5, -10,
   -20, -10, -10, -10, -10, -10, -10, -20,
]

ROOK_TABLE = [
     0,   0,   5,  10,  10,   5,   0,   0,
     0,   0,   5,  10,  10,   5,   0,   0,
     0,   0,   5,  10,  10,   5,   0,   0,
     0,   0,   5,  10,  10,   5,   0,   0,
     0,   0,   5,  10,  10,   5,   0,   0,
     0,   0,   5,  10,  10,   5,   0,   0,
    25,  25,  25,  25,  25,  25,  25,  25,
     0,   0,   5,  10,  10,   5,   0,   0,
]

QUEEN_TABLE = [
   -20, -10, -10,  -5,  -5, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,   5,   5,   5,   0, -10,
    -5,   0,   5,   5,   5,   5,   0,  -5,
     0,   0,   5,   5,   5,   5,   0,  -5,
   -10,   5,   5,   5,   5,   5,   0, -10,
   -10,   0,   5,   0,   0,   0,   0, -10,
   -20, -10, -10,  -5,  -5, -10, -10, -20,
]

KING_MID_TABLE = [
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -20, -30, -30, -40, -40, -30, -30, -20,
   -10, -20, -20, -20, -20, -20, -20, -10,
    20,  20,   0,   0,   0,   0,  20,  20,
    20,  30,  10,   0,   0,  10,  30,  20,
]

KING_END_TABLE = [
   -50, -40, -30, -20, -20, -30, -40, -50,
   -30, -20, -10,   0,   0, -10, -20, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -30,   0,   0,   0,   0, -30, -30,
   -50, -30, -30, -30, -30, -30, -30, -50,
]


def piece_square_bonus(board: chess.Board) -> float:
    """
    Compute total piece-square table bonus from White's perspective.
    Positive → White is better; Negative → Black is better.
    """
    score = 0.0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p:
            continue
        table = None
        pt    = p.piece_type
        if   pt == chess.PAWN:   table = PAWN_TABLE
        elif pt == chess.KNIGHT: table = KNIGHT_TABLE
        elif pt == chess.BISHOP: table = BISHOP_TABLE
        elif pt == chess.ROOK:   table = ROOK_TABLE
        elif pt == chess.QUEEN:  table = QUEEN_TABLE
        elif pt == chess.KING:
            # choose midgame vs endgame based on material
            total_material = sum(
                len(board.pieces(t, chess.WHITE)) + len(board.pieces(t, chess.BLACK))
                for t in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
            )
            table = KING_END_TABLE if total_material < 14 else KING_MID_TABLE

        if table:
            val = table[sq] / 100.0  # convert centipawns to pawn units
            score += val if p.color == chess.WHITE else -val
    return score


def pawn_structure_penalty(board: chess.Board) -> float:
    """
    Simple pawn structure penalties for doubled and isolated pawns.
    Positive → White bad structure; Negative → Black bad structure.
    """
    penalty = 0.0
    for color in (chess.WHITE, chess.BLACK):
        pawns = list(board.pieces(chess.PAWN, color))
        files = [sq % 8 for sq in pawns]
        for f in set(files):
            count = files.count(f)
            if count > 1:
                # penalty per extra pawn on same file
                penalty += (count - 1) * 0.1 * (1 if color == chess.WHITE else -1)
        for sq in pawns:
            f = sq % 8
            # isolated if no adjacent file pawns
            if all(a not in files for a in (f-1, f+1) if 0 <= a < 8):
                penalty += 0.1 * (1 if color == chess.WHITE else -1)
    return penalty

def piece_safety_penalty(board: chess.Board) -> float:
    """
    Penalize any undefended piece that is attacked.
    Returns positive value (bad for White if undefended White piece).
    """
    penalty = 0.0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p:
            continue
        # count attackers vs defenders
        attackers = board.attackers(not p.color, sq)
        if attackers:
            defenders = board.attackers(p.color, sq)
            # if no defenders, heavier penalty; if fewer defenders than attackers, smaller
            if not defenders:
                penalty += (p.piece_type * 0.5) * (1 if p.color == chess.WHITE else -1)
            elif len(defenders) < len(attackers):
                penalty += ((len(attackers) - len(defenders)) * 0.1 * p.piece_type) * (1 if p.color == chess.WHITE else -1)
    return penalty

def king_safety_bonus(board: chess.Board) -> float:
    """
    Positive bonus when a side has castled, 
    negative penalty if the king has moved early (before move 10) 
    or remains in the center too long.
    """
    bonus = 0.0
    for color, start_sq, castled_sqs in [
        (chess.WHITE, chess.E1, {chess.G1, chess.C1}),
        (chess.BLACK, chess.E8, {chess.G8, chess.C8})
    ]:
        king_sq = board.king(color)
        # if castled (king on g-file or c-file)
        if king_sq in castled_sqs:
            bonus += 0.5 if color == chess.WHITE else -0.5
        else:
            # penalty if king moved off start before move 10
            if board.fullmove_number <= 10 and king_sq != start_sq:
                bonus -= 0.3 if color == chess.WHITE else -0.3
            # small penalty for staying in center midgame
            if board.fullmove_number > 10 and king_sq in [chess.D4, chess.D5, chess.E4, chess.E5]:
                bonus -= 0.2 if color == chess.WHITE else -0.2
    return bonus

def piece_development_bonus(board: chess.Board) -> float:
    """
    Rewards minor pieces (knights/bishops) that have left their 
    original back-rank squares (b1, g1 / b8, g8).
    """
    dev = 0.0
    for color, starting in [
        (chess.WHITE, {chess.B1, chess.G1, chess.C1, chess.F1}),
        (chess.BLACK, {chess.B8, chess.G8, chess.C8, chess.F8})
    ]:
        for pt in (chess.KNIGHT, chess.BISHOP):
            for sq in board.pieces(pt, color):
                if sq not in starting:
                    dev += 0.1 if color == chess.WHITE else -0.1
    return dev



def positional_score(board: chess.Board, mobility_weight: float = 0.05) -> float:
    """
    Combined positional score:
      - piece-square bonuses
      - pawn-structure penalties
      - mobility bonus
    Returns a score in pawn units (White positive).
    """
    pst = piece_square_bonus(board)
    pawnp = pawn_structure_penalty(board)
    safetyp = piece_safety_penalty(board) * 5.0
    mob = len(list(board.legal_moves)) * mobility_weight
    kingpb = king_safety_bonus(board)
    devpb  = piece_development_bonus(board)
    return pst - pawnp - safetyp + mob + 0.8*kingpb + 0.5*devpb