import requests
import re
import logging
import traceback
import hashlib
import os
import sys
from bs4 import BeautifulSoup as bs
from entities import Artist, Track, Stream
from config import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from requests.exceptions import Timeout, ConnectionError, TooManyRedirects
from exceptions import Non200StatusCode

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

def fatal(message):
    print("Error: %s" %(message))
    # Exit application with error code 1
    sys.exit(1)

def download(url, timeout = 9):
    # Pose as a Mozilla Firefox agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
    }
    try:
        response = requests.get(url, headers = headers, timeout = timeout)
    except (Timeout, ConnectionError, TooManyRedirects) as err :
        fatal(str(err))

    if response.status_code != 200:
        raise Non200StatusCode(response.status_code, "Response has a status code that is not 200, response code: %d" %(response.status_code))
    return response


def find_artists(soup):
    res = soup.find_all("div", class_="info-table")
    if res != []:
        for artist in res:
            artist_image_download_url = "{base_url}/{relative_path}".format(base_url = BASE_URL, relative_path=artist.find("div", class_="thumb").img['src'].strip("/"))
            artist_info = artist.find("div", class_="info_cat")
            artist_name = artist_info.a.h2.text.strip()
            # Find the Anasheed Id from the target of the link
            artist_anasheed_id = int(re.search(r'.*/(\d+)/.*', artist_info.a['href']).group(1))
            # Retrieve the image extension
            artist_image_ext = re.search(r'^.*\.([a-zA-Z0-9]+)$', artist_image_download_url).group(1)
            # Download the artist's image, the filename used is a hexadecimal sha256 digest of  the artist's name
            artist_image = save_file(artist_image_download_url, '%s.%s' %(hashlib.sha256(artist_name.encode('utf-8')).hexdigest(), artist_image_ext))

            artist_object = Artist(name = artist_name, anasheed_id = artist_anasheed_id, image = artist_image)
            yield artist_object
    else:
        yield None

def save(filepath, content):
    """ Saves content to the hard disk """
    with open(filepath,  "wb") as f:
        for data in content.iter_content(1024):
            f.write(data)

def save_file(source, filename, type="a"):
    # Save the downloaded data to the disk
    if type == "a":
        # It is an artist, save the image in the ARTISTS_IMAGES_BASEDIR
        filepath = "{base_dir}/{filename}".format(base_dir=ARTISTS_IMAGES_BASE_DIR, filename = filename)
    elif type == "t":
        # This is a track, save the track to TRACKS_BASEDIR
        filepath = "{base_dir}/{filename}".format(base_dir=TRACKS_BASE_DIR, filename = filename)
    else:
        raise Exception("Unknown type: %s" %(type))

    if not os.path.exists(filepath):
        # Prevent overwrite and redownload if file was already saved to disk
        response = download(source)
        # Write file to disk
        save(filepath, response)

    return filename

def find_tracks(soup, artist_id):
    playlist = soup.find("ul", attrs={"id": "playlist"}).find_all("li")
    if playlist != []:
        for track in playlist:
            track_link = track.find("a", attrs={"class": "loadit"})
            track_name = track_link.h2.text
            track_anasheed_id = int(str(re.search(".*/(\d+)/.*", track_link['href']).group(1)))
            track_filename = "%s.mp3" %(track_name.lower().replace(" ", "_"))

            track_object = Track(name = track_name, artist_id = artist_id, anasheed_id = track_anasheed_id, filename = track_filename)
            yield track_object
    else:
        yield None


def create_slug(s):
    # Slugs used on anasheed.info are simplistic, Only replace spaces with '-'
    return s.replace(" ", "-")


def main():
    artists_source = "{base_url}/singers".format(base_url=BASE_URL)
    # Fetch the artists page
    response = download(artists_source);
    soup = bs(response.text, "html.parser")

    print("Getting artists...")
    artists = find_artists(soup)
    for artist in artists:
        # write artist to database
        artist_id = artist.save(session)
        artist_name_slug = create_slug(artist.name)
        response = download(ARTIST_DETAIL_TEMPLATE_URL.format(anasheed_id = artist.anasheed_id, artist_name_slug = artist_name_slug))
        soup = bs(response.text, "html.parser")
        print("Getting tracks for: {}...".format(artist.name))
        # Find tracks for this artist
        tracks = find_tracks(soup, artist_id)
        for track in tracks:
            # Download the track before saving track to database to ensure integrity
            print("Downloading track: {track_name}...".format(track_name = track.name))
            try:
                # if any exception is emitted, while downloading a track, continue to the next track
                save_file(TRACK_DOWNLOAD_TEMPLATE_URL.format(anasheed_id = track.anasheed_id), track.filename, type="t")
            except Non200StatusCode:
                continue
            track_id = track.save(session)
            # stream_reference = sha256(<track_name> + <TRACK_REFERENCE_SALT>).hexdigest()
            # Create a reference that will be used when during streaming instead of the real filename
            to_be_hashed = "%s%s" %(track.name, TRACK_REFERENCE_SALT)
            track_stream_reference = hashlib.sha256(to_be_hashed.encode('utf-8')).hexdigest()
            # Save the stream reference to the database
            stream = Stream(reference = track_stream_reference, track_id = track_id)
            stream.save(session)
            
if __name__ == "__main__":
    try:
        main()
    except:
        session.close()
        logging.error(traceback.format_exc())
