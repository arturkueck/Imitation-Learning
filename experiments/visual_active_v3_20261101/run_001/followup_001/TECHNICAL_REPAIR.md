# Single targeted technical repair

The second technical smoke worker (PID37508) ended with a strict replay RGB equality assertion. Host psutil confirmed it no longer existed before the repair. Original logs/results remain in followup_smoke_002.

A deterministic isolated reproduction of family9510001/3, candidate5, with the independent complete-path checker, found both wrist and fixed0 RGB exactly identical, fixed1 one channel of one pixel differing by 1/255 (mean absolute channel difference 0.0000130208); all camera positions were exactly equal. Exact bitwise OpenGL raster equality was unnecessarily strict.

The repaired code retains a strict gate (maximum channel difference <=1 and changed-channel fraction <=0.001), records measured drift, and feeds the actual post-decision acquired RGB/rays/visibility/calibration rather than silently substituting cached data. A substantive mismatch still fails closed. This changes no architecture, loss, data seeds or optimizer settings.

One repair verification uses separate technical smoke artifacts followup_smoke_repair001, not the reserved final families. No further automated repair/restart is permitted after an unsuccessful repair.
