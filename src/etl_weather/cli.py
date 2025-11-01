import typer
from pathlib import Path

from .config import settings
from .fetch import run as fetch_run
from .transform import run as transform_run
from .viz import build_charts, save_charts_html

app = typer.Typer(help="ETL Cuaca & Kualitas Udara")


@app.command()
def hello(name: str = "world") -> None:
    typer.echo(f"Hello, {name}!")


@app.command()
def fetch(
    city: str = typer.Option(None, help="Nama kota (default dari .env atau config)"),
    days: int = typer.Option(7, help="Jumlah hari forecast (1-16 untuk Open-Meteo)"),
    timezone: str = typer.Option(None, help="Timezone, contoh: Asia/Jakarta"),
) -> None:
    c = city or settings.city
    tz = timezone or settings.timezone
    res = fetch_run(c, days=days, timezone=tz)
    typer.echo(
        f"Selesai ambil data '{res['location_name']}'. "
        f"Latest: {res['weather_latest']} , {res['air_latest']}"
    )


@app.command()
def transform(
    city: str = typer.Option(
        None, help="Nama kota; gunakan yang sama dengan saat fetch"
    ),
    output: str = typer.Option(None, help="Path output CSV (opsional)"),
) -> None:
    c = city or settings.city
    out = transform_run(c, out_path=output)
    typer.echo(f"Berhasil transform -> {out}")


@app.command()
def viz(
    city: str = typer.Option(None, help="Nama kota (gunakan CSV hasil transform)"),
    input: str = typer.Option(None, help="Path CSV, jika tidak pakai city"),
    outdir: str = typer.Option("reports/assets", help="Folder output HTML grafik"),
) -> None:
    if input:
        csv_path = Path(input)
    else:
        c = city or settings.city
        csv_path = Path("data/processed") / f"{c.lower().replace(' ', '-')}_daily.csv"
    if not csv_path.exists():
        raise typer.BadParameter(
            f"CSV tidak ditemukan: {csv_path}. Jalankan transform dulu."
        )
    charts = list(build_charts(csv_path))
    files = save_charts_html(charts, outdir)
    typer.echo("Grafik disimpan:")
    for f in files:
        typer.echo(f" - {f}")


if __name__ == "__main__":
    app()
