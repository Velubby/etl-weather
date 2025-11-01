import typer
from .config import settings
from .fetch import run as fetch_run
from .transform import run as transform_run

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


if __name__ == "__main__":
    app()
