from botocore.exceptions import ClientError

from app.aws.inventory import _call


def _client_error(code: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, operation)


class _Buckets:
    def get_bucket_tagging(self, **kwargs):
        raise _client_error("NoSuchTagSet", "GetBucketTagging")

    def get_bucket_lifecycle_configuration(self, **kwargs):
        raise _client_error("NoSuchLifecycleConfiguration", "GetBucketLifecycleConfiguration")


def test_missing_tags_are_an_empty_tag_set() -> None:
    payload, problem = _call(_Buckets(), "get_bucket_tagging", Bucket="untagged")
    assert problem is None
    assert payload == {"TagSet": []}


def test_missing_lifecycle_is_not_an_inventory_failure() -> None:
    payload, problem = _call(_Buckets(), "get_bucket_lifecycle_configuration", Bucket="plain")
    assert payload is None
    assert problem is None
