import secrets
import string


def generate_code_id(prefix):
    characters = string.ascii_uppercase + string.digits
    random_code = ''.join(secrets.choice(characters) for _ in range(6))
    return f"{prefix}-{random_code}"
