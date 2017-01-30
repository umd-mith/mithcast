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
    and looks to see if an mp3 has been uploaded to Amazon. If it hasn't
    then it downloads the video from Vimeo, and extracts the audio, and 
    uploads it to S3. Each entry in the feed object that is passed in is 
    annotated with the enclosure_url and enclosure_length that is needed
    to write out the podcast.
    """

    new_entries = []
    for entry in feed.entries:

        vimeo_url = get_vimeo_url(entry.link)
        if not vimeo_url:
            continue

        logging.info("found video %s", vimeo_url)
        mp3_file = "%s.mp3" % os.path.basename(vimeo_url) 
        mp3_obj = get_object(mp3_file)

        if mp3_obj:
            entry.enclosure_length = mp3_obj.content_length
        else:
            mp3_path = download_mp3(vimeo_url)
            mp3_file = os.path.basename(mp3_path)
            bucket = s3.Bucket(S3_BUCKET)
            key = bucket.upload_file(mp3_path, mp3_file, 
                                     ExtraArgs={"ContentType": "audio/mpeg"})
            entry.enclosure_length = os.path.getsize(mp3_path)

        entry.enclosure_url = S3_BUCKET_URL + mp3_file
        new_entries.append(entry)

        break

    feed.entries = new_entries

def get_vimeo_url(url):
    """
    Scrapes the Vimeo URL out of the detail page for a Digital Dialogue event.
    """
    html = requests.get(url).content
    m = re.search('https://vimeo.com/\d+', html)
    if not m:
        return None
    return m.group(0)

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
    return "tmp/%s.mp3" % video_id

def publish(feed):
    """
    Publishes the feed.
    """
    tmpl = jinja2.Template(codecs.open("podcast.j2", "r", "utf8").read())
    xml = tmpl.render(entries=feed.entries, feed_url=S3_BUCKET_URL + "podcast.xml") 
    codecs.open("tmp/podcast.xml", "w", "utf8").write(xml)

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET)
    bucket.upload_file('tmp/podcast.xml', 'podcast.xml',
                       ExtraArgs={'ContentType': 'application/rss+xml'})

def get_object(key):
    s3 = boto3.resource('s3')
    try:
        o = s3.Object(bucket_name=S3_BUCKET, key=key)
        o.content_length
    except Exception as e:
        o = None
    return o

if __name__ == "__main__":
    logging.basicConfig(
        filename="mithcast.log", 
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO)
    logging.info("started")
    main()
