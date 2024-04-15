#!/usr/bin/env python3

import os
import re

import piexif
from halo import Halo
from PIL import Image

import argparse
from dataclasses import dataclass

# Parse format: YYYYMMDD
REGEX_FILENAME_DATE = r'(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'
REGEX_EXIF_DATE = r'((\d{4}):(\d{2}):(\d{2}))'
REGEX_EXIF_TIME = r'((\d{2}):(\d{2}):(\d{2}))'
FILES_EXT = ['jpeg', 'jpg', 'mp4']


@dataclass
class File(object):
    filename = ''
    file_path = ''
    new_file_path = ''
    extension = ''
    parsed_date = ''
    exif_bytes = ''

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
    args = parser.parse_args()

    if not args:
        raise Exception('Must provide arguments!')

    return args


def get_files_from_path(path=None, ext_list=None):
    """
    Get all files from a given path.
    :param path: Path to scan.
    :param ext_list: List of allowed extensions.
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

    if files:
        print(f'Found {len(files)} files')
    else:
        print('No files found')
    return files


def export_exif_data(file):
    im = Image.open(file.file_path)
    exif_data = im.info.get("exif")
    data = None

    if exif_data:
        data = piexif.load(exif_data).get('Exif')

    return data


def check_exif(file):
    """
    Check if a file has exif data.
    :param file: File path.
    :return: True if file has exif data, False otherwise.
    """
    data = export_exif_data(file)

    if data:
        match = re.search(REGEX_FILENAME_DATE, data)
        if match:
            print(f'Found exif data')
            return True
    return False


def parse_filename_to_date(file):
    """ Parse and return only date from the filename.
    :param file: File path.
    :return: Date if found, None otherwise.
    """
    match = re.search(REGEX_FILENAME_DATE, file.filename)
    if match:
        date_dict = match.groupdict()
        file.parsed_date = f"{date_dict['year']}-{date_dict['month']}-{date_dict['day']}"

    return file


def new_image_exif_data(file):
    """
    Read image data from file.
    :param file: File object.
    :return: Image file object.
    """

    exif_dict = {'Exif': {piexif.ExifIFD.DateTimeOriginal: file.parsed_date}}
    exif_bytes = piexif.dump(exif_dict)
    file.exif_bytes = exif_bytes

    return file, piexif


def save_exif_data(file: File, img: Image, output_path: str, overwrite: bool=False):
    """Read a date from file data and save it to output path.
    :param file: File object.
    :param img: Image object.
    :param output_path: Output path.
    :param overwrite: Overwrite the output file.
    """

    new_name = file.filename.split('.')[0] + file.extension
    file.new_file_path = os.path.join(output_path, new_name)

    try:
        if not overwrite:
            if os.path.exists(file.new_file_path):
                raise FileExistsError(f"File or Path already exists: {file.new_file_path}")
    except Exception as e:
        print(f"\n{str(e)}")

    with img(file.new_file_path, exif=file.exif_bytes) as image:
        image.save()
    print(f"{file.new_file_path} saved successfully")
    return file


def main():
    args = parse_arguments()
    spinner = Halo(text='Retrieving list of media files...\n', spinner='dots')
    spinner.start()
    files_list = get_files_from_path(path=args.input_path)
    for file in files_list:
        # sleep(2)
        spinner.text = f'Processing: {file.filename}'
        im = Image.open(file.file_path)
        try:
            if not check_exif(file=file):
                file = parse_filename_to_date(file=file)

                if file.parsed_date is None:
                    continue
                file, exif = new_image_exif_data(file=file)
                save_exif_data(
                    file=file,
                    img=im,
                    output_path=args.output_path,
                    overwrite=args.overwrite
                )
                print(file.new_file_path)
                spinner.succeed(f"Processing complete on file: '{file.filename}'")
            else:
                spinner.info(f"Skipping file: '{file.filename}'")
        except Exception as e:
            spinner.info(f"An error occurred: {str(e)}")
    spinner.succeed("Run complete.")


if __name__ == '__main__':
    main()
