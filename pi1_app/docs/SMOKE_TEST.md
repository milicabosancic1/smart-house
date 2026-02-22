# FINALNI SMOKE TEST CHECKLIST (15 min)

## Cilj
Verifikuj da sve funkcionalnosti rade pre odbrane. Redosled je optimizovan za minimalnu čekanju i maksimum vidljivosti.

---

## FAZA 0: SETUP (5 min)

### 0.1 Docker infrastruktura
```powershell
cd pi1_app
docker compose up -d
# Čekaj 10s
docker compose ps
```
**✓ Očekuj**: `mosquitto`, `influxdb`, `grafana` u stanju `Up`.

### 0.2 Server
```powershell
cd server
$env:INFLUX_TOKEN="super-secret-token-change"
py app.py
```
**✓ Očekuj**: `[MQTT] enabled`, `[STATE] rules thread running`, ili slična poruka. Ctrl+C NE gaši još!

### 0.3 PI1 simulacija (novi terminal A)
```powershell
cd pi1_app/simulation
py main.py
```
**✓ Očekuj**: `Starting Smart Home app (KT1+KT2) on PI1`, senzorski eventi u konzoli.

### 0.4 PI2 simulacija (novi terminal B)
```powershell
cd pi1_app/simulation
$env:SIM_SETTINGS_FILE="settings_pi2.json"; py main.py
```
**✓ Očekuj**: `Starting Smart Home app ... on PI2`.

### 0.5 PI3 simulacija (novi terminal C)
```powershell
cd pi1_app/simulation
$env:SIM_SETTINGS_FILE="settings_pi3.json"; py main.py
```
**✓ Očekuj**: `Starting Smart Home app ... on PI3`.

### 0.6 Web + Grafana (browser, 4 taba)
- Tab 1: http://localhost:5000/ (web app)
- Tab 2: http://localhost:3000/d/smarthome-kt2/smart-home-kt2 (Grafana)
- Tab 3: http://localhost:8086 (InfluxDB Web UI — opciono, za debug)
- Tab 4: MQTT explorer (opciono, npr. https://www.mqttool.com/ — zatvori ako ne trebaš)

**✓ Očekuj na Tab 1**: Status prikazan ("Alarm idle", person count, timer čini), "Arm" dugme vidljivo.

---

## FAZA 1: KT1 + KT2 OSNOVA (2 min)

### 1.1 Siladni senzori u Grafani
Na Tab 2 (Grafana), skroluj dolje i potraži panele:
- `DS1 - Door Button` (bar jedan 0/1 sample trebalo da se pojavi)
- `DPIR1 - Motion`
- `DUS1 - Ultrasonic Distance (cm)`
- `DMS - Membrane Switch`
- `DHT1/2/3 - Temperature` i `DHT1/2/3 - Humidity`
- `GSG - Gyroscope`

**✓ Očekuj**: Barem po jedan `Point` na svakom panelu (nema greške, linija je vidljiva).

### 1.2 MQTT logovanje
U `server` terminalu, pogledaj `[MQTT]` linije — trebalo bi da vidíš mesidže sa PI1, PI2, PI3 redosled.

**✓ Očekuj**: `[MQTT] home/pi1/door/button -> [...]`, `[MQTT] home/pi2/kitchen/dht -> [...]`, itd.

---

## FAZA 2: ALARM LOGIKA (3 min)

### 2.1 Arming + PIN
Na Tab 1 (web app):
1. Klikni **`Arm (10s)`**
2. Poklaj da se `system_armed` menja sa `false` na `true` nakon ~10s (refresh je automatski, svaku sekundu).

**✓ Očekuj**: `System armed: true` nakon 10s.

### 2.2 DS1 → alarm (armed)
U `server` terminalu, pokreni:
```powershell
docker compose exec mosquitto mosquitto_pub -h localhost -t home/pi1/door/button -m "[{\"pi\":\"PI1\",\"code\":\"DS1\",\"device_name\":\"Door Sensor\",\"value\":1,\"simulated\":true,\"ts\":1730000000}]"
```

**✓ Očekuj na Tab 1**: `ALARM ACTIVE` u crvenoj boji.
**✓ Očekuj na Tab 2 (Grafana)**:  Panel `ALARM Events (ON/OFF)` pokazuje novi `Point` na aktivnom vremenu.

### 2.3 Alarm OFF via web
Na Tab 1, klikni **`Alarm OFF`**.

**✓ Očekuj**: `Alarm idle` ponovo vidljivo, `System armed: false`.

---

## FAZA 3: DS TIMEOUT > 5s (2 min)

### 3.1 Pošalji DS2=1, čekaj >5s, zatim DS2=0
```powershell
# Otvoreno
docker compose exec mosquitto mosquitto_pub -h localhost -t home/pi2/door/button -m "[{\"pi\":\"PI2\",\"code\":\"DS2\",\"device_name\":\"Door Sensor 2\",\"value\":1,\"simulated\":true,\"ts\":1730000001}]"
```

**✓ Očekuj**: Ništa se ne dešava trenutno (5s čeka).

Sačekaj **6 sekundi**, zatim:
```powershell
# Zatvoreno
docker compose exec mosquitto mosquitto_pub -h localhost -t home/pi2/door/button -m "[{\"pi\":\"PI2\",\"code\":\"DS2\",\"device_name\":\"Door Sensor 2\",\"value\":0,\"simulated\":true,\"ts\":1730000007}]"
```

**✓ Očekuj na Tab 1**: `ALARM ACTIVE` sa razlogom `DS2_open_too_long`.
**✓ Očekuj na Tab 2**: Novi event u `ALARM Events` panelu.

### 3.2 Alarm OFF
Na Tab 1, klikni **`Alarm OFF`**.

---

## FAZA 4: TIMER + BTN (1 min)

### 4.1 Web timer kontrola
Na Tab 1:
1. U polje `120` promeni na `60`, klikni **`Set`**.
2. Pokaži da je `Timer: 01:00`.
3. Klikni **`Start`**.
4. Pokaži brojač koji se smanjuje (refresh svakih 1s).

**✓ Očekuj**: `Timer: 00:59`, `00:58`, ..., brojač ide nadole.

### 4.2 Timer +30s
Klikni **`+30s`**.

**✓ Očekuj**: Timer skače za ~30s (npr. sa `00:45` na `01:15`).

### 4.3 Timer stop
Klikni **`Start`** (toggle off).

**✓ Očekuj**: `Timer running: false`, brojač staje.

---

## FAZA 5: BRGB / IR / LCD (1 min)

### 5.1 BRGB kontrola
Na Tab 1:
1. U boji polje stavi `#ff0000` (crvena).
2. Klikni **`ON`**.

**✓ Očekuj na Tab 1**: `BRGB state: true`, `color: #ff0000`.
**✓ Očekuj u PI3 terminal**: `[BRGB] state=True color=#ff0000`.

### 5.2 LCD rotacija
Pokaži da se u `LCD: ...` svakih ~4s menja tekst (DHT1 → DHT2 → DHT3 → DHT1, itd.).

**✓ Očekuj**: Tekst se smenji periodično (npr. `LCD: DHT1 T:21.5C H:45%` → `DHT2 T:19.8C ...`).

---

## FAZA 6: KAMERA (opciono, ako imaš USB kamera)

### 6.1 Pokreni mjpg_streamer (ako kamera dostupna)
Na PI1 ili na drugoj mašini sa kamerom:
```bash
mjpg_streamer -i "input_uvc.so" -o "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www" &
```

### 6.2 Postavi WEBC_URL u serveru
U `server` terminalu **gašim `Ctrl+C`**:
```powershell
$env:WEBC_URL="http://<raspberry_pi_ip>:8080/?action=stream"
py app.py
```

### 6.3 Web app prikazuje kamerw
Na Tab 1, trebalo bi da vidiš `img` sa live stream.

**✓ Očekuj**: Kamera se vidi u aplikaciji.

---

## FINALNA PROVERA (1 min)

### 6.1 Alarm može biti isključen PIN-om (simulacija)
Ako želiš, ručno pošalji DMS događaj sa PIN-om `1234` i pokaži da alarm biva gašen.

### 6.2 Grafana panel osvežavanja
Na Tab 2, postavi `Refresh` na `5s` i `Time range` na `Last 15m` — pokaži da se novi eventi pojavljuju u realnom vremenu.

### 6.3 Web app live status
Na Tab 1, pokazuje `last event` alarm, trenutni state...

---

## AKO NEŠTO NE RADI

- **Nema MQTT događaja**: Proveri da su svi 3 PI procesa pokrenuti, da je `mosquitto` živ (`docker compose ps`), da server loguje MQTT.
- **Grafana nema panela**: Reload browser Tab 2, proveri `Last 15m` i `Refresh 5s`.
- **Web nema stanja**: `http://localhost:5000/health` — trebalo bi `{"status": "ok", ...}`.
- **Alarm ne radi**: Pokaži da je sistem sa `system_armed=true` pre nego što pošalješ DS signal.
- **4SD/LCD/BRGB nema komande**: Pogledaj u PI terminalu — trebalo bi da vidiš `[4SD] ...`, `[LCD] ...`, `[BRGB] ...` poruke.

---

## SUMMARY ZA KOMISIJU (kad sve radi)

1. **KT1**: Senzori su čitani, ispis u konzoli ✓
2. **KT2**: MQTT batch slanje, InfluxDB čuva, alarm eventi ✓
3. **Alarm logika**: DS timeout, PIN, armed/disarm ✓
4. **Web aplikacija**: Prikazuje stanje, omogućava kontrolu ✓
5. **Grafana**: Svi senzori imaju panele, alarm eventi se prate ✓
6. **Kamera (bonus)**: Živa slika ako je dostupna ✓

**OK — gotovo za odbranu!**

---

## VREN OM
- Faza 0: ~3 min (docker, 3 terminala, browser tabovi)
- Faza 1-6: ~12 min (test svake funkcionalnosti)
- **TOTAL: ~15 min** — tačno kao na odbrani.
