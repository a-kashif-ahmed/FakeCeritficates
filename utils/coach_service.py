from utils.ai import call_coach_api


def should_call_llm(analysis):

    classification = analysis["classification"]
    cp_loss = analysis["cp_loss"]

    if classification == "Blunder":
        return True

    if classification == "Mistake":
        return True

    if classification == "Brilliant":
        return True

    if classification == "Inaccuracy" and cp_loss >= 120:
        return True

    return False


def local_feedback(analysis):

    c = analysis["classification"]

    if c == "Excellent":
        return "Excellent move."

    if c == "Good":
        return "Solid move. Keep improving your development."

    if c == "Inaccuracy":
        return "A small improvement was available."

    return None


def coach_user_move(ai_info, analysis):

    # ---------- FREE ----------
    local = local_feedback(analysis)

    if local is not None:
        return local

    # ---------- Paid ----------
    if not should_call_llm(analysis):
        return None

    prompt = f"""
You are an encouraging chess coach.

Move quality:
{analysis["classification"]}

Centipawn loss:
{analysis["cp_loss"]}

Best move:
{analysis["best_move"]}

Player move:
{analysis["played_move"]}

Evaluation before:
{analysis["before_eval"]}

Evaluation after:
{analysis["after_eval"]}

Explain:

1. Why the move was played.

2. Why it wasn't ideal.

3. Better strategic idea.

4. One practical tip.

Maximum 70 words.

Don't mention Stockfish.
"""

    return call_coach_api(
        ai_info["model_name"],
        ai_info["endpoint"],
        ai_info["api_key"],
        prompt
    )