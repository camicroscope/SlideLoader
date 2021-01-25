FROM python:3-stretch

WORKDIR /var/www
RUN apt-get update
RUN apt-get -q update --fix-missing
RUN apt-get -q install -y openslide-tools python-openslide vim
RUN apt-get -q install -y libvips libvips-dev

RUN pip install pyvips
RUN pip install flask
RUN pip install gunicorn
RUN pip install greenlet
RUN pip install gunicorn[eventlet]

ENV FLASK_ENV development

RUN mkdir -p /images/uploading

COPY ./ ./

RUN cp test_imgs/* /images/

RUN pip3 install -r requirements.txt


EXPOSE 4000
EXPOSE 4001

#debug/dev only
# ENV FLASK_APP SlideServer.py
# CMD python -m flask run --host=0.0.0.0 --port=4000

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
