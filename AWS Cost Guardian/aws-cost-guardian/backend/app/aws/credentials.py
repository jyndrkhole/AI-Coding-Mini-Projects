"""Build AWS clients from a profile or an assumed read-only role. Secrets are not stored."""

import boto3

from app.core.config import get_settings
from app.core.exceptions import FinOpsError

COST_EXPLORER_REGION = "us-east-1"


def build_aws_clients():
    settings = get_settings()
    if settings.mock_aws:
        raise FinOpsError("Demo mode does not call AWS.", status_code=400)

    session = boto3.Session(
        profile_name=settings.aws_profile or None,
        region_name=settings.aws_region,
    )
    if settings.aws_role_arn:
        sts = session.client("sts")
        assume_args = {
            "RoleArn": settings.aws_role_arn,
            "RoleSessionName": "aws-cost-guardian",
        }
        if settings.aws_external_id:
            assume_args["ExternalId"] = settings.aws_external_id
        try:
            assumed = sts.assume_role(**assume_args)
        except Exception as exc:
            raise FinOpsError("AWS role assumption failed.", status_code=503) from exc
        credentials = assumed["Credentials"]
        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=settings.aws_region,
        )
    return session.client("sts"), session.client("ce", region_name=COST_EXPLORER_REGION)
