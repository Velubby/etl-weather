import typer
from .config import settings
from .fetch import run as fetch_run
from .transform import run as transform_run
from .transform import run_hourly as transform_hourly_run
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
    days: int = typer.Option(7, help="Jumlah hari forecast (1–16)"),
    timezone: str = typer.Option(None, help="Timezone, contoh: Asia/Jakarta"),
    offline: bool = typer.Option(False, help="Gunakan sample offline di data/samples"),
    sample_dir: str = typer.Option(None, help="Folder sample (opsional)"),
    no_fallback: bool = typer.Option(
        False, help="Matikan fallback ke sample saat network gagal"
    ),
) -> None:
    if days < 1 or days > 16:
        _fail("Parameter --days harus 1–16.")
    try:
        c = city or settings.city
        tz = timezone or settings.timezone
        res = fetch_run(
            c,
            days=days,
            timezone=tz,
            offline=offline,
            sample_dir=sample_dir,
            fallback=not no_fallback,
        )
        typer.echo(
            f"Selesai ambil data. Latest: {res['weather_latest']} , {res['air_latest']}"
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
def transform_hourly(
    city: str = typer.Option(
        None, help="Nama kota; gunakan yang sama dengan saat fetch"
    ),
    output: str = typer.Option(None, help="Path output CSV hourly (opsional)"),
) -> None:
    """Bangun CSV hourly (gabungan cuaca & kualitas udara)."""
    try:
        c = city or settings.city
        out = transform_hourly_run(c, out_path=output)
        typer.echo(f"Berhasil transform hourly -> {out}")
    except Exception as e:
        _fail(f"Gagal transform hourly: {e}")


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
    timezone: str = typer.Option(None, help="Timezone"),
    output: str = typer.Option(None, help="Path HTML output"),
    offline: bool = typer.Option(False, help="Gunakan sample offline"),
    sample_dir: str = typer.Option(None, help="Folder sample (opsional)"),
    no_fallback: bool = typer.Option(False, help="Matikan fallback sample"),
) -> None:
    if days < 1 or days > 16:
        _fail("Parameter --days harus 1–16.")
    try:
        c = city or settings.city
        tz = timezone or settings.timezone
        fetch_run(
            c,
            days=days,
            timezone=tz,
            offline=offline,
            sample_dir=sample_dir,
            fallback=not no_fallback,
        )
        transform_run(c)
        # Selain agregat harian, secara default juga hasilkan hourly untuk keperluan web
        try:
            transform_hourly_run(c)
        except Exception:
            # Jangan gagal keseluruhan bila hourly bermasalah; tetap lanjut laporan harian
            pass
        out = report_run(c, output=output)
        typer.echo(f"Selesai. Laporan: {out}")
    except Exception as e:
        _fail(f"Gagal menjalankan pipeline: {e}")


if __name__ == "__main__":
    app()
