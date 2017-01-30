This utility adds an audio enclosure to [MITH's Digital Dialogue RSS feed] by
extracting the audio from the Vimeo video and putting it up on Amazon S3. It is
able to keep track of videos it has already converted and is designed to be run
on a schedule from cron.

First make sure AWS_SECRET_ACCESS_KEY and AWS_ACCESS_KEY_ID are set in your
environment.

    git clone https://github.com/docnow/mithcast 
    cd mithcast
    pipenv install
    ./mithcast.py

A log will be written about its activity. You should be able to see the end
result at: 

    http://digital-dialogues.s3-website-us-east-1.amazonaws.com/podcast.xml

[MITH's Digital Dialogue RSS feed]: http://mith.umd.edu/digital-dialogues/dialogues/feed/

