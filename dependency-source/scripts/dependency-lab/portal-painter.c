/* Original DionLabs animated shared-memory surface for headless capture tests. */
#define _GNU_SOURCE
#include <wayland-client.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include "xdg-shell.h"
struct paint { struct wl_compositor *compositor; struct wl_shm *shm; struct xdg_wm_base *wm;
    struct wl_surface *surface; int configured; };
static void ping(void *data,struct xdg_wm_base *wm,uint32_t serial) { (void)data; xdg_wm_base_pong(wm,serial); }
static const struct xdg_wm_base_listener wm_listener={.ping=ping};
static void global(void *data,struct wl_registry *registry,uint32_t name,const char *iface,uint32_t version) {
    (void)version;struct paint *p=data;
    if (!strcmp(iface,"wl_compositor")) p->compositor=wl_registry_bind(registry,name,&wl_compositor_interface,1);
    if (!strcmp(iface,"wl_shm")) p->shm=wl_registry_bind(registry,name,&wl_shm_interface,1);
    if (!strcmp(iface,"xdg_wm_base")) {
        p->wm=wl_registry_bind(registry,name,&xdg_wm_base_interface,1);
        xdg_wm_base_add_listener(p->wm,&wm_listener,NULL);
    }
}
static void removed(void *data,struct wl_registry *r,uint32_t name) { (void)data;(void)r;(void)name; }
static const struct wl_registry_listener registry_listener={.global=global,.global_remove=removed};
static void configured(void *data,struct xdg_surface *surface,uint32_t serial) {
    struct paint *p=data;xdg_surface_ack_configure(surface,serial);p->configured=1;
}
static const struct xdg_surface_listener surface_listener={.configure=configured};
static void top_configure(void *data,struct xdg_toplevel *top,int32_t w,int32_t h,struct wl_array *states) {
    (void)data;(void)top;(void)w;(void)h;(void)states;
}
static void close_top(void *data,struct xdg_toplevel *top) { (void)data;(void)top;_exit(0); }
static const struct xdg_toplevel_listener top_listener={.configure=top_configure,.close=close_top};
static void released(void *data,struct wl_buffer *buffer) { (void)buffer;*(int *)data=0; }
static const struct wl_buffer_listener buffer_listener={.release=released};
int main(void) {
    alarm(15);struct paint p={0};struct wl_display *display=wl_display_connect(NULL);if (!display) return 1;
    struct wl_registry *registry=wl_display_get_registry(display);wl_registry_add_listener(registry,&registry_listener,&p);
    wl_display_roundtrip(display);if (!p.compositor||!p.shm||!p.wm) return 2;
    p.surface=wl_compositor_create_surface(p.compositor);struct xdg_surface *xdg=xdg_wm_base_get_xdg_surface(p.wm,p.surface);
    xdg_surface_add_listener(xdg,&surface_listener,&p);struct xdg_toplevel *top=xdg_surface_get_toplevel(xdg);
    xdg_toplevel_add_listener(top,&top_listener,NULL);xdg_toplevel_set_title(top,"Portal capture fixture");
    wl_surface_commit(p.surface);while (!p.configured) if (wl_display_dispatch(display)<0) return 3;
    int fd=memfd_create("portal-painter",MFD_CLOEXEC);size_t bytes=320*240*4;if (fd<0||ftruncate(fd,(off_t)(2*bytes))<0) return 4;
    uint32_t *pixels=mmap(NULL,2*bytes,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);if (pixels==MAP_FAILED) return 5;
    struct wl_shm_pool *pool=wl_shm_create_pool(p.shm,fd,2*bytes);
    struct wl_buffer *buffers[2];int busy[2]={0,0};
    for (unsigned i=0;i<2;i++) {
        buffers[i]=wl_shm_pool_create_buffer(pool,i*bytes,320,240,320*4,WL_SHM_FORMAT_XRGB8888);
        wl_buffer_add_listener(buffers[i],&buffer_listener,&busy[i]);
    }
    for (unsigned frame=0;frame<300;frame++) {
        unsigned slot=frame%2;
        while (busy[slot]) if (wl_display_dispatch(display)<0) return 6;
        for (unsigned i=0;i<320*240;i++) pixels[slot*320*240+i]=(frame%2)?0x00ff0000:0x00000080;
        busy[slot]=1;wl_surface_attach(p.surface,buffers[slot],0,0);
        wl_surface_damage(p.surface,0,0,320,240);wl_surface_commit(p.surface);
        if (wl_display_roundtrip(display)<0) break;
        usleep(40000);
    }
    wl_display_disconnect(display);munmap(pixels,2*bytes);close(fd);return 0;
}
