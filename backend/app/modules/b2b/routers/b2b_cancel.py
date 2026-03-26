from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Path
from fastapi.responses import JSONResponse

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.repos_idempotency import IdempotencyRepo
from app.schemas_b2b_cancel import CancelRequest, CancelRequestResponse
from app.services.b2b_cancel import B2BCancelService

router = APIRouter(prefix="/api/b2b", tags=["b2b-cancel"])


def get_cancel_service(db=Depends(get_db)) -> B2BCancelService:
    return B2BCancelService(db)


def get_idem_repo(db=Depends(get_db)) -> IdempotencyRepo:
    return IdempotencyRepo(db)


@router.post(
    "/bookings/{booking_id}/cancel-requests",
    response_model=CancelRequestResponse,
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin"]))],
)
async def create_b2b_cancel_request(
    booking_id: str = Path(...),
    payload: CancelRequest = Depends(),
    user=Depends(get_current_user),
    cancel_svc: B2BCancelService = Depends(get_cancel_service),
    idem: IdempotencyRepo = Depends(get_idem_repo),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "forbidden", "User is not bound to an agency")

    endpoint = "b2b_cancel_requests_create"
    method = "POST"
    path = f"/api/b2b/bookings/{booking_id}/cancel-requests"

    async def compute():
        case = await cancel_svc.create_cancel_case(
            organization_id=org_id,
            agency_id=agency_id,
            user_email=user.get("email"),
            booking_id=booking_id,
            cancel_req=payload,
        )
        return 200, case.model_dump()

    # Idempotency scope includes booking_id via path in request hash
    status, body = await idem.store_or_replay(
        org_id=org_id,
        agency_id=agency_id,
        endpoint=endpoint,
        key=idempotency_key,
        method=method,
        path=path,
        request_body=payload.model_dump(),
        compute_response_fn=compute,
    )

    if status == 200:
        return CancelRequestResponse(**body)

    return JSONResponse(status_code=status, content=body)
