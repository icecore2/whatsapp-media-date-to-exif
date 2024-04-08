# whatsapp-cdate-parse-and-save
This is a script that parses a date of creation from Whatsapp media files and save it as exif.
=======

Whatsapp date parsing from file names
---

Issue: When downloading files from Whatsapp application and saving them to a local storage,\
there are no `exif` data saved within the file.

Solution: Whatsapp photos are stored with sent date names. \
This data can be parsed and saved in a new `exif` data.\

This is a simple script to get Whatsapp name,
parse and save to new file with the new `exif` data.

Screenshot
---
![Screenshot](screenshots/1.jpg)

Usage
---
- Make sure Python install in your system with app dependencies installed.
- Run command prompt and use CLI command.

### Available options
| Argument       | Description                                         |
|----------------|-----------------------------------------------------|
| `--input_path` | Whatsapp images or videos folder to scanned         |
| `--ouput_path` | The output path to save the resulted media          |
| `--overwrite`  | Of overwrite the existing images in the output path |

Example:\
>python.exe main.py --input_path C:\whatsapp_images_path -ouput_path C:\output_path