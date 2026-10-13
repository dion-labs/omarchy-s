/* Private bounded Weston15 input bridge. Only explicitly allowlisted Bluetooth
 * evdev nodes mounted under /trial/input; no key content logging. */
#include <libweston/libweston.h>
#include <linux/input.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <glob.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
#include <time.h>
#include <stdio.h>
#include <limits.h>
void weston_seat_init(struct weston_seat *,struct weston_compositor *,const char *);
void weston_seat_release(struct weston_seat *);
int weston_seat_init_pointer(struct weston_seat *);
int weston_seat_init_keyboard(struct weston_seat *,struct xkb_keymap *);
void notify_key(struct weston_seat *,const struct timespec *,uint32_t,enum wl_keyboard_key_state,enum weston_key_state_update);
void notify_button(struct weston_seat *,const struct timespec *,int32_t,enum wl_pointer_button_state);
void notify_motion(struct weston_seat *,const struct timespec *,struct weston_pointer_motion_event *);
void notify_axis(struct weston_seat *,const struct timespec *,struct weston_pointer_axis_event *);
void notify_axis_source(struct weston_seat *,uint32_t);
void notify_pointer_frame(struct weston_seat *);
static struct weston_seat seat;
static struct wl_listener listener;
struct input {char path[PATH_MAX];int fd;struct wl_event_source *source;int dx,dy;unsigned char down[KEY_CNT];};
static struct input inputs[8];
static unsigned count, recovered;
static struct wl_event_source *retry_timer;
static struct weston_compositor *compositor;
static const char *allowed;
static void report_inputs(void) {
 unsigned active=0;for(unsigned i=0;i<count;i++)if(inputs[i].fd>=0)active++;
 FILE *f=fopen("/trial/input-status.json.tmp","w");
 if(f){fprintf(f,"{\"active_nodes\":%u,\"recovered_opens\":%u}\n",active,recovered);fclose(f);rename("/trial/input-status.json.tmp","/trial/input-status.json");}
}
static void key_event(unsigned code,int value,const struct timespec *t) {
 if(code>=BTN_MOUSE && code<BTN_JOYSTICK)notify_button(&seat,t,code,value?WL_POINTER_BUTTON_STATE_PRESSED:WL_POINTER_BUTTON_STATE_RELEASED);
 else if(code<BTN_MISC)notify_key(&seat,t,code,value?WL_KEYBOARD_KEY_STATE_PRESSED:WL_KEYBOARD_KEY_STATE_RELEASED,STATE_UPDATE_AUTOMATIC);
}
static void close_input(struct input *in) {
 struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
 for(unsigned k=0;k<KEY_CNT;k++)if(in->down[k]){key_event(k,0,&t);in->down[k]=0;}
 in->dx=in->dy=0;
 if(in->source){wl_event_source_remove(in->source);in->source=NULL;}
 if(in->fd>=0){ioctl(in->fd,EVIOCGRAB,0);close(in->fd);in->fd=-1;}
 report_inputs();
}
static int events(int fd,uint32_t mask,void *data) {
 struct input *in=data;struct input_event ev[32];ssize_t n;
 if(mask&(WL_EVENT_HANGUP|WL_EVENT_ERROR)){close_input(in);return 0;}
 while((n=read(fd,ev,sizeof(ev)))>0) {
  if(n%sizeof(ev[0])){close_input(in);return 0;}
  for(unsigned i=0;i<(unsigned)n/sizeof(ev[0]);i++) {
   struct input_event *e=&ev[i];struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
   if(e->type==EV_SYN && e->code==SYN_DROPPED){close_input(in);return 0;}
   if(e->type==EV_KEY && e->code<KEY_CNT && e->value!=2) {in->down[e->code]=!!e->value;key_event(e->code,e->value,&t);}
   if(e->type==EV_REL) {
    if(e->code==REL_X)in->dx+=e->value;
    else if(e->code==REL_Y)in->dy+=e->value;
    else if(e->code==REL_WHEEL || e->code==REL_HWHEEL) {
     struct weston_pointer_axis_event axis={.axis=e->code==REL_WHEEL?WL_POINTER_AXIS_VERTICAL_SCROLL:WL_POINTER_AXIS_HORIZONTAL_SCROLL,.value=-10.0*e->value,.has_discrete=true,.discrete=-e->value};
     notify_axis_source(&seat,WL_POINTER_AXIS_SOURCE_WHEEL);notify_axis(&seat,&t,&axis);
    }
   }
   if(e->type==EV_SYN && e->code==SYN_REPORT) {
    if(in->dx || in->dy) {
     struct weston_pointer_motion_event motion={.mask=WESTON_POINTER_MOTION_REL,.time=t,.rel={.x=in->dx,.y=in->dy}};
     notify_motion(&seat,&t,&motion);in->dx=in->dy=0;
    }
    notify_pointer_frame(&seat);
   }
  }
 }
 if(n==0 || (errno!=EAGAIN && errno!=EINTR))close_input(in);
 return 0;
}
static int open_input(struct input *in) {
 struct input_id id;char uniq[80]={0},token[84];unsigned char keys[(KEY_CNT+7)/8]={0};
 int fd=open(in->path,O_RDONLY|O_NONBLOCK|O_CLOEXEC);if(fd<0)return -1;
 if(ioctl(fd,EVIOCGID,&id)<0 || id.bustype!=BUS_BLUETOOTH || ioctl(fd,EVIOCGUNIQ(sizeof(uniq)),uniq)<0)goto fail;
 snprintf(token,sizeof(token),",%s,",uniq);
 if(!strcasestr(allowed,token) || ioctl(fd,EVIOCGKEY(sizeof(keys)),keys)<0)goto fail;
 /* Wait for all physical keys/buttons to be released before reacquiring. */
 for(size_t k=0;k<sizeof(keys);k++)if(keys[k])goto fail;
 if(ioctl(fd,EVIOCGRAB,1)<0)goto fail;
 in->source=wl_event_loop_add_fd(wl_display_get_event_loop(compositor->wl_display),fd,WL_EVENT_READABLE,events,in);
 if(!in->source){ioctl(fd,EVIOCGRAB,0);goto fail;}
 in->fd=fd;return 0;
fail:
 close(fd);return -1;
}
static int retry_closed_inputs(void *unused) {
 (void)unused;
 for(unsigned i=0;i<count;i++)if(inputs[i].fd<0 && open_input(&inputs[i])==0){recovered++;report_inputs();}
 wl_event_source_timer_update(retry_timer,1000);
 return 0;
}
static void destroy(struct wl_listener *l,void *data) {
 (void)data;wl_list_remove(&l->link);
 if(retry_timer){wl_event_source_remove(retry_timer);retry_timer=NULL;}
 for(unsigned i=0;i<count;i++)close_input(&inputs[i]);
 weston_seat_release(&seat);
}
__attribute__((visibility("default")))
int wet_module_init(struct weston_compositor *c,int *argc,char *argv[]) {
 const char *allow=getenv("S9P_INPUT_UNIQS");glob_t paths={0};int status=-1;
 compositor=c;allowed=allow;
 for(unsigned i=0;i<8;i++)inputs[i].fd=-1;
 (void)argc;(void)argv;
 if(!getenv("S9P_EXTERNAL_DRM") || !allow || !getenv("XDG_RUNTIME_DIR") || strcmp(getenv("XDG_RUNTIME_DIR"),"/trial/run") || access("/dev/input",F_OK)==0)return -1;
 struct xkb_context *context=xkb_context_new(XKB_CONTEXT_NO_FLAGS);
 struct xkb_rule_names names={.layout="it"};
 struct xkb_keymap *keymap=xkb_keymap_new_from_names(context,&names,XKB_KEYMAP_COMPILE_NO_FLAGS);
 xkb_context_unref(context);if(!keymap)return -1;
 weston_seat_init(&seat,c,"phone-dock-bluetooth");
 if(weston_seat_init_pointer(&seat)<0 || weston_seat_init_keyboard(&seat,keymap)<0)goto out;
 if(glob("/trial/input/event*",0,NULL,&paths) || paths.gl_pathc>8)goto out;
 for(size_t i=0;i<paths.gl_pathc;i++) {
  struct input *in=&inputs[count++];
  if(strlen(paths.gl_pathv[i])>=sizeof(in->path))goto out;
  strcpy(in->path,paths.gl_pathv[i]);
  if(open_input(in)<0 && !getenv("S9P_DOCK_SESSION"))goto out;
 }
 if(count){
  retry_timer=wl_event_loop_add_timer(wl_display_get_event_loop(c->wl_display),retry_closed_inputs,NULL);
  if(!retry_timer)goto out;
  wl_event_source_timer_update(retry_timer,1000);
  listener.notify=destroy;wl_signal_add(&c->destroy_signal,&listener);status=0;report_inputs();
 }

out:
 globfree(&paths);xkb_keymap_unref(keymap);
 if(status){for(unsigned i=0;i<count;i++)close_input(&inputs[i]);weston_seat_release(&seat);}
 return status;
}
