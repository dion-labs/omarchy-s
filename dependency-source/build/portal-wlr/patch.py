from pathlib import Path
p=Path('source/src/screencast/wlr_screencast.c')
s=p.read_text();needle='if (!strcmp(interface, ext_image_copy_capture_manager_v1_interface.name)) {'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n\t\tif (getenv("OMARCHY_PORTAL_WLR_SCREENCOPY")) {\n\t\t\tlogprint(INFO, "Omarchy: selecting wlr-screencopy compatibility protocol");\n\t\t\treturn;\n\t\t}')
p.write_text(s)
# Cancel compositor ownership before returning its buffer during renegotiation.
p=Path('source/src/screencast/wlr_screencast.c');s=p.read_text()
needle='void xdpw_wlr_frame_capture(struct xdpw_screencast_instance *cast) {'
assert s.count(needle)==1
cancel='''void xdpw_wlr_frame_cancel(struct xdpw_screencast_instance *cast) {
	struct xdpw_timer *timer, *tmp;
	wl_list_for_each_safe(timer, tmp, &cast->ctx->state->timers, link) {
		if (timer->user_data == cast && timer->func == wlr_frame_capture_timer) {
			xdpw_destroy_timer(timer);
		}
	}
	if (cast->ctx->ext_image_copy_capture_manager && cast->ctx->ext_output_image_capture_source_manager) {
		if (cast->ext_session.frame) {
		ext_image_copy_capture_frame_v1_destroy(cast->ext_session.frame);
		cast->ext_session.frame = NULL;
		}
	} else if (cast->ctx->screencopy_manager && cast->wlr_session.wlr_frame) {
		zwlr_screencopy_frame_v1_destroy(cast->wlr_session.wlr_frame);
		cast->wlr_session.wlr_frame = NULL;
	}
}

'''
s=s.replace(needle,cancel+needle);p.write_text(s)
p=Path('source/include/wlr_screencast.h');s=p.read_text();s=s.replace('void xdpw_wlr_frame_capture(', 'void xdpw_wlr_frame_cancel(struct xdpw_screencast_instance *cast);\nvoid xdpw_wlr_frame_capture(');p.write_text(s)
p=Path('source/src/screencast/pipewire_screencast.c');s=p.read_text();needle='case PW_STREAM_STATE_PAUSED:\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\t\txdpw_wlr_frame_cancel(cast);\n');p.write_text(s)
