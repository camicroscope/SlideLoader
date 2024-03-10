FROM camicroscope/image-decoders:latest

WORKDIR /var/www
RUN apt-get update
RUN apt-get -q update --fix-missing
RUN apt-get -q install -y python3-pip openslide-tools python3-openslide vim openssl
RUN apt-get -q install -y openssl libcurl4-openssl-dev libssl-dev
RUN apt-get -q install -y libvips libvips-dev

### Install BioFormats wrapper

WORKDIR /root/src/BFBridge/python
RUN pip install -r requirements.txt --break-system-packages
RUN python3 compile_bfbridge.py

### Set up the server

WORKDIR /root/src/

RUN pip install pyvips --break-system-packages
RUN pip install flask --break-system-packages
RUN pip install gunicorn --break-system-packages
RUN pip install greenlet --break-system-packages
RUN pip install gunicorn[eventlet] --break-system-package

run openssl version -a

ENV FLASK_DEBUG True
ENV BFBRIDGE_LOGLEVEL=WARN

RUN mkdir -p /images/uploading

COPY openslide_copy.sh .
RUN bash openslide_copy.sh

COPY requirements.txt .
RUN pip3 install -r requirements.txt --break-system-packages

COPY ./ ./
RUN cp test_imgs/* /images/

EXPOSE 4000
EXPOSE 4001

#debug/dev only
# ENV FLASK_APP SlideServer.py
# CMD python3 -m flask run --host=0.0.0.0 --port=4000

# The Below BROKE the ability for users to upload images.
# # non-root user
# RUN chgrp -R 0 /var && \
#     chmod -R g+rwX /var && \
#     chgrp -R 0 /images/uploading && \
#     chmod -R g+rwX /images/uploading
#
# USER 1001

#prod only
CMD gunicorn -w 4 -b 0.0.0.0:4000 SlideServer:app --timeout 400
