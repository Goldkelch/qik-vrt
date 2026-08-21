/* QIK-VRT Universal Terminal monitor sampling guard.
 * Sampling completeness is claimable only with a finite declared f_max and
 * sample_hz >= 2*f_max. Unknown bandwidth requires event-driven observation.
 */
(function (global) {
  'use strict';
  function finitePositive(x) { return Number.isFinite(x) && x > 0; }
  function evaluate(opts) {
    var fmax = opts && opts.sourceMaxHz;
    var sample = opts && opts.sampleHz;
    var eventDriven = !!(opts && opts.eventDriven);
    var guard = (opts && opts.guardFactor != null) ? opts.guardFactor : 2.5;
    if (!Number.isFinite(guard) || guard < 2) {
      return { admitted: false, completenessClaimAllowed: false, disposition: 'HOLD_INVALID_GUARD_FACTOR' };
    }
    if (fmax == null) {
      return eventDriven
        ? { admitted: true, completenessClaimAllowed: false, disposition: 'EVENT_DRIVEN_BOUND_UNKNOWN_GAP_REOBSERVE_REQUIRED' }
        : { admitted: false, completenessClaimAllowed: false, disposition: 'HOLD_SAMPLING_BOUND_UNKNOWN' };
    }
    if (!finitePositive(fmax)) {
      return { admitted: false, completenessClaimAllowed: false, disposition: 'HOLD_INVALID_SOURCE_MAX_HZ' };
    }
    if (eventDriven) {
      return { admitted: true, completenessClaimAllowed: false, nyquistBoundaryHz: 2 * fmax,
               minimumHz: guard * fmax, disposition: 'EVENT_DRIVEN_PRIMARY_POLLING_OPTIONAL' };
    }
    if (!finitePositive(sample)) {
      return { admitted: false, completenessClaimAllowed: false, disposition: 'HOLD_SAMPLE_RATE_MISSING' };
    }
    if (sample < 2 * fmax) {
      return { admitted: false, completenessClaimAllowed: false, nyquistBoundaryHz: 2 * fmax,
               disposition: 'HOLD_BELOW_NYQUIST' };
    }
    return { admitted: true, completenessClaimAllowed: true, nyquistBoundaryHz: 2 * fmax,
             minimumHz: guard * fmax,
             disposition: sample >= guard * fmax ? 'ADMITTED_WITH_GUARD_MARGIN' : 'NYQUIST_BOUNDARY_MET_GUARD_MARGIN_NOT_MET' };
  }
  global.QIKVRTMonitorSampling = Object.freeze({ evaluate: evaluate });
}(typeof window !== 'undefined' ? window : globalThis));
