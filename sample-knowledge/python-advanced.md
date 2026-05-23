# Python Advanced Concepts

Covers Python features beyond the basics: decorators, generators, context managers, and type hints.

## Decorators

A decorator is a function that wraps another function to extend its behaviour without modifying it.

```python
import functools
import time

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper

@timer
def slow_function():
    time.sleep(0.5)
```

`functools.wraps` preserves the original function's `__name__` and `__doc__`.

### Decorator with arguments

```python
def repeat(n):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(n):
                func(*args, **kwargs)
        return wrapper
    return decorator

@repeat(3)
def say_hello():
    print("Hello!")
```

### Class-based decorators

```python
class Memoize:
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        if args not in self.cache:
            self.cache[args] = self.func(*args)
        return self.cache[args]

@Memoize
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)
```

## Generators

Generators produce values lazily — only computing the next item on demand. They use `yield` instead of `return`.

```python
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

gen = fibonacci()
print([next(gen) for _ in range(10)])  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

### Generator expressions

```python
# List comprehension (eager — all in memory)
squares_list = [x**2 for x in range(1_000_000)]

# Generator expression (lazy — one at a time)
squares_gen = (x**2 for x in range(1_000_000))
```

Use generators for large datasets or infinite sequences to avoid memory exhaustion.

### `yield from`

```python
def chain(*iterables):
    for it in iterables:
        yield from it

list(chain([1, 2], [3, 4], [5]))  # [1, 2, 3, 4, 5]
```

## Context Managers

Context managers handle setup/teardown automatically using the `with` statement.

```python
# Built-in example
with open("data.txt", "r") as f:
    content = f.read()
# File is closed automatically, even if an exception is raised
```

### Custom context manager using `__enter__` / `__exit__`

```python
class DatabaseConnection:
    def __init__(self, url: str) -> None:
        self.url = url
        self.conn = None

    def __enter__(self):
        self.conn = connect(self.url)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        return False  # don't suppress exceptions
```

### Context manager using `contextlib.contextmanager`

```python
from contextlib import contextmanager

@contextmanager
def temporary_directory():
    import tempfile, shutil
    path = tempfile.mkdtemp()
    try:
        yield path
    finally:
        shutil.rmtree(path)

with temporary_directory() as tmp:
    print(f"Working in {tmp}")
```

## Type Hints

Python's type system is gradual — hints are optional and checked by tools like `mypy`, not at runtime.

```python
from typing import Optional

def greet(name: str, times: int = 1) -> str:
    return (f"Hello, {name}! " * times).strip()

def find_user(user_id: int) -> Optional[dict]:
    ...
```

### Common type hint patterns

```python
from typing import Union, Callable, TypeVar

# Union (Python 3.9 onward: int | str)
def parse(value: Union[int, str]) -> str:
    return str(value)

# Callable
def apply(func: Callable[[int], int], value: int) -> int:
    return func(value)

# TypeVar for generics
T = TypeVar("T")

def first(items: list[T]) -> T:
    return items[0]
```

### Dataclasses with type hints

```python
from dataclasses import dataclass, field

@dataclass
class Point:
    x: float
    y: float
    label: str = "origin"
    tags: list[str] = field(default_factory=list)

p = Point(1.0, 2.0)
```
