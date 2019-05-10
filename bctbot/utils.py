import math
import time
from functools import wraps

import logging_setup
logger = logging_setup.logging.getLogger(__name__)


class RetrySettings:
    tries = 10
    delay = 2
    backoff = 1.5

    class PersistentErrorAfterRetries(Exception):
        """Raised when api calls fail even after retries so that manual intervention is necessary"""
        pass

    @staticmethod
    def raise_retry_error(*args, **kwargs):
        raise RetrySettings.PersistentErrorAfterRetries


def retry(exceptions, tries=RetrySettings.tries, delay=RetrySettings.delay, backoff=RetrySettings.backoff, logger=None,
          on_fail=None):
    """
    Retry calling the decorated function using an exponential backoff.

    Args:
        exceptions: The exception to check. may be a tuple of
            exceptions to check.
        tries: Number of times to try (not retry) before giving up.
        delay: Initial delay between retries in seconds.
        backoff: Backoff multiplier (e.g. value of 2 will double the delay
            each retry).
        logger: Logger to use. If None, print.
    """

    if backoff < 1:
        raise ValueError("backoff can't be less than 1")
    tries = math.floor(tries)
    if tries < 0:
        raise ValueError("tries must be 0 or greater")
    if delay < 0:
        raise ValueError("delay can't be less than 0")

    def deco_retry(f):

        @wraps(f)
        def f_retry(self, *args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(self, *args, **kwargs)
                except exceptions as e:
                    msg = '{}, Retrying {} in {} seconds... ({} tries left out of {})'.format(e.__class__.__name__,
                                                                                              f.__name__, mdelay,
                                                                                              mtries - 1, tries)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            if on_fail:
                return on_fail(self)
            return f(self, *args, **kwargs)

        return f_retry  # true decorator

    return deco_retry