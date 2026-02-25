Current status (v0.7.09) – Procurement planner separated
Release date: 2026-02-25
Previous: v0.3.03 finalized
Implemented in Odoo 17 Community:
- Shortage analysis (v0.4.01+):
  - planning.batch.shortage model (product-level shortage storage)
  - Analyze Shortage button (on-hand + confirmed/in-progress MO supply)
  - Shortage table with red/green status and drill-down to SO lines
  - Create MOs (shortage qty only)
  - Last run info (date + user) + completion notification
  - Manufacture tab with MOs + MO lines + created at/by
  - Undo MOs on Manufacture (info popup when none)
- Batch header buttons: Select Sales Orders, Analyze Shortage, Create MOs
- Dashboard layout (full-width, collapsible sections) + KPI bar
  - Sales Orders Included, Products Included, Products without BOM, MO Coverage %, Uncovered Demand Qty,
    Shortage Count, Shortage Qty, MOs Created, Last Analyzed
- Tabs: Dashboard, Selection, Shortage, Manufacture, Workflow overview
- Unified app navigation:
  - Planner + Sales + Manufacturing + Purchase + Inventory menus inside Fulfillment Planner
  - Sales: Orders / To Invoice / Products / Customers / Reporting
  - Manufacturing: Manufacturing Orders / Bills of Materials / Reporting
  - Purchase: RFQs / Purchase Orders / Products / Vendors / Reporting
  - Inventory: Receipts / Deliveries / Internal Transfers / Products / Reporting
- Validation rules:
  - only one Draft batch per company
  - Planning Batch list hides `New` when a Draft batch already exists in current company
  - shortage analysis auto-resets to Draft after 30 minutes (on open/list)
  - shortage clears + Draft reset when linked sales orders/lines change
  - sales orders locked while linked to any batch; line edits blocked except pricing
  - Undo MOs now reverts batch status to Draft
  - fixed `sale.order.line.create` compatibility for delivery/shipping line creation flow
  - SO line fulfillment status: new → planned → delivered → invoiced
  - SO fulfillment status computed from line statuses
- Sales fields:
  - `sale.order.schedule_date` (Date)
  - `sale.order.priority` (Selection 1..5, default 3)
  - `sale.order.line.reserved` (Boolean)
  - `schedule_date` and `priority` positioned under `Customer` on SO form with visible labels
  - `schedule_date` and `priority` are available on Sales Order list view as optional columns
- Default UI behavior:
  - Fulfillment Planner set as default home action on login (internal users + default user template)
  - Discuss app root menu is hidden
  - Dashboards entry added into Fulfillment Planner app navigation
- v0.6 additions:
  - Analyze Structure action: multi-level BOM explosion from selected SO lines
  - New persisted models:
    - `planning.batch.explosion.node` (tree nodes with level, parent, type, source, state)
    - `planning.batch.demand.summary` (aggregated manufacture/procurement demand by product)
  - New Explosion tab:
    - structure run metadata
    - explosion line list (level 0 roots by default)
    - demand summary list
    - full-screen Manufacturing Chain view action
    - read-only chain browsing with drill-down to child nodes
    - improved visual separation (root-only table focus, badges, and section containers)
    - manufacturing chain list now shows all levels grouped by level-0 product with aggregated demand lines
    - dedicated read-only chain report model (`planning.batch.chain.line`) with level/type/status badges
  - Analyze flow polish:
    - header now uses one `Analyze` action (backend still executes structure + shortage steps separately)
    - batch status label shown as `Analyzed`
    - Explosion and Shortage tabs are split into Level0..Level4 sections; empty sections stay hidden
  - Batch workflow controls:
    - in `calculated`: `Revert to Draft` + `Confirm All MOs`
    - in `confirmed`: `Check Manufacturing Orders` popup with Open / Closed / Canceled sections
  - Odoo 17 view syntax update:
    - header button visibility moved from legacy `modifiers` to `invisible=\"...\"` expressions
  - v0.6.07 polish:
    - batch auto-moves from `confirmed` to `done` when all linked MOs are in `done/cancel` (checked on `Check Manufacturing Orders`)
    - Selection / Shortage / Explosion / Manufacture / Procurement tabs use collapsible section blocks (collapsed by default)
  - v0.6.08 UI cleanup:
    - removed colored header badges in collapsible section titles
    - kept plain text section headers with collapsed behavior
  - v0.6.09 layout cleanup:
    - `Open Manufacturing Chain` moved to main header actions
    - removed duplicated shortage/explosion meta sections from tabs (kept on dashboard KPIs)
    - Explosion tab now shows `Demand Summary` as first section
    - Manufacture tab shows only Manufacturing Orders list (MO meta and MO lines removed)
  - v0.6.10 UX polish:
    - first section in each planner tab is open by default
    - remaining sections stay collapsed by default
- v0.7.01 additions:
  - Procurement analysis scope selector with toggles:
    - Open Demands
    - Minimum Stock Quantities
  - Global demand analysis (company scope) from open MO component demands
  - Draft/sent/open purchase quantities are netted in analysis to avoid duplicate planning
  - New procurement analysis result model:
    - `planning.batch.procurement.line`
  - RFQ creation from procurement suggestions:
    - enforces one draft RFQ per vendor per company
    - groups lines by vendor and links created RFQs/PO lines to batch
  - Shortage analysis now uses exploded multi-level demand
    - source_type `mo` for manufacturable demand
    - source_type `po` for procurement input demand
  - Create MOs now creates MOs for manufacturable shortages from exploded structure
- v0.7.02 additions:
  - Procurement planning moved to separate model and screen:
    - `procurement.batch`
    - `procurement.batch.line`
  - New Planner menu entry:
    - `Procurement Planning`
  - Procurement batch lifecycle:
    - draft → analyzed → rfq_created → done
  - Global-by-company procurement analysis with toggles persisted on procurement batch:
    - Open Demands
    - Minimum Stock Quantities
    - Show All Open RFQs (default: run-created only)
  - Prepared RFQs are listed on the procurement batch for review/open/manual modification
  - Planning Batches menu/action title changed to:
    - `Fulfillment Planning`
- v0.7.03 fix:
  - fixed procurement/open-demand calculation compatibility on Odoo 17 stock moves
  - replaced unsupported `stock.move.quantity_done` usage with Odoo 17-compatible done quantity handling
- v0.7.04 fix:
  - procurement analysis now only includes products where `Can be Purchased = true`
- v0.7.05 polish + validation:
  - Procurement Planning page uses full-width sheet/layout (improved readability)
  - Added section headers in Procurement Planning form:
    - `Analysis`
    - `RFQs`
  - Analysis and RFQ tables are rendered full width
  - Added one-draft-per-company validation for `procurement.batch`
  - Procurement Planning list hides `New` when a draft procurement batch already exists in current company
- v0.7.06 UI polish:
  - fixed Procurement Planning Analysis/RFQ table overlap with responsive container behavior
  - added bordered section containers for Analysis and RFQs
  - RFQ table extended with extra columns (`Origin`, `Created On`) for easier review
- v0.7.07 purchasing pricing/currency:
  - RFQ line `price_unit` now comes from supplier price (`product.supplierinfo`) when vendor is configured on the product
  - fallback remains product `standard_price` if no supplier price is found
  - RFQ currency is set from supplier currency (fallback: vendor purchase currency / company currency)
- v0.7.08 vendor confirmation gate:
  - new procurement status inserted:
    - `vendors_confirmed` (between `analyzed` and `rfq_created`)
  - if analyzed lines include multi-vendor products, user must run `Confirm Vendors` before RFQ creation
  - vendor confirmation wizard lists only multi-vendor analyzed lines
  - each line must be checked (`confirmed`) and vendor selected
  - real-time comparison shown per line:
    - selected price / selected lead time
    - best price / fastest lead time
  - if no multi-vendor lines exist, analysis auto-moves batch directly to `vendors_confirmed`
  - `Create RFQs` is blocked until vendor confirmation is completed
- v0.7.09 fix:
  - fixed empty Confirm Vendors popup by creating wizard lines directly from matching analyzed multi-vendor lines
- Selected Products aggregated list + “Need BoM correction” list
- Select Sales Orders wizard (modal):
  - auto-loads open SOs (state = sale) on open
  - search by Order/Customer
  - select/deselect per row + Select All / Deselect All
  - visual status icons (green filled / red outline)
  - SO rows read-only, row-open form shows SO number + SO lines (read-only)
  - Product Summary aggregates selected SO lines by product + UoM
  - Load Sales Orders links selected SOs and SO lines to the batch
- Safety:
  - cannot delete Sales Orders / lines when MOs exist
  - deleting a Sales Order removes its batch lines
  - deleting a Sales Order line clears Shortage analysis
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
Roadmap (overridden – current plan)
v0.6 – Multi-level BOM structure analysis + semi-goods demand expansion
v0.7 – Procurement Planner MVP
• Demand source: exploded manufacturing demand
• Netting with minimum stock target
v0.8 – Procurement Planner Full
• lead time, MOQ/multiples, vendor policy, advanced validations
v0.9 – UI revamp + polishing
v1.0 – Full automation + control points
• Planner ready: minimal user action for daily fulfillment
• Periodic procurement planning supported
________________________________________
Codex prompt – v0.6 (legacy, superseded by roadmap above)
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
