from pathlib import Path
from typing import Tuple

import rich_click as click
from prompt_toolkit import choice
from prompt_toolkit.shortcuts import confirm
from rich.markup import escape
from sqlalchemy.orm import Session

from ..app import Context
from ..checks.checker import Checker
from ..library import scanner
from ..library.import_album import import_album, make_library_paths
from ..library.scanner import scan
from .cli_context import enter_folder_context, pass_context, require_configured, require_library, require_persistent_context


@click.command("import", help="check albums, copy each to library after it passes", add_help_option=False)
@click.argument("scan_folder", required=True)
@click.option("--extra", "-x", is_flag=True, help="copy extra files not scanned by albums")
@click.option("--recursive", "-r", is_flag=True, help="copy folders (one album max, implies --extra)")
@click.option("--automatic", "-a", is_flag=True, help="perform automatic fixes + import to default location")
@click.help_option("--help", "-h", help="show this message and exit")
@pass_context
def import_command(ctx: Context, extra: bool, recursive: bool, automatic: bool, scan_folder: str):
    require_configured(ctx)
    require_persistent_context(ctx)
    require_library(ctx)
    library = ctx.config.library
    parent_context = enter_folder_context(ctx, scan_folder)
    (albums_total, _) = scan(ctx, check_first_full_scan_path_count=_check_path_count)
    if albums_total == 0:
        ctx.console.print(f"Album not found at {escape(scan_folder)}")
        raise SystemExit(1)
    if albums_total > 1 and recursive:
        ctx.console.print(f"THe [bold]--recursive[/bold] option cannot be used because there is more than one album at {escape(scan_folder)}")
        raise SystemExit(1)

    ctx.console.print(f"Ready to try importing {albums_total} albums")
    checker = Checker(ctx, automatic, preview=False, fix=False, interactive=True, show_ignore_option=True)
    non_interactive_checker = Checker(ctx, False, False, False, False, False)
    with Session(ctx.db) as session:
        for album in ctx.select_album_entities(session):
            (exists, ok) = _check_existing_destination(ctx, make_library_paths(ctx, album))
            if not ok:
                continue
            issues = 0
            quit = False
            ctx.select_album_entities = lambda _: iter([album])
            ctx.console.print(f"Starting import: {escape(album.path)}", highlight=False)
            while not quit and checker.run_enabled(session):
                ctx.console.print("Remaining issues:")
                issues = non_interactive_checker.run_enabled(session)
                if issues == 0:
                    ctx.console.print("No issues")
                quit = issues == 0 or confirm("There are still issues. Do you want to skip importing this album?")

            if not issues:
                library_paths = make_library_paths(ctx, album)
                if not exists:  # check again in case tag fixes changed the destination paths
                    (exists, ok) = _check_existing_destination(ctx, library_paths)
                    if not ok:
                        continue
                source_path = Path(scan_folder) / album.path
                if automatic:
                    path_in_library = library_paths[0]
                else:
                    options = [(album_path, f">> Copy to: {album_path}") for album_path in library_paths] + [("", ">> Cancel")]
                    path_in_library = choice(message=f"Ready to copy from {source_path}", options=options)
                if path_in_library:
                    ctx.console.print(f"Import album from {source_path} to {str(library / path_in_library)}")
                    import_album(ctx, source_path, path_in_library, album, extra, recursive)

    ctx.console.print("importing complete! scanning library...")
    scanner.scan(parent_context)


def _check_path_count(ctx: Context, path_count: int) -> None:
    if path_count > ctx.config.import_scan_max_paths:
        ctx.console.print(
            f"found {path_count} paths, but import command is limited to {ctx.config.import_scan_max_paths} (controlled by global setting [bold]import_scan_max_paths[/bold])"
        )
        raise SystemExit(1)


def _check_existing_destination(ctx: Context, library_paths: list[str]) -> Tuple[bool, bool]:
    root_ctx = ctx.parent if ctx.parent is not None else ctx
    # TODO check for duplicate album by tag values too
    existing = next((path for path in library_paths if (root_ctx.config.library / path).exists()), None)
    if existing is not None:
        ctx.console.print(f"This album appears to be in the library: [bold]{escape(existing)}[/bold]")
        if confirm("Do you want to add it anyway?"):
            return (True, True)
        else:
            return (True, False)
    return (False, True)
