#!/usr/bin/env python3
import logging
import json
import configparser

from tolinocloud import TolinoCloud
from calibre.library import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Load config
confparse = configparser.ConfigParser()
confparse.read(['.tolinoclientrc'])
conf = dict(confparse.items('Defaults'))

# Initialise DB and counters
db = db(conf['dbpath']).new_api
book_cnt = 0
cover_cnt = 0
failed_book_cnt = 0
failed_cover_cnt = 0
no_epub_cnt = 0
ignored_cnt = 0

# Load list of already uploaded books - can't compare metadata as title in Tolino comes from epub
# and may disagree with data in Calibre, causing repeated uploads
with open(conf['idfilepath'], 'r') as doc_id_file:
    doc_ids = json.load(doc_id_file)

# Gather books from Calibre
local = db.search('')

# Connect and gather list of books online - mainly to ensure IDs from cache file
# are still valid, otherwise re-upload
c = TolinoCloud(int(conf['partner']))
c.login(conf['user'], conf['password'])
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
            try:
                doc_id = c.upload(local_path, local_meta.title + ".epub")
                logger.info("Uploaded %s by %s as %s" %(local_meta.title, local_meta.authors, doc_id))
                doc_ids[local_meta.title] = doc_id
                book_cnt += 1
                # Instantly persist, in case something goes horribly wrong or we get Ctrl-C-ed
                with open('doc_ids.json', 'w') as doc_id_file:
                    json.dump(doc_ids, doc_id_file)
                try:
                    # Add the cover
                    cover_path = db.cover(book, as_path=True)
                    c.add_cover(cover_path, doc_ids[local_meta.title])
                    cover_cnt += 1
                except TolinoException:
                    # The file is probably too large, not sure what to do about that
                    logger.warning("Error uploading cover for %s"%local_meta.title)
                    failed_cover_cnt += 1
            except TolinoException:
                logger.error("Error uploading book for %s"%local_meta.title)
                failed_book_cnt += 1
        else:
            logger.info("Not uploading %s by %s, already found"%(local_meta.title, local_meta.authors))
            ignored_cnt += 1
    elif local_path != None:
        # New book!
        try:
            doc_id = c.upload(local_path, local_meta.title + ".epub")
            logger.info("Uploaded %s by %s as %s" %(local_meta.title, local_meta.authors, doc_id))
            doc_ids[local_meta.title] = doc_id
            book_cnt += 1
            # Instantly persist, in case something goes horribly wrong or we get Ctrl-C-ed
            with open('doc_ids.json', 'w') as doc_id_file:
                json.dump(doc_ids, doc_id_file)
            try:
                # Add the cover
                cover_path = db.cover(book, as_path=True)
                c.add_cover(cover_path, doc_ids[local_meta.title])
                cover_cnt += 1
            except TolinoException:
                # The file is probably too large, not sure what to do about that
                logger.warning("Error uploading cover for %s"%local_meta.title)
                failed_cover_cnt += 1
        except TolinoException:
            logger.error("Error uploading book for %s"%local_meta.title)
            failed_book_cnt += 1
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