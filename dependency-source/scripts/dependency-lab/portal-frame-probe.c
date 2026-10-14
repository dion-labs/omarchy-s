/* Original DionLabs disposable PipeWire video consumer; no host devices. */
#include <pipewire/pipewire.h>
#include <spa/param/video/format-utils.h>
#include <spa/param/props.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

struct probe { struct pw_main_loop *loop; struct pw_stream *stream; struct pw_core *core;
    struct pw_proxy *link; uint32_t target; unsigned frames; struct spa_video_info_raw format; };
static void process(void *data) {
    struct probe *p=data; struct pw_buffer *b=pw_stream_dequeue_buffer(p->stream);
    if (!b) return;
    if (b->buffer->n_datas && b->buffer->datas[0].data && b->buffer->datas[0].chunk && b->buffer->datas[0].chunk->size) {
        struct spa_data *d=&b->buffer->datas[0]; unsigned long sum=0, color=0;
        uint32_t offset=d->chunk->offset, size=d->chunk->size;
        if (offset<=d->maxsize && size<=d->maxsize-offset) {
            unsigned char *bytes=(unsigned char *)d->data+offset;
            for (uint32_t i=0;i<size;i++) { sum+=bytes[i]; if (i%4!=3) color+=bytes[i]; }
            p->frames++;
            if (p->frames<=3) { printf("{\"frame\":%u,\"bytes\":%u,\"width\":%u,\"height\":%u,\"sum\":%lu,\"color\":%lu}\n",
                p->frames,size,p->format.size.width,p->format.size.height,sum,color); fflush(stdout); }
        }
    }
    pw_stream_queue_buffer(p->stream,b);
}
static void param(void *data,uint32_t id,const struct spa_pod *pod) {
    struct probe *p=data;
    if (id==SPA_PARAM_Format && pod) spa_format_video_raw_parse(pod,&p->format);
}
static void state(void *data,enum pw_stream_state old,enum pw_stream_state current,const char *error) {
    (void)old; struct probe *p=data; fprintf(stderr,"state %s %s\n",pw_stream_state_as_string(current),error?error:"");
    if (current==PW_STREAM_STATE_ERROR) { fprintf(stderr,"stream error: %s\n",error); pw_main_loop_quit(p->loop); }

}
static const struct pw_stream_events events={PW_VERSION_STREAM_EVENTS,.state_changed=state,.param_changed=param,.process=process};
int main(int argc,char **argv) {
    if (argc!=3) return 2;
    alarm(12);pw_init(NULL,NULL);struct probe p={0};p.target=(uint32_t)strtoul(argv[2],NULL,10);
    p.loop=pw_main_loop_new(NULL);struct pw_context *ctx=pw_context_new(pw_main_loop_get_loop(p.loop),NULL,0);
    p.core=pw_context_connect_fd(ctx,atoi(argv[1]),NULL,0);if (!p.core) return 3;
    p.stream=pw_stream_new(p.core,"omarchy-lab-probe",pw_properties_new(PW_KEY_MEDIA_TYPE,"Video",PW_KEY_MEDIA_CATEGORY,"Capture",NULL));
    struct spa_hook hook;pw_stream_add_listener(p.stream,&hook,&events,&p);
    uint8_t storage[1024];struct spa_pod_builder builder=SPA_POD_BUILDER_INIT(storage,sizeof(storage));
    const struct spa_pod *params[1];
    params[0]=spa_pod_builder_add_object(&builder,SPA_TYPE_OBJECT_Format,SPA_PARAM_EnumFormat,
        SPA_FORMAT_mediaType,SPA_POD_Id(SPA_MEDIA_TYPE_video),SPA_FORMAT_mediaSubtype,SPA_POD_Id(SPA_MEDIA_SUBTYPE_raw),
        SPA_FORMAT_VIDEO_format,SPA_POD_CHOICE_ENUM_Id(5,SPA_VIDEO_FORMAT_BGRx,SPA_VIDEO_FORMAT_BGRx,SPA_VIDEO_FORMAT_RGBx,SPA_VIDEO_FORMAT_BGRA,SPA_VIDEO_FORMAT_RGBA));
    int ret=pw_stream_connect(p.stream,PW_DIRECTION_INPUT,p.target,PW_STREAM_FLAG_MAP_BUFFERS|PW_STREAM_FLAG_AUTOCONNECT,params,1);
    if (ret<0) return 4;
    pw_main_loop_run(p.loop);
    if (p.link) pw_proxy_destroy(p.link);
    pw_stream_destroy(p.stream);pw_core_disconnect(p.core);
    pw_context_destroy(ctx);pw_main_loop_destroy(p.loop);return p.frames?0:5;
}
