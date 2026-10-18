from dataclasses import dataclass

@dataclass

class Cuenta:
    email: str
    username: str
    password_hash: str
    verified: bool = False
    verify_code: str | None = None
    verify_expires: str | None = None
    reset_code: str | None = None
    reset_expires: str | None = None
    created_at: str = ""