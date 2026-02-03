# KT2 – Proširenje (MQTT + InfluxDB + Grafana)

Ovo proširenje nadograđuje KT1 skriptu na **PI1** tako da:
1. očitava ili simulira senzore/aktuatore (kao KT1)
2. **batch-uje** poruke (queue + daemon nit) i šalje ih preko **MQTT**
3. server preuzima MQTT poruke i upisuje ih u **InfluxDB**
4. **Grafana** prikazuje podatke u panelima

## 1) Konfiguracija (`simulation/settings.json`)

KT2 format:

```json
{
  "global": {
    "pi_id": "PI1",
    "mqtt": {
      "enabled": true,
      "broker": "localhost",
      "port": 1883,
      "batch_interval_sec": 5
    }
  },
  "devices": {
    "DS1": {
      "enabled": true,
      "simulated": true,
      "pin": 5,
      "poll_s": 0.1,
      "device_name": "Door Sensor (Button)",
      "topic": "home/pi1/door/button"
    }
  }
}
```

Svaka poruka ima tag `simulated` u payload-u.

## 2) Pokretanje infrastrukture (na laptopu)

U folderu `pi1_app`:

```bash
docker compose up -d
```

Servisi:
- MQTT broker: `localhost:1883`
- InfluxDB: `http://localhost:8086`
- Grafana: `http://localhost:3000`

InfluxDB init token (za demo) je u `docker-compose.yml`:
`super-secret-token-change`

## 3) Pokretanje servera (MQTT -> InfluxDB)

```bash
cd pi1_app/server
pip install -r requirements.txt

# Windows PowerShell primer:
$env:INFLUX_TOKEN="super-secret-token-change"
python app.py
```

Health endpoint:
- `GET http://localhost:5000/health`

## 4) Pokretanje PI1 aplikacije

Na Raspberry Pi (ili PC-u sa simulacijom):

```bash
cd pi1_app/simulation
pip install -r requirements_pi.txt
python main.py
```

## 5) Kontrola aktuatora preko MQTT (opciono)

Server ima endpoint koji objavi MQTT komandu:

- LED:
```bash
curl -X POST http://localhost:5000/actuator/pi1/led -H "Content-Type: application/json" -d "{"state":true}"
```

- Buzzer beep:
```bash
curl -X POST http://localhost:5000/actuator/pi1/buzzer -H "Content-Type: application/json" -d "{"action":"beep","ms":150,"count":2}"
```

PI1 aplikacija sluša:
- `home/pi1/cmd/#`
