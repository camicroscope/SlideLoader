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

#debug/dev only
# ENV FLASK_APP SlideServer.py
# CMD python -m flask run --host=0.0.0.0 --port=4000

#prod only
CMD gunicorn -w 4 -b 0.0.0.0:4000 SlideServer:app --timeout 400
