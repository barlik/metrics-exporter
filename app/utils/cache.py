import cachepy


def cached(hours=0, minutes=0, seconds=0):
    """
    Decorator for caching functions
    """
    ttl = ((hours * 60) + minutes) * 60 + seconds

    return cachepy.Cache(ttl=ttl)
