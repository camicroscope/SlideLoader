FROM camicroscope/image-decoders:latest

WORKDIR /var/www
RUN apt-get update
RUN apt-get -q update --fix-missing
RUN apt-get -q install -y python3-pip openslide-tools python3-openslide vim openssl
RUN apt-get -q install -y openssl libcurl4-openssl-dev libssl-dev

# Tony has a future use case where we may adapt caMic to GIS visualization
# install libvips-dev for pyvips. No need for libvips.
RUN apt-get -q install -y libvips-dev

# But, build libvips instead of using libvips-dev from apt
# Build without OpenSlide to open images with rather ImageMagick to handle
# images without pyramids. Otherwise opens e.g. DICOM with OpenSlide so conversion
# of files OpenSlide cannot open does not help at all.
# So, we'll have two copies on openslide on the system.
# By changing LD_LIBRARY_PATH before we launch python
# we can choose which openslide to run
# TODO: use libjpeg-turbo8-dev instead of libjpeg-dev if current apt repo has it; for performance
RUN apt-get -q install -y meson libjpeg-turbo8-dev libexif-dev libgsf-1-dev libtiff-dev libfftw3-dev liblcms2-dev libpng-dev libmagickcore-dev libmagickwand-dev liborc-0.4-dev libopenjp2-7 libgirepository1.0-dev
WORKDIR /root/src
RUN git clone https://github.com/libvips/libvips.git --depth=1 --branch=8.14
RUN mkdir /root/src/libvips/build
WORKDIR /root/src/libvips
RUN mkdir /usr/local/vips-no-openslide/
# normally --prefix=/usr/local/ --libdir=lib build
RUN meson setup -Dopenslide=disabled --buildtype=release --prefix=/usr/local/vips-no-openslide/ --libdir=lib build
RUN meson compile -C build
RUN meson test -C build
RUN meson install -C build

RUN pip install pyvips --break-system-packages

# verify pyvips can call libvips
RUN python3 -c "import pyvips"

# verify that the apt libvips has openslide
ADD test_imgs/CMU-1-Small-Region.svs .
RUN python3 -c "import pyvips; pyvips.Image.openslideload(('CMU-1-Small-Region.svs'))"

# back up previous ld_library_path
ENV LD_LIBRARY_PATH_ORIG="${LD_LIBRARY_PATH}"

# now, prioritize openslideless libvips
# the path shown in output lines of "meson install" where .so.42 are installed
# normally /usr/local/lib/:
ENV LD_LIBRARY_PATH="/usr/local/vips-no-openslide/lib/:${LD_LIBRARY_PATH}"

# verify that this libvips has no openslide
RUN ! python3 -c "import pyvips; pyvips.Image.openslideload(('CMU-1-Small-Region.svs'))"

# ok, so to recap,
# there are two libvips are installed and which one pyvips connects to
# is chosen when "import pyvips" is run.
# at this point in this dockerfile,
# ld_library_path is set so that no-openslide version is run
# but if you do LD_LIBRARY_PATH="${LD_LIBRARY_PATH_ORIG}" python a.py
# or likewise using docker ENV command or os.environ in python before
# importing, this will remove the no-openslide libvips from path.

WORKDIR /root/src/

RUN pip install flask --break-system-packages
RUN pip install gunicorn --break-system-packages
RUN pip install greenlet --break-system-packages
RUN pip install gunicorn[eventlet] --break-system-package

run openssl version -a

ENV FLASK_DEBUG True

RUN mkdir -p /images/uploading

COPY requirements.txt .
RUN pip3 install -r requirements.txt --break-system-packages

COPY ./ ./
RUN cp test_imgs/* /images/

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
