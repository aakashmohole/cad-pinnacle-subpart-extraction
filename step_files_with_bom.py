import os
import logging
import pandas as pd
from datetime import datetime

from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
from OCP.TDF import TDF_LabelSequence
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs


# ---------------- LOGGER SETUP ----------------
def setup_logger():
    log_folder = "logs"
    os.makedirs(log_folder, exist_ok=True)

    log_file = os.path.join(
        log_folder,
        f"step_bom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


logger = setup_logger()


# ---------------- EXPORT STEP ----------------
def export_shape_to_step(shape, filename):
    try:
        writer = STEPControl_Writer()
        writer.Transfer(shape, STEPControl_AsIs)
        writer.Write(filename)

        logger.info(f"STEP exported: {filename}")

    except Exception as e:
        logger.error(f"Failed to export STEP file {filename}: {e}")


# ---------------- MAIN FUNCTION ----------------
def split_step_and_create_bom(input_file, output_folder="output_parts"):
    try:
        logger.info("Process started")
        logger.info(f"Input file: {input_file}")

        os.makedirs(output_folder, exist_ok=True)

        bom_data = []

        app = XCAFApp_Application.GetApplication_s()
        doc = TDocStd_Document(TCollection_ExtendedString("doc"))
        app.InitDocument(doc)

        reader = STEPCAFControl_Reader()
        status = reader.ReadFile(input_file)

        if status != 1:
            logger.error("Failed to read STEP file")
            return

        logger.info("STEP file read successfully")

        reader.Transfer(doc)

        shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

        labels = TDF_LabelSequence()
        shape_tool.GetFreeShapes(labels)

        logger.info(f"Found {labels.Length()} top-level assemblies")

        count = 0

        for i in range(labels.Length()):
            parent_label = labels.Value(i + 1)

            assembly_id = f"ASM-{i+1:03d}"
            item_no = f"{i+1}"

            # Parent assembly row
            bom_data.append({
                "Item No": item_no,
                "Parent Item": "-",
                "Part Number": assembly_id,
                "Part Name": f"Assembly_{i+1}",
                "Quantity": 1,
                "Level": 0,
                "Type": "Assembly",
                "File Name": input_file
            })

            logger.info(f"Processing assembly: {assembly_id}")

            components = TDF_LabelSequence()
            XCAFDoc_ShapeTool.GetComponents_s(parent_label, components)

            logger.info(f"Found {components.Length()} child components")

            for j in range(components.Length()):
                comp = components.Value(j + 1)
                shape = XCAFDoc_ShapeTool.GetShape_s(comp)

                count += 1

                part_id = f"PART-{count:03d}"
                child_item_no = f"{item_no}.{j+1}"

                file_name = f"part_{count}.step"
                file_path = os.path.join(output_folder, file_name)

                export_shape_to_step(shape, file_path)

                bom_data.append({
                    "Item No": child_item_no,
                    "Parent Item": item_no,
                    "Part Number": part_id,
                    "Part Name": f"Part_{count}",
                    "Quantity": 1,
                    "Level": 1,
                    "Type": "Part",
                    "File Name": file_name
                })

        # Save BOM
        df = pd.DataFrame(bom_data)

        excel_file = os.path.join(output_folder, "BOM_Standard.xlsx")
        df.to_excel(excel_file, index=False)

        logger.info(f"BOM Excel saved: {excel_file}")
        logger.info(f"Total exported parts: {count}")
        logger.info("Process completed successfully")

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")


if __name__ == "__main__":
    split_step_and_create_bom("2_126.stp")