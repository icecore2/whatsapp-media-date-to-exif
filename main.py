#!/usr/bin/env python3
import argparse
import json
from dataclasses import dataclass

import requests
import os
import re

from datetime import datetime
from halo import Halo
from tabulate import tabulate
from tqdm import tqdm
from urllib.parse import urlparse
from exif import Image

# Parse format: YYYYMMDD
REGEX_DATE = r'(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'
FILES_EXT = ['jpeg', 'jpg', 'mp4']


@dataclass
class File(object):
    filename = ''
    file_path = ''
    new_file_path = ''
    extension = ''
    parsed_date = ''

    def __repr__(self):
        return f'Filename: {self.filename}'


def parse_arguments():
    """
    Parse and modify Whatsapp images and videos exif attributes.
    :return:
    """
    parser = argparse.ArgumentParser(
        description=f'Parse and modify Whatsapp images and videos exif attributes. '
                    f'Allowed extensions are: {",".join(FILES_EXT)}')
    parser.add_argument('--input_path', help='Whatsapp Images and videos path to scan', required=True)
    parser.add_argument('--output_path', help='New Whatsapp Images and videos path to scan', required=True)
    # parser.add_argument('--suffix',
    #                     help='Add a suffix to file name, Defaults is empty and output same name as original filename')
    parser.add_argument('--overwrite', action='store_false', help='Overwrite existing, default is False')
    args = parser.parse_args()

    if not args:
        raise Exception('Must provide arguments!')

    return args


def get_files_from_path(path=None, ext_list=None):
    """
    Get all files from a given path.
    :param path: Path to scan.
    :param ext_list: List of allowed extentions.
    :return: List of files.
    """
    files = []
    allowed_extensions = ext_list if ext_list else FILES_EXT

    for root, dirs, filenames in os.walk(path, topdown=False):
        for filename in filenames:
            if [x for x in filenames if filename.endswith(tuple(allowed_extensions))]:
                file = File()
                file.file_path = os.path.join(root, filename)
                file.extension = os.path.splitext(filename)[-1]
                file.filename = os.path.splitext(filename)[0]
                files.append(file)

    return files


def check_exif(file):
    """
    Check if a file has exif data.
    :param file: File path.
    :return: True if file has exif data, False otherwise.
    """
    try:
        with open(file.file_path, 'rb') as image_file:
            my_image = Image(image_file)
        has_exif = True if my_image.has_exif else False
    except:
        has_exif = False

    return has_exif


def parse_filename_to_date(file):
    """ Parse and return only date from the filename.
    :param file: File path.
    :return: Date if found, None otherwise.
    """
    match = re.search(REGEX_DATE, file.filename)
    if match:
        date_dict = match.groupdict()
        file.parsed_date = f"{date_dict['year']}-{date_dict['month']}-{date_dict['day']}"

    return file


def read_image_data(file):
    """
    Read image data from file.
    :param file: File object.
    :return: Image file object.
    """
    img = None
    try:
        with open(file.file_path, 'rb') as image_file:
            img = Image(image_file)
            img.date_time = file.parsed_date
            img.datetime_original = file.parsed_date
    except Exception as e:
        print(f"\n{str(e)}")

    return img


def save_exif_data(file, img, output_path, overwrite=False):
    """Read a date from file data and save it to output path.
    :param file: File object.
    :param img: Image object.
    :param output_path: Output path.
    :param overwrite: Overwrite the output file.
    """
    new_name = file.filename.split('.')[0] + file.extension
    new_file_path = os.path.join(output_path, new_name)

    try:
        if overwrite:
            if os.path.exists(new_file_path):
                os.remove(new_file_path)
        else:
            if os.path.exists(new_file_path):
                print(f"File or Path already exists: {new_file_path}")
                return

        with open(new_file_path, 'wb') as new_image_file:
            new_image_file.write(img.get_file())

    except Exception as e:
        print(f"\n{str(e)}")

    file.new_file_path = new_file_path

    return file


def main():
    args = parse_arguments()
    spinner = Halo(text='Retrieving list of media files...', spinner='dots')
    spinner.start()

    try:
        files_list = get_files_from_path(path=args.input_path)

        for file in files_list:
            spinner.text = f'Processing: {file.filename}'

            if not check_exif(file=file):
                file = parse_filename_to_date(file=file)

                if file.parsed_date is None:
                    continue
                img = read_image_data(file=file)
                save_exif_data(
                    file=file,
                    img=img,
                    output_path=args.output_path,
                    overwrite=args.overwrite)
                spinner.succeed(f"Processing complete on file: '{file.filename}'")
            else:
                spinner.info(f"Skipping file: '{file.filename}'")
    except Exception as e:
        spinner.info(f"An error occurred: {str(e)}")
    spinner.succeed("Run complete.")


if __name__ == '__main__':
    main()
