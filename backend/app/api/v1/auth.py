
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import (
    CurrentUser,
    get_auth_service,
)
from app.schemas.auth import (
    Message,
    MFADisableRequest,
    MFAEnableRequest,
    MFASetupResponse,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserPublic,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    # Prefer X-Forwarded-For if behind proxy (Caddy)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    ua = request.headers.get("user-agent")
    return ip, ua


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client_meta(request)
    return await svc.register(body.email, body.password, ip=ip, ua=ua)


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),  # supports Swagger OAuth2
    svc: AuthService = Depends(get_auth_service),
    # Also accept JSON body for convenience
):
    """
    Supports both:
    - application/x-www-form-urlencoded (OAuth2PasswordRequestForm) — Swagger
    - For pure JSON clients, prefer the /login/json endpoint below.
    """
    ip, ua = _client_meta(request)
    # form_data.username is the email
    return await svc.login(
        email=form_data.username,
        password=form_data.password,
        mfa_code=None,  # form path; use /login/json for MFA in one shot
        ip=ip,
        ua=ua,
    )


@router.post("/login/json", response_model=TokenPair)
async def login_json(
    body: UserLogin,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client_meta(request)
    return await svc.login(
        email=body.email,
        password=body.password,
        mfa_code=body.mfa_code,
        ip=ip,
        ua=ua,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client_meta(request)
    return await svc.refresh(body.refresh_token, ip=ip, ua=ua)


@router.post("/logout", response_model=Message)
async def logout(
    body: RefreshRequest | None = None,
    current_user: CurrentUser = None,  # type: ignore
    svc: AuthService = Depends(get_auth_service),
):
    # Soft: allow unauthenticated logout of a known refresh token
    raw = body.refresh_token if body else None
    uid = current_user.id if current_user else None
    await svc.logout(raw, user_id=uid)
    return Message(message="Logged out")


@router.get("/me", response_model=UserPublic)
async def me(current_user: CurrentUser):
    return UserPublic.model_validate(current_user)


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    current_user: CurrentUser,
    svc: AuthService = Depends(get_auth_service),
):
    return await svc.setup_mfa(current_user)


@router.post("/mfa/enable", response_model=Message)
async def mfa_enable(
    body: MFAEnableRequest,
    current_user: CurrentUser,
    svc: AuthService = Depends(get_auth_service),
):
    await svc.enable_mfa(current_user, body.code)
    return Message(message="MFA enabled")


@router.post("/mfa/disable", response_model=Message)
async def mfa_disable(
    body: MFADisableRequest,
    current_user: CurrentUser,
    svc: AuthService = Depends(get_auth_service),
):
    await svc.disable_mfa(current_user, body.code, body.password)
    return Message(message="MFA disabled")
