Backup your eBooks from tolino cloud with Python 3
==================================================

Forked from https://github.com/darkphoenix/tolino-calibre-sync to add Tolino Cloud backup functionality. Many thanks to darkphoenix.

*Warning*: This is a quick hack to rescue books purchased from Weltbild. Weltbild goes end-of-life at 2024-08-31! See https://www.heise.de/news/Weltbild-Insolvenz-Gekaufte-E-Books-muessen-gesichert-werden-9839051.html for more information. This script is tested on my machine with 3 different Weltbild.de accounts only (Podman and Ubuntu 24.04).

**TolinoCloud** is an inofficial implementation of the tolino cloud
web reader REST API.

**tolino-cloud-backup** is a fork that uses the tolino API to download all book from the tolino cloud - this includes all books in epub and pdf format.

The *tolino ebook reader* is sold by several different partners, most
of them based in Germany, e.g. Thalia, Weltbild or Hugendubel.

The tolino reader comes with its own cloud storage service.

Run by Telekom / T-Systems, the tolino cloud is used to both

- store / backup ebooks purchased by the user

and

- allow the user to upload / sync own files to the user's device(s)

Users can manage their purchased ebooks and uploads through a web
interface, the tolino web reader, which is a HTML5/javascript
application within the user's browser.

Getting started with backing up your library
============================================
Setting this script up currently requires some added preparation, this will
hopefully improve in the future.

A Python 3.9+ installation with the requests module installed is required.

On Windows, installing
Python 3.9+ from the Windows Store is probably the easiest option. requests can be installed using the following command:

```
pip install requests
```

Afterwards, download or git clone this repository to a location of your choice.
Rename tolinoclientrc.example to .tolinoclientrc, then adjust the values in it using any text editor - user and password are your credentials with your tolino reseller, partner is your reseller's ID (see further down this document for a list of IDs).
Set download-dir to a (non-existent) directory where you want to place the downloaded files.

Run the command to backup the books:

```
$ python tolino-cloud-backup.py
INFO:root:Downloading #1 (bosh_3_30738066628338171089): Voelter How to Understand Almost Anything - A Pratitioner's Guide to Domain Analysis (application/epub+zip) to Voelter__How_to_Understand_Almost_Anything_-_A_Pratitioner_s_Guide_to_Domain_Analysis__bosh_3_30738066628338171089.epub ...
INFO:root:Skipping download of target/Voelter__How_to_Understand_Almost_Anything_-_A_Pratitioner_s_Guide_to_Domain_Analysis__bosh_3_30738066628338171089.epub because it does already exist.
INFO:root:Downloading #2 (bosh_3_30738066777058467313): Turner C++ Best Practices (application/epub+zip) to Turner__C___Best_Practices__bosh_3_30738066777058467313.epub ...
INFO:root:Downloading #3 (bosh_3_30738066655747240056): Starke arc42 by Example (application/epub+zip) to Starke__arc42_by_Example__bosh_3_30738066655747240056.epub ...
[...]
INFO:root:Downloaded 155 items to target2. Failures: 14.
WARNING:root:  - bosh_3_3073806677158768188312345: Monadic Java
[...]
WARNING:root:  - bosh_6_1227002670654084262764432: Microsoft Word - Working with Time Series Data in R
```

There might be failures due to missing or corrupt files (I don't know why the cloud did not keep some items safe).

Please take a look at the logging output at the end:

```
INFO:root:Downloaded 155 items to target. Failures: 14.
WARNING:root:  - bosh_3_3073806677158768188312345: Monadic Java
[...]
WARNING:root:  - bosh_6_1227002670654084262764432: Microsoft Word - Working with Time Series Data in R
```

Use OCI/Podman/Docker image
===========================

```
# NOTE: docker works the same
podman build -t tolino-cloud-backup:latest .
# mount the project directory into the container and start the container
podman run --rm -it \
  -v $(pwd):/app:rw \
  tolino-calibre-sync:latest \
  --download-dir downloads
```

You'll find the downloads afterwards in the working directory "downloads" directory.

Command line client to tolino cloud
===================================

**tolinoclient.py** executes the web reader's REST API commands
to allow scripted access to a few very basic commands:

- list ebooks / uploads
- upload a file to the user's personal tolino cloud storage
- download a file from the tolino cloud
- delete an ebook / upload
- list devices connected to an account
- unregister a device from an account
- upload cover images
- update metadata for a book
- add books to collections

Status
======

**It may be buggy. Bad things might happen. You were warned.**

Works with these partners:
- Weltbild.de (10)

Maybe work with these partners:
- Thalia.de (3)
- Thalia.at (4)
- Buch.de (6)
- books.ch / orellfuessli.ch (8)
- Hugendubel.de (13) (currently non-functional)
- Osiander.de (23)
- Buecher.de (30)

(More may be added in the future.)

Tested with Linux. Patches welcome. Handle with care.

Some items may not be downloadable because of "Reason: download request failed: User-Upload for given deliverableId does not exist". These files were not downloadable via web reader interface either, so it's not a scripting issue. I don't know where this comes from (the cloud should keep uploaded data safe ;-)).

Audio books are *NOT* supported! Please download them manually via the browser.

Workaround for auth issues
=====
Currently, some tolino providers are using heavy-handed bot blocking
on their authentication servers.  This will break this script.  As a
workaround, I implemented a method to use existing auth credentials
instead of having the script sign in itself.

To do this,

1. open the web reader, and *before* you sign in
2. open "Inspect element" and go to the network tab.
3. Now sign in as normal
4. then search for the request to a document called "registerhw" or "inventory" (most browsers have a search field at the top of the network panel).
5. Click that request, scroll down to "request headers", and use
the content of "hardware_id" as the user name.
6. Now search for "token", and copy the "refresh_token" from the (JSON) response.
7. Also set `use_device = true` in the configuration, and make sure to use the correct partner ID you used to sign in. Do not sign out in the browser. tolino-cloud-backup will now use
this session to synchronize.

Example `.tolinoclientrc`:

```
[Defaults]
user = 3xxxA-[...]-OPQRh
password = eyJhbGciOiJSUzUxMiJ9[...]in3QA
use_device = true
partner = 10
download-dir = target
```

To-Do
=====

Better error handling.

More REST API calls (e.g. more collection features).

Support for more resellers.

Hey, tolino developers at Telekom / T-Systems, please look at
the comments in tolinocloud.py. It'd be really nice to get the
specifications for the REST API. Thanks!

License
=======

**tolino-cloud-backup** is distributed under the terms of the
[GNU Lesser General Public License 2.1](http://www.gnu.org/licenses/lgpl-2.1.txt).
