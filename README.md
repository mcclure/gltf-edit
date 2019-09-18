This is a script that normalizes the bone weights in a GLTF or GLB file.

In GLTF, files with skeleton animations are required by the file format to have "normalized weights". However, many programs that export GLTFs do not follow this rule, including (as of v2.8.0) Blender. This can confuse programs that open the GLTF files. This script fixes those files.

# More technical explanation

In the standard way of doing doing skeletons with GLTF, each vertex can be associated with up to four bones. The vertex then has a "weights" 4-vector indicating the percentage influence that each bone has on the vertex. These percentages are required to add up to 1. However, sometimes they don't. For example Blender v2.8.0 assigns a weights value of 0,0,0,0 for vertices which are not associated with any bones at all. In [the game engine I use](http://lovr.org/), this causes the zero-weighted vertices to not draw at all.

The script assigns a "default" value of 1,0,0,0 for all-zero weights, and for nonzero weights which add up to something other than 1 it rescales them until they do.

(An exception: If the numbers add up to *almost* one, the script by default does nothing, because that probably indicates normal rounding or floating-point behavior and not a broken file.)

# Usage

## First run

I suggest using a virtualenv for this script. Before first running the script, run:

	python3 -m venv env
	source env/bin/activate
	pip3 install -r requirements.txt

## Normal usage

	source env/bin/activate
	python3 normalize.py anyGLTF.glb newGLTF.glb

The input and output can be either GLTF or GLB. The output will be formatted GLTF or GLB depending on the file extension you give it.

## Fancy usage

The script has many options. You can see them with `python3 normalize.py --help`. For example here is an example that normalizes a custom WEIGHTS_1 attribute in addition to the standard WEIGHTS_0 one, and which does not tolerate "almost one" weights:

	source env/bin/activate
	python3 normalize.py anyGLTF.glb newGLTF.glb --attr WEIGHTS_0 --attr WEIGHTS_1 --float-good-enough 0 --short-good-enough 0 --byte-good-enough 0

# Known issues

This script currently cannot handle GLTF files that have multiple independent buffers. Also, in my testing, the sizes of the output files are slightly different from the input files, even if the script did not change anything. I *think* this is only because pygltflib makes different decisions about padding and no actual content has been altered, but I don't know for a fact. I have not tested the reweighting feature with a file that binary-packs its weights as UNSIGNED_BYTE or UNSIGNED_SHORT.

# License

This script was created by <<andi.m.mcclure@gmail.com>>. It is made available to you under the [Creative Commons Zero](https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt) license, which is to say, it is public domain. If you reproduce the script in its *entirety* it would be polite to keep a credit to me, but this is not a legal requirement.