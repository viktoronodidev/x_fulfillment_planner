Current status (v0.4.08) – In progress
Release date: 2026-01-28
Previous: v0.3.03 finalized
Implemented in Odoo 17 Community:
- Shortage analysis (v0.4.01):
  - planning.batch.shortage model (product-level shortage storage)
  - Analyze Shortage button (on-hand + confirmed/in-progress MO supply)
  - Shortage table with red/green status and drill-down to SO lines
  - Create Suggested MOs (shortage qty only)
  - Last run info (date + user) + completion notification
  - Manufacture tab with MOs + MO lines + created at/by
  - Undo Created MOs (removes draft MOs created by batch) + created at/by
  - Selection tab shows aggregated Selected Products list
- Batch header buttons: Select Sales Orders, Calculate, Create MO (Planner)
- Select Sales Orders wizard (modal):
  - auto-loads open SOs (state = sale) on open
  - search by Order/Customer
  - select/deselect per row + Select All / Deselect All
  - visual status icons (green filled / red outline)
  - SO rows read-only, row-open form shows SO number + SO lines (read-only)
  - Product Summary aggregates selected SO lines by product + UoM
  - Load Sales Orders links selected SOs and SO lines to the batch
- Calculate = validation only (sets status/message on batch lines, moves batch to Calculated)
- Create MO = persistence (aggregated MO per product, default BOM, links MO to batch lines)
- Company filter applied when multi-company is active

Codex prompt – v0.1 (Planning Batch alap)
Prompt:
Odoo 17 Community modult fejlesztesz az x_fulfillment_planner addonban.
Cél: v0.1 stabil MVP.
Feladat:
1.	Hozz létre egy új modellt: planning.batch.
2.	Mezők:
•	name (Char, required, default: sequence, 7 jegy paddinggel)
•	status (Selection: draft / calculated / confirmed / done, default draft)
•	date (Date, required)
•	note (Text)
•	create_date (system)
3.	Hozz létre:
•	tree view
•	form view
4.	Form view-ben:
•	header statusbar (draft → calculated → confirmed → done)
•	semmilyen automatizmus
5.	Security:
•	ir.model.access: admin full + backoffice csoport full
•	backoffice csoport külön létrehozva (implied: base.group_user)
•	jogosultság bővíthető későbbi role-okkal
Korlátok:
•	Community only
•	Nincs integráció SO/MO/Stock felé
•	Teljes fájlokat adj vissza
Minden döntési pontnál kérdezz, ha:
•	mező típusa vitatható
•	sequence vs manuális név kérdéses
Definition of Done (v0.1):
•	Modul telepíthető.
•	Batch létrehozható UI-ból.
•	Tree + form stabil.
________________________________________
Codex prompt – v0.2 (Egységes workflow UI – read-only)
Prompt:
Odoo 17 Community, x_fulfillment_planner.
Ez a v0.2, a v0.1-re épül.
Cél: egységes, READ-ONLY áttekintő UI a Batch-en belül.
Feladat:
1.	Bővítsd a planning.batch form view-t:
•	új notebook page: „Workflow overview”
2.	A page-en jeleníts meg (read-only listák):
•	kapcsolt Sales Orderök (SO)
•	kapcsolt Sales Order sorok (SO line)
•	kapcsolt Manufacturing Orderök (MO)
•	kapcsolt Manufacturing Order sorok (MO line)
•	kapcsolt Purchase Orderök (PO)
•	kapcsolt Purchase Order sorok (PO line)
3.	Technikai elv:
•	csak read-only megjelenítés
•	nincs core rekord módosítás
4.	Ha még nincs kapcsolat:
•	empty state (üres listák) korrekt megjelenítése
Korlátok:
•	nincs gomb
•	nincs állapotváltás
•	nincs automatizmus
•	nincs adatírás core modellekbe
•	teljes fájlokat adj vissza
Minden döntési pontnál kérdezz, ha:
•	hogyan legyen a Batch ↔ SO kapcsolat (explicit reláció vs csak UI-s keresés)
•	melyik SO mező alapján kapcsolunk (pl. origin, custom mező, m2m)
•	lista sorrend (dátum / prioritás / state)
Definition of Done (v0.2):
•	Batch formon egy oldalon látható SO/SO line/MO/MO line/PO/PO line.
•	Minden lista read-only.
•	Üres eset korrekt.
•	Core adatok érintetlenek.
________________________________________
Codex prompt – v0.3 (Batchből indítható gyártás – manual trigger)
Prompt:
Odoo 17 Community, x_fulfillment_planner.
Ez a v0.3, v0.1–v0.2-re épül.
Cél: Batchből 1 gombbal MO indítás, kontrolláltan.
Feladat:
1.	Adj hozzá gombokat a Batch formhoz:
•	„Calculate” – validálás és batch lineok képzése
•	„Create MO (Planner)” – MO létrehozás aggregáltan
2.	Selection:
•	SO-k listázása (state = sale) egy modal wizardban
•	SO line-ok kijelölése SO-n belül, read-only megjelenítéssel
3.	A gomb logikája:
•	a kiválasztott SO line-ok alapján 1 MO termékenként (aggregált mennyiség)
•	default BOM használata
3.	Kapcsolás nyoma:
•	legyen látható, hogy az SO-ból jött létre az MO (linkelés vagy hivatkozás)
4.	Validációk:
•	duplikáció kezelés: hibás sorok jelölése és kihagyása
•	ha nem lehet MO-t létrehozni (pl. hiányzó product/BOM), adjon érthető hibát
5.	UI:
•	gombok state alapján: draft → calculate, calculated → create MO
Korlátok:
•	MVP: csak a legszükségesebb mezők az MO-n
•	nincs teljes lánc automatizmus
•	nincs készlethiány számítás (az v0.4+)
•	teljes fájlokat adj vissza
Minden döntési pontnál kérdezz, ha:
•	1 SO → 1 MO, vagy SO line-onként MO?
•	BOM kiválasztás szabálya (default BOM vs speciális)
•	duplikáció kezelés: tiltás, vagy újragenerálás opció?
•	a gomb SO-n legyen, vagy Batch-en belül?
Definition of Done (v0.3):
•	Batchből gombnyomásra MO-k létrejönnek (termékenként).
•	Duplikáció kontrollált.
•	Hibaesetek érthető üzenetet adnak.
•	UI gomb logikusan elérhető.
________________________________________
Codex prompt – v0.4 (Félkész / hiány automatikus felismerése és javasolt MO)
Prompt:
Odoo 17 Community, x_fulfillment_planner.
Ez a v0.4, v0.3-ra épül.
Cél: hiány felismerés és javaslat (nem teljes automatizmus).
Feladat:
1.	Készíts hiány-elemzést SO (vagy SO line) szinten:
•	termék igény vs készlet (elérhető mennyiség)
2.	Eredmény megjelenítés a Planner UI-ban:
•	mely termékből mennyi hiányzik
•	javasolt művelet: „Create suggested MO” (csak javaslatként)
3.	Hiány logika MVP-ben:
•	csak késztermék / közvetlen termék szint
•	félkész szint csak akkor, ha egyszerűen meghatározható BOM-ból
4.	Gomb(ok) a javasolt MO létrehozására:
•	csak a hiányzó mennyiségre hozzon létre MO-t
5.	Validáció:
•	ha készlet közben változott, számoljon újra, vagy jelezzen eltérést
Korlátok:
•	még nincs aggregált igénylista (az v0.5)
•	még nincs BOM veszteség % (az v0.6)
•	teljes fájlokat adj vissza
Minden döntési pontnál kérdezz, ha:
•	„készlet” definíció: on-hand vagy forecast?
•	multi-warehouse eset: melyik raktárból számolunk?
•	hiány számítás időpontja: real-time computed vs manuális refresh?
Definition of Done (v0.4):
•	Hiánylista megjelenik.
•	Hiány mennyiségek logikusak.
•	Javasolt MO létrehozható a hiányra.
•	Készletváltozásra nincs „csendes” rossz eredmény (jelez vagy újraszámol).
________________________________________
Codex prompt – v0.5 (Gyártási igénylista – SO + MO + készlethiány aggregálva)
Prompt:
Odoo 17 Community, x_fulfillment_planner.
Ez a v0.5, v0.4-re épül.
Cél: egy aggregált igénylista (planning backlog), ami összevonja: SO igényeket + meglévő MO-kat + hiányt.
Feladat:
1.	Vezess be egy „Batch Lines” koncepciót (új modell vagy strukturált tárolás):
•	termék szintű aggregáció
•	igény mennyiség (SO-ból)
•	már lefedett mennyiség (MO / készlet)
•	nettó hiány
2.	UI a Batch-ben:
•	egy táblázat termékenként
•	drill-down linkek: mely SO-k és MO-k adják az értéket
3.	Műveletek:
•	„Create MO from net shortage” termékenként vagy tömegesen
4.	Konszisztencia:
•	refresh újraszámolja a sorokat
•	legyen egy „Last computed at” jellegű információ (ha szükséges)
Korlátok:
•	még nincs veszteség% számítás (az v0.6)
•	még nincs teljes lánc automatizmus (az v0.7)
•	teljes fájlokat adj vissza
Minden döntési pontnál kérdezz, ha:
•	aggregáció kulcsa: product + UoM? warehouse? company?
•	meglévő MO-k hogyan számítsanak bele (state szűrés)?
•	részszállítás / részgyártás kezelése MVP-ben kell-e?
Definition of Done (v0.5):
•	Batch-ben látszik termékszintű aggregált igénylista.
•	Nettó hiány helyes.
•	MO generálás működik nettó hiányra.
•	Drill-down működik.
________________________________________
Codex prompt – v0.6 (Veszteség % kezelése BOM-on – custom logika)
Prompt:
Odoo 17 Community, x_fulfillment_planner.
Ez a v0.6, v0.5-re épül.
Cél: BOM veszteség % figyelembevétele a számításokban és MO qty-kben.
Feladat:
1.	Adj veszteség % mezőt BOM-ra (pl. loss_percent).
2.	Számítási szabály MVP:
•	nettó igény → bruttó igény = nettó * (1 + loss%)
3.	Alkalmazási pontok:
•	hiány számítás (v0.4)
•	aggregált igénylista (v0.5)
•	MO generálás mennyisége
4.	UI:
•	BOM formon szerkeszthető, validált érték (0–100)
5.	Validáció:
•	negatív és túl magas érték tiltása
•	hiányzó BOM esetén fallback viselkedés
Korlátok:
•	még nincs teljes SO→MO lánc automatizmus (az v0.7)
•	teljes fájlokat adj vissza
Minden döntési pontnál kérdezz, ha:
•	veszteség % BOM szintű legyen-e, vagy komponens szintű? (MVP-ben BOM szintű javasolt)
•	rounding szabály (UoM kerekítés)
•	több BOM esetén melyik BOM veszteségét vegyük?
Definition of Done (v0.6):
•	BOM-on beállítható loss%.
•	Hiány és aggregáció ennek megfelelően változik.
•	MO mennyiség bruttósítva jön létre.
•	Validációk működnek.
________________________________________
Codex prompt – v0.7 (Teljes SO → MO lánc automatizmus – kész → félkész → alapanyag)
Prompt:
Odoo 17 Community, x_fulfillment_planner.
Ez a v0.7, v0.6-ra épül.
Cél: end-to-end automatizmus: SO igényből generált gyártási lánc (késztermék → félkész → alapanyag), kontrolláltan.
Feladat:
1.	Készíts „Planner run” folyamatot Batch szinten:
•	bemenet: kiválasztott SO-k / igénylista
•	kimenet: MO-k (többszintű BOM alapján) + szükséges beszerzési igény jelzés
2.	BOM robbantás MVP:
•	több szint kezelése (kész → félkész)
•	alapanyag esetén: purchase javaslat / hiány jelzés (nem feltétlen automatikus PO)
3.	Idempotencia:
•	újrafuttatás ne duplikáljon kontroll nélkül
•	legyen „recompute” és „apply” külön lépés, ha kell
4.	Workflow állapotok Batch-ben:
•	pl. draft → planned → applied (vagy hasonló)
5.	Logging / audit:
•	futtatás eredménye látható (mely MO-k készültek, miért)
Korlátok:
•	MVP: PO automatikus létrehozása opcionális; ha túl kockázatos, csak javaslat
•	teljes fájlokat adj vissza
Minden döntési pontnál kérdezz, ha:
•	automatikusan hozzunk létre PO-t is, vagy csak javaslat legyen?
•	BOM robbantás mélység limit (végtelen vs max N szint)?
•	duplikáció kezelés: merge vagy tiltás?
•	multi-warehouse és lead time számítás MVP-ben kell-e?
Definition of Done (v0.7):
•	Batch futtatás létrehoz több szintű MO láncot determinisztikusan.
•	Újrafuttatás kontrollált (nincs csendes duplikáció).
•	Az eredmény UI-ban áttekinthető.
•	Hiányzó alapanyagokra jelzés/javaslat van.
