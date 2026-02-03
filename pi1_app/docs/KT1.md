# KT1 – PI1 skripta (Smart Home)

## Šta je implementirano
- Skripta se pokreće na **PI1** i upravlja **PI1** uređajima:
  - Senzori: `DS1` (button), `DPIR1` (PIR), `DUS1` (ultrazvučni), `DMS` (membranski prekidač – simulacija)
  - Aktuatori: `DL` (LED), `DB` (buzzer)
- **Konfiguracija** omogućava da svaki uređaj bude:
  - `enabled=true/false` (uključen/isključen)
  - `simulated=true/false` (simuliran ili realan preko GPIO pinova)
- **Ulazni podaci sa svakog senzora se ispisuju u konzoli** (timestamp + kod + vrednost).
- **Upravljanje aktuatorima kroz konzolnu aplikaciju** (REPL komande `led ...`, `buzzer ...`).

## Kako se podešava simulacija
Sve se podešava u `simulation/settings.json`.
Primer:
- da DS1 bude realan: `"DS1": {"enabled": true, "simulated": false, "pin": 5, "pull":"UP"}`
- da DUS1 bude isključen: `"DUS1": {"enabled": false, ... }`

## Kako se pokreće
U folderu `pi1_app/simulation`:

```bash
python main.py
```

## Napomena
Web kamera (`WEBC`) nije implementirana (nije potrebna za KT1).
