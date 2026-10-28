"""Errors that should reach the operator as a clear message, not a fabricated result."""


class DatasetNotFound(FileNotFoundError):
    pass


class DatasetSchemaError(ValueError):
    pass


class NotFoundError(LookupError):
    pass


class BadRequestError(ValueError):
    pass
