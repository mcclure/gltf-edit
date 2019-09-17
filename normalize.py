import click

@click.command()
@click.argument('infile', type=click.File('rb'))
@click.argument('outfile', type=click.File('wb'))
def normalize(infile, outfile):
    pass

normalize()
