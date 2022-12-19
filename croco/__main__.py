import click


@click.command()
@click.argument("file", type=click.Path(exists=True), required=False)
def main(file=None):
    if file is None:
        click.echo("Entering interactive mode")
        from croco.parser.repl import Repl

        Repl().run()
    else:
        click.echo(f"Reading from file {file}")

        from croco.parser import run
        import pathlib
        path = pathlib.Path(file)
        if not path.is_file():
            path /= "__main__.crc"
            if not path.is_file():
                click.echo(f"File {file} does not exist")
                exit(1)
                return

        with open(file) as f:
            run(f.read(), filename=file, mode="exec")

    exit(0)

if __name__ == '__main__':
    main()
