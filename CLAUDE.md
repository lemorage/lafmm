# LAFMM — Code Standards

## Stack

Python 3.14. uv. ruff. ty. Free software only.

---

## Philosophy

Code as poetry. Each function a verse. Types as truth. Composition over inheritance. Functions over classes.

Inspired by **Bauhaus**, **KISS**, and the pragmatism of Linus Torvalds.

---

## Guiding Principles

1. **Types First** — Type hints everywhere. `ty` is law. Define the shape, then the logic follows.

2. **Immutability Default** — `frozen=True` dataclasses. Tuples over lists when size is known. `Sequence` over `list` in signatures. Never mutate in place — create new.

3. **Functions Over Classes** — Pure functions are the default unit of logic. Classes exist only for data (`@dataclass(frozen=True)`) and protocols. No method-heavy objects. Closures over stateful classes.

4. **Pure Domain Logic** — Separate domain types, repository functions, and service orchestration. Thin handlers, fat domain. Side effects at the edges, pure logic at the core.

5. **No Comments Unless Essential** — Self-documenting names. All use lowercase_snake. Comments explain *why*, never *what*. Bauhaus: form follows function.

6. **Early Return** — Guard clauses over nested conditionals. Flat is better than deep.

---

## Patterns

### Result Type
```python
@dataclass(frozen=True)
class Ok[T]:
    value: T

@dataclass(frozen=True)
class Fail[E]:
    error: E

type Result[T, E = Exception] = Ok[T] | Fail[E]

def ok[T](value: T) -> Ok[T]:
    return Ok(value)

def fail[E](error: E) -> Fail[E]:
    return Fail(error)
```

### Railway-Oriented Error Handling
```python
async def process(agent_id: str) -> Result[Output]:
    match await find_agent(agent_id):
        case Fail() as err:
            return err
        case Ok(agent):
            pass

    match await execute(agent):
        case Fail() as err:
            return err
        case Ok(output):
            return ok(output)
```

### Structural Typing with Protocol
```python
class Searchable(Protocol):
    async def search(self, query: str) -> Result[Sequence[Painting]]: ...

async def search_all(sources: Sequence[Searchable], query: str) -> Sequence[Painting]:
    results = await asyncio.gather(
        *(source.search(query) for source in sources),
        return_exceptions=True,
    )
    return [
        painting
        for r in results
        if isinstance(r, Ok)
        for painting in r.value
    ]
```

### Thin Handlers
```python
@router.get("/search")
async def search(query: str | None = None) -> dict:
    if not query:
        raise HTTPException(status_code=400, detail="missing query")

    return await search_all_museums(query)
```

---

## Functional Patterns

### Comprehensions Over Loops
```python
# yes
titles = [p.title for p in paintings if p.is_public_domain]

# no
titles = []
for p in paintings:
    if p.is_public_domain:
        titles.append(p.title)
```

### Higher-Order Functions
```python
def with_retry[T](attempts: int, fn: Callable[[], Awaitable[Result[T]]]) -> Callable[[], Awaitable[Result[T]]]:
    async def wrapper() -> Result[T]:
        for _ in range(attempts):
            match await fn():
                case Ok() as result:
                    return result
                case Fail():
                    continue
        return fail(Exception("exhausted retries"))
    return wrapper
```

### Closures Over Stateful Classes
```python
# yes — closure captures config, returns pure function
def make_searcher(base_url: str, api_key: str) -> Callable[[str], Awaitable[Result[SearchResult]]]:
    async def search(query: str) -> Result[SearchResult]:
        return await fetch(f"{base_url}/search", query=query, key=api_key)
    return search

# no — class with state just to hold config
class Searcher:
    def __init__(self, base_url: str, api_key: str): ...
    async def search(self, query: str): ...
```

---

## Naming

| Category | Convention | Example |
|----------|-----------|---------|
| Functions | verbs, snake_case | `search_artic`, `normalize_object`, `build_image_url` |
| Types | Nouns, PascalCase | `Painting`, `SearchResult`, `SourceApi` |
| Predicates | Boolean questions | `has_image`, `is_public_domain` |
| Constants | UPPER_SNAKE | `BASE_URL`, `SEARCH_FIELDS` |
| Modules | short, snake_case | `models`, `routes`, `adapters` |

Avoid abbreviations. `painting_id` not `p_id`. `source_url` not `src_url`.

---

## Type Hints

- Use `collections.abc` types in signatures: `Sequence`, `Mapping`, `Callable`, `Iterable`
- Use concrete types only for construction: `list[int]()`, `dict[str, int]()`
- `X | None` over `Optional[X]`
- `type` statement for aliases: `type PaintingId = str`
- `Protocol` for structural typing — no ABCs, no inheritance hierarchies
- `@override` decorator when implementing protocol methods
- `Never` for exhaustiveness checking in match arms

---

## Async

### Parallel When Possible
```python
results = await asyncio.gather(
    search_artic(query),
    search_met(query),
    search_rijksmuseum(query, api_key),
    return_exceptions=True,
)
```

### Fault Tolerance
One source down must never kill the others. `return_exceptions=True` over bare `gather`.

---

## Error Handling

- Use `Result[T]` for expected failures (API errors, validation)
- Use `try/except` only at system boundaries (network, I/O)
- Never swallow errors silently — log or propagate
- Structured errors over string messages when the caller needs to branch
- `match/case` to branch on Result, not `isinstance` chains

---

## File Organization

```
src/
├── models/      — Domain types (frozen dataclasses, type aliases, protocols)
├── lib/         — Pure domain logic (adapters, transformers)
├── routes/      — Route handlers (thin controllers)
└── main.py      — App entry, middleware, route mounting
```

---

## Tooling

All from the Astral ecosystem. `pyproject.toml` is the single source of truth.

- **uv** — Package management, virtualenv, script running
  - `uv sync` to install
  - `uv run` to execute
  - `uv add` / `uv remove` to manage deps
  - Lock file committed. No `requirements.txt`.
- **ruff** — Lint and format. One tool, zero config fuss.
  - `ruff check` / `ruff format`
- **ty** — Type checking. Strict mode.
  - `ty check`

---

## Testing

Types catch bugs. Simple code needs no tests. Test only:
- Complex logic with edge cases
- External integrations (mocked)
- Critical business flows

Use the 3A pattern: **Arrange, Act, Assert**. Test behavior, not implementation.

Run with `uv run pytest`.

---

## Anti-Patterns

- **God Objects** — One class doing everything. Split into functions.
- **Primitive Obsession** — `(id: str, name: str, email: str)` -> use a frozen dataclass.
- **Magic Numbers** — Name your constants.
- **`Any`** — Use proper generics and type narrowing. `Any` is a lie that infects everything it touches.
- **Mutable Defaults** — `def f(items: list = [])` is a sin. Use `None` sentinel.
- **Bare `except`** — Always name what you catch.
- **Inheritance Hierarchies** — Use `Protocol` and composition. Inheritance is not FP.
- **Mutation** — Rebuilding a frozen dataclass with `replace()` is cheap. Mutating is a debt.

---

## Code Review Checklist

- [ ] No `Any` types
- [ ] Functions < 20 lines
- [ ] Single responsibility per function
- [ ] Immutable data by default (frozen dataclasses)
- [ ] Error handling via Result type with match/case
- [ ] Self-documenting names
- [ ] Parallel async where possible
- [ ] `Sequence`/`Mapping` in signatures, not `list`/`dict`
- [ ] Protocol over inheritance
- [ ] All deps are free software
- [ ] ruff clean, ty clean

---

*"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away."*
— Antoine de Saint-Exupery
