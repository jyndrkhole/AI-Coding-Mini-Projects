"""Provider errors. Agents depend on these types, not on yfinance."""


class TickerNotFound(LookupError):
    pass


class ProviderError(RuntimeError):
    pass
