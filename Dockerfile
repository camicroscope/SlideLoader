FROM python:3-jessie

WORKDIR /var/www

RUN apt-get -q update
RUN apt-get -q install -y openslide-tools python-openslide

RUN pip install flask
RUN pip install gunicorn
RUN pip install greenlet
RUN pip install gunicorn[eventlet]

ENV FLASK_ENV development

run mkdir -p /data/images

COPY ./ ./

RUN cp test_imgs/* /data/images/

RUN pip3 install -r requirements.txt


EXPOSE 4000

#debug/dev only
#ENV FLASK_APP SlideServer.py
#CMD python -m flask run --host=0.0.0.0 --port=4000

CMD gunicorn -w 4 -b 0.0.0.0:4000 SlideServer:app
