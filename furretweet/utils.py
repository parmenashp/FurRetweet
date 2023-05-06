import asyncio
import functools
from loguru import logger


def log_exception(message: str = ""):
    """Logs if an unhandled exception occurs in the given function
    and cancels the current task if it exists.

    If a message is given, it will be logged with the exception.
    """

    def decorator(coro):
        @functools.wraps(coro)
        async def wrapper(*args, **kwargs):
            try:
                return await coro(*args, **kwargs)
            except Exception as e:
                if message:
                    logger.exception(message)
                else:
                    logger.exception(e)

                task = asyncio.current_task()
                if task is not None:
                    logger.info("Cancelling task due to exception")
                    task.cancel()

        return wrapper

    return decorator
