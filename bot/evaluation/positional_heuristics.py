# positional_heuristics.py

import chess

# ========== Global Tuning Constants ====================================
MOBILITY_MAX            = 30    # how many moves this is relevant for
MOBILITY_WEIGHT         = 0.05  # 0.05-0.1 - high mobility   0.05-0.02 - low mobility
BISHOP_PAIR_BONUS       = 0.30  # 0.4-0.5 - favor bishop pair  0.15-0.2 - less power to bishops
PASSED_PAWN_BONUS        = 0.20 # 0.3-0.4 - passed PAWNS   0.1-0.15 - careful pawn structure
SAFETY_MULTIPLIER       = 1.0   # 1.2–1.5 - avoids hanging pieces   0.5–0.8 - can offer pieces
KING_SHIELD_BONUS       = 0.25  # After castling pawn shield keeping rate
# ========================================================================



""" Definition:
#       1. Centipawn :   adj unit of measurement used to quantify adj player's advantage 
#                       in adj chess position. It's equal to 1/100th of adj pawn.
#         ( For Piece Tables )
#
# Functions:
#
#      1. piece_square_bonus      : ( chess.Board ) -> FLOAT
#         - calculate the total score for the current board for Piece-Square table
#
#      2. pawn_structure_penalty  : ( chess.Board ) -> FLOAT
#         - penalizes doubled and isolated pawns
#
#      3. piece_safety_penalty    : ( chess.Board ) -> FLOAT
#         - penalizes pieces that are attacked without adequate defense
#
#      4. king_safety_bonus       : ( chess.Board ) -> FLOAT
#         - Rewards castled kings and penalizes unsafe kings
#
#      5. piece_development_bonus : ( chess.Board ) -> FLOAT
#         - Rewards developing knights and bishops from the back rank
#
#      6. passed_pawn_bonus       : ( chess.Board ) -> FLOAT
#         - no enemy pawn ahead on same file
#
#      7. bishop_pair_bonus       : ( chess.Board ) -> FLOAT
#         - Tunable value
#
#      8. intermediate_penalty    : ( chess.Board ) -> FLOAT
#         - score for hanging and losing pieces
#
#      ***
#      9. positional_score        : ( chess.Board ) -> FLOAT
#         - Adds all the Previous bonuses and penalties
"""






# ===============================================================================
#                   Piece-Square Tables (in centipawns)
# ===============================================================================

# Tables represent values for White; For Black, values are negated automatically.
# -------------------------------------------------------------------------------

# PAWN_TABLE : Encourages central advanced pawns and penalizes backward/overexposed pawns.
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

# KNIGHT_TABLE  : Rewards knights in the center; punishes on the rim.
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

# Rest of the Pieces -----------------------------
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
     0,   0,   5,  11,  11,   5,   0,   0,
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
# ----------------------------------------------

# KING_MID_TABLE vs KING_END_TABLE:
#    1. Midgame table penalizes early central deployment
#    2. Endgame table rewards central king activity 
# #     when few pieces remaining

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





# ===========================================================
#                      Functions
# ===========================================================

#                         1

# ======================================================
def piece_square_bonus(board: chess.Board) -> float:
    """
    Compute total piece-square table score from White's perspective.
    Positive → White is better; Negative → Black is better.
    """
    score = 0.0
    for sq in chess.SQUARES:
        # Find the piece - p
        p = board.piece_at(sq)
        if not p:
            continue
        table = None
        # Piece type - pt
        pt    = p.piece_type
        # Map the table to piece type
        if   pt == chess.PAWN:   table = PAWN_TABLE
        elif pt == chess.KNIGHT: table = KNIGHT_TABLE
        elif pt == chess.BISHOP: table = BISHOP_TABLE
        elif pt == chess.ROOK:   table = ROOK_TABLE
        elif pt == chess.QUEEN:  table = QUEEN_TABLE
        elif pt == chess.KING:
            # KING --> choose Midgame vs Endgame : based on material 
            totalMaterial = 0
            for t in (chess.QUEEN, chess.ROOK, chess.KNIGHT, chess.BISHOP):
                totalMaterial += ( len(board.pieces(t, chess.WHITE)) + len(board.pieces(t, chess.BLACK)) )
            table = KING_END_TABLE if totalMaterial < 14 else KING_MID_TABLE

        if table:
            # mirror the index for Black so we pick the correct orientation
            i = sq if p.color == chess.WHITE else chess.square_mirror(sq)
            val = table[i] / 100.0
            score += val if p.color == chess.WHITE else -val
    return score
# =======================================================
#
#
#                         2
#
#
# =======================================================
def pawn_structure_penalty(board: chess.Board) -> float:
    """
    Simple pawn structure penalties for doubled and isolated pawns.
    Positive → White bad structure; Negative → Black bad structure.
    """
    score = 0.0
    for color in (chess.WHITE, chess.BLACK):
        pawns = list(board.pieces(chess.PAWN, color))
        files = [sq % 8 for sq in pawns]
        for f in set(files):
            count = files.count(f)
            if count > 1:
                # score per extra pawn on same file
                score += (count - 1) * 0.1 * (1 if color == chess.WHITE else -1)
        for sq in pawns:
            f = sq % 8
            # isolated if no adjacent file pawns
            if all(adj not in files for adj in (f-1, f+1) if 0 <= adj < 8):
                score += 0.1 * (1 if color == chess.WHITE else -1)
    return score
# =======================================================


#                         3


# =======================================================
def piece_safety_penalty(board: chess.Board) -> float:
    score = 0.0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p:
            continue
        attackers = board.attackers(not p.color, sq)
        defenders = board.attackers(p.color, sq)
        if attackers and not defenders:
            score += p.piece_type * (1 if p.color==chess.WHITE else -1) * SAFETY_MULTIPLIER
        elif attackers and len(defenders) < len(attackers):
            score += (  ( (len(attackers)-len(defenders)) * 0.1 * p.piece_type ) * (1 if p.color==chess.WHITE else -1)  )
    return score
# =======================================================


#                         4


# =======================================================
def king_safety_bonus(board: chess.Board) -> float:
    """
    Positive score when adj side has castled, 
    negative score if the king has moved early (before move 10) 
    or remains in the center too long.
    """
    score = 0.0
    for color, startSq, castledSqs in [
        (chess.WHITE, chess.E1, {chess.G1, chess.C1}),
        (chess.BLACK, chess.E8, {chess.G8, chess.C8})
    ]:
        kingSq = board.king(color)
        # if castled (king on g-file or c-file)
        if kingSq in castledSqs:
            score += 0.5 if color == chess.WHITE else -0.5
        else:
            # score if king moved off start before move 10
            if board.fullmove_number <= 10 and kingSq != startSq:
                score -= 0.3 if color == chess.WHITE else -0.3
            # small score for staying in center midgame
            if board.fullmove_number > 10 and kingSq in [chess.D4, chess.D5, chess.E4, chess.E5]:
                score -= 0.2 if color == chess.WHITE else -0.2
    return score
# =======================================================


#                         5


# =======================================================
def piece_development_bonus(board: chess.Board) -> float:
    """
    Rewards minor pieces (knights/bishops) that have left their 
    original back-rank squares (b1, g1 / b8, g8).
    """
    score = 0.0
    for color, starting in [
        (chess.WHITE, {chess.B1, chess.G1, chess.C1, chess.F1}),
        (chess.BLACK, {chess.B8, chess.G8, chess.C8, chess.F8})
    ]:
        for pt in (chess.KNIGHT, chess.BISHOP):
            for sq in board.pieces(pt, color):
                if sq not in starting:
                    score += 0.1 if color == chess.WHITE else -0.1
    return score
# =======================================================


#                         6


# =======================================================
def passed_pawn_bonus(board: chess.Board) -> float:
    score = 0.0
    for color in (chess.WHITE, chess.BLACK):
        for sq in board.pieces(chess.PAWN, color):
            file = sq % 8
            rank = sq // 8
            # White: no black pawn on same file ahead
            ahead = range(rank+1, 8) if color==chess.WHITE else range(rank-1, -1, -1)
            if all(not board.piece_at(f*8 + file) 
                   or board.piece_at(f*8 + file).color==color
                   for f in ahead):
                score += PASSED_PAWN_BONUS * (1 if color==chess.WHITE else -1)
    return score
# =======================================================


#                         7


# =======================================================
def bishop_pair_bonus(board: chess.Board) -> float:
    score = 0.0
    for color in (chess.WHITE, chess.BLACK):
        bishops = len(board.pieces(chess.BISHOP, color))
        if bishops >= 2:
            score += BISHOP_PAIR_BONUS * (1 if color==chess.WHITE else -1)
    return score
# =======================================================


#                         8


# =======================================================
def intermediate_penalty(board: chess.Board) -> float:
    """
    Penalise pieces attacked more than defended.  Positive for White advantage,
    negative for Black.
    """
    score = 0.0
    for sq, pc in board.piece_map().items():
        attackers = board.attackers(not pc.color, sq)
        defenders = board.attackers(pc.color, sq)
        total = len(attackers) - len(defenders)
        if total > 0:
            score += 0.05 * total * (1.0 if pc.color == chess.WHITE else -1.0)
    return score
# =======================================================


#                         9


# =======================================================
def positional_score(board: chess.Board) -> float:
    """
    Combined positional score in pawn units (White positive).
    """
    pst     = piece_square_bonus(board)
    pawnp   = pawn_structure_penalty(board)
    safety  = piece_safety_penalty(board)
    score     = piece_development_bonus(board)
    kingpb  = king_safety_bonus(board)
    bpBonus    = bishop_pair_bonus(board)
    ppBonus    = passed_pawn_bonus(board)

    # Count legal moves for **both** colours so the score is symmetrical.
    cur_turn = board.turn
    moves_sideToMove = board.legal_moves.count()

    board.push(chess.Move.null())            # give the move to the opponent
    moves_otherSide    = board.legal_moves.count()
    board.pop()

    if cur_turn == chess.WHITE:
        whiteMoves, blackMoves = moves_sideToMove, moves_otherSide
    else:
        whiteMoves, blackMoves = moves_otherSide, moves_sideToMove

    scale = max(-MOBILITY_MAX, min(MOBILITY_MAX, whiteMoves - blackMoves))     
    mob = (scale / MOBILITY_MAX) * MOBILITY_WEIGHT

    # pawn shield: award +0.25 for White, –0.25 for Black if king is castled and front pawn intact
    shield = 0.0
    for color, kingSq, pawnSq in [
        (chess.WHITE, chess.G1, chess.F2),
        (chess.BLACK, chess.G8, chess.F7)
    ]:
        if board.king(color) == kingSq and board.piece_at(pawnSq):
            shield += KING_SHIELD_BONUS * (1 if color == chess.WHITE else -1)

    mistakePen = intermediate_penalty(board)



    return (
        pst
      - pawnp
      - safety
      - mistakePen
      + mob
      + 0.8 * kingpb
      + 0.5 * score
      + bpBonus
      + ppBonus
      + shield
    )
# =======================================================