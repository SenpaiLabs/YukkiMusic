# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import traceback


async def meval(code: str, globs: dict, **kwargs):
    """
    Asynchronously evaluate a code string in a controlled environment.
    """
    locs = {}
    combined_globals = {**globals(), **globs, **kwargs}
    lines = code.strip().splitlines()
    if lines and not lines[-1].strip().startswith(("return", "yield")):
        lines[-1] = f"return {lines[-1]}"
    body = "\n    ".join(lines)
    exec_code = f"async def _eval_func():\n    {body}"

    try:
        exec(compile(exec_code, "<eval>", "exec"), combined_globals, locs)
        return await locs["_eval_func"]()
    except SyntaxError:
        exec_code = "async def _eval_func():\n" + "\n".join(f"    {line}" for line in code.strip().splitlines())
        exec(compile(exec_code, "<eval>", "exec"), combined_globals, locs)
        return await locs["_eval_func"]()


def format_exception(exc: BaseException, tb=None) -> str:
    """Format exception traceback into a readable string."""
    if tb is not None:
        return (
            "Traceback (most recent call last):\n"
            f"{''.join(traceback.format_list(tb))}"
            f"{type(exc).__name__}{': ' + str(exc) if str(exc) else ''}"
        )
    return "".join(traceback.format_exception(exc))
