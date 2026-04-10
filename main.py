from step_files_with_bom import split_step_and_create_bom
from meta_data_extractor import process_all_parts


if __name__ == "__main__":
    split_step_and_create_bom("5_51.stp")
    process_all_parts("output_parts")

