#!/usr/bin/env python3

from datetime import datetime
import logging
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class File:
    filename: str = ''
    file_path: str = ''
    new_file_path: str = ''
    extension: str = ''
    parsed_date: str = ''
    last_modified_date: datetime | None = None
    exif_bytes: bytes = b''

    def __repr__(self):
        return f'Filename: {self.filename}'


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=f'Parse and modify Whatsapp images and videos exif attributes. '
                    f'Allowed extensions are: {",".join(FILES_EXT)}')
    parser.add_argument('--input_path', help='Whatsapp Images and videos path to scan', required=True)
    parser.add_argument('--output_path', help='New Whatsapp Images and videos path to scan', required=True)
    parser.add_argument('--recursive', action='store_true', help='Run recursively in the provided folder')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files in the output path')
    parser.add_argument('--experimental' or '--exp', action='store_true', help='Overwrite existing files in the output path')
    args = parser.parse_args()

    if not args:
        raise Exception('Must provide arguments!')

    return args


def get_files_from_path(path, recursive=False, output_path=''):
    files = []
    if recursive:
        file_paths = [os.path.join(root, file) for root, _, files in os.walk(path) for file in files]
    else:
        file_paths = [os.path.join(path, file) for file in os.listdir(path) if os.path.isfile(os.path.join(path, file))]
    
    for file_path in file_paths:
        filename = os.path.basename(file_path)
        extension = os.path.splitext(filename)[1][1:].lower()
        if extension in FILES_EXT:
            new_file_path = os.path.join(output_path, filename) if output_path else ''
            files.append(File(
                filename=filename,
                file_path=str(file_path),
                new_file_path=new_file_path,
                extension=extension,
                parsed_date='',
                exif_bytes=b''
            ))
    
    return files


def export_exif_data(file: File):
    with open(file.file_path, 'rb') as f:
        im = Image.open(f)
        exif_data = im.info.get("exif")
        data = None

        if exif_data:
            data = piexif.load(exif_data).get('Exif')

        file.last_modified_date = get_last_modified_date(f)

    return data


def check_exif(file: File):
    """
    Check if a file has exif data.
    :param file: File path.
    :return: True if file has exif data, False otherwise.
    """
    data = export_exif_data(file)

    if data:
        for tag_id, value in data.items():
            if isinstance(value, bytes):
                try:
                    decoded_value = value.decode('utf-8')
                    match = re.search(re.compile(REGEX_FILENAME_DATE), decoded_value)
                    if match:
                        logger.info(f'Found exif data')
                        return True

                except UnicodeDecodeError:
                    continue
    return False

def get_last_modified_date(file):
    """ This function is for extracting last date modification from EXIF data """
    return datetime.fromtimestamp(
        os.fstat(file.fileno()).st_mtime
    )


def parse_filename_to_date(file):
    """ Parse and return date and time from the filename. """
    date_match = re.search(REGEX_FILENAME_DATE, file.filename)
    time_match = re.search(r'at (\d{2})\.(\d{2})\.(\d{2})', file.filename)
    
    if date_match:
        date_dict = date_match.groupdict()
        date_str = f"{date_dict['year']}:{date_dict['month']}:{date_dict['day']}"
        
        if time_match:
            hour, minute, second = time_match.groups()
            time_str = f"{hour}:{minute}:{second}"
        else:
            time_str = "00:00:00"
        
        file.parsed_date = f"{date_str} {time_str}"
        logger.info(f'Parsed date and time from filename: {file.parsed_date}')
    
    return file

def new_image_exif_data(file):
    exif_dict = {'Exif': {}}
    parsed_datetime = datetime.strptime(
        file.parsed_date,
        '%Y:%m:%d %H:%M:%S'
    )
    date_time = f"{file.parsed_date} 00:00:00"  # Add a default time

    if (
            file.last_modified_date is not None
            and file.last_modified_date.date() == parsed_datetime.date()
    ):
        date_time = file.last_modified_date.strftime('%Y:%m:%d %H:%M:%S')
    else:
        date_time = file.parsed_date

    exif_dict['Exif'] = {
        piexif.ExifIFD.DateTimeOriginal: date_time.encode('utf-8'),
        piexif.ExifIFD.DateTimeDigitized: date_time.encode('utf-8'),
    }

    logger.info(f'New exif data: {exif_dict}')
    file.exif_bytes = piexif.dump(exif_dict)

    return file, file.exif_bytes


def save_exif_data(file, img, output_path, overwrite):
    os.makedirs(output_path, exist_ok=True)
    new_file_path = os.path.join(output_path, file.filename)
    if os.path.exists(new_file_path):
        if not overwrite:
            return
        else:
            os.remove(new_file_path)
        
    base, ext = os.path.splitext(file.filename)
    counter = 1

    new_filename = f"{base}_{counter}{ext}"
    new_file_path = os.path.join(output_path, new_filename)
    counter += 1
    img.save(new_file_path, exif=file.exif_bytes)
    img.close()
    
    file.new_file_path = new_file_path
    logger.info(f"'{file.new_file_path}' saved successfully")
    
    assert check_exif(file), "New file doesn't have exif data."

    return file

def main():
    args = parse_arguments()
    spinner = Halo(text='Retrieving list of media files...\n', spinner='dots')
    spinner.start()
    files_list = get_files_from_path(path=args.input_path, recursive=args.recursive)

    for file in files_list:
        if isinstance(file, str):
            file = File(filename=os.path.basename(file), file_path=file)
        
        spinner.text = f'Processing: {file.filename}'
        
        try:
            process_file(file, args, spinner)
        except Exception as e:
            spinner.info(f"An error occurred: {str(e)}")
    
    spinner.succeed("Run complete.")


def process_file(file, args, spinner):
    im = Image.open(file.file_path)
    
    if check_exif(file=file):
        spinner.info(f"Skipping file: '{file.filename}'")
        return

    file = parse_filename_to_date(file=file)
    if file.parsed_date is None:
        return

    file, exif = new_image_exif_data(file=file)
    save_exif_data(
        file=file,
        img=im,
        output_path=args.output_path,
        overwrite=args.overwrite
    )
    
    logger.info(file)
    spinner.succeed(f"Processing complete on file: '{file.filename}'")


if __name__ == '__main__':
    main()
