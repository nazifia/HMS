import random

def generate_retainership_reg_number():
    """Generate a unique 10-digit retainership registration number starting with 3."""
    return int(f"3{random.randint(0, 999999999):09d}")
