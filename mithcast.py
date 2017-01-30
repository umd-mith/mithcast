#!/usr/bin/env python

S3_BUCKET = "digital-dialogues"
S3_BUCKET_URL = "http://digital-dialogues.s3-website-us-east-1.amazonaws.com/"

import os
import re
import glob
import boto3
import codecs
import jinja2
import requests
import feedparser
import youtube_dl

def main():
    feed_url = "http://mith.umd.edu/digital-dialogues/dialogues/feed/"
    feed = feedparser.parse(feed_url)
    add_enclosures(feed)
    write_podcast(feed, "bucket/podcast.xml")
    publish()

def write_podcast(feed, filename):
    tmpl = jinja2.Template(codecs.open("feed.j2", "r", "utf8").read())
    xml = tmpl.render(entries=feed.entries, feed_url=S3_BUCKET_URL + "podcast.xml") 
    codecs.open(filename, "w", "utf8").write(xml)

def add_enclosures(feed):
    """
    This does most of the work. It walks through the entries in the feed
    and looks to see if an mp3 has been uploaded to Amazon. If it hasn't
    then it downloads the video from Vimeo, and extracts the audio.
    """
 
    for entry in feed.entries:

        vimeo_url = get_vimeo_url(entry.link)
        if not vimeo_url:
            continue
        
        mp3_file = "%s.mp3" % os.path.basename(vimeo_url) 
        mp3_obj = get_object(mp3_file)

        if mp3_obj:
            entry.enclosure_length = mp3_obj.content_length
        else:
            mp3_path = download_mp3(vimeo_url)
            entry.enclosure_length = os.path.getsize(mp3_path)

        entry.enclosure_url = S3_BUCKET_URL + mp3_file

def get_vimeo_url(url):
    html = requests.get(url).content
    m = re.search('https://vimeo.com/\d+', html)
    if not m:
        return None
    return m.group(0)

def download_mp3(vimeo_url):
    video_id = os.path.basename(vimeo_url)
    opts = {
        #'quiet': True,
        'outtmpl': 'bucket/%(id)s.%(ext)s',
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }
    ydl = youtube_dl.YoutubeDL(opts)
    ydl.download([vimeo_url])
    return "bucket/%s.mp3" % video_id

def publish():
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET)
    published = published_files()

    # always update the feed
    bucket.upload_file('bucket/podcast.xml', 'podcast.xml',
                       ExtraArgs={'ContentType': 'application/rss+xml'})

    # only upload files that aren't already there
    for mp3 in os.listdir("bucket"):
        mp3_obj = get_object(mp3)
        if not mp3_obj:
            key = bucket.upload_file(path, mp3, 
                                     ExtraArgs={"ContentType": "audio/mpeg"})

def published_files():
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET)
    return set([key.key for key in bucket.objects.all()])

def get_object(key):
    s3 = boto3.resource('s3')
    o = None
    try:
        o = s3.Object(S3_BUCKET, key)
    except:
        pass
    return o

if __name__ == "__main__":
    main()
