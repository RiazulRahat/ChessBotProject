import chess

# ───---- global tuning constants ─────────────────────────────────────────
MOBILITY_MAX            = 30    # how many moves this is relevant for
MOBILITY_WEIGHT         = 0.05  # 0.05-0.1 - high mobility   0.05-0.02 - low mobility
BISHOP_PAIR_BONUS       = 0.30  # 0.4-0.5 - favor bishop pair  0.15-0.2 - less power to bishops
PASSED_PAWN_BONUS        = 0.20 # 0.3-0.4 - passed PAWNS   0.1-0.15 - careful pawn structure
SAFETY_MULTIPLIER       = 1.0   # 1.2–1.5 - avoids hanging pieces   0.5–0.8 - can offer pieces
KING_SHIELD_BONUS       = 0.25  # After castling pawn shield keeping rate
# ────────────────────────────────────────────────────────────────────────

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
            # mirror the index for Black so we pick the correct orientation
            idx = sq if p.color == chess.WHITE else chess.square_mirror(sq)
            val = table[idx] / 100.0
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
    penalty = 0.0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p:
            continue
        attackers = board.attackers(not p.color, sq)
        defenders = board.attackers(p.color, sq)
        if attackers and not defenders:
            penalty += p.piece_type * SAFETY_MULTIPLIER * (1 if p.color==chess.WHITE else -1)
        elif attackers and len(defenders) < len(attackers):
            penalty += ((len(attackers)-len(defenders)) * 0.1 * p.piece_type
                       ) * (1 if p.color==chess.WHITE else -1)
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



def passed_pawn_bonus(board: chess.Board) -> float:
    bonus = 0.0
    for color in (chess.WHITE, chess.BLACK):
        for sq in board.pieces(chess.PAWN, color):
            file = sq % 8
            rank = sq // 8
            # White: no black pawn on same file ahead
            ahead = range(rank+1, 8) if color==chess.WHITE else range(rank-1, -1, -1)
            if all(not board.piece_at(f*8 + file) 
                   or board.piece_at(f*8 + file).color==color
                   for f in ahead):
                bonus += PASSED_PAWN_BONUS * (1 if color==chess.WHITE else -1)
    return bonus

def bishop_pair_bonus(board: chess.Board) -> float:
    bonus = 0.0
    for color in (chess.WHITE, chess.BLACK):
        bishops = len(board.pieces(chess.BISHOP, color))
        if bishops >= 2:
            bonus += BISHOP_PAIR_BONUS * (1 if color==chess.WHITE else -1)
    return bonus

def positional_score(board: chess.Board) -> float:
    """
    Combined positional score in pawn units (White positive).
    """
    pst     = piece_square_bonus(board)
    pawnp   = pawn_structure_penalty(board)
    safety  = piece_safety_penalty(board)
    dev     = piece_development_bonus(board)
    kingpb  = king_safety_bonus(board)
    # new bonuses
    bp_bonus    = bishop_pair_bonus(board)
    pp_bonus    = passed_pawn_bonus(board)

    # normalized mobility
    # clamp and avoid list allocation
    moves = min(len(board.legal_moves), MOBILITY_MAX)
    mob   = (moves / MOBILITY_MAX) * MOBILITY_WEIGHT

    # pawn shield: award +0.25 for White, –0.25 for Black if king is castled and front pawn intact
    shield = 0.0
    for color, ksquare, pawn_sq in [
        (chess.WHITE, chess.G1, chess.F2),
        (chess.BLACK, chess.G8, chess.F7)
    ]:
        if board.king(color) == ksquare and board.piece_at(pawn_sq):
            shield += KING_SHIELD_BONUS * (1 if color == chess.WHITE else -1)

    return (
        pst
      - pawnp
      - safety
      + mob
      + 0.8 * kingpb
      + 0.5 * dev
      + bp_bonus
      + pp_bonus
      + shield
    )
