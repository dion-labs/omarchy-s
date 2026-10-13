FROM ubuntu@sha256:a853f94d226358a79c740cfc7bce0c289748f3fe3488d921d038ccd752c61b60
ENV DEBIAN_FRONTEND=noninteractive
COPY packages /packages
RUN apt-get --allow-downgrades -y install /packages/*.deb && python3 -m venv --system-site-packages /opt/meson && /opt/meson/bin/pip install --no-index /packages/meson-1.7.2-py3-none-any.whl && tar -xJf /packages/wayland-protocols-1.49-1-any.pkg.tar.xz -C / usr/share/wayland-protocols usr/share/pkgconfig/wayland-protocols.pc && rm -rf /packages
ENV PATH=/opt/meson/bin:$PATH
WORKDIR /work
