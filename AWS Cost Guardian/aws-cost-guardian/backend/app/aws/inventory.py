"""Read-only inventory. Missing permissions are recorded and never filled with guessed resources."""

from botocore.exceptions import ClientError

from app.core.logging import get_logger

logger = get_logger(__name__)

PAGE_LIMIT = 20
BUCKET_LIMIT = 50
SNAPSHOT_LIMIT = 100


def collect_inventory(clients: dict) -> tuple[list[dict], list[dict]]:
    resources: list[dict] = []
    problems: list[dict] = []
    collectors = (
        ("ec2", _instances),
        ("ec2", _volumes),
        ("ec2", _snapshots),
        ("ec2", _addresses),
        ("ec2", _nat_gateways),
        ("ec2", _vpc_endpoints),
        ("rds", _databases),
        ("s3", _buckets),
        ("lambda", _functions),
        ("elbv2", _load_balancers),
    )
    for service, collector in collectors:
        client = clients.get(service)
        if client is None:
            problems.append({"service": service, "error": f"{service} client was not available."})
            continue
        try:
            found, problem = collector(client)
        except Exception:
            logger.exception("Inventory collector failed for %s", service)
            found, problem = [], {"service": service, "error": "Inventory unavailable."}
        resources.extend(found)
        if problem:
            problems.append(problem)
    return resources, problems


def _denied(exc: ClientError) -> bool:
    code = exc.response.get("Error", {}).get("Code", "")
    return code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}


def _call(client, method: str, **kwargs):
    function = getattr(client, method, None)
    if function is None:
        return None, "Inventory unavailable."
    try:
        return function(**kwargs), None
    except ClientError as exc:
        logger.exception("AWS %s failed", method)
        if _denied(exc):
            return None, f"Missing IAM permission for {method}."
        return None, "Inventory unavailable."
    except Exception:
        logger.exception("AWS %s failed", method)
        return None, "Inventory unavailable."


def _tags(items: list | None) -> dict:
    tags = {}
    for item in items or []:
        key = item.get("Key") or item.get("key")
        if key:
            tags[str(key)] = str(item.get("Value") or item.get("value") or "")
    return tags


def _environment(tags: dict) -> str | None:
    for key in ("Environment", "environment", "env", "Env"):
        if tags.get(key):
            return tags[key]
    return None


def _name(tags: dict, fallback: str) -> str:
    return tags.get("Name") or fallback


def _region(zone: str | None) -> str:
    if not zone:
        return ""
    return zone[:-1] if zone[-1].isalpha() else zone


def _resource(
    resource_id: str,
    resource_type: str,
    service: str,
    region: str,
    state: str | None,
    instance_type: str | None,
    tags: dict,
    metadata: dict,
    name: str | None = None,
) -> dict:
    return {
        "resource_id": resource_id,
        "resource_type": resource_type,
        "service": service,
        "region": region or "",
        "name": name or _name(tags, resource_id),
        "state": state,
        "instance_type": instance_type,
        "environment": _environment(tags),
        "tags": tags,
        "metadata": metadata,
    }


def _pages(client, method: str, result_key: str, token_key: str = "NextToken", **kwargs):
    items = []
    token = None
    problem = None
    for _ in range(PAGE_LIMIT):
        call_args = dict(kwargs)
        if token:
            call_args[token_key] = token
        payload, problem = _call(client, method, **call_args)
        if payload is None:
            return items, {"service": method, "error": problem or "Inventory unavailable."}
        items.extend(payload.get(result_key) or [])
        token = payload.get(token_key)
        if not token:
            break
    return items, None


def _instances(client):
    reservations, problem = _pages(client, "describe_instances", "Reservations")
    if problem and not reservations:
        return [], problem
    resources = []
    for reservation in reservations:
        for instance in reservation.get("Instances") or []:
            tags = _tags(instance.get("Tags"))
            resources.append(
                _resource(
                    instance.get("InstanceId", ""),
                    "instance",
                    "EC2",
                    _region(instance.get("Placement", {}).get("AvailabilityZone")),
                    instance.get("State", {}).get("Name"),
                    instance.get("InstanceType"),
                    tags,
                    {
                        "platform": instance.get("PlatformDetails"),
                        "vpc_id": instance.get("VpcId"),
                        "subnet_id": instance.get("SubnetId"),
                        "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                    },
                )
            )
    return [item for item in resources if item["resource_id"]], problem


def _volumes(client):
    volumes, problem = _pages(client, "describe_volumes", "Volumes")
    resources = []
    for volume in volumes:
        tags = _tags(volume.get("Tags"))
        attachments = volume.get("Attachments") or []
        resources.append(
            _resource(
                volume.get("VolumeId", ""),
                "volume",
                "EBS",
                _region(volume.get("AvailabilityZone")),
                volume.get("State"),
                volume.get("VolumeType"),
                tags,
                {
                    "size_gib": volume.get("Size"),
                    "attached_to": attachments[0].get("InstanceId") if attachments else None,
                },
            )
        )
    return [item for item in resources if item["resource_id"]], problem


def _snapshots(client):
    snapshots, problem = _pages(client, "describe_snapshots", "Snapshots", OwnerIds=["self"], MaxResults=SNAPSHOT_LIMIT)
    resources = []
    for snapshot in snapshots[:SNAPSHOT_LIMIT]:
        tags = _tags(snapshot.get("Tags"))
        started = snapshot.get("StartTime")
        resources.append(
            _resource(
                snapshot.get("SnapshotId", ""),
                "snapshot",
                "EBS",
                "",
                snapshot.get("State"),
                None,
                tags,
                {
                    "started_at": started.date().isoformat() if started else None,
                    "volume_size_gib": snapshot.get("VolumeSize"),
                    "description": snapshot.get("Description"),
                },
                name=_name(tags, snapshot.get("SnapshotId", "")),
            )
        )
    return [item for item in resources if item["resource_id"]], problem


def _addresses(client):
    payload, problem = _call(client, "describe_addresses")
    if payload is None:
        return [], {"service": "ec2", "error": problem}
    resources = []
    for address in payload.get("Addresses") or []:
        tags = _tags(address.get("Tags"))
        associated = bool(address.get("AssociationId") or address.get("InstanceId") or address.get("NetworkInterfaceId"))
        resources.append(
            _resource(
                address.get("AllocationId") or address.get("PublicIp", ""),
                "elastic_ip",
                "EC2",
                "",
                "associated" if associated else "unassociated",
                None,
                tags,
                {
                    "public_ip": address.get("PublicIp"),
                    "association_id": address.get("AssociationId"),
                    "associated_to": address.get("InstanceId") or address.get("NetworkInterfaceId"),
                },
            )
        )
    return resources, None


def _nat_gateways(client):
    gateways, problem = _pages(client, "describe_nat_gateways", "NatGateways")
    resources = []
    for gateway in gateways:
        tags = _tags(gateway.get("Tags"))
        resources.append(
            _resource(
                gateway.get("NatGatewayId", ""),
                "nat_gateway",
                "NAT Gateway",
                "",
                gateway.get("State"),
                None,
                tags,
                {
                    "vpc_id": gateway.get("VpcId"),
                    "subnet_id": gateway.get("SubnetId"),
                    "connectivity": gateway.get("ConnectivityType"),
                },
            )
        )
    return [item for item in resources if item["resource_id"]], problem


def _vpc_endpoints(client):
    endpoints, problem = _pages(client, "describe_vpc_endpoints", "VpcEndpoints")
    resources = []
    for endpoint in endpoints:
        tags = _tags(endpoint.get("Tags"))
        resources.append(
            _resource(
                endpoint.get("VpcEndpointId", ""),
                "vpc_endpoint",
                "VPC",
                "",
                endpoint.get("State"),
                endpoint.get("VpcEndpointType"),
                tags,
                {"service_name": endpoint.get("ServiceName"), "vpc_id": endpoint.get("VpcId")},
            )
        )
    return [item for item in resources if item["resource_id"]], problem


def _databases(client):
    instances, problem = _pages(client, "describe_db_instances", "DBInstances")
    resources = []
    for instance in instances:
        tags = _tags(instance.get("TagList"))
        resources.append(
            _resource(
                instance.get("DBInstanceIdentifier", ""),
                "db_instance",
                "RDS",
                _region(instance.get("AvailabilityZone")),
                instance.get("DBInstanceStatus"),
                instance.get("DBInstanceClass"),
                tags,
                {
                    "engine": instance.get("Engine"),
                    "multi_az": instance.get("MultiAZ"),
                    "storage_gib": instance.get("AllocatedStorage"),
                },
            )
        )
    return [item for item in resources if item["resource_id"]], problem


def _buckets(client):
    payload, problem = _call(client, "list_buckets")
    if payload is None:
        return [], {"service": "s3", "error": problem}
    buckets = (payload.get("Buckets") or [])[:BUCKET_LIMIT]
    resources = []
    for bucket in buckets:
        name = bucket.get("Name")
        if not name:
            continue
        region = ""
        location, _location_problem = _call(client, "get_bucket_location", Bucket=name)
        if location:
            region = location.get("LocationConstraint") or "us-east-1"
        tagging, _tag_problem = _call(client, "get_bucket_tagging", Bucket=name)
        tags = _tags((tagging or {}).get("TagSet"))
        lifecycle, lifecycle_problem = _call(client, "get_bucket_lifecycle_configuration", Bucket=name)
        versioning, _version_problem = _call(client, "get_bucket_versioning", Bucket=name)
        resources.append(
            _resource(
                name,
                "bucket",
                "S3",
                region,
                "active",
                None,
                tags,
                {
                    "lifecycle": None if lifecycle is None or lifecycle_problem else "configured",
                    "versioning": (versioning or {}).get("Status") or "Disabled",
                },
                name=name,
            )
        )
    note = None
    if len(payload.get("Buckets") or []) > BUCKET_LIMIT:
        note = {"service": "s3", "error": f"Only the first {BUCKET_LIMIT} buckets were inventoried."}
    return resources, note


def _functions(client):
    functions, problem = _pages(client, "list_functions", "Functions", token_key="Marker")
    resources = []
    for function in functions:
        name = function.get("FunctionName", "")
        resources.append(
            _resource(
                name,
                "function",
                "Lambda",
                "",
                function.get("State") or "active",
                function.get("Runtime"),
                {},
                {"memory_mb": function.get("MemorySize"), "timeout_seconds": function.get("Timeout")},
                name=name,
            )
        )
    return [item for item in resources if item["resource_id"]], problem


def _load_balancers(client):
    balancers, problem = _pages(client, "describe_load_balancers", "LoadBalancers")
    resources = []
    for balancer in balancers:
        resources.append(
            _resource(
                balancer.get("LoadBalancerArn", ""),
                "load_balancer",
                "ELB",
                "",
                balancer.get("State", {}).get("Code"),
                balancer.get("Type"),
                {},
                {"scheme": balancer.get("Scheme"), "vpc_id": balancer.get("VpcId"), "dns_name": balancer.get("DNSName")},
                name=balancer.get("LoadBalancerName"),
            )
        )
    return [item for item in resources if item["resource_id"]], problem
