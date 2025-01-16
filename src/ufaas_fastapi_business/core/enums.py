from enum import Enum


class Currency(str, Enum):
    none = "none"

    IRR = "IRR"
    IRT = "IRT"

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

    USDT = "USDT"
    BTC = "BTC"
    ETH = "ETH"
