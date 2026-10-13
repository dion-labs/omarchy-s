from pathlib import Path
import sys
root=Path(sys.argv[1]);p=root/'src/gallium/drivers/panfrost/pan_jm.c';s=p.read_text()
assert 'OMARCHY_PANFROST_CPU_INVALIDATE' not in s
s=s.replace('#include "decode.h"', '''#include "decode.h"
#include "util/cache_ops.h"
#include "util/u_debug.h"

#if PAN_ARCH == 6 && DETECT_ARCH_AARCH64
DEBUG_GET_ONCE_BOOL_OPTION(omarchy_cpu_invalidate,
                          "OMARCHY_PANFROST_CPU_INVALIDATE", false)
#endif''',1)
needle='   submit.bo_handles = (uint64_t)(uintptr_t)bo_handles;'
assert s.count(needle)==1
s=s.replace(needle,'''   /* Opt-in S9+ diagnostic: preserve BO mapping policies and synchronize
    * only live CPU mappings pinned by this submission. No imported mappings
    * are traversed. Keep disabled unless explicitly selected for testing. */
#if PAN_ARCH == 6 && DETECT_ARCH_AARCH64
   if (debug_get_option_omarchy_cpu_invalidate()) {
      util_pre_flush_fence();
      for (unsigned i = 0; i < submit.bo_handle_count; ++i) {
         struct panfrost_bo *bo = pan_lookup_bo(dev, bo_handles[i]);
         if (bo->ptr.cpu && !(bo->flags & PAN_BO_SHARED))
            util_flush_inval_range_no_fence(bo->ptr.cpu, panfrost_bo_size(bo));
      }
      util_post_flush_inval_fence();
   }
#endif

'''+needle,1)
p.write_text(s)
(root/'VERSION').write_text('26.2.3-omarchy-cache1\n')
