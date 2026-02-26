# PI1 Smart Home (KT1 + KT2)

Ovaj paket sadrži:
- **KT1**: PI1 skripta (senzori + simulacija + ispis + konzolna kontrola aktuatora)
- **KT2**: MQTT batch slanje + Flask server (MQTT -> InfluxDB) + Grafana (paneli) + MQTT komande za aktuatore

Za odbranu (15 min runbook): `docs/DEFENSE_15MIN.md`

## 1) Infrastruktura (MQTT + InfluxDB + Grafana)

U folderu `pi1_app/`:

```bash
docker compose up -d
```

- MQTT: `localhost:1883`
- InfluxDB: `http://localhost:8086`
- Grafana: `http://localhost:3000` (admin/admin)

**Grafana je provision-ovana**:
- Data source: InfluxDB (Flux)
- Dashboard: **Smart Home - KT2** (folder *SmartHome*)

> Napomena: u `docker-compose.yml` je dodat `GF_INSTALL_PLUGINS=speakyourcode-button-panel` kako bi se mogla napraviti dugmad za kontrolu aktuatora direktno iz Grafane.

## 2) Server (MQTT -> InfluxDB)

```bash
cd server
pip install -r requirements.txt

# Windows PowerShell primer:
$env:INFLUX_TOKEN="super-secret-token-change"
python app.py
```

Health: `GET http://localhost:5000/health`

Minimal web app (status + control):
- `http://localhost:5000/`
- koristi API rute: `/state`, `/api/system/*`, `/api/alarm/*`, `/api/timer/*`, `/api/brgb`, `/api/camera`
- za prikaz kamere postavi `WEBC_URL` (npr. mjpeg/http stream) pre pokretanja servera

## 3) PI1 aplikacija

```bash
cd simulation
pip install -r requirements_pi.txt
python main.py
```

### Aktuator komande
- LED: `POST http://localhost:5000/actuator/pi1/led  {"state":true}`
- Buzzer: `POST http://localhost:5000/actuator/pi1/buzzer  {"action":"beep","ms":150,"count":2}`

PI1 sluša MQTT komande na: `home/pi1/cmd/#`

### PI1 kamera (WEBC) preko USB + mjpg_streamer

Na Raspberry Pi možeš ručno pokrenuti stream:

```bash
mjpg_streamer -i "input_uvc.so" -o "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www"
```

Stream URL:
- `http://<raspberry_pi_ip>:8080/?action=stream`

Ovaj URL može direktno da ide u `img src` (web aplikacija ga prikazuje preko `WEBC_URL`).

Ako želiš da Python skripta sama startuje `mjpg_streamer`, podesi `global.webcam.enabled=true` i `global.webcam.auto_start=true` u `simulation/settings.json`.

### Laptop fallback (bez Raspberry Pi)

Ako nemaš Raspberry Pi, možeš koristiti laptop kameru kao lokalni MJPEG stream:

```bash
cd pi1_app
py -m pip install -r webcam_requirements.txt
py tools/webcam_stream.py
```

Zatim postavi:

```bash
$env:WEBC_URL="http://localhost:8080/?action=stream"
docker compose up -d --build server
```

Test URL u browseru:
- `http://localhost:8080/?action=stream`

## 4) Simulacija PI2 i PI3 (odbrana)

U folderu `pi1_app/simulation` pokreni zaseban proces po PI profilu:

```bash
# PI1 (postojeći profil)
python main.py

# PI2 profil
$env:SIM_SETTINGS_FILE="settings_pi2.json"; python main.py

# PI3 profil
$env:SIM_SETTINGS_FILE="settings_pi3.json"; python main.py
```

PI2 profil šalje: `DS2`, `DPIR2`, `DUS2`, `DHT3`, `GSG`.
PI3 profil šalje: `DPIR3`, `DHT1`, `DHT2`.
