import fixyourdocs


def test_import() -> None:
    assert fixyourdocs.__version__ == "0.1.0"


def test_public_exports() -> None:
    for name in (
        "Client",
        "AsyncClient",
        "Report",
        "ReportBody",
        "AgentInfo",
        "Evidence",
        "TaskContext",
        "ReportKind",
        "EvidenceKind",
        "SendResult",
        "FixYourDocsError",
        "ValidationError",
        "AuthError",
        "NotFoundError",
        "OptedOutError",
        "PayloadTooLargeError",
        "UnsupportedMediaTypeError",
        "PolicyRejectedError",
        "RateLimitedError",
        "ServerError",
    ):
        assert hasattr(fixyourdocs, name), f"missing public export: {name}"
