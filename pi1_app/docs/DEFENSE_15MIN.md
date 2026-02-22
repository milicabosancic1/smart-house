# Odbrana projekta – 15 min (runbook)

Ovaj plan je optimizovan za stabilnu demonstraciju u kratkom vremenu.
Cilj: jasno prikazati KT1 + KT2 + ključnu logiku odbrane (alarm, multi-PI, web, Grafana).

## 0) Pre-flight (2–3 min pre odbrane)

U root-u `pi1_app/`:

1. Podigni infrastrukturu:
```powershell
docker compose up -d
```

2. Pokreni server:
```powershell
cd server
$env:INFLUX_TOKEN="super-secret-token-change"
py app.py
```

3. Pokreni PI simulacije u 3 terminala (folder `simulation`):
```powershell
# Terminal A (PI1)
py main.py

# Terminal B (PI2)
$env:SIM_SETTINGS_FILE="settings_pi2.json"; py main.py

# Terminal C (PI3)
$env:SIM_SETTINGS_FILE="settings_pi3.json"; py main.py
```

3.1 (Ako koristiš realnu USB kameru na PI1) pokreni `mjpg_streamer`:

```bash
mjpg_streamer -i "input_uvc.so" -o "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www"
```

ili u pozadini:

```bash
mjpg_streamer -i "input_uvc.so" -o "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www" &
```

Stream URL:
- `http://<raspberry_pi_ip>:8080/?action=stream`

Alternativa: uključi `global.webcam.auto_start=true` u `simulation/settings.json` i PI1 `main.py` će pokušati da ga startuje sam.

4. Otvori:
- Web app: `http://localhost:5000/`
- Grafana: `http://localhost:3000` (admin/admin)
- Dashboard: `Smart Home - KT2`

Ako koristiš kameru, pokreni server sa:

```powershell
$env:WEBC_URL="http://<raspberry_pi_ip>:8080/?action=stream"
py app.py
```

---

## 1) Timeline za 15 minuta

## Min 0–2: Arhitektura (kratko)
- 3 PI procesa šalju batch MQTT poruke.
- Server prima MQTT, upisuje InfluxDB.
- Grafana prikazuje senzore + alarm događaje.
- Web aplikacija prikazuje stanje i upravlja sistemom.

## Min 2–5: KT1/KT2 osnova uživo
- U terminalima pokaži da stižu događaji za PI1/PI2/PI3.
- U Grafani pokaži panele za DS/DPIR/DUS/DMS/DHT/GSG tokove (u vremenu).
- Naglasi da je simulacija konfigurabilna po uređaju (`simulated: true/false`).

## Min 5–9: Alarm logika (ključni deo)

1. U web app klikni `Arm (10s)` i sačekaj 10s da `system_armed=True`.
2. Ručno okini DS1 događaj preko MQTT (deterministički):
```powershell
docker compose exec mosquitto mosquitto_pub -h localhost -t home/pi1/door/button -m "[{\"pi\":\"PI1\",\"code\":\"DS1\",\"device_name\":\"Door Sensor\",\"value\":1,\"simulated\":true,\"ts\":1730000000}]"
```
3. Pokaži da je alarm aktiviran (web + Grafana panel `ALARM Events (ON/OFF)`).
4. U web app klikni `Alarm OFF` (ili unesi ispravan PIN na DMS ako demonstriraš tastaturu).

## Min 9–11: Pravilo “DS otvoren > 5s”

1. Pošalji `DS2=1`, sačekaj >5s, zatim `DS2=0`:
```powershell
# otvoreno
docker compose exec mosquitto mosquitto_pub -h localhost -t home/pi2/door/button -m "[{\"pi\":\"PI2\",\"code\":\"DS2\",\"device_name\":\"Door Sensor 2\",\"value\":1,\"simulated\":true,\"ts\":1730000001}]"

# zatvoreno
docker compose exec mosquitto mosquitto_pub -h localhost -t home/pi2/door/button -m "[{\"pi\":\"PI2\",\"code\":\"DS2\",\"device_name\":\"Door Sensor 2\",\"value\":0,\"simulated\":true,\"ts\":1730000007}]"
```
2. Pokaži alarm događaj sa razlogom u web/raw state i u Grafani.

## Min 11–13: Timer + web kontrola
- U web app: `Set 120`, `Start`, zatim `+30s`, pa `Stop`.
- Objasni da timer status ide kroz centralni state i koristi se za 4SD logiku.

Opcionalno (30–60s):
- pokaži `Set BTN step (N)` i sačekaj `BTN` event iz PI2 simulatora da automatski doda N sekundi.

## Min 13–14: GSG + BRGB/IR + LCD
- GSG: sačekaj ili ručno okini poruku sa većim pomerajem i pokaži alarm.
- BRGB: u web app uključi/isključi i promeni boju; u PI3 terminalu vidi komandu.
- LCD: pokaži da se tekst sa DHT1-3 smenjuje periodično.

## Min 14–15: Završni rezime
- Pokazano: multi-PI, MQTT batch, Influx, Grafana, web kontrola, alarm enter/exit događaji.
- Naglasi da je sistem spreman za mix realnog hardvera + simulacije.

---

## 2) Plan B (ako nešto zapne)

- Ako ne radi Grafana panel refresh: u Grafani `Last 15m` + `Refresh 5s`.
- Ako nema MQTT događaja: proveri `docker compose ps` i server terminal log.
- Ako web ne radi: proveri `http://localhost:5000/health`.
- Ako random simulacija ne da željeni scenario: koristi gore navedene `mosquitto_pub` komande.

---

## 3) Šta obavezno verbalno naglasiti

- KT1 i KT2 funkcionalnosti su zadržane i proširene.
- Kritične sekcije su minimalno zaključane, obrada je kroz daemon niti.
- Alarm događaji se čuvaju i vizualizuju (Influx + Grafana).
- Demonstracija je spremna i za realne senzore (prebacivanjem `simulated=false`).
