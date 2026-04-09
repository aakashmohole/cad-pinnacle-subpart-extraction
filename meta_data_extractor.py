import os
import glob
import json
import logging
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Sphere, GeomAbs_Torus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_part_metadata(filepath):
    """Extracts geometric and topological metadata from a single STEP file."""
    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != 1:
        logging.error(f"Failed to read file: {filepath}")
        return None
    
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape is None or shape.IsNull():
        logging.warning(f"No valid shape found in {filepath}")
        return None
    
    metadata = {}
    
    # --- 1. Top Level & Naming ---
    filename = os.path.basename(filepath)
    part_id = os.path.splitext(filename)[0]
    metadata["part_id"] = part_id
    metadata["file_name"] = filename
    
    # --- 2. Advanced Physics & Mass Properties ---
    props_vol = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props_vol)
    volume = props_vol.Mass()
    metadata["volume"] = volume
    
    cog = props_vol.CentreOfMass()
    metadata["center_of_gravity"] = {"x": cog.X(), "y": cog.Y(), "z": cog.Z()}
    
    props_area = GProp_GProps()
    BRepGProp.SurfaceProperties_s(shape, props_area)
    metadata["surface_area"] = props_area.Mass()
    
    # --- 3. Bounding Box & External Dimensions ---
    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    
    len_x = xmax - xmin
    len_y = ymax - ymin
    len_z = zmax - zmin
    dims = [len_x, len_y, len_z]
    dims.sort(reverse=True) # Longest to shortest
    
    metadata["bounding_box"] = {
        "x_min": xmin, "y_min": ymin, "z_min": zmin,
        "x_max": xmax, "y_max": ymax, "z_max": zmax,
    }
    metadata["dimensions"] = {
        "length_x": len_x,
        "length_y": len_y,
        "length_z": len_z,
        "longest": dims[0],
        "middle": dims[1],
        "shortest": dims[2]
    }
    
    # --- 4. Topological Granularity ---
    def count_topology(topo_type):
        exp = TopExp_Explorer(shape, topo_type)
        count = 0
        while exp.More():
            count += 1
            exp.Next()
        return count
        
    metadata["topology_counts"] = {
        "faces": count_topology(TopAbs_FACE),
        "edges": count_topology(TopAbs_EDGE),
        "vertices": count_topology(TopAbs_VERTEX)
    }
    
    # --- 5. Advanced Geometric Surface Categorization ---
    # We will iterate every face to determine if it's planar, cylindrical, etc.
    surfaces = {
        "planar_faces": 0,
        "cylindrical_faces": 0,
        "conical_faces": 0,
        "spherical_faces": 0,
        "toroidal_faces": 0,
        "other_curved_faces": 0
    }
    
    face_explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while face_explorer.More():
        current_face = TopoDS.Face(face_explorer.Current())
        surf_adaptor = BRepAdaptor_Surface(current_face)
        geom_type = surf_adaptor.GetType()
        
        if geom_type == GeomAbs_Plane:
            surfaces["planar_faces"] += 1
        elif geom_type == GeomAbs_Cylinder:
            surfaces["cylindrical_faces"] += 1
        elif geom_type == GeomAbs_Cone:
            surfaces["conical_faces"] += 1
        elif geom_type == GeomAbs_Sphere:
            surfaces["spherical_faces"] += 1
        elif geom_type == GeomAbs_Torus:
            surfaces["toroidal_faces"] += 1
        else:
            surfaces["other_curved_faces"] += 1
            
        face_explorer.Next()
        
    metadata["surface_categorizations"] = surfaces

    return metadata

def process_all_parts(target_folder="output_parts"):
    logging.info(f"Scanning target directory '{target_folder}' for STEP files...")
    search_pattern = os.path.join(target_folder, "*.step")
    step_files = glob.glob(search_pattern)
    
    if not step_files:
        logging.warning("No STEP files found in the directory.")
        return
        
    logging.info(f"Found {len(step_files)} STEP files. Beginning advanced metadata extraction...")
    
    for filepath in step_files:
        logging.info(f"Extracting metadata from: {filepath}")
        data = extract_part_metadata(filepath)
        
        if data:
            filename = os.path.basename(filepath)
            part_id = os.path.splitext(filename)[0]
            json_filepath = os.path.join(target_folder, f"{part_id}_metadata.json")
            
            with open(json_filepath, 'w') as jf:
                json.dump(data, jf, indent=4)
            logging.info(f"--> Saved payload: {json_filepath}")
        else:
            logging.error(f"--> Failed payload generation for: {filepath}")
