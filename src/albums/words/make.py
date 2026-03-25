from typing import Sized


def is_plural(items: int | Sized, single_thing: str) -> str:
    count = items if isinstance(items, int) else len(items)
    verb = "is" if count == 1 else "are"
    return f"{verb} {plural(items, single_thing)}"


def a_plural(items: int | Sized, single_thing: str) -> str:
    count = items if isinstance(items, int) else len(items)
    article = "a " if count == 1 else ""
    return f"{article}{pluralize(single_thing, items)}"


def plural(items: int | Sized, single_thing: str) -> str:
    count = items if isinstance(items, int) else len(items)
    return f"{count} {pluralize(single_thing, items)}"


def pluralize(single_thing: str, items: int | Sized) -> str:
    count = items if isinstance(items, int) else len(items)
    if count == 1:
        thing = single_thing
    elif single_thing.endswith("y"):
        thing = f"{single_thing[:-1]}ies"
    else:
        thing = f"{single_thing}s"

    return thing
