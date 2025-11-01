import typer

app = typer.Typer(help="ETL Cuaca & Kualitas Udara")


@app.command()
def hello(name: str = "world") -> None:
    typer.echo(f"Hello, {name}!")


if __name__ == "__main__":
    app()
