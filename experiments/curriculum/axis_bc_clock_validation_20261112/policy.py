"""Input adapter: cap only the final-release clock, never the physical clock."""


def effective_steps(phase, placement_stage, elapsed, cap):
    if elapsed < 0 or cap < 0:
        raise ValueError('Elapsed time and cap must be nonnegative')
    return min(elapsed, cap) if phase == 6 and placement_stage == 2 else elapsed


def make_policy(base, historical, model, threshold, stage, cap=None):
    class ReleaseClockPolicy(base.DevicePolicy):
        def action(self, obs, target, source):
            phase, raw = self.phase, self.steps
            used = raw if cap is None else effective_steps(phase, stage(), raw, cap)
            self.intervened = used != raw
            self.raw_steps, self.used_steps = raw, used
            anchor = (source if phase < 4 else target) if self.anchor is None else self.anchor
            self.last_x = historical.vector(obs, anchor, used)
            self.steps = used
            try:
                result = super().action(obs, target, source)
            except BaseException:
                self.steps = raw
                raise
            # Phase 6 never advances via the completion classifier. Keep the
            # real counter for the sequencer, stop criteria, and next call.
            if phase == 6:
                self.steps = raw+1
            return result
    return ReleaseClockPolicy(model, historical, threshold)
