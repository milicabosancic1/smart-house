# PI1 – Povezivanje uređaja (BCM pinovi)

Ovaj projekat može da radi u **simulaciji** i na **pravom Raspberry Pi**.

## Osnovno
- U `simulation/settings.json` za pravi hardver postavi `"simulated": false` za uređaje koje stvarno povezuješ.
- Svi pinovi u projektu su **BCM (GPIO)** numeracija.
- Obavezno poveži **zajednički GND** (sve mase zajedno).

## DS1 – Door Sensor (taster)
Default u `settings.json`:
- `pin: 5`
- `pull: UP`
- `use_events: true`
- `debounce_ms: 150`

Preporučeno vezivanje (kao u vežbama sa tasterom):
- Taster između **GPIO5** i **GND**
- Pull-up je uključen u kodu (`PUD_UP`), pa nema potrebe za spoljnim otpornikom.

## DPIR1 – PIR senzor pokreta
Default:
- `pin: 19`
- `use_events: true`

Vezivanje (tipični PIR modul):
- VCC → 5V (ili 3.3V ako modul podržava)
- GND → GND
- OUT → **GPIO19**

## DUS1 – Ultrazvučni senzor (HC-SR04)
Default:
- `trigger_pin: 23`
- `echo_pin: 24`

Vezivanje:
- VCC → 5V
- GND → GND
- TRIG → **GPIO23**
- ECHO → **GPIO24** (NAPOMENA: ECHO je 5V, obavezno spusti na 3.3V deliteljem napona)

## DMS – Membranska tastatura 4x4 (matrica)
Default pinovi su preuzeti iz primera sa vežbi:
- Row: `[25, 8, 7, 1]`
- Col: `[12, 16, 20, 21]`

Default keymap:
- R1: `1 2 3 A`
- R2: `4 5 6 B`
- R3: `7 8 9 C`
- R4: `* 0 # D`

Vezivanje:
- 4 Row žice na GPIO: **25, 8, 7, 1**
- 4 Col žice na GPIO: **12, 16, 20, 21**

U kodu su kolone podešene sa internim pull-down (`PUD_DOWN`), kao u vežbama.

## DL – Door Light (LED)
Default:
- `pin: 6`

Vezivanje:
- GPIO6 → otpornik (npr. 220Ω) → anoda LED
- katoda LED → GND

## DB – Door Buzzer
Default:
- `pin: 13`

Ako imaš "active" buzzer modul koji radi na 3.3V/GPIO:
- SIG → GPIO13
- GND → GND

Ako je buzzer jači ili traži više struje, koristi tranzistor (NPN) + diodu po potrebi.
