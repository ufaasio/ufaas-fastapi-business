import asyncio
import functools
import logging


def get_all_subclasses(cls: type):
    subclasses = cls.__subclasses__()
    return subclasses + [
        sub for subclass in subclasses for sub in get_all_subclasses(subclass)
    ]


def try_except_wrapper(func):
    @functools.wraps(func)
    async def wrapped_func(*args, **kwargs):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            import traceback

            traceback_str = "".join(traceback.format_tb(e.__traceback__))
            logging.error(traceback_str)
            logging.error(f"An error occurred in {func.__name__}: {e}")
            return None

    return wrapped_func


def delay_execution(seconds):
    def decorator(func):
        @functools.wraps(func)
        async def wrapped_func(*args, **kwargs):
            await asyncio.sleep(seconds)
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return await asyncio.to_thread(func, *args, **kwargs)

        return wrapped_func

    return decorator


def retry_execution(attempts, delay=0):
    def decorator(func):
        @functools.wraps(func)
        async def wrapped_func(*args, **kwargs):
            last_exception = None
            for attempt in range(attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    return await asyncio.to_thread(func, *args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logging.error(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}"
                    )
                    if delay > 0:
                        await asyncio.sleep(delay)
            # If the loop finishes and the function didn't return successfully
            logging.error(f"All {attempts} attempts failed for {func.__name__}")
            raise last_exception

        return wrapped_func

    return decorator
