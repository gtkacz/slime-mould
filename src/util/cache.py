from typing import Callable

from cachetools import LRUCache, cached, keys


def method_lru_cache(maxsize: int = 1024) -> Callable:
    """
    Variation of the lru_cache decorator meant for class methods, meaning the `self` attribute is not cached.

    Args:
        maxsize (int, optional): The maximum size of the cache. Defaults to 1024.

    Returns:
        Callable: The lru_cache wrapper.
    """
    return cached(cache=LRUCache(maxsize=maxsize), key=keys.methodkey)
