RNG-ELIGIBLE: 24

# dynamics.md — a dinamika-katalógus

Ez a fájl a dinamika-katalógus **egyetlen tulajdonosa**. Minden rendszerdinamika
itt van definiálva, egyszer. A többi referenciafájl (`methodology.md`,
`healing-sentences.md`, `body-language.md`) **DYN-azonosítóra hivatkozik**, és
nem ismétli meg a dinamikák tartalmát — ha egy dinamika leírása változik, csak
itt változik.

A **DYN-id** stabil és befagyasztott: `DYN-01`-től folytonosan, sorszám sosem
kerül újrafelhasználásra, akkor sem, ha egy sor később kikerülne.
Az **ELIGIBLE-index** ettől külön dolog: összefüggő `1..k` számozás, amit
**kizárólag a véletlen húzás** használ (`SKILL.md` "Mező-szimuláció"). Nem
azonos a DYN-id-vel, és a `NEVER` partícióba tartozó sorok nem kapnak ilyen
indexet (`-`). A fájl első sora (`RNG-ELIGIBLE: 24`) adja a húzás felső határát.

## A katalógus

| DYN-id | ELIGIBLE-index | trigger-feltetel | erzet | testi impulzus | tipikus megszolalas | oldo mozdulat | particio | forras |
|---|---|---|---|---|---|---|---|---|
| DYN-01 | 1 | Van a rendszerben meg nem nevezett, elhallgatott vagy "rossz hiru" tag; vagy a kliens olyan mintat ir le, ami a sajat elettortenetebol nem kovetkezik | A sajat kontur elmosodottabb lett, mint az elozo korben; hidegebb a hat mogotti ter | Hatrafordulas kesztetese; a tekintet a csoporton kivulre huz | "Van itt valaki, akit nem neveztunk meg. En az o helyen allok." | Uj kepviselo a kizartnak, a kor szelen; a kliens-kepviselo ranez es megnevezi: "Latlak, te is hozzam tartozol" | ELIGIBLE | [F7][F26] |
| DYN-02 | 2 | A kliens egy szulo destruktiv mintajat ismetli (ital, munka, kapcsolati minta), es huseg-erzeskent eli meg | A jaras ritmusa atvaltott a masikera; a hang melyebb lett, mint elobb | Felveszi a szulo-kepviselo tartasat, ugyanabban a szogben all | "Ugy csinalom, ahogy te. Igy maradok veled." | A ketto szembe egymassal; a kliens-kepviselo egy lepest hatra: "En a sajat modomon szeretlek teged" | ELIGIBLE | [F7] |
| DYN-03 | - | CSAK ha a kliens intake-je maga nevezett meg halalt koveto vagy "utanad megyek" temat. Huzasbol sosem jon | A talaj mintha elhuzodna a lab alol; a suly elore-lefele csuszott az elozo allashoz kepest | Megallithatatlannak erzett lepes egy elhunyt kepviseloje fele | "Nem maradok itt nelkuled." | Az elhunyt kepviseloje leul vagy hatralep; a kliens-kepviselo felall es a jelen fele fordul: "Te vagy a halott, en meg elek. Meg maradok" | NEVER | [F7][F28] |
| DYN-04 | - | CSAK ha az intake maga nevezte meg az atvallalt szenvedes vagy betegseg temajat | Nehezebb lett a mellkas, mintha mas terhe kerult volna ra | Elore-fole hajlas a szenvedo kepviseloje fele, a vall behuzasa | "Inkabb en, mint te." | Szimbolikus visszaadas: a kliens-kepviselo kinyitja a tenyeret es leengedi a kart: "A te sorsod a tied. En a sajatomat viszem" | NEVER | [F7][F28] |
| DYN-05 | 3 | A kliens ugy irja le magat, mint aki egy szulo hianyat potolja, vagy aki "mindig o old meg mindent" | Melegebb lett a felsotest, merevebb a hat; nagyobb nyomas a vallon, mint az elozo korben | A szulo fele nyulo kar, ami nem talal celt | "Jovateszem, ami neked hianyzott." | A kliens-kepviselo a gyerek helyere kerul, alacsonyabb poziciora: "Te vagy a nagy, en a kicsi. A te hianyod nem az en dolgom" | ELIGIBLE | [F7][F26] |
| DYN-06 | 4 | Haboru, uldoztetes, kitelepites, eroszakos halal a felmenoknel; a kliensnel ok nelkuli riadtsag, panik | Gyorsabb lett a legzes, hidegebb a tarko; a ter szukebbnek erzodik, mint elobb | Osszerandulas, dermedt allas, kitagult szem | "Valami tortent, ami nem az en idomben tortent." | Kepviselo az esemenynek, a felmeno ele; a kliens-kepviselo hatrabb, biztonsagos tavolsagba: "Ez a te idodben tortent, nem az enyemben" | ELIGIBLE | [F7] |
| DYN-07 | 5 | A kliens ismetlodoen elrontja a sajat sikeret, nem enged maganak jot; a csaladban feldolgozatlan igazsagtalansag van | Rosszabb lett, amikor a jo hir elhangzott; a gyomor osszehuzodott | Elhuzodas a jotol, a kez hatrahuzasa | "Nem all jogomban, hogy nekem jobb legyen." | Az igazsagtalansag elszenvedojenek kepviseloje bejon es megtisztelest kap: "Latom, mit fizettel. En elfogadom, ami az enyem" | ELIGIBLE | [F7] |
| DYN-08 | 6 | El nem ismert vagy el nem gyaszolt halott a rendszerben; a kliens folyamatos "huzast" ir le a mult fele | Hidegebb lett a jobb oldal, mintha valaki kozel allna, akit nem latunk | A tekintet ismetelten lefele es a hatso terbe csuszik | "Valaki all mogottem, es senki nem nez ra." | A halott kepviseloje bejon, helyet kap, a kliens-kepviselo meghajol: "Latlak. Megkapod a helyed. Nem kapaszkodom beled" | ELIGIBLE | [F7][F18] |
| DYN-09 | 7 | Valakit kitagadtak, elkuldtek, nem beszelnek rola; vagy a kliens kivulallonak erzi magat a sajat csaladjaban | A kor szele felol hidegebb; a kepviselo tavolabbnak erzi magat, mint ahol all | Oldallepes kifele, kilepes a korbol | "Nekem itt nincs helyem." | A kort ujra zarjuk, a kepviselot fizikailag bevesszuk a vonalba: "Te is hozzank tartozol, barmi tortent" | ELIGIBLE | [F26][F30] |
| DYN-10 | 8 | Kesobb erkezo all a korabban erkezo elott (gyerek a szulo elott, kisebb testver a nagyobb elott); a kliens dont a szulei helyett | Instabilabb lett az egyensuly, mint az elozo helyen; a lab nem talalja a sulypontot | Apro korrekcios lepesek, a torzs hatracsavarodasa | "Elottetek allok, es ez nem jo hely." | Idorendbe rendezes: a korabban erkezok elore, a kesobbiek moge: "Te vagy a nagy, en a kicsi. Bekeben hagylak" | ELIGIBLE | [F26][F28] |
| DYN-11 | 9 | Egyoldalu kapcsolat: valaki csak ad, a masik csak kap; vagy a kliens nem tud elfogadni | A kar nehezebb lett a nyujtas vegen; a mellkas zarul, amikor felajanlanak valamit | Az egyik fel folyamatosan elore nyujtja a kezet, a masik a hata moge teszi | "En csak adok." / "En nem tudom elvenni." | Egy szimbolikus atadas-atvetel a ketto kozott: "Elfogadom, amit adtal, es a magamet adom tovabb" | ELIGIBLE | [F26] |
| DYN-12 | 10 | Korai szetvalas, korhaz, mas gondozo, elutasitas az elso evekben; a kliensnel hideg vegtagok, kimerultseg, tartos kapcsolat hianya | Az anya-kepviselo fele indulo mozdulat feluton lefagy; hidegebb lett a kez, mint elobb | Fel lepes elore, majd megallas; a tekintet elfordul | "Elindultam feled, es megalltam." | A mozdulat lassu, tudatos befejezese: a kliens-kepviselo vegigmegy a felbeszakadt uton, a szulo-kepviselo mozdulatlan es fogado: "Most vegigmegyek" | ELIGIBLE | [F17] |
| DYN-13 | 11 | A kliens gyerekkoraban a szuleje szuloje volt: gondoskodott, kozvetitett, dontott helyette | Felnottnek erzi magat egy gyerek helyen; magasabban a vall, mint az elozo korben | Elore-fole hajlas a szulo fele, mintha tamasztana | "En vigyaztam ra. Nekem kellett erosnek lennem." | Pozicio-csere: a szulo-kepviselo elore, a kliens-kepviselo moge: "Te vagy a szulo, en a gyerek. Visszaadom, ami a tied" | ELIGIBLE | [szintezis] |
| DYN-14 | 12 | A kliens elettortenete nem magyarazza a mintat; egy felmeno sorsa ismetlodik (eletkorok, evszamok, esemenytipusok egybeesnek) | A sajat eletkor erzete elcsuszott; masfajta faradtsag, mint az elozo korben | Ugyanaz a tartas es szog, mint a felmeno kepviselojenel | "Az o eletet elem, nem az enyemet." | A ketto szembeallitasa, majd a kliens-kepviselo kilep a vonalbol a sajat helyere: "Ez a te sorsod volt. Az enyem mas" | ELIGIBLE | [F7] |
| DYN-15 | 13 | A kliens egesz eleten at tarto keresest, megmagyarazhatatlan maganyt vagy "hianyzik egy darab" erzest ir le. Csak elvetheto hipoteziskent kinalhato | Uresebb lett a bal oldal; a kepviselo olyasvalaki fele fordul, aki nincs ott | A kez oldalra nyul, tarsat keres | "Volt itt mellettem valaki." | Kepviselo a testvernek, hely a rendszerben - nem bucsu, hanem elismeres: "Te a testverem vagy. Latlak. Mindig lesz helyed" | ELIGIBLE | [F10][F11] |
| DYN-16 | 14 | Az intake-ben elhangzott veteles, halva szuletes vagy korai gyerekhalal; vagy a szuloknel meg nem nevezett "lett volna meg egy" | A szulo-kepviselo tekintete atsiklik a kliens-kepviselon; lathatatlanabb lett, mint az elozo korben | A szulo-kepviselo teste egy ures pont fele fordul | "Nem engem nezel." | Kepviselo az elveszett gyereknek, a testverek szuletesi sorrendjebe allitva: "Te vagy a testverem. Neked is van helyed kozottunk" | ELIGIBLE | [F30][F18] |
| DYN-17 | 15 | A szulo vagy nagyszulo korabbi hazassaga, jegyese, elhagyott partnere; vagy a jelen kapcsolatban egy ki nem mondott elozmeny | A par kozott szukebb lett a ter, mint az elozo felallasban; harmadik jelenlet erzete | A par egyik tagja oldalra pillant, mielott a masikra nezne | "Nem vagyunk ketten." | A korabbi partner kepviseloje bejon, megtisztelest kap, majd a par mogott, tavolabb kap helyet: "Koszonom, hogy helyet csinaltal. Elismerlek" | ELIGIBLE | [F30] |
| DYN-18 | 16 | Orokseg, vagyon, allas vagy tulelesi elony, ami masok karabol vagy halalabol szarmazott a csaladban | Rosszabb lett, amikor a nyereseget megneveztuk; sullyed a gyomor | Hatralepes arrol a helyrol, ami a nyereseget jeloli | "Ami az enyem, valakinek a karabol lett." | A karosult kepviseloje bejon, meghajlas fele: "Latom, mibe kerult ez neked. Tisztelettel viszem tovabb" | ELIGIBLE | [F30] |
| DYN-19 | - | CSAK ha a kliens intake-je maga nevezte meg. Huzasbol sosem jon | A mezo egy pont korul elnemul; csendesebb lett, mint az elozo korben | Minden kepviselo elfordul ugyanabbol az iranybol | "Rola nem beszelunk." | Kepviselo, hely, meghajlas, egyetlen mondat - grafikus reszletezes es jelenetezes nelkul: "Latlak. Te is hozzank tartozol" | NEVER | [F30] |
| DYN-20 | - | CSAK ha az intake maga nevezte meg a bantalmazast vagy a tettes-aldozat viszonyt | A ter ket felere szakadt; az egyik oldalon melegebb, a masikon hidegebb lett | Az egyik kepviselo elfordul, a masik utananez | "Nem allok vele ugyanabban a terben." | Kulon hely mindkettonek. Semmilyen kozeledes, terdeles vagy bocsanatkeres nem kerheto. A felelosseg ott marad, ahol tortent: "Ami tortent, a te felelosseged. En nem hordom tovabb" | NEVER | [F30][F32] |
| DYN-21 | - | CSAK ha a kliens maga hozta be, es a K-kapu nem all fenn (nincs jelen ideju onveszely). Huzasbol sosem jon | A test egy resze mintha nem tartozna a kepviselohoz; tompabb lett, mint az elozo korben | Befele fordulo, a sajat testre iranyulo mozdulat | "Valakinek fizetnie kell." | Nincs jelenetezes: megnevezes, majd a kiegyenlites atteresztese egy kepviselore (DYN-07 oldo iranya): "Nem az en testem a fizetseg" | NEVER | [szintezis] |
| DYN-22 | 17 | A problema tunetkent jelenik meg (betegseg, panik, alvaszavar, fuggoseg), es a kliens kivulallo dologkent irja le | A tunet kepviselojenel: hasznosabbnak erzi magat, mint amikor beallt. A tobbieknel: a figyelem elszivodik | A tunet-kepviselo a kliens es valaki mas koze all | "Azert vagyok itt, hogy ne kelljen odanezned." | Megkerdezzuk, kire nezne a kliens-kepviselo a tunet nelkul, es a tunetet oldalra tesszuk: "Latom, mit vedtel. Mostantol en nezek oda" | ELIGIBLE | [F1][F26] |
| DYN-23 | 18 | Haboru, kitelepites, menekules, kisebbsegi sors vagy kollektiv veszteseg a csaladtortenetben, amit senki nem nevezett meg | A kepviselo tobbes szamban kezd beszelni; tagabb lett a sajat kontur, mint az elozo korben | A tekintet a szoban tulra, a horizont fele | "Nem csak rolam van szo." | Kepviselo a kollektivumnak (egy ferfi a ferfiaknak, egy no a noknek), a csaladi vonal ele allitva: "Ez nagyobb nalam. Latom, es leteszem" | ELIGIBLE | [szintezis] |
| DYN-24 | 19 | A kliens megfogalmazott egy celt, es nevesitheto valami, ami az utjaban all | A Fokusz-kepviselonel keskenyebb lett az ut a Cel fele; a Cel homalyosabb, mint elobb | A Fokusz elindul, majd oldalra terul ki | Az Akadaly: "En allok itt, es nem veletlenul." | Megkerdezzuk az Akadalyt, mit ved; a valasz utan az Eroforras kepviselojet melle allitjuk: "Latom, mit vedsz. Kerek valakit, aki segit" | ELIGIBLE | [F2][F4] |
| DYN-25 | 20 | A problema tartosan fennall, es a megoldas kozelseget a kliens kellemetlennek eli meg | A Fokusz kozelebb lep a Celhoz, es a testben rosszabb lett, nem jobb | A Nyereseg-kepviselo a Fokusz hata moge lep es ott marad | A Nyereseg: "Amig ez megvan, nem kell valtoznod." | A rejtett Nyereseget megnevezzuk es megkoszonjuk, majd megkerdezzuk, mi mas adhatna ugyanezt: "Koszonom, hogy vedtel. Mostantol maskepp kerem" | ELIGIBLE | [F2][F4] |
| DYN-26 | 21 | A kep megall, senki nem mozdul, es a vezeto sem tudja megnevezni, mi hianyzik | Egyszerre mindenkinel laposabb lett a ter; varakozas-erzet, ami nem oldodik | Mindenki ugyanaz fele az ures pont fele pillant | "Hianyzik valaki, de nem tudom, ki." | Helytarto kepviselo "az, ami meg hianyzik" nevvel, es megkerdezzuk, mit erez: "Nem tudom a neved, de latom, hogy kellesz" | ELIGIBLE | [F2] |
| DYN-27 | 22 | A felallasban a Cel es a jovobeli Feladat is jelen van, es a Cel tavolabb all a Fokusztol, mint a Feladat | A Fokusz-kepviselonel surgetes es faradtsag egyszerre; elorehajol, de nem indul | A Feladat fele fordul, mielott a Celt elerne | A Fokusz: "Mar azt csinalom, ami csak azutan jonne." | Sorrend-helyreallitas: megnevezzuk az elso lepest, a Feladatot hatrebb tesszuk: "Eloszor az elso lepes" | ELIGIBLE | [F2] |
| DYN-28 | 23 | A hivatalos tema korul a kepviselok reakcioja tul halvany, vagy egy mellekmondat sokkal erosebb reakciot valt ki | A hivatalos tema kepviselojenel semmi nem valtozott; egy masik iranyban surubb lett a ter | A kepviselok a hivatalos tema mellett elneznek | "Nem errol van szo." | Harmadik kepviselo "a kitakart tema" nevvel; megkerdezzuk a Fokuszt, melyikre nez szivesebben: "Van itt egy masik tema. Adok neki helyet" | ELIGIBLE | [F4] |
| DYN-29 | 24 | A kliens ket lehetoseg kozott orlodik ("vagy ez, vagy az"), es nem tud dontesre jutni | A Fokusz-kepviselo mindket iranyba egyforma huzast erez; a suly ide-oda vandorol | Apro, ismetlodo sulyathelyezes a ket lab kozott | "Barhova lepek, a masikat vesztem el." | Behozzuk a "mindketto" es az "egyik sem" kepviselojet, majd az otodik, nem-poziciot: "Nem csak ez a ketto van" | ELIGIBLE | [F4] |

## NEVER-RNG particio — hasznalati szabaly

A `NEVER` sorok (DYN-03, DYN-04, DYN-19, DYN-20, DYN-21) valódi, forrásolt
dinamikák — azért maradnak a katalógusban, mert egy ülés eljuthat hozzájuk. A
véletlen húzásból viszont **ki vannak zárva**, mert krízistartalmat injektálnának
egy olyan ülésbe, ahol a kliens nem hozta be a témát.

A használat szabálya:

1. **Csak a kliens saját intake-anyaga nyithatja meg.** Ha az intake-ben vagy az
   ülés során a felhasználó maga nevezte meg a témát (halált követés, átvállalt
   szenvedés, öngyilkosság a családban, bántalmazás, önbántás), akkor a sor
   használható. Egyébként nem — sem húzásból, sem vezetői ötletből.
2. **Sosem meglepetés.** A `SKILL.md` precedencia-szabálya érvényes: halál-közeli
   kategóriára felajánlható elvethető hipotézis ("legyen itt egy hely annak, aki
   korán elment"), de NEVER-dinamikát csak megnevezett anyaghoz kapcsolunk.
3. **Visszafogott protokoll.** Megnevezés, méltóság, egyetlen mondat. Nincs
   jelenetezés, nincs grafikus részletezés, nincs hatásvadász kibontás, nincs
   alávetési vagy bocsánatkérési rituálé (`DYN-20`-nál ez kifejezett tiltás).
4. **A képviselő állítása nem tény.** A képviselői észlelés hipotézis és impulzus,
   nem a kliens valódi családjának leírása [F19]. Egyetlen NEVER-sor sem
   használható arra, hogy kimondjuk, mi történt valójában.
5. **A K-kapu elsőbbséget élvez.** Ha jelen idejű önveszély jelenik meg, az ülés
   leáll (`SKILL.md` (K) ág) — a NEVER-sor akkor sem játszható, ha korábban a
   kliens megnevezte a témát. Öngyilkossági gondolat, pszichózis, súlyos
   depresszió vagy friss trauma esetén a módszer eleve ellenjavallt [F20], és a
   facilitátornak nem szabad retraumatizálnia [F9].

## Terbeli olvasasi dimenziok

Amit forrásból olvasunk. Ezek dimenziók, nem jelentések — a jelentést mindig a
képviselők beszámolója adja hozzá, nem a facilitátor szótára.

- **Közel / távol** — szorosan együtt vagy távol állnak-e egymástól [F8].
- **Felé fordulva / elfordulva** — egymás felé vagy egymástól elfordulva [F8].
- **Takarás** — ki takarja el kinek a kilátását [F8].
- **Izoláció** — ki áll egyedül, a csoporton kívül [F8].
- **Alcsoport** — kik alkotnak szövetséget, kik állnak egy blokkban [F8].
- **Tekintetirány mint önálló dimenzió** — nem a testtartás mellékterméke, hanem
  külön kérdezett információ (Blickrichtung). Ezt az eszközök is megerősítik: a
  padlóhorgonyok külön jelöléssel jelzik a nézésirányt, a rendszertábla
  figuráinak pedig arcuk van, hogy egymásra vagy elfelé nézhessenek [F27].
- **Mozgástendenciák** — a képviselői észlelés explicit része: nem csak érzet és
  testérzet, hanem irányított húzás valaki felé vagy valakitől el [F6].

**Az egyetlen publikált konfigurációs szabály** a SySt-vonalról: ha a **Cél
távolabb van a Fókusztól, mint a jövőbeli Feladat**, akkor tipikusan olyan
problémáról van szó, amiben az illető a *második lépést próbálja megtenni az
első előtt* [F2]. Ez a `DYN-27` sor forrása.

**Amire nincs forrás.** Publikált testtartás- és tekintet-szótár **nem létezik**
(lane-a FORRÁS-HIÁNY 3. pont): a dimenziók dokumentáltak, a konkrét
jelentés-hozzárendelések ("lefelé néző tekintet = a halottakat nézi", "remegő
láb = X", fej vs. törzs vs. láb elkülönült olvasata) egyetlen szakmai vagy fő
gyakorlói forrásban sem szerepelnek. Ami empirikusan alátámasztott, az annyi,
hogy a **pozíció** meghatározza az észlelést, és a térbeli elrendezés
nyelvszerű szemantikát követ (Schlötter, 2800 próba / 250 fő) — de hogy melyik
elrendezés pontosan mit jelent, azt a nyilvános ismertetők nem adják meg [F29].
Ezért a `body-language.md` jelentései **a jelen eszköz saját konvenciói**, nem
idézhető módszertani kánon.

## Forrasok

- **[F1]** Family Constellations Europe: *What Happens in a Family Constellation Session? A Step-by-Step Guide* — https://familyconstellationseurope.com/what-happens-in-a-family-constellation-session-a-step-by-step-guide-to-the-family-constellation-process/
- **[F2]** Wikipedia (de): *Systemische Strukturaufstellung* — https://de.wikipedia.org/wiki/Systemische_Strukturaufstellung
- **[F4]** SySt Institut®: *Grundformen der SySt®* — https://syst.info/de/grundformen-der-systr
- **[F6]** Wikipedia (de): *Repräsentierende Wahrnehmung* — https://de.wikipedia.org/wiki/Repr%C3%A4sentierende_Wahrnehmung
- **[F7]** xmoves / Familienstellen-Wiki (Eva & Franz Reuter): *Verstrickungsdynamiken (Ordnungen der Liebe)* — https://www.xmoves.de/familienstellen-wiki/verstrickungsdynamiken/
- **[F8]** Bettina Köthner: *Systemische Aufstellungen: Der Ablauf* — https://bettina-koethner.de/systemische-aufstellungen-ablauf/
- **[F9]** ISCA (International Systemic Constellations Association): *Code of Ethics* — https://isca-network.org/about/code-of-ethics/
- **[F10]** Marina Toledo / Hellinger Institute (2021-05-13): *What is Vanishing Twin Syndrome — Are You a Vanishing Twin Survivor?* — https://www.hellingerinstitute.com/what-is-vanishing-twin-syndrome-and-could-you-be-a-vanishing-twin-survivor/
- **[F11]** Relationship Constellations: *The Vanishing Twin Syndrome in Family Constellations* — https://www.relationshipconstellations.com/post/the-vanishing-twin-syndrome-in-family-constellations-the-unseen-bond-and-its-lasting-impact
- **[F17]** systemstellen.org: *Unterbrochene Hinbewegung — fehlende Bindung* — https://www.systemstellen.org/wiki/familienaufstellung/unterbrochene-hinbewegung/
- **[F18]** systemstellen.org: *Tote und die Dynamik in Familienaufstellungen* — https://www.systemstellen.org/wiki/familienaufstellung/tote/
- **[F19]** DGSF Fachgruppe Systemische Aufstellungen: *Qualitätssicherung für die Aufstellungsleitung* — https://dgsf.org/ueber-uns/gruppen/fachgruppen/fachgruppe-systemische-aufstellungen/qualitaetssicherung
- **[F20]** sana.wiki: *Systemische Therapie und Familienaufstellung* — https://sanawiki.de/systemische-therapie-familienaufstellung/
- **[F26]** lelkidolgaink.hu: *Családállítás lépésről lépésre* — https://lelkidolgaink.hu/csaladallitas-lepesrol-lepesre/
- **[F27]** familienstellen-mit-figuren.de (Systembrett, arccal rendelkező figurák) — https://www.familienstellen-mit-figuren.de/ ; system-in-balance.de: *Systemische Aufstellungen in Einzelarbeit* (Bodenanker nézésirány-jelöléssel) — https://system-in-balance.de/systemaufstellung.html
- **[F28]** NLP Hessen Lexikon: *Aufstellungsarbeit nach Hellinger* ("Lieber ich als du", "Ich folge dir") — https://www.nlp-hessen.de/nlp-lexikon/aufstellungsarbeit
- **[F29]** Schlötter, Peter: *Vertraute Sprache und ihre Entdeckung. Systemaufstellungen sind kein Zufallsprodukt — der empirische Nachweis*, Carl-Auer 2005 — https://www.carl-auer.de/vertraute-sprache-und-ihre-entdeckung
- **[F30]** Saskia John: *Familienaufstellung — Wer gehört zur Schicksalsfamilie?* — https://saskiajohn.de/familienaufstellung/schicksalsfamilie/
- **[F32]** Peaceful Possibilities (Robertson): *Family Constellations — Incest* (felelős gyakorlat kritériumai) — https://www.peacefulpossibilities.ca/family-constellation-calagry-incest/

`[szintezis]` = a jelen eszköz saját szintézise, amelyre a lane-a kutatás nem
ad idézhető forrást (DYN-13 parentifikáció: a lane-a 8.5 csak keresési
összegzést hoz, F-jelölés nélkül; DYN-21 önbántás mint kiegyenlítés: a
`Der gerechte Ausgleich` önszabotázs-leírásának saját kiterjesztése; DYN-23
kollektíva-képviselet: lane-a FORRÁS-HIÁNY 1. pontja szerint a konkrét
gyakorlat dokumentálatlan, ezért forrásra hivatkozva nem állítható).
