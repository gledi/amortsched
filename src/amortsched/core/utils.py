import datetime


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def today() -> datetime.date:
    return datetime.datetime.now(datetime.UTC).date()
