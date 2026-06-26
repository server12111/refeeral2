import random


def generate_captcha() -> tuple[str, int]:
    a = random.randint(5, 20)
    b = random.randint(1, 10)
    op = random.choice(["+", "-"])
    if op == "+":
        answer = a + b
        question = f"{a} + {b}"
    else:
        if a < b:
            a, b = b, a
        answer = a - b
        question = f"{a} - {b}"
    return question, answer


_FRUITS = ["🍎", "🍊", "🍋", "🍇", "🍓", "🍒", "🥭", "🍑", "🍌"]


def generate_fruit_captcha() -> tuple[str, list[str]]:
    """Returns (target_emoji, shuffled_9_emoji_grid)."""
    grid = _FRUITS.copy()
    random.shuffle(grid)
    target = random.choice(grid)
    return target, grid
