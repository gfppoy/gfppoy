/* Shared path mechanics. Distances are model units, independent of playback. */
(() => {
  "use strict";
  const normal = (rng = Math.random) => Math.sqrt(-2 * Math.log(Math.max(1 - rng(), Number.EPSILON))) * Math.cos(2 * Math.PI * rng());
  function ou(curvature, distance, persistence, sigma, rng = Math.random) {
    const decay = Math.exp(-distance / persistence);
    return decay * curvature + sigma * Math.sqrt(-Math.expm1(-2 * distance / persistence)) * normal(rng);
  }
  const exponential = (rate, rng = Math.random) => rate > 0 ? -Math.log(Math.max(rng(), Number.EPSILON)) / rate : Infinity;
  const mirror = curvature => -curvature;
  // Invert the integrated hazard for beta(a) = initialRate * exp(-a / decayLength).
  // Finite remaining hazard means a tip may never fork again (Infinity).
  function ageDecayingFork(age, initialRate, decayLength, rng = Math.random) {
    const remainingHazard = initialRate * decayLength * Math.exp(-age / decayLength);
    const threshold = exponential(1, rng);
    return threshold >= remainingHazard ? Infinity : -decayLength * Math.log1p(-threshold / remainingHazard);
  }
  function sourceWeight(d2, radius, strength = 1) {
    const taper = Math.max(0, 1 - d2 / (radius * radius));
    return strength * taper * taper / (d2 + 1);
  }
  function sourcePotential(d2, radius) {
    const a = radius * radius;
    if (d2 >= a) return 0;
    const q = (a - d2) / (a + 1);
    const integral = q < 0.001 ? q ** 3 * (1 / 3 + q / 4 + q * q / 5 + q ** 3 / 6) : -Math.log1p(-q) - q - q * q / 2;
    return (a + 1) ** 2 / (2 * a * a) * integral;
  }
  function slope(state, curvature, field, gain) {
    const [fx, fy] = field(state.x, state.y);
    const x = Math.cos(state.angle), y = Math.sin(state.angle);
    return { x, y, angle: curvature + gain * (-fx * y + fy * x) };
  }
  const advance = (s, d, h) => ({ x: s.x + h * d.x, y: s.y + h * d.y, angle: s.angle + h * d.angle });
  function rk4(state, curvature, distance, field, gain) {
    const k1 = slope(state, curvature, field, gain);
    const k2 = slope(advance(state, k1, distance / 2), curvature, field, gain);
    const k3 = slope(advance(state, k2, distance / 2), curvature, field, gain);
    const k4 = slope(advance(state, k3, distance), curvature, field, gain);
    const next = {
      x: state.x + distance / 6 * (k1.x + 2 * k2.x + 2 * k3.x + k4.x),
      y: state.y + distance / 6 * (k1.y + 2 * k2.y + 2 * k3.y + k4.y),
      angle: state.angle + distance / 6 * (k1.angle + 2 * k2.angle + 2 * k3.angle + k4.angle)
    };
    const midpoint = advance(state, k2, distance);
    return { next, positionError: Math.hypot(next.x - midpoint.x, next.y - midpoint.y), angleError: Math.abs(next.angle - midpoint.angle) };
  }
  // Exact transport with constant curvature during an OU splitting step.
  function arc(state, curvature, distance) {
    const half = curvature * distance / 2;
    const sinc = Math.abs(half) < 1e-5 ? 1 - half * half / 6 : Math.sin(half) / half;
    return { x: state.x + distance * sinc * Math.cos(state.angle + half), y: state.y + distance * sinc * Math.sin(state.angle + half), angle: state.angle + 2 * half };
  }
  function circleExit(state, curvature, distance, radius) {
    const radial = state.x * Math.cos(state.angle) + state.y * Math.sin(state.angle);
    const c = state.x * state.x + state.y * state.y - radius * radius;
    let candidates;
    if (Math.abs(curvature) < 1e-10) {
      candidates = [-radial + Math.sqrt(Math.max(0, radial * radial - c))];
    } else {
      // Substitute v = tan(k*s/2) in |arc(s)|² = R². This avoids
      // subtracting the huge radii of two circles when k is small.
      const transverse = state.x * Math.sin(state.angle) - state.y * Math.cos(state.angle);
      const a = curvature * curvature * c - 4 * curvature * transverse + 4;
      const b = 4 * curvature * radial;
      const d = curvature * curvature * c;
      const discriminant = b * b - 4 * a * d;
      if (discriminant < 0) return null;
      const q = -0.5 * (b + (b < 0 ? -1 : 1) * Math.sqrt(discriminant));
      const roots = Math.abs(a) < 1e-14 ? [-d / b] : q === 0 ? [0] : [q / a, d / q];
      candidates = roots.map(v => 2 * Math.atan(v) / curvature);
    }
    let first = Infinity;
    for (const s of candidates) {
      if (!Number.isFinite(s) || s < -1e-8 || s > distance + 1e-8) continue;
      const p = arc(state, curvature, Math.max(0, s));
      if (p.x * Math.cos(p.angle) + p.y * Math.sin(p.angle) > 1e-9) first = Math.min(first, Math.max(0, s));
    }
    return first === Infinity ? null : Math.min(distance, first);
  }
  function discountedLength(t, distance, beta) {
    return beta === 0 ? distance : Math.exp(-beta * t) * -Math.expm1(-beta * distance) / beta;
  }
  function seeded(seed) {
    return () => {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  globalThis.GrowthPhysics = Object.freeze({ normal, ou, exponential, ageDecayingFork, mirror, sourceWeight, sourcePotential, slope, rk4, arc, circleExit, discountedLength, seeded });
})();
