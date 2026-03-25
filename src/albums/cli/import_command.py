import rich_click as click

from ..app import Context
from ..library import scanner
from ..library.importer import Importer
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

    parent_context = enter_folder_context(ctx, scan_folder)
    importer = Importer(ctx, extra, recursive, automatic)
    albums_total = importer.scan()
    ctx.console.print(f"Ready to try importing {albums_total} albums")

    importer.run()

    ctx.console.print("importing complete! scanning library...")
    scanner.scan(parent_context)
