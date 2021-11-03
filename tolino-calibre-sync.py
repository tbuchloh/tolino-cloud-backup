#!/usr/bin/env python3
import logging
import json
import configparser
import argparse

from tolinocloud import TolinoCloud, TolinoException
from calibre.library import db

def upload_cover(db, c, book, doc_id):
    global cover_cnt
    global failed_cover_cnt
    # Add the cover
    try:
        local_meta = db.get_metadata(book)
        local_path = db.format_abspath(book, "epub")

        cover_path = db.cover(book, as_path=True)
        c.add_cover(doc_id, cover_path)
        cover_cnt += 1
    except TolinoException:
        # The file is probably too large, not sure what to do about that
        logger.warning("Error uploading cover for %s"%local_meta.title)
        failed_cover_cnt += 1

def update_meta(db, c, book, doc_id):
    global meta_cnt
    global failed_meta_cnt
    try:
        local_meta = db.get_metadata(book)

        c.metadata(doc_id, title=local_meta.title, author=', '.join(local_meta.authors), publisher=local_meta.publisher,
            isbn=local_meta.identifiers['isbn'] if 'isbn' in local_meta.identifiers else None, issued=local_meta.pubdate,
            language=local_meta.languages[0] if len(local_meta.languages)>0 else None)
        meta_cnt += 1
    except TolinoException:
        logger.warning("Error updating meta for %s"%local_meta.title)
        failed_meta_cnt += 1

def update_collections(db, c, book, doc_id):
    global collection_cnt
    global failed_collection_cnt
    try:
        local_meta = db.get_metadata(book)
        if local_meta.series != None:
            c.add_to_collection(doc_id, local_meta.series)
            collection_cnt += 1
    except TolinoException:
        logger.warning("Error updating collections for %s"%local_meta.title)
        failed_collection_cnt += 1

def upload_book(db, c, book):
    global book_cnt
    global failed_book_cnt
    try:
        local_meta = db.get_metadata(book)
        local_path = db.format_abspath(book, "epub")

        doc_id = c.upload(local_path, local_meta.title + ".epub")
        logger.info("Uploaded %s by %s as %s" %(local_meta.title, local_meta.authors, doc_id))
        book_cnt += 1
        # Instantly persist, in case something goes horribly wrong or we get Ctrl-C-ed
        upload_cover(db, c, book, doc_id)
        update_meta(db, c, book, doc_id)
        update_collections(db, c, book, doc_id)
    except TolinoException:
        logger.error("Error uploading book for %s"%local_meta.title)
        failed_book_cnt += 1


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
parser.add_argument('--dbpath', metavar='FILE', help='path of calibre database')
parser.add_argument('--libpath', metavar='FILE', help='path of system python dist-packages')
parser.add_argument('--use-device', action="store_true", help='use existing device credentials instead of signing in')
parser.add_argument('--debug', action="store_true", help='log additional debugging info')
parser.add_argument('--force-covers', action="store_true", help='forcibly update covers for existing books')
parser.add_argument('--force-meta', action="store_true", help='forcibly update meta for existing books')
parser.add_argument('--force-collections', action="store_true", help='forcibly update collections for existing books')

args = parser.parse_args(remaining_argv)

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Initialise DB and counters
db = db(args.dbpath).new_api
book_cnt = 0
cover_cnt = 0
meta_cnt = 0
collection_cnt = 0
failed_book_cnt = 0
failed_cover_cnt = 0
failed_meta_cnt = 0
failed_collection_cnt = 0
no_epub_cnt = 0
ignored_cnt = 0

# Gather books from Calibre
local = db.search('')

# Connect and gather list of books online - mainly to ensure IDs from cache file
# are still valid, otherwise re-upload
c = TolinoCloud(args.partner, args.use_device, args.libpath)
c.login(args.user, args.password)
c.register()
remote = c.inventory()

for book in local:
    local_meta = db.get_metadata(book)
    local_path = db.format_abspath(book, "epub")
    matches = [remote_book for remote_book in remote if local_meta.title == remote_book['title']]
    # Check if uploaded already
    if len(matches) == 0:
        if local_path != None:
            # New book!
            upload_book(db, c, book)
        else:
            # We're only uploading epubs, just tell the user to convert in Calibre
            logger.warning("Warning: %s has no epub format"%local_meta.title)
            no_epub_cnt += 1
    else:
        doc_id = matches[0]['id']
        logger.info("Not uploading %s by %s, already found"%(local_meta.title, local_meta.authors))
        ignored_cnt += 1
        if args.force_covers:
            logger.info("Forcibly updating cover for %s by %s"%(local_meta.title, local_meta.authors))
            upload_cover(db, c, book, doc_id)
        if args.force_meta:
            logger.info("Forcibly updating meta for %s by %s"%(local_meta.title, local_meta.authors))
            update_meta(db, c, book, doc_id)
        if args.force_collections:
            logger.info("Forcibly updating collections for %s by %s"%(local_meta.title, local_meta.authors))
            update_collections(db, c, book, doc_id)


c.unregister()
c.logout()

# Print stats
logger.info("Uploaded %d new books, %d new covers, %d sets of metadata, and %d collection tags."%(book_cnt, cover_cnt, meta_cnt, collection_cnt))
logger.info("Failed to upload %d books, %d covers, %d sets of metadata, and %d collection tags."%(failed_book_cnt, failed_cover_cnt, failed_meta_cnt, failed_collection_cnt))
logger.info("Ignored %d already uploaded books, and %d books with no epub format."%(ignored_cnt, no_epub_cnt))
