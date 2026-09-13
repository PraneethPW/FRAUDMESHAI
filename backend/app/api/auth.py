import re

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update

from app.api.deps import CurrentUser, DB
from app.core.security import create_token, decode_token, hash_password, token_digest, verify_password
from app.models.domain import RefreshToken, Role, User, Workspace, PasswordReset
from app.schemas.domain import LoginRequest, RefreshRequest, TokenPair, UserCreate, UserOut, PasswordChange, ForgotPasswordRequest, ResetPasswordRequest
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
    if await db.scalar(select(Workspace.id).where(Workspace.name == payload.workspace_name)):
        raise HTTPException(409, "Workspace name already exists. Choose another name or ask its administrator for access.")
    workspace = Workspace(name=payload.workspace_name, slug=slug)
    db.add(workspace)
    await db.flush()
    user = User(
        workspace_id=workspace.id, email=email, full_name=payload.full_name, password_hash=hash_password(payload.password), role=Role.ADMIN
    )
    db.add(user)
    await db.flush()
    await audit(db, workspace.id, "REGISTER", user.id, "user", user.id)
    return await issue_tokens(db, user)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: DB) -> TokenPair:
    user = (await db.execute(select(User).where(User.email == payload.email.lower()))).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    await audit(db, user.workspace_id, "LOGIN", user.id, "user", user.id)
    return await issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: DB) -> TokenPair:
    try:
        decoded = decode_token(payload.refresh_token, "refresh")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    user = await db.get(User, decoded["sub"])
    if not user or not user.is_active:
        raise HTTPException(401, "User unavailable")
    from datetime import UTC, datetime

    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_digest(payload.refresh_token),
            RefreshToken.user_id == user.id,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        .values(revoked=True)
    )
    if result.rowcount != 1:
        raise HTTPException(401, "Refresh token revoked")
    return await issue_tokens(db, user)


@router.post("/logout", status_code=204)
async def logout(payload: RefreshRequest, user: CurrentUser, db: DB) -> None:
    stored = (
        await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_digest(payload.refresh_token), RefreshToken.user_id == user.id)
        )
    ).scalar_one_or_none()
    if stored:
        stored.revoked = True
        await db.commit()


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: DB) -> dict:
    import asyncio
    import secrets
    from datetime import UTC, datetime, timedelta
    from app.core.config import settings
    from app.services.mail import send_reset
    if not settings.smtp_host or not settings.smtp_sender:
        return {"configured": False, "message": "Email recovery is not configured. Contact your workspace administrator for account recovery."}
    user=await db.scalar(select(User).where(User.email==payload.email.lower(),User.is_active.is_(True)))
    if user:
        token=secrets.token_urlsafe(40)
        await db.execute(update(PasswordReset).where(PasswordReset.user_id==user.id).values(used=True))
        db.add(PasswordReset(user_id=user.id,token_hash=token_digest(token),expires_at=datetime.now(UTC)+timedelta(minutes=15)))
        await db.commit()
        try: await asyncio.to_thread(send_reset,user.email,token)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Password recovery delivery failed")
    return {"configured": True, "message": "If the account is active, a password reset link will be sent. It expires in 15 minutes."}

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: DB):
    from datetime import UTC, datetime
    stored=await db.scalar(select(PasswordReset).where(PasswordReset.token_hash==token_digest(payload.token),PasswordReset.used.is_(False),PasswordReset.expires_at>datetime.now(UTC)).with_for_update())
    if not stored: raise HTTPException(400,"Reset link is invalid or expired")
    user=await db.get(User,stored.user_id)
    if not user or not user.is_active: raise HTTPException(400,"Account unavailable")
    result=await db.execute(update(PasswordReset).where(PasswordReset.id==stored.id,PasswordReset.used.is_(False)).values(used=True))
    if result.rowcount!=1: raise HTTPException(400,"Reset link was already used")
    user.password_hash=hash_password(payload.new_password)
    await db.execute(update(RefreshToken).where(RefreshToken.user_id==user.id).values(revoked=True))
    await audit(db,user.workspace_id,"PASSWORD_RESET",user.id,"user",user.id)
    await db.commit()
    return {"message":"Password updated. Sign in with your new password."}


@router.post("/change-password")
async def change_password(payload: PasswordChange, user: CurrentUser, db: DB):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    await db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    await audit(db, user.workspace_id, "PASSWORD_CHANGED", user.id, "user", user.id)
    await db.commit()
    return {"message": "Password updated. Sign in again on your other devices."}
