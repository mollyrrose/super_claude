# Mező-panel — a többügynökös mód

Ez a fájl azt írja le, hogyan fut az ülés úgy, hogy **minden képviselőt külön
AI-ügynök szólaltat meg**, és a teret több, egymástól független szem olvassa.

## Miért

Egyetlen kontextusban a vezető tudja, mit érez minden képviselő, mert ő találja
ki mindet. Hiába szól az utasítás úgy, hogy "a képviselő csak azt tudja, amit
lát" — ez csak ígéret. Külön ügynökökkel **szerkezeti tulajdonság** lesz: az
apa képviselője fizikailag nem kapja meg azt az információt, amit a lánya
képviselője érez, tehát nem is tud rá ráhangolódni.

A cél nem a látvány, hanem ez az egy dolog: hogy a képviselők **tényleg ne
lássanak bele egymásba**, és a köztük lévő ellentmondás valódi legyen.

## Ki mit lát — a brífing szabálya

Minden képviselő-ügynök PONTOSAN ennyit kap:

1. **Kit vagy mit képvisel** — egy sor. ("Az apát képviseled." / "A
   pénztelenséget képviseled.")
2. **A saját ÁLLAPOT-sora** — hol áll, merre néz, milyen a tartása.
3. **Amit LÁT**: azoknak a képviselőknek a sora, akik a látóterében vannak.
   Aki mögötte áll, arról annyit kap: "valaki áll mögötted", név nélkül —
   amíg meg nem fordul.
4. **Ami hangosan elhangzott** az előző körben. Szó szerint, nem összefoglalva.
5. Ha rá vonatkozik egy aktív dinamika: a `dynamics.md` sorából **csak a
   trigger és az érzet** oszlop — az "oldó mozdulat" oszlopot NEM kapja meg.
   (Különben eljátszaná a megoldást ahelyett, hogy megélné a helyzetet.)

Amit **soha nem kap meg**: a kliens története, az intake-válaszok, a vezető
terve, a többi képviselő belső jelentése, a korábbi körök elemzése, és hogy
mi a dinamika neve.

## Mit ad vissza

Kötött alak, legfeljebb 60 szó:

```
gondolat: <ami atfut rajta, egy mondat>
erzes: <a SAJAT elozo allapotahoz kepesti VALTOZAS>
test: <hol, mit erez a testeben>
impulzus: <mit tenne: mozdulat, fordulas, lepes; vagy "semmit">
mondat: <ha van, amit ki akar mondani; egyebkent ures>
```
(A blokk kulcsai ASCII-ban vannak, mint az ALLAPOT-blokke — gepi olvasasra
keszul. A kepviselo VALASZA termeszetesen ekezetes magyar.)

Tilos neki: tanácsot adni, a családot értelmezni, a klienshez beszélni, más
képviselő nevében megszólalni, vagy "megoldani" a helyzetet.

## Mező-lencsék — a teret olvasó panel

Párhuzamosan futó, egymást nem látó olvasók. **A kliens történetét ők sem
kapják meg** — csak a tablót és az elhangzott mondatokat. Így nem tudják
visszamondani a sztorit; tényleg a teret kell olvasniuk.

| Lencse | Mit néz |
|---|---|
| `rend` | Generációs sorrend, ki áll a helyén és ki nem |
| `kizaras` | Ki vagy mi hiányzik, ki fordult el, kire nem néz senki |
| `test` | Testbeszéd-olvasat a `body-language.md` szerint |
| `vektor` | Feszültség-irányok, ki takarja el kinek a kilátását |
| `hiany` | Melyik behozandó elem változtatna a képen |

Mindegyik 2-3 mondatot ad vissza, plusz javasolt DYN-azonosítókat.

## Kereszt-modell hang

Egy MÁSIK gyártó modellje (jelenleg OpenAI) ugyanazt a tablót és
kör-jelentéseket kapja, és önálló olvasatot ad. Ez az egyetlen pont, ahol nem
Claude néz Claude-ra.

- Futtatás a skill sajat konyvtarabol:
  `python scripts/run_field_voice.py --allapot <fajl> --elhangzott <fajl>`
  A ket fajlt a kor vegen irod ki (pl. `.scratch/family-setting/allapot.txt`
  es `.../elhangzott.txt`). Argumentum nelkul, ures stdinnel nem fut.
- Ritmus: minden 2-3. körben, és **mindig a rendezett zárás előtt**.
- Ha nem elérhető: az ülés megy tovább, de a vezető **kimondja**, hogy ebben a
  körben nem volt külső hang.

Őszinte leltár (2026-08-22): OpenAI elérhető; DeepSeek kulcsa megvan, de a
kerete kimerült; GLM, SubQ nincs beállítva; a helyi Ornith nem fut. Tehát a
"sok AI" gyakorlatban: **sok független Claude-kontextus + egy másik gyártó
modellje**. Ne állítsd többnek.

## Szintézis — a vezető dolga

A vezető NEM átlagol. Szabályok:

1. **Az ellentmondás adat, nem hiba.** Ha R3 közeledni akar és R5 épp ettől
   lép hátra, azt kimondod, nem simítod el. A valódi állításban is ez történik.
2. **A külső hangot nevesíted**: "egy másik modell ezt látja a képen: ..." —
   különösen, ha mást lát, mint a többiek.
3. **Az ÁLLAPOT-blokkot csak a vezető írja.** Az ügynökök impulzust jelentenek;
   hogy abból lesz-e mozdulat, azt a vezető dönti el és narrálja.
4. **A kliensnek egy hang szól.** A panel a színfalak mögött van; a
   felhasználó a vezetőt hallja, és a képviselők megszólalásait — nem
   ügynök-jelentéseket.

## Fokozatok és költség

| Mód | Mit indít körönként | Nagyságrend |
|---|---|---|
| `teljes` | minden képviselő külön ügynök + 5 lencse + kereszt-modell | 8-14 hívás/kör |
| `kozepes` (alap) | a 3-4 legaktívabb képviselő + 3 lencse + kereszt-modell a fordulópontokon | 6-8 hívás/kör |
| `egy` | a vezető szólaltat meg mindenkit (az alap-protokoll) | 0 extra hívás |

Egy 9 körös ülés `teljes` módban nagyságrendileg 70-120 ügynökhívás. Ezt
mondd meg a felhasználónak az elején, ne utólag.

Alapértelmezés: `kozepes`. A felhasználó kérheti a `teljes`-t.

## Biztonsági invariánsok — ezek nem alkuképesek

1. **A biztonsági kapu a VEZETŐ kontextusában fut**, minden felhasználói
   üzenetre, **mielőtt bármit kiosztanál**. Képviselő-ügynök soha nem kap
   olyan üzenetet, ami nem ment át a kapun.
2. A képviselő-brífing tartalmaz egy tiltást: nincs krízis-tartalom, nincs
   önbántásra vagy halálra vonatkozó buzdítás, nincs a klienshez intézett
   tanács. NEVER-particíós témánál a brífing a visszafogott protokollt is
   tartalmazza.
3. **Kimeneti ellenőrzés**: a vezető minden ügynök-választ átnéz, mielőtt
   megjeleníti. Ami sérti a fenti tiltást, azt eldobja — és ezt jelzi
   magának, nem játssza tovább.
4. Ha egy ügynök-hívás elbukik, a vezető maga szólaltatja meg azt a
   képviselőt, és megjelöli: `[egy hangon]`. A degradáció látható, nem csendes.

## Amit ez a mód NEM old meg

- Nem teszi a szimulációt valódi állítássá. Több független hang koherensebb
  ellentmondásokat ad, de a mező attól még szimuláció.
- Nem hitelesíti a módszert. Ugyanaz a tudományos státusz, ugyanaz a
  disclaimer.
- Nem csökkenti a kockázatot. A biztonsági kapu ugyanaz marad — sőt, több
  hang mellett szigorúbban kell tartani, mert több helyről jöhet tartalom.
