from typing import Callable, Any
from functools import wraps


def validator_health(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator de módulo que verifica `self.is_healthy` antes de executar o método.

    Use dentro da classe `RedisQueue` como:

        @validator_health
        def metodo(self, ...):
            ...
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        if not getattr(args[0], "is_healthy", False):
            raise ConnectionError("Redis não está disponível")
        return func(*args, **kwargs)

    return wrapper
