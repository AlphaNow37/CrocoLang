import click


@click.command()
@click.option("file", "-f", "--file", type=click.Path(exists=True))
def main(file=None):
    if file is None:
        click.echo("Entering interactive mode")
        from croco.parser.repl import Repl

        Repl().run()
    else:
        click.echo(f"Reading from file {file}")

if __name__ == '__main__':
    main()
