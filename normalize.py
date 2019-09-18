from pygltflib import GLTF2, BufferFormat
import click
import sys
from enum import IntEnum
from struct import unpack_from, pack_into

class ComponentType(IntEnum):
    FLOAT = 5126
    UNSIGNED_BYTE = 5121
    UNSIGNED_SHORT = 5123

def componentTypeString(componentType): # Get name of enum
    try:
        componentTypeEnum = ComponentType(componentType)
    except ValueError:
        return "[INVALID]"
    return componentTypeEnum.name

def ratioWithDeadzone(value, compare, deadzone): # Returns a ratio that turns value into compare-- UNLESS the values have less than "deadzone" difference, then returns false. 
    diff = abs(compare - value)
    if diff < deadzone:
        return False
    return compare/value

@click.command(help="Normalizes weight attributes of a GLTF file")
@click.argument('infile')
@click.argument('outfile')
@click.option('--attr', default=["WEIGHTS_0"], multiple=True, help="Attribute to normalize. Can be passed multiple times. If no --attr argument is included, defaults to WEIGHTS_0 only")
@click.option('--zero-replacement', default=[1.0, 0.0, 0.0, 0.0], nargs=4, type=click.FLOAT, help="Four decimal numbers separated by spaces, representing the replacement vec4 that all-zero weights will be replaced with.              Default is 1 0 0 0")
@click.option('--no-reweight', count=True, help="Do not normalize nonzero weights (will still perform replacement on all-zero weights)")
@click.option('--float-good-enough', default=1/1024, type=click.FLOAT, help="If error on a vertex is less than this, reweighting will be skipped. Applies to weights stored as floats only. Default 1/1024. Set to 0 for \"reweight unless perfect\"")
@click.option('--short-good-enough', default=4, type=click.INT, help="If error on a vertex is less than this, reweighting will be skipped. Applies to weights stored as unsigned shorts only. Default 4. Set to 0 for \"reweight unless perfect\"")
@click.option('--byte-good-enough', default=4, type=click.INT, help="If error on a vertex is less than this, reweighting will be skipped. Applies to weights stored as unsigned bytes only. Default 4. Set to 0 for \"reweight unless perfect\"")
@click.option('--dry-run', count=True, help="Do not save OUTFILE (will still print information about INFILE)")
@click.option('--verbose', '-v', count=True, help="Explain what the script is doing in STDOUT")
def normalize(infile, outfile, attr, zero_replacement, no_reweight, float_good_enough, short_good_enough, byte_good_enough, dry_run, verbose):
    gltf = GLTF2().load(infile)

    attrAccessor = []                   # Track all found accessors for requested attributes
    attrFound = {a:False for a in attr} # Track whether each attribute exists somewhere in the file
    reweightCount, alterCount, visitCount = 0,0,0 # Track if we did anything

    # First iterate over the meshes and record the offset of each attribute we are looking for
    for meshI, mesh in enumerate(gltf.meshes):
        for primitiveI, primitive in enumerate(mesh.primitives):
            for a in attr:
                try:
                    attrAccessor.append(getattr(primitive.attributes, a))
                except AttributeError: # There was an attribute error, this mesh doesn't have that attribute
                    pass
                else:                  # There was no attribute error, the value was found
                    attrFound[a] = True
                    if verbose:
                        print("Mesh {} ({}), primitive {} has attribute {} at accessor {}.".format(meshI, mesh.name, primitiveI, a, attrAccessor[-1]))

    for a in attr:
        if not attrFound[a]:
            print("Warning: No mesh in this file has an attribute", a, file=sys.stderr)
    
    gltf.convert_buffers(BufferFormat.BINARYBLOB) # In principle it would be possible to leave URIs as is
    gltf._glb_data = bytearray(gltf._glb_data) # This technically violates the api but we're not given another way to mutate

    for accessorI in attrAccessor:
        try: # Extract accessor object
            accessor = gltf.accessors[accessorI]
        except IndexError:
            print("Warning: File is corrupt: accessor", accessorI, "not found. Skipping accessor...", file=sys.stderr)
            continue
        if verbose:
            print("Accessor {} points to bufferView {}, offset {}, component type {}.".format(accessorI, accessor.bufferView, accessor.byteOffset, componentTypeString(accessor.componentType)))
        if accessor.type != 'VEC4':
            print("Warning: Accessor {} is a '{}', not a VEC4 (i.e. it is not a weight). Skipping accessor...".format(accessorI, accessor.type), file=sys.stderr)
            continue
        componentType = accessor.componentType

        try: # Extract bufferView object
            bufferView = gltf.bufferViews[accessor.bufferView]
        except IndexError:
            print("Warning: File is corrupt: Accessor {} points to bufferView {}, which is not found. Skipping accessor...".format(accessorI, accessor.bufferView), file=sys.stderr)
            continue
        byteOffset = (bufferView.byteOffset or 0) + (accessor.byteOffset or 0)
        byteLength = (bufferView.byteLength or 0) - (accessor.byteOffset or 0)
        byteGoal = byteOffset + byteLength
        byteStride = bufferView.byteStride
        if verbose:
            print("BufferView {} points to buffer {}, offset {}, length {}, stride {}.".format(accessor.bufferView, bufferView.buffer, bufferView.byteOffset, bufferView.byteLength, byteStride))
            if accessor.byteOffset:
                print("(De facto offset {}, de facto length {}.)".format(byteOffset, byteLength))
        if byteStride == 0:
            print("Warning: File is corrupt: Accessor {} has a byteStride of 0. The standard does not say what to do in this case. Continuing but treating the byteStride as undefined".format(accessorI, byteOffset+byteLength-1, buff.byteLength), file=sys.stderr)

        if bufferView.buffer > 0:
            print("Warning: Accessor {} points to buffer {}. This is valid, but unfortunately this script cannot handle multi-buffer files! Skipping accessor...".format(accessorI, bufferView.buffer), file=sys.stderr)
            continue
        try: # Extract buffer object (only used for error checking)
            buff = gltf.buffers[bufferView.buffer]
        except IndexError:
            print("Warning: File is corrupt: Accessor {} points to buffer {}, which is not found. Skipping accessor...".format(accessorI, bufferView.buffer), file=sys.stderr)
            continue
        if buff.byteLength < byteGoal:
            print("Warning: File is corrupt: Accessor {} wants to span up to byte {}, but the buffer is only length {}. Skipping accessor...".format(accessorI, byteGoal-1, buff.byteLength), file=sys.stderr)
            continue

        if componentType == ComponentType.FLOAT:
            componentFormat = "<ffff"
            byteStride = byteStride or 16
        elif componentType == ComponentType.UNSIGNED_BYTE:
            componentFormat = "<BBBB"
            byteStride = byteStride or 4
        elif componentType == ComponentType.UNSIGNED_SHORT:
            componentFormat = "<HHHH"
            byteStride = byteStride or 8
        else:
            print("Warning: File is corrupt: Accessor {} has component type {}. This is not a recognized type. Skipping accessor...".format(accessorI, componentType), file=sys.stderr)
            continue

        # Alter data
        blob = gltf.binary_blob()
        while byteOffset < byteGoal:
            readVec = unpack_from(componentFormat, blob, byteOffset)
            readSum = sum(readVec)
            replaceVec = zero_replacement if readSum == 0 else None
            ratio = None

            if componentType == ComponentType.FLOAT:
                if not replaceVec and not no_reweight:
                    ratio = ratioWithDeadzone(readSum, 1.0, float_good_enough)
                    if ratio:
                        replaceVec = [x*ratio for x in readVec]

                byteOffset += (byteStride or 16)
            elif componentType == ComponentType.UNSIGNED_BYTE:
                ratio = ratioWithDeadzone(readSum, 1.0, byte_good_enough)
                if ratio:
                    pass

                byteOffset += (byteStride or 4)
            elif componentType == ComponentType.UNSIGNED_SHORT:
                ratio = ratioWithDeadzone(readSum, 1.0, short_good_enough)
                if ratio:
                    pass

            if replaceVec:
                pack_into(componentFormat, blob, byteOffset, *replaceVec)
                alterCount += 1
                if ratio:
                    reweightCount += 1
                if verbose:
                    print("At offset {}: {} {} {} {}".format(byteOffset, "reweighted" if ratio else "replaced", readVec, "to" if ratio else "with", replaceVec))

            byteOffset += byteStride
            visitCount += 1

    if verbose:
        print()
    print("Of {} vertices, replaced {} zeroes and reweighted {} non-normals{}".format(visitCount, alterCount-reweightCount, reweightCount, "" if alterCount else " (did nothing)"))

    if not dry_run:
        gltf.save(outfile)

normalize()
