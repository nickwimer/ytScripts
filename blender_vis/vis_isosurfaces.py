"""Uses blender API to visualize pre-computed isosurfaces."""
import os
import sys

import bpy
import numpy as np

sys.path.append(os.path.abspath(os.path.join(sys.argv[0], "../../")))
import ytscripts.blender_args as bargs  # noqa: E402


def get_args():
    """Parse command line arguments."""
    # Initialize the class for blender arguments
    bparse = bargs.blenderArgs()
    # Return the parsed arguments
    return bparse.parse_args()


def setup_scene(clean=False):
    """Sets up the scene either from scratch or remove default objects."""
    if clean:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    else:
        # Delete the cube
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_by_type(type="MESH")
        bpy.ops.object.delete(use_global=False)

        # Delete the light
        bpy.ops.object.select_by_type(type="LIGHT")
        bpy.ops.object.delete(use_global=False)

        # Delete the camera
        bpy.ops.object.select_by_type(type="CAMERA")
        bpy.ops.object.delete(use_global=False)


def set_light(
    name,
    location,
    rotation=(0.0, 0.0, 0.0),
    scale=(1.0, 1.0, 1.0),
    energy=1000,
    light_type="POINT",
):
    """Set up the light source for the scene."""
    light_data = bpy.data.lights.new(name=f"{name}-data", type=light_type)
    light_data.energy = energy

    # Create new object, pass the light data
    light_object = bpy.data.objects.new(name=name, object_data=light_data)

    # Set the light parameters
    light_object.location = location
    light_object.rotation_mode = "XYZ"
    light_object.rotation_euler = rotation
    light_object.scale = scale

    # Link object to collection in context
    bpy.context.collection.objects.link(light_object)


def set_camera(name, location, rotation=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
    """Set up the camera for the scene."""
    cam_data = bpy.data.cameras.new(name=f"{name}-data")

    # Create new object, pass the camera data
    cam_object = bpy.data.objects.new(name=name, object_data=cam_data)
    cam_object.location = location
    cam_object.rotation_mode = "XYZ"
    cam_object.rotation_euler = rotation
    cam_object.scale = scale

    bpy.context.collection.objects.link(cam_object)

    bpy.context.scene.camera = cam_object


def create_materials():
    """Create the materials to be used later."""
    mat = bpy.data.materials.new(name="Metal")
    mat.use_nodes = True
    mat_nodes = mat.node_tree.nodes
    mat_links = mat.node_tree.links

    output = mat_nodes["Material Output"]

    # Configure BSDF node
    BSDF = mat_nodes["Principled BSDF"]
    BSDF.inputs["Metallic"].default_value = 1.0
    BSDF.inputs["Roughness"].default_value = 0.2
    BSDF.inputs["Specular"].default_value = 0.5
    BSDF.inputs["Sheen Tint"].default_value = 0.5
    BSDF.inputs["Alpha"].default_value = 1.0
    BSDF.inputs["Emission"].default_value = (0, 0, 0, 1)

    # Add some noise node
    noise = mat_nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 500.0
    noise.inputs["Detail"].default_value = 10.0
    noise.inputs["Roughness"].default_value = 1.0
    noise.inputs["Distortion"].default_value = 0.0

    # Add bump node
    bump = mat_nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    bump.inputs["Distance"].default_value = 0.1

    # Make connections between nodes
    mat_links.new(noise.outputs["Fac"], bump.inputs["Height"])
    mat_links.new(bump.outputs["Normal"], BSDF.inputs["Normal"])
    mat_links.new(BSDF.outputs["BSDF"], output.inputs["Surface"])

    return mat


def main():
    """Main function for visualizing the isosurfaces."""

    # Parse the input arguments
    args = get_args()

    if args.outpath:
        outpath = args.outpath
    else:
        outpath = os.path.abspath(os.path.join(sys.argv[0], "../../outdata", "blender"))
    os.makedirs(outpath, exist_ok=True)

    # Write arguments to file for later use
    bargs.write_args(args, os.path.join(outpath, f"args_{args.oname}.json"))

    # Initialize the scene
    setup_scene(clean=False)
    # Set up the light source
    set_light(
        name="Light",
        location=(args.lloc[0], args.lloc[1], args.lloc[2])
        if args.lloc
        else (-1, -6, -6),
        rotation=(
            np.radians(args.lrot[0]),
            np.radians(args.lrot[1]),
            np.radians(args.lrot[2]),
        )
        if args.lrot
        else (0, 0, 0),
        energy=args.energy,
        light_type=args.ltype,
    )
    # Set up the camera source
    set_camera(
        name="Camera",
        location=(args.cloc[0], args.cloc[1], args.cloc[2])
        if args.cloc
        else (0, -6, -6),
        rotation=(
            np.radians(args.crot[0]),
            np.radians(args.crot[1]),
            np.radians(args.crot[2]),
        )
        if args.crot
        else (np.radians(135), 0, 0),
    )
    # Create the materials
    if args.material:
        metal = create_materials()

    if args.ftype == "obj":
        for idx, fname in enumerate(args.fname):
            bpy.ops.wm.obj_import(
                filepath=(os.path.join(args.datapath, f"{fname}.{args.ftype}")),
            )
            if args.material[idx] == "metal":
                new_obj = bpy.context.active_object
                if len(new_obj.material_slots) == 0:
                    bpy.ops.object.material_slot_add()
                new_obj.material_slots[0].material = metal

    else:
        sys.exit(f"File type {args.ftype} is not supported!")

    # Set the output file and render the scene
    bpy.context.scene.render.filepath = os.path.join(
        outpath, f"render_{args.oname}.png"
    )
    bpy.ops.render.render(write_still=True)

    if args.oname:
        bpy.ops.wm.save_as_mainfile(
            filepath=os.path.join(outpath, f"{args.oname}.blend")
        )


if __name__ == "__main__":
    main()
