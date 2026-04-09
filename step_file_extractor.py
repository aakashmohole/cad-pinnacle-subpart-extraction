import os
import logging
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
from OCP.TDF import TDF_LabelSequence
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def export_shape_to_step(shape, filename):
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    writer.Write(filename)

def split_step_assembly(input_file, output_folder="output_parts"):
    logging.info(f"Starting extraction for {input_file}")
    
    os.makedirs(output_folder, exist_ok=True)

    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    app.InitDocument(doc)

    reader = STEPCAFControl_Reader()
    logging.info("Reading STEP file...")
    status = reader.ReadFile(input_file)

    if status != 1:
        logging.error(f"Failed to read STEP file: {input_file}")
        return

    logging.info("STEP file read successfully. Transferring data to document...")
    reader.Transfer(doc)

    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labels = TDF_LabelSequence()
    shape_tool.GetFreeShapes(labels)
    
    top_level_count = labels.Length()
    logging.info(f"Found {top_level_count} top-level free shapes.")

    count = 0

    for i in range(top_level_count):
        label = labels.Value(i + 1)

        components = TDF_LabelSequence()
        XCAFDoc_ShapeTool.GetComponents_s(label, components)

        if components.Length() == 0:
            shape = XCAFDoc_ShapeTool.GetShape_s(label)
            count += 1
            export_shape_to_step(
                shape,
                f"{output_folder}/part_{count}.step"
            )
        else:
            for j in range(components.Length()):
                comp = components.Value(j + 1)
                shape = XCAFDoc_ShapeTool.GetShape_s(comp)

                count += 1
                export_shape_to_step(
                    shape,
                    f"{output_folder}/part_{count}.step"
                )

    logging.info(f"Extraction complete! {count} total parts exported to '{output_folder}'.")
