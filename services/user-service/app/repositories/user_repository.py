import uuid

from sqlalchemy.orm import Session

from app.models.user import AppUser


def get_by_username(db: Session, username: str) -> AppUser | None:
    return db.query(AppUser).filter(AppUser.username == username).first()


def get_by_id(db: Session, user_id: uuid.UUID) -> AppUser | None:
    return db.query(AppUser).filter(AppUser.user_id == user_id).first()


def create(
    db: Session, *, username: str, display_name: str, password_hash: str, role: str = "user"
) -> AppUser:
    user = AppUser(
        username=username,
        display_name=display_name,
        password_hash=password_hash,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
