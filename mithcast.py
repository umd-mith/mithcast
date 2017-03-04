#!/usr/bin/env python

S3_BUCKET = "digital-dialogues"
S3_BUCKET_URL = "http://digital-dialogues.s3-website-us-east-1.amazonaws.com/"

import os
import re
import glob
import boto3
import codecs
import jinja2
import logging
import datetime
import requests
import feedparser
import youtube_dl

def main():
    feed_url = "http://mith.umd.edu/digital-dialogues/dialogues/feed/"
    feed = feedparser.parse(feed_url)
    add_enclosures(feed)
    publish(feed)

def add_enclosures(feed):
    """
    This does most of the work. It walks through the entries in the feed
    and looks to see if an mp3 has been uploaded to Amazon S3. If it hasn't
    then it downloads the video from Vimeo, and extracts the audio, and 
    uploads it to S3. Each entry in the feed object that is passed in is 
    annotated with the title, enclosure_url and enclosure_length that is 
    needed to write out the podcast.
    """

    new_entries = []
    for entry in feed.entries:

        dd = DigitalDialogue(entry.link)
        if not dd.vimeo_url:
            continue

        logging.info("found video %s", dd.vimeo_url)
        entry.title = dd.title
        mp3_file = "%s.mp3" % os.path.basename(dd.vimeo_url) 
        mp3_obj = get_object(mp3_file)

        if mp3_obj:
            entry.enclosure_length = mp3_obj.content_length
        else:
            tries = 0
            while tries < 5:
                tries += 1
                try:
                    mp3_path = download_mp3(dd.vimeo_url)
                    break
                except youtube_dl.utils.DownloadError as e:
                    logging.error(e)
                    logging.info("trying again %s", tries)
            mp3_file = os.path.basename(mp3_path)
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(S3_BUCKET)
            key = bucket.upload_file(mp3_path, mp3_file, 
                                     ExtraArgs={"ContentType": "audio/mpeg"})
            entry.enclosure_length = os.path.getsize(mp3_path)

        entry.enclosure_url = S3_BUCKET_URL + mp3_file
        new_entries.append(entry)

    feed.entries = new_entries

def download_mp3(vimeo_url):
    """
    Uses the magic of youtub-dl to download the Vimeo URL and extract the mp3.
    """
    logging.info("downloading %s", vimeo_url)
    video_id = os.path.basename(vimeo_url)
    opts = {
        'quiet': True,
        'no_warnings': True,
        'outtmpl': u"tmp/%(id)s.%(ext)s",
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }
    ydl = youtube_dl.YoutubeDL(opts)
    ydl.download([vimeo_url])
    mp3_file = "tmp/%s.mp3" % video_id
    logging.info("got mp3 %s", mp3_file)
    return mp3_file

def publish(feed):
    """
    Publishes the feed.
    """
    tmpl = jinja2.Template(codecs.open("podcast.j2", "r", "utf8").read())
    now = datetime.datetime.utcnow()
    xml = tmpl.render(
        pub_date=now.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        entries=feed.entries,
        feed_url=S3_BUCKET_URL + "podcast.xml"
    ) 
    codecs.open("tmp/podcast.xml", "w", "utf8").write(xml)

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET)
    bucket.upload_file('tmp/podcast.xml', 'podcast.xml',
                       ExtraArgs={'ContentType': 'application/rss+xml'})
    logging.info("published podcast.xml")
    for path in glob.glob("tmp/*"):
        os.remove(path)

def get_object(key):
    s3 = boto3.resource('s3')
    try:
        o = s3.Object(bucket_name=S3_BUCKET, key=key)
        o.content_length
    except Exception as e:
        o = None
    return o

class DigitalDialogue():
    def __init__(self, url):
        self.url = url
        self.title = None
        self.vimeo_url = None

        html = requests.get(url).text
        m = re.search('https://vimeo.com/\d+', html)
        if m:
            self.vimeo_url = m.group(0)

        m = re.search('<h1 class="entry-title">(.+?)</h1>', html)
        if m:
            self.title = m.group(1)


if __name__ == "__main__":
    logging.basicConfig(
        filename="mithcast.log", 
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO)
    logging.info("started")
    main()
