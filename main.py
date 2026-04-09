from step_file_extractor import split_step_assembly
from meta_data_extractor import process_all_parts


if __name__ == "__main__":
    split_step_assembly("5_54.stp")
    process_all_parts("output_parts")

