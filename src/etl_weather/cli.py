import typer
from .config import settings
from .fetch import run as fetch_run
from .transform import run as transform_run
from .report import run as report_run

app = typer.Typer(help="ETL Cuaca & Kualitas Udara")


def _fail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


@app.command()
def hello(name: str = "world") -> None:
    typer.echo(f"Hello, {name}!")


@app.command()
def fetch(
    city: str = typer.Option(None, help="Nama kota (default dari .env atau config)"),
    days: int = typer.Option(7, help="Jumlah hari forecast (1–16 untuk Open-Meteo)"),
    timezone: str = typer.Option(None, help="Timezone, contoh: Asia/Jakarta"),
) -> None:
    if days < 1 or days > 16:
        _fail("Parameter --days harus 1–16.")
    try:
        c = city or settings.city
        tz = timezone or settings.timezone
        res = fetch_run(c, days=days, timezone=tz)
        typer.echo(
            f"Selesai ambil data '{res['location_name']}'. "
            f"Latest: {res['weather_latest']} , {res['air_latest']}"
        )
    except Exception as e:
        _fail(f"Gagal fetch: {e}")


@app.command()
def transform(
    city: str = typer.Option(
        None, help="Nama kota; gunakan yang sama dengan saat fetch"
    ),
    output: str = typer.Option(None, help="Path output CSV (opsional)"),
) -> None:
    try:
        c = city or settings.city
        out = transform_run(c, out_path=output)
        typer.echo(f"Berhasil transform -> {out}")
    except Exception as e:
        _fail(f"Gagal transform: {e}")


@app.command()
def report(
    city: str = typer.Option(None, help="Nama kota (default dari .env atau config)"),
    input: str = typer.Option(None, help="Path CSV (opsional, override)"),
    output: str = typer.Option(
        None, help="Path HTML output (default: reports/<city>.html)"
    ),
) -> None:
    try:
        c = city or settings.city
        out = report_run(c, output=output, csv_path=input)
        typer.echo(f"Laporan tersimpan -> {out}")
    except Exception as e:
        _fail(f"Gagal membuat laporan: {e}")


@app.command()
def all(
    city: str = typer.Option(None, help="Nama kota"),
    days: int = typer.Option(7, help="Jumlah hari forecast (1–16)"),
    timezone: str = typer.Option(None, help="Timezone, contoh: Asia/Jakarta"),
    output: str = typer.Option(
        None, help="Path HTML output (default: reports/<city>.html)"
    ),
) -> None:
    if days < 1 or days > 16:
        _fail("Parameter --days harus 1–16.")
    try:
        c = city or settings.city
        tz = timezone or settings.timezone
        fetch_run(c, days=days, timezone=tz)
        transform_run(c)
        out = report_run(c, output=output)
        typer.echo(f"Selesai. Laporan: {out}")
    except Exception as e:
        _fail(f"Gagal menjalankan pipeline: {e}")


if __name__ == "__main__":
    app()
