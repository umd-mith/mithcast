This utility adds an audio enclosure to MITH's existing [Digital Dialogue RSS
feed] by extracting the audio from the Vimeo video and putting it up on Amazon
S3 along with a new RSS file that is optimized for podcast playing. It is able
to keep track of videos it has already converted and is designed to be run on a
schedule from cron.

If the audio from our Vimeo videos was URL addressable it would be more feasible
to manage this in Wordpress. But I couldn't seem to find away to get audio out
of Vimeo, and didn't want to make our production workflow for Digital Dialogues
any more involved. 

## Run

First make sure AWS_SECRET_ACCESS_KEY and AWS_ACCESS_KEY_ID are set in your
environment.

    git clone https://github.com/umd-mith/mithcast 
    cd mithcast
    pipenv install
    ./mithcast.py

A log will be written about its activity. You should be able to see the end
result at: 

    http://digital-dialogues.s3-website-us-east-1.amazonaws.com/podcast.xml

[Digital Dialogue RSS feed]: http://mith.umd.edu/digital-dialogues/dialogues/feed/

