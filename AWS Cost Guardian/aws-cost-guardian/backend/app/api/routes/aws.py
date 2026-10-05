from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.account import AccountResponse
from app.schemas.scan import ScanResponse
from app.services.account_service import get_account
from app.services.scan_service import run_scan

router = APIRouter(tags=["aws"])


@router.get("/aws/account", response_model=AccountResponse)
def aws_account(session: Session = Depends(get_db)) -> AccountResponse:
    return AccountResponse(**get_account(session))


@router.post("/aws/scan", response_model=ScanResponse)
def aws_scan(session: Session = Depends(get_db)) -> ScanResponse:
    return ScanResponse(**run_scan(session))
