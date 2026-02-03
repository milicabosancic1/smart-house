# PI1 Smart Home (KT1 + KT2)

Ovaj paket sadrži:
- **KT1**: PI1 skripta (senzori + simulacija + ispis + konzolna kontrola aktuatora)
- **KT2**: MQTT batch slanje + Flask server (MQTT -> InfluxDB) + Grafana (paneli) + MQTT komande za aktuatore

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
