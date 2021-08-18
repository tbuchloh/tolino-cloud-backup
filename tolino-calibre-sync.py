#!/usr/bin/env python3
import logging
import json
import configparser
import argparse

from tolinocloud import TolinoCloud, TolinoException
from calibre.library import db

def upload_cover(db, c, book, doc_ids):
    global cover_cnt
    global failed_cover_cnt
    # Add the cover
    try:
        local_meta = db.get_metadata(book)
        local_path = db.format_abspath(book, "epub")

        cover_path = db.cover(book, as_path=True)
        c.add_cover(cover_path, doc_ids[local_meta.title])
        cover_cnt += 1
    except TolinoException:
        # The file is probably too large, not sure what to do about that
        logger.warning("Error uploading cover for %s"%local_meta.title)
        failed_cover_cnt += 1

def upload_book(db, c, book):
    global book_cnt
    global failed_book_cnt
    global doc_ids
    try:
        local_meta = db.get_metadata(book)
        local_path = db.format_abspath(book, "epub")

        doc_id = c.upload(local_path, local_meta.title + ".epub")
        logger.info("Uploaded %s by %s as %s" %(local_meta.title, local_meta.authors, doc_id))
        doc_ids[local_meta.title] = doc_id
        book_cnt += 1
        # Instantly persist, in case something goes horribly wrong or we get Ctrl-C-ed
        with open('doc_ids.json', 'w') as doc_id_file:
            json.dump(doc_ids, doc_id_file)
        upload_cover(db, c, book, doc_ids)
    except TolinoException:
        logger.error("Error uploading book for %s"%local_meta.title)
        failed_book_cnt += 1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

parser = argparse.ArgumentParser(
    description='cmd line client to access personal tolino cloud storage space.'
)
parser.add_argument('--config', metavar='FILE', default='.tolinoclientrc', help='config file (default: .tolinoclientrc)')
args, remaining_argv = parser.parse_known_args()

# Load config
confparse = configparser.ConfigParser()
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
parser.add_argument('--idfilepath', metavar='FILE', help='path of bosh ID cache')
parser.add_argument('--debug', action="store_true", help='log additional debugging info')
parser.add_argument('--force-covers', action="store_true", help='forcibly update covers for existing books')

args = parser.parse_args(remaining_argv)

# Initialise DB and counters
db = db(args.dbpath).new_api
book_cnt = 0
cover_cnt = 0
failed_book_cnt = 0
failed_cover_cnt = 0
no_epub_cnt = 0
ignored_cnt = 0

# Load list of already uploaded books - can't compare metadata as title in Tolino comes from epub
# and may disagree with data in Calibre, causing repeated uploads
with open(args.idfilepath, 'r') as doc_id_file:
    doc_ids = json.load(doc_id_file)

# Gather books from Calibre
local = db.search('')

# Connect and gather list of books online - mainly to ensure IDs from cache file
# are still valid, otherwise re-upload
c = TolinoCloud(args.partner)
c.login(args.user, args.password)
c.register()
remote = c.inventory()

for book in local:
    local_meta = db.get_metadata(book)
    local_path = db.format_abspath(book, "epub")
    #matches = [remote_book for remote_book in remote if local_meta.title == remote_book['title'] and local_meta.authors == remote_book['author']]
    if local_meta.title in doc_ids:
        # Check if uploaded already
        cached_doc_id = doc_ids[local_meta.title]
        matches = [remote_book for remote_book in remote if remote_book['id'] == cached_doc_id]
        if len(matches) == 0 and local_path != None:
            # Book vanished from cloud, upload again
            upload_book(db, c, book)
        else:
            logger.info("Not uploading %s by %s, already found"%(local_meta.title, local_meta.authors))
            ignored_cnt += 1
            if args.force_covers:
                logger.info("Forcibly updating cover for %s by %s"%(local_meta.title, local_meta.authors))
                upload_cover(db, c, book, doc_ids)

    elif len([remote_book for remote_book in remote if local_meta.title == remote_book['title'] and local_meta.authors == remote_book['author']]) > 0:
        logger.info("Not uploading %s by %s, found exact match, but not in cache - presumably bought via tolino"%(local_meta.title, local_meta.authors))
        ignored_cnt += 1
    elif local_path != None:
        # New book!
        upload_book(db, c, book)
    else:
        # We're only uploading epubs, just tell the user to convert in Calibre
        logger.warning("Warning: %s has no epub format"%local_meta.title)
        no_epub_cnt += 1

c.unregister()
c.logout()

# Print stats
logger.info("Uploaded %d new books, and %d new covers."%(book_cnt, cover_cnt))
logger.info("Failed to upload %d books, and %d covers."%(failed_book_cnt, failed_cover_cnt))
logger.info("Ignored %d already uploaded books, and %d books with no epub format."%(ignored_cnt, no_epub_cnt))