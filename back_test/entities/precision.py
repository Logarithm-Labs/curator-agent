import math

def ceil_to_6dp(amount: float) -> float:
    return math.ceil(amount * 1e6) / 1e6

def floor_to_6dp(amount: float) -> float:
    return math.floor(amount * 1e6) / 1e6