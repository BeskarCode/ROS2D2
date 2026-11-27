// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Who wants each rosbridge topic and how often. rosbridge keeps one subscription per topic, so it
// is asked for the fastest rate anyone wants; each callback still gets the topic at its own rate.
//   const w = topicWants();
//   w.add(topic, cb, ms)     -> the throttle to (re)subscribe with, or null if the current one serves
//   w.remove(topic, cb)      -> { gone: true } (nobody left: unsubscribe), a throttle to subscribe
//                               with again (the fastest one left is slower), or null (nothing to do)
//   w.deliver(topic, msg, now) calls each callback whose own throttle has passed

/** A callback may be called a little early: rosbridge's own timing jitters, and a callback that
 *  asked for 200 ms must not drop every other message of a 200 ms stream. */
const EARLY_MS = (ms) => Math.min(ms * 0.1, 50);

export function topicWants() {
  const want = {};      // topic -> [{ cb, ms, last }]
  const rate = {};      // topic -> the throttle rosbridge was last asked for

  const fastest = (topic) => Math.min(...want[topic].map((w) => w.ms));

  return {
    add(topic, cb, ms = 0) {
      (want[topic] ||= []).push({ cb, ms: Math.max(0, ms || 0), last: -Infinity });
      const min = fastest(topic);
      if (topic in rate && rate[topic] <= min) return null;
      rate[topic] = min;
      return min;
    },
    remove(topic, cb) {
      const old = want[topic];
      if (!old) return null;
      const list = old.filter((w) => w.cb !== cb);
      if (list.length === old.length) return null;
      want[topic] = list;
      if (!list.length) {
        delete want[topic];
        const was = topic in rate;
        delete rate[topic];
        return was ? { gone: true } : null;
      }
      const min = fastest(topic);
      if (min <= rate[topic]) return null;
      rate[topic] = min;
      return min;
    },
    deliver(topic, msg, now) {
      for (const w of [...(want[topic] || [])]) {      // a callback may unsubscribe itself
        if (w.ms && now - w.last < w.ms - EARLY_MS(w.ms)) continue;
        w.last = now;
        w.cb(msg);
      }
    },
    rate: (topic) => rate[topic],
    has: (topic) => topic in rate,
  };
}
