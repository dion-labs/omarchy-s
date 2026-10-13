FROM scratch
ADD rootfs.tar /
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/bin
ENV LANG=C.UTF-8
RUN /usr/bin/ldconfig
WORKDIR /build
