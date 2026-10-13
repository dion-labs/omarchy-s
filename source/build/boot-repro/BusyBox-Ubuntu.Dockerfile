FROM ubuntu@sha256:a853f94d226358a79c740cfc7bce0c289748f3fe3488d921d038ccd752c61b60
ENV DEBIAN_FRONTEND=noninteractive
COPY packages /packages
RUN apt-get --no-install-recommends --allow-downgrades -y install /packages/*.deb && rm -rf /packages
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
WORKDIR /build
