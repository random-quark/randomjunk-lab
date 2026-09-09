# Phone sensors from a web app

Works in a plain `--static` experiment — no backend needed unless you are logging
readings. Requires HTTPS, which every lab subdomain has.

## The platform split

**Android/Chrome** has the Generic Sensor API: `Accelerometer`, `Gyroscope`,
`LinearAccelerationSensor`, `AbsoluteOrientationSensor`.

**iOS/Safari has none of it.** iOS supports only the older `DeviceMotionEvent`
(acceleration, rotation rate) and `DeviceOrientationEvent` (alpha/beta/gamma,
plus `webkitCompassHeading`).

Feature-detect and write both paths.

## iOS needs a tap

Since iOS 13, permission must be requested from inside a real user gesture.
Called on page load it silently does nothing. **Every sensor app needs a Start
button.**

```js
async function startMotion(onMotion) {
  // `globalThis.` matters: a bare `DeviceMotionEvent?.` still throws a
  // ReferenceError where the identifier is not declared at all.
  const dme = globalThis.DeviceMotionEvent;

  // iOS: explicit permission, must be inside a click handler
  if (typeof dme?.requestPermission === 'function') {
    if (await dme.requestPermission() !== 'granted') throw new Error('motion permission denied');
    addEventListener('devicemotion', onMotion);
    return 'ios';
  }

  // Android/Chrome: Generic Sensor API, richer and higher rate
  if ('Accelerometer' in globalThis) {
    const { state } = await navigator.permissions.query({ name: 'accelerometer' });
    if (state === 'denied') throw new Error('accelerometer denied');
    const sensor = new Accelerometer({ frequency: 60 });
    sensor.addEventListener('reading', () =>
      onMotion({ acceleration: { x: sensor.x, y: sensor.y, z: sensor.z } }));
    sensor.start();
    return 'generic';
  }

  if ('ondevicemotion' in globalThis) {            // older Android browsers
    addEventListener('devicemotion', onMotion);
    return 'legacy';
  }

  throw new Error('no motion sensors available');
}

document.querySelector('#start').addEventListener('click', () => {
  startMotion(e => {
    const a = e.acceleration || e.accelerationIncludingGravity;
    if (a) render(a.x, a.y, a.z);
  }).catch(err => alert(err.message));
});
```

## Magnetometer is the weak one

- **iOS** never exposes raw magnetometer values — only `webkitCompassHeading`,
  a bearing in degrees.
- **Android/Chrome** has `Magnetometer`, but behind
  `chrome://flags/#enable-generic-sensor-extra-classes`, so it cannot be relied on.

**Compass heading works on both; raw magnetometer effectively does not.**

## Also available

Camera and microphone (`getUserMedia`), geolocation, vibration (Android only),
screen wake lock, notifications (iOS only for an installed PWA, 16.4+), gamepad,
ambient light (patchy).

## Not available from the web

Background sensor access when the app is closed, barometer, NFC on iOS, true
background execution. **Capacitor** wraps the same web app natively if one of
these is genuinely required — but that means Xcode and provisioning profiles.

## Gotcha

"Worked on localhost, broke on the server" is almost always the secure-context
rule. Lab subdomains are HTTPS, so it should not bite here.

## Map sensor axes to the screen

DeviceOrientation beta/gamma use the device's natural coordinate frame, not the
current screen frame. Gamma alone is not screen-relative tilt in landscape.
Transform the orientation into screen coordinates using the current screen angle,
or explicitly support portrait with a visible rotate-device fallback when a lock
is unavailable. Do not treat Euler angles as universally interchangeable axes.
Test direction against a fixed visible landmark at 0/90/180/270 degrees, including
sign, permission denial and unavailable-sensor fallback.

For tilt controls prefer a suitable relative orientation source; compass bearing
needs an earth-referenced source. Feature-detect and check event.absolute for
legacy orientation events. Choosing legacy deviceorientation does not guarantee
that magnetometer input is excluded or that latency is lower. Record measured
behavior on real target phones; browser emulation does not validate sensors.
Coordinate/reference definitions: https://www.w3.org/TR/orientation-event/
