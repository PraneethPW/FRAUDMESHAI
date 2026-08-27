import re

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.core.security import create_token, decode_token, hash_password, token_digest, verify_password
from app.models.domain import RefreshToken, Role, User, Workspace
from app.schemas.domain import LoginRequest, RefreshRequest, TokenPair, UserCreate, UserOut
from app.services.audit import audit

router = APIRouter(prefix="/auth", tags=["authentication"])


async def issue_tokens(db: DB, user: User) -> TokenPair:
    access, _, _ = create_token(user.id, user.role.value, user.workspace_id)
    refresh, _, expires = create_token(user.id, user.role.value, user.workspace_id, "refresh")
    db.add(RefreshToken(user_id=user.id, token_hash=token_digest(refresh), expires_at=expires))
    await db.commit()
    return TokenPair(access_token=access, refresh_token=refresh, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenPair, status_code=201)
async def register(payload: UserCreate, db: DB) -> TokenPair:
    email = payload.email.lower()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    slug_base = re.sub(r"[^a-z0-9]+", "-", payload.workspace_name.lower()).strip("-") or "workspace"
    slug = slug_base
    suffix = 1
    while await db.scalar(select(Workspace.id).where(Workspace.slug == slug)):
        suffix += 1
        slug = f"{slug_base}-{suffix}"
    workspace = Workspace(name=payload.workspace_name, slug=slug)
    db.add(workspace)
    await db.flush()
    user = User(workspace_id=workspace.id, email=email, full_name=payload.full_name, password_hash=hash_password(payload.password), role=Role.ADMIN)
    db.add(user)
    await db.flush()
    await audit(db, workspace.id, "REGISTER", user.id, "user", user.id)
    return await issue_tokens(db, user)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: DB) -> TokenPair:
    user = (await db.execute(select(User).where(User.email == payload.email.lower()))).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    await audit(db, user.workspace_id, "LOGIN", user.id, "user", user.id)
    return await issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: DB) -> TokenPair:
    try:
        decoded = decode_token(payload.refresh_token, "refresh")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    stored = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_digest(payload.refresh_token), RefreshToken.revoked.is_(False)))).scalar_one_or_none()
    user = await db.get(User, decoded["sub"])
    if not stored or not user:
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    stored.revoked = True
    return await issue_tokens(db, user)


@router.post("/logout", status_code=204)
async def logout(payload: RefreshRequest, user: CurrentUser, db: DB) -> None:
    stored = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_digest(payload.refresh_token), RefreshToken.user_id == user.id))).scalar_one_or_none()
    if stored:
        stored.revoked = True
        await db.commit()


@router.post("/forgot-password")
async def forgot_password() -> dict:
    return {"message": "If the account exists, a reset instruction will be issued by the configured email provider.", "configured": False}

