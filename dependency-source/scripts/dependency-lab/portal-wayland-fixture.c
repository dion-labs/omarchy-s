/* Original DionLabs test fixture. Registry only: never supplies capture frames. */
#include <wayland-server.h>
#include <stdio.h>
#include "capture.h"
#include "source.h"

static int reject(const void *impl, void *target, uint32_t opcode,
                  const struct wl_message *message, union wl_argument *args) {
    (void)impl; (void)opcode; (void)message; (void)args;
    wl_resource_post_error(target, 0, "registry-only test fixture: capture unsupported");
    return 0;
}
static void bind_global(struct wl_client *client, void *data, uint32_t version, uint32_t id) {
    const struct wl_interface *interface = data;
    struct wl_resource *resource = wl_resource_create(client, interface, version, id);
    if (!resource) { wl_client_post_no_memory(client); return; }
    wl_resource_set_dispatcher(resource, reject, NULL, NULL, NULL);
}
int main(void) {
    struct wl_display *display = wl_display_create();
    if (!display || wl_display_init_shm(display) < 0) return 1;
    if (!wl_global_create(display, &ext_image_copy_capture_manager_v1_interface, 1,
                          (void *)&ext_image_copy_capture_manager_v1_interface, bind_global) ||
        !wl_global_create(display, &ext_output_image_capture_source_manager_v1_interface, 1,
                          (void *)&ext_output_image_capture_source_manager_v1_interface, bind_global)) return 2;
    if (wl_display_add_socket(display, "wayland-lab") < 0) return 3;
    wl_display_run(display);
    wl_display_destroy(display);
    return 0;
}
