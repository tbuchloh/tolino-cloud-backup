#!/usr/bin/env python3
import logging
import json
import configparser
import argparse
import re
import os

from tolinocloud import TolinoCloud, TolinoException

def safe_filename(input_string, replacement_char='_'):
    # Replace any character that is not alphanumeric or a valid file character with '_'
    return re.sub(r'[^\w\-.]', replacement_char, input_string)

def get_author(book):
    logging.debug(f"get_author({book})")
    author = book['author']
    if author == None or author == '' or len(author) == 0 or author[0] == None or author[0].strip == '':
        return "Unbekannt"
    else:
        first_author = author[0].split(',')[0]
        name_components = first_author.split(' ')
        return name_components[len(name_components) - 1]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='cmd line client to access personal tolino cloud storage space.'
    )
    parser.add_argument('--config', metavar='FILE', default='.tolinoclientrc', help='config file (default: .tolinoclientrc)')
    args, remaining_argv = parser.parse_known_args()

    # Load config
    confparse = configparser.ConfigParser(strict=False, interpolation=None)
    path = '.tolinoclientrc'
    if args.config:
        path = args.config
    confparse.read([path])
    conf = dict(confparse.items('Defaults'))

    parser.set_defaults(**conf)

    parser.add_argument('--user', type=str, help='username (usually an email address)')
    parser.add_argument('--password', type=str, help='password')
    parser.add_argument('--partner', type=int, help='shop / partner id (use 0 for list)')
    parser.add_argument('--use-device', action="store_true", help='use existing device credentials instead of signing in')
    parser.add_argument('--debug', action="store_true", help='log additional debugging info')
    parser.add_argument('--download-dir', type=str, help='path to the download directory')

    args = parser.parse_args(remaining_argv)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()

    # Initialise counters
    book_cnt = 0

    download_dir = args.download_dir
    logging.info(f"Use download-dir: {download_dir}")
    os.makedirs(download_dir, exist_ok=True)

    # Connect and gather list of books online
    c = TolinoCloud(args.partner, args.use_device, path)
    c.login(args.user, args.password)
    c.register()
    remote = c.inventory()

    file_extensions = {
        "application/epub+zip": "epub",
        "application/pdf": "pdf",
    }

    # download all books
    failed_items = []
    for book in remote:
        book_cnt += 1
        id = book['id']
        author = get_author(book)
        title = book['title']
        mimetype = book['mime']
        file_ext = file_extensions[mimetype]
        filename = safe_filename(f"{author}__{title}__{id}.{file_ext}")
        logger.info(f"Downloading #{book_cnt} ({id}): {author} {title} ({mimetype}) to {filename} ...")
        file_path = f"{download_dir}/{filename}"
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            try:
                dl_path = c.download(download_dir, id)
                os.rename(dl_path, file_path)
            except TolinoException as e:
                failed_items.append(book)
                logging.warning(f"Downloading {id} ({title}) failed! Reason: {e}")
        else:
            logging.info(f"Skipping download of {file_path} because it does already exist.")

    if args.use_device == False:
        c.unregister()
        c.logout()

    logging.info(f"Downloaded {book_cnt} items to {download_dir}. Failures: {len(failed_items)}.")
    for item in failed_items:
        logging.warning(f"  - {item['id']}: {item['title']}")
