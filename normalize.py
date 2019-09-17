from pygltflib import GLTF2
import click
import sys

@click.command()
@click.argument('infile')
@click.argument('outfile')
@click.option('--attr', default=["WEIGHTS_0"], multiple=True, help="Attribute to normalize. Can be passed multiple times. If no --attr argument is included, defaults to WEIGHTS_0 only.")
def normalize(infile, outfile, attr):
    gltf = GLTF2().load(infile)

    attrOffset = []                     # Track binary offset of each requested attribute
    attrFound = {a:False for a in attr} # Track whether each attribute exists somewhere in the file

    # First iterate over the meshes and record the offset of each attribute we are looking for
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            for a in attr:
                try:
                    attrOffset.append(getattr(primitive.attributes, a))
                except AttributeError: # There was an attribute error, this mesh doesn't have that attribute
                    pass
                else:                  # There was no attribute error, the value was found
                    attrFound[a] = True

    for a in attr:
        if not attrFound[a]:
            print("Warning: No mesh in this file has an attribute", a, file=sys.stderr)

    gltf.save(outfile)

normalize()
