# ISC MotorBeep — ESP32 dual-stepper + audio board, 3xAA powered

Improved derivative of the ESP32 DevKit DOIT v1.
Target: 2 stepper motors + 1 small speaker, powered from 3x AA cells.

## 1. The supply: 3x AA

| Chemistry      | Fresh | Nominal | Practical cutoff | Usable energy |
|----------------|-------|---------|------------------|---------------|
| Alkaline 3xAA  | 4.8 V | 4.5 V   | ~2.8 V           | ~11 Wh at low current |
| NiMH 3xAA      | 4.2 V | 3.6 V   | 3.0 V            | ~7 Wh, good pulse behaviour |

Going from 2 to 3 cells changes the architecture, it does not just add margin:

- **The motor and audio rails no longer need a converter.** The pack stays
  inside the STSPIN220 (1.8-10 V) and MAX98357A (2.5-5.5 V) supply ranges for
  the whole discharge, so both run **straight off VBAT**. The 5 V boost that
  2xAA forced is deleted: fewer parts, less EMI, and no conversion loss on the
  dominant load.
- **The 3.3 V logic rail still needs a buck-boost.** The pack starts at 4.8 V
  (above 3.3) and ends at 2.8 V (below it), so it crosses the output voltage.
  An LDO would drop out; a plain boost cannot regulate down. This stays
  non-negotiable.
- ~50% more energy than 2xAA, and the boost is gone, so runtime improves by
  appreciably more than 50%.

**Still recommended: NiMH (Eneloop) over alkaline.** Alkaline internal
resistance rises steeply as it discharges, and stepper coil current is pulsed;
the pack voltage will sag under each step. NiMH holds up far better.

## 2. Power architecture

    3xAA --> VBAT (2.8-4.8 V)
      |
      +--> U4, U5  STSPIN220   VS   direct   (1.8-10 V range)   motors
      +--> U6      MAX98357A   VDD  direct   (2.5-5.5 V range)  audio
      +--> U2      TPS63001 buck-boost -----> +3V3              ESP32 + logic

One converter in the whole design. `TPS63001` is the fixed-3.3 V member of the
TPS63000 family (Vin 1.8-5.5 V, 1.7 A switch); on the fixed-output parts **FB is
tied to GND**. Powering the ESP32 through a buck-boost also means it rides
through the VBAT sag caused by motor current pulses instead of browning out.

There is **no load switch** on the motor/audio domain: the STSPIN220 `STBY` and
the MAX98357A `SD_MODE` already put those parts in sub-microamp standby, so a
series FET would add loss and parts for nothing.

### 2.1 USB power path — and the back-feed trap it avoids

USB is for programming, but the board must also be usable with the pack in
place, so the two sources have to be OR'd **without letting USB charge the
batteries**. Alkaline cells being charged is a leak-and-rupture hazard.

The obvious circuit is wrong: a P-MOSFET reverse-polarity "ideal diode" with its
gate at GND is only a diode *until it turns on* — after that it conducts in both
directions. With VBUS = 5 V sitting above VBAT = 4.8 V it would push current
straight back into the pack. So:

    VBUS ---|>|--- D1 Schottky ---+
                                  +--- VIN of U2 (TPS63001) only
    VBAT ---|>|--- D2 Schottky ---+

    VBAT ------------------------------> motors + audio  (battery only, never USB)

- Diodes, not a FET, on the OR: they cannot conduct backwards, so USB can never
  reach the cells.
- The OR feeds **only the 3.3 V converter**. Motors and audio stay on the
  battery, which also stops a 500 mA USB port being asked to drive two steppers.
- Schottky drop ~0.3 V: at a flat pack, 2.8 - 0.3 = 2.5 V, still above the
  TPS63001 1.8 V minimum.
- The reverse-polarity FET is therefore only needed in the battery leg; with
  the Schottky there it becomes optional (see 8.5).

## 3. Stepper drivers — STSPIN220

**STSPIN220 x2** (U4, U5), QFN16 + exposed pad. Chosen because its supply range
starts at **1.8 V**: the usual A4988 / DRV8825 need 8 V and simply cannot run
from a battery pack this size. STEP/DIR ("STCK"/"DIR") interface, microstepping
to 1/256, integrated current control.

Motors are small **bipolar** steppers. Bipolar with current chopping is far more
efficient per unit of torque than the classic 28BYJ-48 unipolar + ULN2003, which
burns power in a Darlington array and has no current regulation at all.

Per-driver pins that need deliberate treatment:

| Pin | # | Treatment |
|---|---|---|
| `STCK`, `DIR` | 2, 1 | from ESP32 |
| `MODE1`, `MODE2` | 16, 15 | resistor straps -> microstep mode |
| `STBY/RESET` | 14 | **pull-down**; ESP32 raises to leave standby |
| `EN/FLT` | 13 | bidirectional: 10k series from GPIO + pull-down, so the open-drain fault can pull it low without fighting the GPIO |
| `REF` | 11 | divider from +3V3 sets the current limit |
| `TOFF` | 12 | resistor to GND sets the chopper off-time |
| `SENSEA`, `SENSEB` | 4, 9 | sense resistors to GND |
| `EPAD` | 17 | to GND — it is the thermal path |

**Microstep latching:** on the STSPIN220 the mode is latched when the device
leaves standby, and `MODE3`/`MODE4` are *multiplexed onto the `STCK`/`DIR`
pins*. Firmware must therefore set STCK/DIR to the wanted mode bits **before**
raising `STBY`, not after. This is the single easiest thing to get wrong.

## 4. Audio

**MAX98357A** (U6): I2S digital input -> Class-D output, 2.0-5.5 V supply,
~92% efficient, no separate DAC needed. Replaces the ESP32's own 8-bit DAC +
analog amp: better SNR, and Class-D matters when the energy budget is 5 Wh.
Runs directly from **VBAT**, `SD_MODE` gated by the ESP32 to mute/shutdown.

## 5. What is actually improved vs. the DOIT DevKit v1

| DOIT v1 weakness | Fix here |
|---|---|
| AMS1117 LDO: ~1.1 V dropout, no low-power mode, burns Vin-Vout as heat | TPS63001 buck-boost; motors/audio need no converter at all |
| Thin bulk capacitance near module -> brownout on WiFi TX bursts | 22 uF bulk + 10 uF + 100 nF at the module, plus a 100 uF reservoir on +3V3 |
| Micro-USB | USB-C receptacle, CC1/CC2 5.1k pulldowns |
| CP2102 (old), no ESD protection on USB | CP2102N + USBLC6-2SC6 ESD array |
| No reverse-polarity protection | P-MOSFET ideal diode (DMG2301L) |
| No battery sensing | divider on an **ADC1** pin, gated by a MOSFET so it draws nothing when idle |
| ADC2 pins unusable while WiFi is on (silent trap) | all analog routed to ADC1 only |
| Strapping pins exposed with no guidance | GPIO0/2/15 kept free of boot-breaking loads; **GPIO12 left NC** (anything on it risks a bad flash-voltage strap) |
| EN/BOOT buttons with marginal RC | proper RC + the two-transistor DTR/RTS auto-reset |

## 6. Sheet plan (hierarchical)

1. `power.kicad_sch`  — battery, Schottky OR, TPS63001 buck-boost, USB-C + ESD, battery sensing
2. `mcu.kicad_sch`    — ESP32-WROOM-32E, decoupling, CP2102N, auto-reset, buttons, LED
3. `motors.kicad_sch` — 2x STSPIN220 + shared bias/straps + connectors
4. `audio.kicad_sch`  — MAX98357A + speaker connector

## 7. Pin budget (ESP32-WROOM-32E)

| Function | GPIO | Note |
|---|---|---|
| M1 `STCK` / `DIR` | 32 / 33 | also carry MODE3/MODE4 at standby exit |
| M2 `STCK` / `DIR` | 25 / 26 | idem |
| Motors `STBY` (shared) | 27 | pull-down: both drivers asleep at reset |
| M1 `EN/FLT` | 14 | 10k series, bidirectional fault line |
| M2 `EN/FLT` | 13 | separate, so a fault is attributable to one motor |
| I2S `BCLK` / `LRCLK` / `DIN` | 18 / 19 / 21 | MAX98357A |
| Audio `SD_MODE` | 22 | mute / channel select |
| VBAT sense | 34 | **ADC1**_CH6, input-only pin |
| VBAT sense gate | 23 | MOSFET, divider draws nothing when idle |
| Status LED | 2 | strapping pin; LED to GND is the safe use |
| User button | 4 | |
| BOOT button | 0 | with the DTR/RTS auto-reset |
| — | **12** | **left NC** — MTDI straps the flash voltage |

Free and brought to a header: GPIO5, 15, 35, 36, 39.

## 8. Detail decisions (review pass)

Things that are easy to get wrong and are fixed deliberately here.

### 8.1 Default-safe straps — the important one
At ESP32 reset every GPIO is high-Z. Anything the ESP32 gates must therefore
have a resistor defining the safe state, or the motors twitch and the speaker
pops at power-up:

| Net | Pull | Why |
|---|---|---|
| `MOT_STBY` (GPIO27 -> both STSPIN220 `STBY`) | 100k **pull-down** | drivers stay in standby, coils unpowered |
| `M1_EN`, `M2_EN` (GPIO14/13 -> `EN/FLT`) | 100k **pull-down** + 10k series | outputs disabled; series R lets the open-drain fault win without fighting the GPIO |
| `AUD_SD` (GPIO22 -> `SD_MODE`) | see 8.3 | amp muted until driven |

**Caveat on GPIO14 (`M1_EN`).** GPIO14 is MTMS and has an *internal pull-up*
active during boot. Through the 10k series resistor against the 100k pull-down
it settles around 2 V, i.e. a logic HIGH, so `M1_EN` is briefly asserted while
the ESP32 boots. This is harmless **only because `STBY` (GPIO27) is the master
gate and has no boot pull** — the driver stays in standby regardless, so no
current reaches the coils. If that ordering ever changes, move the EN lines to
GPIO16/17, which have no boot pulls.

### 8.2 STSPIN220 — current limit and the two easy mistakes
Phase current is set by the `REF` voltage together with the `SENSEA`/`SENSEB`
resistors; `TOFF` sets the chopper off-time. Planned: Rsense = 0.33 ohm, a
39k/10k divider from +3V3 giving VREF ~= 0.67 V, TOFF resistor for ~20 us.
**The exact VREF-to-current gain is a datasheet check before fab** (see 8.5) —
the divider is placed so the ratio can be retrimmed without a layout change.

Two mistakes this design avoids:
- `EPAD` (pin 17) is the only thermal path — tied to GND, not left floating.
- Microstep mode is latched leaving standby and `MODE3`/`MODE4` sit on the
  `STCK`/`DIR` pins, so firmware sets those **before** raising `STBY`.

### 8.3 MAX98357A — SD_MODE is dual-purpose
`SD_MODE` is not a plain shutdown pin: the resistor from it to GND **selects the
channel** through the voltage it develops with the internal pull-up — (L+R)/2,
L only, or R only. The value is therefore chosen deliberately (100k -> (L+R)/2
mono sum, what a single small speaker wants), and the ESP32 pulls the pin low to
mute. `GAIN_SLOT` to GND selects 15 dB, right for a small 4-8 ohm speaker.

Output power tracks VBAT (P ~ V^2), so the speaker gets quieter as the pack
drains. For a "petit haut-parleur" there is ample headroom either way.

### 8.4 CP2102N powered from VBUS, not +3V3
The USB bridge runs off `VREGIN` = VBUS through its own internal LDO, so it
draws **nothing from the battery** when USB is unplugged. (This is the one thing
the DOIT board already gets right; it is kept.)

### 8.5 Open items to confirm against datasheets before fab
Stated as checks, not as facts:
- **STSPIN220 `REF` -> phase-current gain**, and the `TOFF` resistor value for
  the chosen off-time. The divider and Rsense above are a starting point.
- **TPS63001 output current at Vin = 2.8 V.** The ESP32 needs ~500 mA peaks on
  WiFi TX; confirm the buck-boost still delivers that from a nearly-flat pack.
- **Reverse-polarity FET.** At 3xAA the worst-case gate drive is Vgs = -2.8 V
  (against -2.0 V with 2 cells), comfortably inside the DMG2301L
  characterisation — the 3-cell change resolves what was a real concern at 2.
- **Logic-level abs-max on both loads.** The ESP32 drives 3.3 V logic into the
  STSPIN220 and MAX98357A while their own supply may be as low as 2.8 V. Both
  are believed to rate their digital inputs independently of VS (to ~5 V), but
  **if either input rating is VS-referenced the design is broken at low
  battery**. One datasheet line each settles it; it is the single most
  consequential open item on this list.
- **ERC housekeeping:** `PWR_FLAG` on `VBAT` and `VBUS`, otherwise ERC reports
  "power pin not driven" on every rail. *(Done — root ERC is at 0 errors.)*

### 8.6 Footprint caveats found while assigning packages

Both are real and were found by checking, not assumed:

- **USB-C J1 has no exact stock footprint.** The symbol
  `USB_C_Receptacle_USB2.0_16P` exposes 11 pin numbers
  (A1 A4 A5 A6 A7 A8 B5 B6 B7 B8 S1); every stock 16-pad Type-C footprint also
  has A9/A12/B1/B4/B9/B12 for the duplicated VBUS and GND contacts. All 26
  `USB_C_Receptacle_*` footprints were scanned — none matches the symbol
  one-to-one. `USB_C_Receptacle_G-Switch_GT-USB-7010ASV` is assigned as the
  physically correct 16-pad part, but **before layout** either tie the extra
  VBUS/GND pads by hand or move to the 24P symbol + 24P footprint.
- **QFN-16 exposed-pad size is provisional.** U5/U6 (STSPIN220) and U7
  (MAX98357A) are assigned
  `QFN-16-1EP_3x3mm_P0.5mm_EP1.45x1.45mm_ThermalVias`. The body and pitch are
  right; **confirm the exposed-pad dimension** against each datasheet — stock
  variants range from 1.45 to 1.85 mm and the wrong one degrades the thermal
  path that 8.2 depends on.
