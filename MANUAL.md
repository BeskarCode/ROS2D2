<p align="center">
  <img src="media/ros2d2-logo.png" alt="ROS2D2" width="420">
</p>

# ROS2D2 web console · User manual

[Versión en castellano](MANUAL_es.md)

The console is served by the Pi inside R2: open `http://<pi>:8080` in any browser on the same network
(the Pi's address on your home network, or `10.42.0.1` on R2's own WiFi). It has three pages, in the
bar at the top: **Console**, **Navigation** and **Setup**. The **Manual** button (marked ↗: it leaves
the console) opens this manual on GitHub, in a new tab, at the part about the page (or tab) you are
on. Every button has a tooltip: hold the mouse over it, and each card or tab has a folded **How it
works** at its top.

The pills next to the menu are the same on every page and say how things are: **ROS** (the
console's link to ROS), the **Mega**, the **Pico** board (its firmware version), the **Lidar**, the
**Camera** (or how many of the cameras answer) and the **Mode** on (an automatic one, or face
tracking). Green is fine, amber means look, red means it is not there. A click on the Pico, Lidar,
Camera or Mode pill opens its Setup tab; each Setup tab has its own address (`setup.html#system`…). If R2 stops answering, a
window says so and goes away by itself when it is back. **Ctrl+S** saves the page you are on, from
anywhere on it.

- [Console](#console)
- [Navigation](#navigation)
- [Remote control](#remote-control): [Controllers](#controllers) · [Shortcuts](#shortcuts)
- [Setup](#setup): [Cameras](#setup--cameras) · [Sensors](#setup--sensors) · [Modes](#setup--modes) ·
  [System](#setup--system) · [File](#setup--file)

---

## Console

![The Console page: cameras, dome and Mega](media/manual/console.png)

**Cameras**: the pictures of R2's cameras, numbered left to right. *Identify* shows each camera's
number on its picture. *Pixelate faces* blurs the faces it finds (for photos and videos of events).
Below: how many faces it sees, the best score and where the best one is.

**Dome**: R2 in 3D with the dome turned as the Pi believes it is.

- The bar under it is the dome's speed (left / right).
- *Track* turns face tracking on or off: the dome turns to look at the nearest face.
- *Dome to front* turns it back to the front.
- The dome has no position sensor: its angle is estimated from the speed commands. Time a full
  turn at speed 80 and type `360 ÷ seconds` in **°/s at speed 80**.
- *Simulate (no Mega)* tries the tracking with no Mega: the faces move as if the camera had turned.
- *Camera view* draws where the camera looks.

**Mega**: what goes to the Mega (→) and what it answers (←). *Pause* stops the list scrolling,
*Clear* empties it, *show replies* hides or shows the answers.

---

## Navigation

![The Navigation page: map, R2 in 3D and readings](media/console-navigation-modes.gif)

Video of every mode in the simulator: <https://youtu.be/Smfn6zQICm0>

**Navigation (map)**: the floor around R2 seen from above. The lidar's points are cyan, each
sensor's beam is drawn in its colour, and the green dashed circle is the free space round R2 (with
the distance, *36 cm free*). **Click the floor** to send R2 there (the goal is a green flag);
*Cancel goal* forgets it. *Sensor beams* and *trail* show or hide the beams and the way R2 has gone.
R2 only drives there when the automatic mode is on (Go to a point, see [Modes](#setup--modes)).

**PS + L2 starts** (also on the Console, in the Mega card): pick which mode PS + L2 on the foot
controller starts (Go to a point, Go forward, Patrol, Follow a colour); the green text says which one
is on. Only the controller switches a mode on: that keeps someone with the controller in hand
whenever R2 starts moving by itself. **Stop** switches it off from the page. Picking a mode here is
the same as giving it PS + L2 in [Modes](#setup--modes): the mode that had PS + L2 gets the picked
mode's old combination, so none is lost.

**Patrol route**: with *route point* on, each click on the floor adds a numbered point; in Patrol R2
goes round them in a loop (the point it heads for is filled). A point it cannot reach is skipped; if
it reaches none it stops. *Clear route* forgets it. *goal* puts clicks back to sending R2 somewhere.

**Go forward**: R2 drives straight on along the way it was facing, steering round things. When it is
boxed in (or the only way out is well off to a side) it turns slowly on the spot looking for a free
way and carries on along it; after a full turn with no way out it stops and plays the *give up* sound.

**Safety circle**: the red dashed circle round R2 (*safety circle* in Settings). R2 does not drive on
while something is inside it ahead (within *circle watched ahead*, 60° each side by default): it
turns away until it is clear. Something beside or behind (a wall it runs along) does not stop it.
The faster R2 goes, the bigger the circle ahead grows, by the distance it needs to stop (*real
braking*). When it has to stop for something in the way it cuts its speed at once, without a ramp.

**Lost sensors and odometry**: a sensor that was reporting and goes silent (the Pico unplugged, the
lidar stopped) is not taken as "nothing there": R2 stops (state *sensor lost*) and its reading shows
**LOST** in red with the seconds since it last spoke (hover a reading for its age). Without odometry
(*/odom*) R2 does not move either (state *no odom*); the line under the state says how old */odom* is,
in red when it is missing. On the droid the odometry comes from what went to the Mega plus the IMU
(the *dead_reckoning* node); in the simulator, from the simulated room.

**Settings**: every setting of how R2 moves on its own (nav.yaml), in groups: safety circle, speed
(with *slowing down* for gentle slow-downs and *real braking*, the deceleration R2 really stops with:
measure it on the droid), what to do when blocked (Go to a point, Patrol: how long it waits, how far it
backs up, when a try counts and how long the way must be clear), Go forward's slow search, and the
distance sensors. The safety circle cannot be smaller than 0.40 m (half the body is 0.36).
A change applies at once (try it in the simulator); **Save** keeps it in `~/.config/ros2d2/nav.yaml`,
**Defaults** brings back the package's values. Until you save, R2 uses the defaults; a setting you
changed from its default shows in amber.

**Only where it can see**: in every automatic mode R2 only drives towards directions that a sensor
in use and reporting covers, as placed in Setup -> Sensors (each one's direction and field of view;
the lidar's blind sectors and floor sensors do not count). Forward needs something looking ahead; to
head somewhere no sensor sees it turns first and drives once a sensor looks there. Backing up needs a
rear sensor or a lidar that sees behind, with the way free: without it R2 does not back up, it stops
and turns instead (the status says *no sensor looks behind*). With nothing looking ahead it stays
stopped.

**Only in simulation**:
- **Room**: load a living room (sofa, table and chair legs, a low box), a narrow corridor with a
  door, several rooms joined by doors, or an event with people (one wearing the colour) and
  barriers. R2 goes back to its start; you can still add chair legs, boxes and people on top.
- **PS + L2** (next to the mode buttons): the simulated controller's PS + L2, to start and stop the
  mode it is set to.
- **on / off** next to each reading: simulate that sensor unplugged, to see what R2 does without it
  (sensors.yaml is not touched).

**R2 in 3D**: the same in 3D, with the lidar's point cloud and the sensors' cones. Drag to orbit,
wheel to zoom. *Follow R2* keeps it in the middle; *Show the room* draws the simulated room (only in
simulation, where you can also add chair legs and boxes and drag them).

**Telemetry**: every sensor's reading. The bar fills as things get closer; the red mark is where R2
stops for that sensor, the thin mark the raw reading before filtering. Greyed with *ignored* means
that sensor is ignored (see [Sensors](#setup--sensors)). Below: what the navigator is doing and why,
and whether the Mega is connected (without it nothing reaches the feet).

---

## Remote control

![The Remote window: the two virtual Navs](media/manual/remote.png)

The **Remote** button, on every page, opens two virtual PS3 Navs, the **foot** one and the **dome**
one, to try things at home without the real controllers. The Mega takes them exactly as real Navs:
the same buttons do the same things. It needs a Mega firmware with the virtual Nav
(`ENABLE_VIRTUAL_PAD` in ShadowMD Lite or the classic ShadowMD); each Nav's chip says how it is:

| Chip | Means |
|---|---|
| **virtual** | the window drives this Nav |
| **real Nav connected** | a real controller is on: the window warns before the first action, and if someone moves the real one, **the real one wins** |
| **no Mega** / **this firmware has no virtual Nav** | nothing to send to: the Nav is greyed |

While the window is open both Navs are "on" (their state goes out 20 times a second, like a real
Nav). **Closing the window, hiding the tab or leaving the page switches them off**: everything is let
go and the Mega stops the motors and the modes by itself, as when a real controller is lost. Only one
Remote window is open at a time, across tabs.

### Controllers

- **Click** a button: press and release.
- **Hold a button 0.6 s**: it stays pressed (**HOLD**, yellow; it turns yellow as soon as the time is
  reached, so you know you can let go). Then press another button to send the **combination**: the
  held ones and that one together. Hold more than one to make longer combinations (*L2* + *Cross* +
  an arrow…).
- **Click a held button**, or press **Esc**, to let it go.
- **The stick**: drag the knob; it goes back to the centre when you let go. A click on the knob
  without moving it is **L3**.

### Shortcuts

![The Remote window: Shortcuts](media/manual/remote-shortcuts.png)

Every combination that does something, sent for you with **one click**, with a box to find one
(*holo*, *song*, *panel*, *Patrol*…). They come in three groups:

- **Automatic modes**: the combination each mode has in Setup → Modes (on / off).
- **Face tracking**: Dome PS + L2 (on / off).
- **MarcDuino actions**: ShadowMD Lite's default map (the one in its `CheatSheet.md`). A combination
  given to a mode is listed as that mode, as it no longer plays its action; free combinations are
  not listed.

The window presses the buttons in the order the Mega reads them: first the modifiers (Cross, Circle,
PS, L1, L2, L3), then the arrow, and with the dome Nav connected the modifier goes on the other Nav,
as the cheat sheet says (*Foot ↑ + Cross* is the foot's ↑ with the dome's Cross). After each
shortcut the list waits 1.2 s: the Mega ignores an arrow that comes less than a second after the
last one.

---

## Setup

Setup has five tabs, each with its own address (`setup.html#cameras`, `#sensors`, `#modes`, `#system`,
`#file`). On a computer screen the page does not scroll: each tab fills the window and its columns
scroll inside. **Save** keeps the tab's settings on the Pi (they apply at once);
**Save and restart** is only needed for the camera list.

### Setup → Cameras

![Setup, Cameras](media/manual/setup-cameras.png)

The map on the left is R2 seen from above with each camera's fan; on the right, every camera
plugged into the Pi (or on R2's WiFi), with:

- **use** (on or off), **number** (the arrows move it left or right in the list), **size** and
  **turn** (the two arrows turn the picture a quarter each way: 0, 90, 180, 270°, seen at once),
- **points to** and **field of view**: where it looks on R2, so the dome tracking knows where a face is.

*Identify* puts each number on its picture: cover a camera with your hand to see which picture goes
dark. Direction and field of view apply at once; turning a camera on or off or renumbering needs
**Save and restart**.

### Setup → Sensors

![Setup, Sensors](media/console-sensors-setup.gif)

R2 seen from above, to scale (rings every 50 cm), and R2 in 3D (*Top*, *3D* or *Both*).

- **Drag a sensor** on the map to move it. Click its card to set where it **points**, how wide it
  sees (**field of view**), how far (**range**), its **height**, how much it **tilts down**, and at
  what distance R2 **stops** for it.
- **colour**: each sensor can take one of 9 fixed colours, used on the map, in 3D, on its card and next
  to its connector on the board (System); the ones another sensor uses look faded. The button next to it brings back its type's colour.
- **Red dots** are places near R2 that no sensor covers; the numbers under the map say how much of
  the floor is covered up to 50 cm and 1 m, and where R2 is blind. The dashed red ring is the
  **navigation's safety circle**, to set the sensors against it.
- Over the list: **Connected only** hides the sensors that are not measuring; **Hide all** and **Show
  all** hide or show every beam (and the lidar's points) on the map at once, like each card's eyes.
- **Test object**: pick one (chair leg, person, wall, low box) and drag it: the sensors that would
  see it light up, with the distance they would read.
- **Add sensor** takes the first free connector of the Pico board; **Remove** takes it out.
- Each card says whether the sensor answers (*plugged in*, *not responding*...). The lightbulb makes
  its connector's LED blink on the board, to find it.

**In use / ignored**: the switch on each card. A sensor that gives false readings can be ignored in
one click: navigation and follow stop using it within a second or two, but it keeps measuring and its
reading stays on the card, greyed, so you can see when it is fine again and switch it back on. The
switch is saved at once (only that line); it stays ignored after a restart. If nothing in use is left
looking ahead, the console warns you: R2 will not move.

**The lidar's card** also sets the lidar itself:

- **USB**: *Disconnect* stops the motor and unplugs the lidar's USB in software, as if the cable were
  pulled (its driver stops); *Connect* plugs it back and the driver starts again in a few seconds.
  It applies at once, with no Save, and a reboot of the Pi connects it again. The port keeps its 5 V
  (a Pi 4 cannot switch one port off). Needs `setup/install_lidar_usb.sh` run once on the Pi.
- **Motor**: *Always*; *Only with an automatic mode* (R2 standing still is quiet; when a mode starts,
  it waits up to 5 s for the lidar before moving; the motor stops 5 s after the last mode); or *Off*.
- **Scan mode**: the modes the lidar says it has (a C1: *Standard*, 16 m; *DenseBoost*, 40 m).
  Changing it restarts only the lidar for a few seconds.
- **Upside down**: if it is mounted upside down.
- **Blind sectors**: angles of the lidar's own view to ignore (R2's leg), drawn red on the map.
- The **lidar** line: model, firmware, hardware, health, mode, turns per second and points per turn.
  The C1's speed cannot be changed (it turns at about 10 per second).

**Save** applies at once: ROS moves the sensors and the lidar's cut.

### Setup → Modes

![Setup, Modes](media/manual/setup-modes.png)

Each automatic mode starts with its own **controller combination**; pressing it again switches the
mode off, and touching the stick takes the control back at once. A combination given to a mode no
longer plays its MarcDuino action. *Dome PS + L2* is face tracking and cannot be given to a mode.

| | |
|---|---|
| ![Go to a point](ros2_ws/src/r2_web/www/img/modes/goto.svg) | ![Go forward](ros2_ws/src/r2_web/www/img/modes/forward.svg) |
| ![Patrol](ros2_ws/src/r2_web/www/img/modes/patrol.svg) | ![Follow a colour](ros2_ws/src/r2_web/www/img/modes/follow.svg) |

**Follow a colour**: wear something of a clear colour, **click on it in the camera picture** and
check how much of the picture it matches (the matches are painted magenta). Its sliders set how
close a colour must be, the distance to keep, the top speed and how long it searches when it loses
the colour. With the ESP32-P4 dome camera (`firmware/r2_domecam_p4`) the camera finds the colour
itself while R2 follows it, so no video goes over the WiFi; with other cameras the Pi finds it in
the video, as before.

The tab has three columns: the modes, each with its combination and a small picture of what it does;
the camera picture to click the colour on; and the colour's settings.

### Setup → System

![Setup, System: the display switched on, a screen picked, the DISPLAY button and a LED identified](media/manual/setup-system.gif)

Two cards: on the left, what the Pi finds and the Pico board, live; on the right, one block per part
(the Raspberry Pi, the Pico board and each dome camera) with its telemetry, and a button that opens
its details and settings in a window of their own.

**On top, what the Pi finds**: a strip with the Mega, the Pi, the lidar, the Pico board and each
camera, green when found and grey when not, joined by the USB cables (green when both ends are
there). Sabertooth, SyRen, MarcDuino and the controllers do not show: the Pi cannot see them.

**The Pico board, live** (Pico firmware 0.3.0 or newer): a copy of the real board,
to scale and with each part where it is on the PCB: the connectors, the Pico, the DISPLAY button and
the 0.96" display on its module, at its real size. While the display shows one sensor, its
connector gets a yellow frame and an arrow points at it (on the *all* screen, every connector
with a sensor), so the DISPLAY button's steps are easy to follow. Each connector's LED lights and
blinks as the real one, with the sensor's reading beside it; the Pico's own green LED too; the
display shows the real display's picture, pixel for pixel. The **DISPLAY** button works like the
real one: a click is a press, holding it 3 s turns the display off (a bar fills while you hold).
Press the real button and the copy follows. PWR lights when an HC-SR04 answers (they need its 5 V);
with none answering it shows dashed, as the Pico cannot tell. The board only sends this while this
tab is open.

![Setup, System: telemetry](media/manual/setup-system-telemetry.png)

**Telemetry** (the green switch): how busy each part is, read only while it is on and this tab is
open. The gauges are always there: **in colour** while it is on, **grey** with the last values (or
empty) while it is off. Each value is a ring with its colour ranges (green, amber, red), filled up to
the value in its range's colour; hover it for the range seen and the limits. **every** sets how often
it is read (1 to 30 s; the Pico is still asked every 2 s so it keeps sending).

- **Raspberry Pi**: free SD, free RAM, CPU (and each core) and temperature, with its normal, warm and
  throttling zones; a voltage warning shows under them. **Details**: its name, how long it has been
  up, its addresses (cable and R2's WiFi), the system and ROS 2 versions, the software version, and
  **R2's WiFi**: R2's own access point (the one the dome camera joins) picks the quietest of channels
  1, 6 and 11 each time it starts; a bar per channel shows how busy it is (green clear, amber busy,
  red very busy; ● the one in use). **Check now** looks again without dropping anything; **Move to
  the quietest** restarts the access point so it moves (the cameras drop for a few seconds). Needs
  `setup/install_wifi_channel.sh` run once on the Pi.
- **Pico board**: each core's load, the I2C bus and the chip temperature. **Settings**: whether it
  is connected, its firmware, how long it has been up, the readings per second of each sensor, and
  - **its settings**: how long the board's display stays on, its brightness and when its LEDs light
    (*only with the display on*, *always on*, *on, only the ones connected*, *always off*, *only the
    ones failing*); turn the display on (showing the screen you pick) or off; *Identify* makes a
    connector's LED blink;
  - **its firmware**: *Check for update* asks GitHub; *Flash firmware* downloads, builds and flashes
    it from the Pi (a few minutes; not while an automatic mode drives); the window stays open with a
    progress bar until it says it is done. If the copy fails, *Retry* copies it again without building.
- **Each dome camera** (each network camera in cameras.yaml, asked by the Pi): chip temperature, how
  busy each core is (core 0: WiFi and web; core 1: the face or colour finder) and the WiFi signal.
  **Details**: how long it has been up, how many times it has started and why it last did (a
  *crash*, *watchdog* or *brownout* shows in red), how many times the WiFi dropped and why, how fast
  it answers, what it is finding and how often, its clients, memory and firmware. A camera with older
  firmware shows only part of it.

### Setup → File

![Setup, File](media/manual/setup-file.png)

The settings of the last tab you used, as text (`sensors.yaml`, `modes.yaml`, `cameras.yaml`...).
You can edit them here or by hand on the Pi (`~/.config/ros2d2/`): both edit the same file. **Save**
checks the file first and does not save a broken one.
