# Technical Architecture Document (TAD)
**Project:** `x_fulfillment_planner` (Fulfillment Planner)  
**Platform:** Odoo 17 Community  
**Implemented Baseline:** v0.6.10 (release date: 2026-02-25)  
**Document Purpose:** C-level + technical handover, acceptance/sign-off, and onboarding-ready architecture reference.

---

## 1) Executive Summary (non-technical)

Fulfillment Planner addresses a coordination gap between Sales demand and execution planning by introducing a controlled Planning Batch workflow inside Odoo. It lets planners select open Sales Orders, aggregate demand, run shortage analysis, create Manufacturing Orders for uncovered demand, and track the workflow in one place.

### Business value delivered (implemented)
- Centralized planning cockpit with consistent workflow tabs and KPI dashboard.
- Controlled batch lifecycle with key guardrails:
  - one Draft batch per company,
  - sales-order locking while under planning control,
  - stale shortage auto-reset.
- Reduced manual planning effort:
  - selected product aggregation,
  - shortage quantification,
  - one-click MO creation for shortage quantities.
- Better operational visibility:
  - shortage status table with drill-down to SO lines,
  - multi-level manufacturing structure and demand summaries,
  - MO creation metadata (when/by whom),
  - SO and SO line fulfillment statuses.

### Current major limitations
- No Purchase Order generation yet (Procurement tab is placeholder).
- Shortage uses `qty_available` + MO supply only (no forecast/netting by warehouse rules).
- Multi-level structure uses default BOM paths; alternate/multi-BOM decision logic is still out of scope.
- Concurrency protections are mostly application-level (no SQL-level unique lock on draft batch).
- Reservation checkbox on SO line is informational in this module (not tied to Odoo stock reservation engine).

### Operational risks
- If users avoid opening/listing batches, stale shortage reset logic is not triggered (no cron).
- Large datasets may stress UI and compute chains (many stored compute fields and O2M recomputations).
- Locking and duplicate-prevention are not fully transactional against concurrent clicks/users.

---

## 2) System Context & Scope Boundaries

### 2.1 Modules touched (implemented)

| Domain | Odoo Module | Usage in implementation |
|---|---|---|
| Core | `base` | security groups, default user action |
| Sales | `sale` | SO/SO line selection, statuses, custom fields, locking |
| Purchase | `purchase` | read-only workflow visibility + app navigation entries |
| Manufacturing | `mrp` | shortage supply input and MO creation/undo |
| Inventory | `stock` | MO line visibility; on-hand stock (`qty_available`) source |
| Dashboards | `spreadsheet_dashboard` | Fulfillment app menu entry for dashboards |

### 2.2 Scope boundaries (implemented vs not)

**Implemented (v0.6.10):
- Batch-based SO planning and shortage analysis.
- MO creation from shortage.
- SO/SO-line locking and status propagation.
- Unified app navigation under Fulfillment Planner.
- Multi-level BOM explosion analysis (`planning.batch.explosion.node`).
- Demand summary by exploded structure (`planning.batch.demand.summary`).
- Manufacturing chain aggregated reporting (`planning.batch.chain.line`).
- Header action/status workflow polish (single Analyze action, state-based button visibility).
- MO check wizard with Open/Closed/Canceled sections.
- Collapsible section UX across planner tabs (first section default expanded).

**Out of scope / roadmap (not implemented in v0.6.10):**
- PO generation from MO-driven demand (`v0.6` target).
- Multi-BOM logic (`v0.7` target).
- Additional polishing/validation and UI phases (`v0.8`, `v0.9`).
- End-to-end full automation/control points (`v1.0`).

---

## 3) Architecture Overview

### 3.1 High-level component architecture (text diagram)

```text
User (Planner)
  -> Planning Batch Form (views/planning_batch_views.xml)
      -> Selection Wizard (planning.batch.select.so + transient lines/products)
      -> Batch Core Model (planning.batch)
          -> Batch Orders (planning.batch.order)
          -> Batch Lines (planning.batch.line)
          -> Product Summary (planning.batch.product_summary; computed persisted)
          -> BOM Issues (planning.batch.bom_issue; computed persisted)
          -> Shortage Lines (planning.batch.shortage)
          -> MRP Productions linkage (mrp.production M2M)
      -> Sale Order Extensions (models/sale_order.py)
          -> SO lock, SO/SO-line fulfillment status, smart button
      -> Odoo Standard Modules
          -> Sales data source
          -> MRP supply source + MO creation target
          -> Inventory on-hand source
          -> Purchase/Inventory read-only visibility
```

### 3.2 Data flow narratives

#### A) Selection -> Batch loading
1. User opens `Select Sales Orders` from a Draft batch.
2. Wizard auto-loads SOs with domain:
   - `state = sale`,
   - same company as batch,
   - excludes SOs already linked to other batches.
3. User selects/deselects SOs (single row, all, none).
4. On `Load Sales Orders`:
   - existing batch orders and batch lines are deleted,
   - batch links (`sale_order_ids`) are rebuilt from selected SOs,
   - batch order records are created,
   - batch line records are created from SO lines (`display_type = False`),
   - shortage data is reset and status may return to Draft.

#### B) Shortage analysis
1. User clicks `Analyze Shortage` (allowed only in Draft / Shortage Analyzed).
2. System reads selected batch lines and aggregates demand by product in product UoM.
3. Available is computed as:
   - on-hand (`product.qty_available`, company-aware) +
   - existing MOs in states `confirmed`, `progress` for same product/company.
4. `planning.batch.shortage` lines are recreated for each product.
5. Batch stores analysis timestamp/user; status set to `shortage_analyzed`.

#### C) MO creation from shortage
1. User clicks `Create MOs` (allowed only in `shortage_analyzed`).
2. System filters shortage lines where `shortage_qty > 0`.
3. Validation checks:
   - at least one shortage,
   - no duplicate product vs already linked MOs in batch,
   - BOM exists for product (default `_bom_find`).
4. Creates one MO per shortage product, quantity = shortage qty, origin = batch name.
5. Links created MOs to batch, stamps created at/by, sets batch status `calculated`.

#### D) Undo MOs
1. User clicks `Undo MOs`.
2. If no linked MOs -> info notification.
3. If any linked MO is not draft -> error.
4. If all linked MOs are draft:
   - unlinks/deletes those MOs,
   - clears MO metadata,
   - resets batch to Draft and clears shortage data.

#### E) Locking and validation loop
- SO line linked to any `planning.batch.line` -> SO is considered fulfillment-locked.
- While locked, SO line structure changes are blocked (add/remove/edit non-pricing fields).
- If batch sales content changes, shortage is reset to avoid stale planning.

---

## 4) Security & Access Model

### 4.1 Security groups
- `group_fulfillment_planner_backoffice`
  - category: Fulfillment Planner
  - implied: `base.group_user`
- `base.group_system` (admin) has full access to custom models.

### 4.2 Access rights (`security/ir.model.access.csv`)
Read/Write/Create/Delete are all enabled for backoffice + admin on:
- `planning.batch`
- `planning.batch.line`
- `planning.batch.order`
- `planning.batch.select.so` (transient)
- `planning.batch.select.so.line` (transient)
- `planning.batch.select.so.product` (transient)
- `planning.batch.shortage`
- `planning.batch.product_summary`
- `planning.batch.bom_issue`

### 4.3 Record rules
- **No custom record rules were found** in module files (implementation relies on ACL + business logic).

### 4.4 UI-level restrictions
- `Create MOs` button shown only when shortage exists and status is `shortage_analyzed`.
- `Select Sales Orders` available only in Draft status.
- Planning Batch list creation disabled dynamically if same-company Draft exists (`fields_view_get` mutates tree arch).
- Discuss root menu hidden via `data/ui_defaults.xml` (`mail.menu_root_discuss.active = False`).

---

## 5) Data Model (FULL)

## 5.1 Custom models

### 5.1.1 `planning.batch`
| Field | Type | Relation / Values | Req | Default | Compute / Store | Index | Company behavior | Notes |
|---|---|---|---|---|---|---|---|---|
| `name` | Char | - | Yes | sequence `planning.batch` | - | No explicit | shared | readonly, copy=False |
| `date` | Date | - | Yes | `context_today` | - | No explicit | shared | planning date |
| `company_id` | Many2one | `res.company` | Yes | `env.company` | - | implicit M2O | scoped | key company scope field |
| `status` | Selection | draft, shortage_analyzed, calculated, confirmed, done | Yes | draft | - | No explicit | scoped | lifecycle state |
| `note` | Text | - | No | - | - | No | shared | free note |
| `sale_order_ids` | Many2many | `sale.order` via `planning_batch_sale_order_rel` | No | - | - | relation indexes by ORM | scoped by wizard domain | canonical SO linkage |
| `batch_order_ids` | One2many | `planning.batch.order` | No | - | - | No | scoped | selected SO rows |
| `line_ids` | One2many | `planning.batch.line` | No | - | - | No | scoped | selected SO lines |
| `mrp_production_ids` | Many2many | `mrp.production` via `planning_batch_mrp_production_rel` | No | - | - | relation indexes by ORM | scoped | linked created/related MOs |
| `mo_line_ids` | Many2many | `stock.move` via `planning_batch_mo_line_rel` | No | - | - | relation indexes by ORM | scoped | domain raw material moves |
| `purchase_order_ids` | Many2many | `purchase.order` via `planning_batch_purchase_order_rel` | No | - | - | relation indexes by ORM | scoped | currently read-only visibility |
| `purchase_order_line_ids` | Many2many | `purchase.order.line` via `planning_batch_purchase_order_line_rel` | No | - | - | relation indexes by ORM | scoped | currently read-only visibility |
| `shortage_line_ids` | One2many | `planning.batch.shortage` | No | - | - | No | scoped | analysis output |
| `product_summary_ids` | One2many | `planning.batch.product_summary` | No | - | compute/store | No | scoped | rebuilt from selected lines |
| `bom_missing_ids` | One2many | `planning.batch.bom_issue` | No | - | compute/store | No | scoped | rebuilt from selected products |
| `sales_order_count` | Integer | - | No | - | compute/store | No | scoped | KPI |
| `product_count` | Integer | - | No | - | compute/store | No | scoped | KPI |
| `bom_missing_count` | Integer | - | No | - | compute/store | No | scoped | KPI |
| `shortage_count` | Integer | - | No | - | compute/store | No | scoped | KPI |
| `shortage_qty_total` | Float | - | No | - | compute/store | No | scoped | KPI |
| `uncovered_demand_qty` | Float | - | No | - | compute/store | No | scoped | KPI |
| `mo_coverage_pct` | Float | - | No | - | compute/store | No | scoped | KPI |
| `mo_created_count` | Integer | - | No | - | compute/store | No | scoped | KPI |
| `shortage_last_run` | Datetime | - | No | - | - | No | scoped | analysis timestamp |
| `shortage_last_run_by` | Many2one | `res.users` | No | - | - | implicit M2O | scoped | analysis actor |
| `suggested_mo_created_at` | Datetime | - | No | - | - | No | scoped | MO creation timestamp |
| `suggested_mo_created_by` | Many2one | `res.users` | No | - | - | implicit M2O | scoped | MO creation actor |

### 5.1.2 `planning.batch.order`
| Field | Type | Relation / Values | Req | Default | Compute / Store | Index | Company behavior | Notes |
|---|---|---|---|---|---|---|---|---|
| `batch_id` | Many2one | `planning.batch` | Yes | - | - | implicit M2O | scoped | cascade delete |
| `sale_order_id` | Many2one | `sale.order` | Yes | - | - | implicit M2O | scoped | selected SO |
| `partner_id` | Many2one (related) | `sale_order_id.partner_id` | No | - | related/store | implicit M2O | scoped by SO | readonly |
| `date_order` | Datetime (related) | `sale_order_id.date_order` | No | - | related/store | No | scoped by SO | readonly |
| `state` | Selection (related) | `sale_order_id.state` | No | - | related/store | No | scoped by SO | readonly |
| `amount_total` | Monetary (related) | `sale_order_id.amount_total` | No | - | related/store | No | scoped by SO | readonly |
| `currency_id` | Many2one (related) | `sale_order_id.currency_id` | No | - | related/store | implicit M2O | scoped by SO | readonly |
| `batch_line_ids` | One2many | `planning.batch.line` | No | - | - | No | scoped | lines under SO in batch |

### 5.1.3 `planning.batch.line`
| Field | Type | Relation / Values | Req | Default | Compute / Store | Index | Company behavior | Notes |
|---|---|---|---|---|---|---|---|---|
| `batch_id` | Many2one | `planning.batch` | Yes | - | - | implicit M2O | scoped | cascade delete |
| `batch_order_id` | Many2one | `planning.batch.order` | Yes | - | - | implicit M2O | scoped | cascade delete |
| `selected` | Boolean | - | No | True | - | No | scoped | line-level inclusion |
| `sale_order_line_id` | Many2one | `sale.order.line` | Yes | - | - | implicit M2O | scoped by SO line company | key linkage |
| `sale_order_id` | Many2one (related) | `sale_order_line_id.order_id` | No | - | related/store | implicit M2O | scoped | readonly |
| `product_id` | Many2one (related) | `sale_order_line_id.product_id` | No | - | related/store | implicit M2O | scoped | readonly |
| `product_uom` | Many2one (related) | `sale_order_line_id.product_uom` | No | - | related/store | implicit M2O | scoped | readonly |
| `product_uom_qty` | Float (related) | `sale_order_line_id.product_uom_qty` | No | - | related/store | No | scoped | readonly |
| `qty_product_uom` | Float | - | No | - | compute/store | No | scoped | converted qty |
| `status` | Selection | ok, failed | No | - | - | No | scoped | validation output |
| `message` | Char | - | No | - | - | No | scoped | validation message |
| `mrp_production_id` | Many2one | `mrp.production` | No | - | - | implicit M2O | scoped | currently not populated by MO create flow |

### 5.1.4 `planning.batch.shortage`
| Field | Type | Relation / Values | Req | Default | Compute / Store | Index | Company behavior | Notes |
|---|---|---|---|---|---|---|---|---|
| `batch_id` | Many2one | `planning.batch` | Yes | - | - | implicit M2O | scoped | cascade delete |
| `company_id` | Many2one (related) | `batch_id.company_id` | No | - | related/store | implicit M2O | scoped | readonly |
| `product_id` | Many2one | `product.product` | Yes | - | - | implicit M2O | scoped | shortage key |
| `uom_id` | Many2one | `uom.uom` | Yes | - | - | implicit M2O | scoped | product UoM |
| `demand_qty` | Float | - | No | - | - | No | scoped | aggregated demand |
| `available_qty` | Float | - | No | - | - | No | scoped | on-hand + MO supply |
| `shortage_qty` | Float | - | No | - | - | No | scoped | max(demand-available,0) |
| `source_type` | Selection | so, mo, po | Yes | so | - | No | scoped | `mo` and `po` are actively used in v0.6+ multi-level analysis |
| `related_line_ids` | Many2many | `sale.order.line` via `planning_batch_shortage_sale_line_rel` | No | - | - | relation indexes by ORM | scoped | drill-down lines |

### 5.1.5 `planning.batch.product_summary`
| Field | Type | Relation / Values | Req | Default | Compute / Store | Index | Company behavior | Notes |
|---|---|---|---|---|---|---|---|---|
| `batch_id` | Many2one | `planning.batch` | Yes | - | - | implicit M2O | scoped | cascade delete |
| `product_id` | Many2one | `product.product` | Yes | - | - | implicit M2O | scoped | aggregated product |
| `uom_id` | Many2one | `uom.uom` | Yes | - | - | implicit M2O | scoped | product UoM |
| `qty` | Float | - | No | - | - | No | scoped | aggregated qty |

### 5.1.6 `planning.batch.bom_issue`
| Field | Type | Relation / Values | Req | Default | Compute / Store | Index | Company behavior | Notes |
|---|---|---|---|---|---|---|---|---|
| `batch_id` | Many2one | `planning.batch` | Yes | - | - | implicit M2O | scoped | cascade delete |
| `product_id` | Many2one | `product.product` | Yes | - | - | implicit M2O | scoped | missing-BOM product |
| `uom_id` | Many2one | `uom.uom` | Yes | - | - | implicit M2O | scoped | product UoM |

### 5.1.7 Transient wizard models

#### `planning.batch.select.so` (TransientModel)
| Field | Type | Relation / Values | Req | Default | Compute / Store | Index | Notes |
|---|---|---|---|---|---|---|---|
| `batch_id` | Many2one | `planning.batch` | Yes | context/default | - | implicit M2O | wizard context anchor |
| `search_text` | Char | - | No | - | - | No | search term |
| `line_ids` | One2many | `planning.batch.select.so.line` | No | - | - | No | selectable SO list |
| `product_line_ids` | One2many | `planning.batch.select.so.product` | No | - | - | No | included products summary |
| `has_product_summary` | Boolean | - | No | - | compute (non-store) | No | UI visibility flag |

#### `planning.batch.select.so.line` (TransientModel)
| Field | Type | Relation / Values | Req | Default | Compute / Store | Index | Notes |
|---|---|---|---|---|---|---|---|
| `wizard_id` | Many2one | `planning.batch.select.so` | Yes | - | - | implicit M2O | cascade delete |
| `sale_order_id` | Many2one | `sale.order` | Yes | - | - | implicit M2O | SO record |
| `selected` | Boolean | - | No | False | - | No | row flag |
| `selection_state` | Selection | selected, not_selected | No | - | compute/store | No | badge status |
| `partner_id` | Many2one (related) | `sale_order_id.partner_id` | No | - | related/store | implicit M2O | readonly |
| `date_order` | Datetime (related) | `sale_order_id.date_order` | No | - | related/store | No | readonly |
| `amount_total` | Monetary (related) | `sale_order_id.amount_total` | No | - | related/store | No | readonly |
| `state` | Selection (related) | `sale_order_id.state` | No | - | related/store | No | readonly |
| `currency_id` | Many2one (related) | `sale_order_id.currency_id` | No | - | related/store | implicit M2O | readonly |
| `sale_order_line_ids` | One2many (related) | `sale_order_id.order_line` | No | - | related (non-store) | No | readonly drill-down |

#### `planning.batch.select.so.product` (TransientModel)
| Field | Type | Relation / Values | Req | Default | Compute / Store | Index | Notes |
|---|---|---|---|---|---|---|---|
| `wizard_id` | Many2one | `planning.batch.select.so` | Yes | - | - | implicit M2O | cascade delete |
| `product_id` | Many2one | `product.product` | Yes | - | - | implicit M2O | aggregated product |
| `product_uom_id` | Many2one | `uom.uom` | Yes | - | - | implicit M2O | UoM |
| `qty` | Float | - | No | - | - | No | aggregated qty |

## 5.2 Custom fields on core models

### `sale.order` (inherited)
| Field | Type | Values / Relation | Req | Default | Compute / Store | Index | Notes |
|---|---|---|---|---|---|---|---|
| `schedule_date` | Date | - | No | - | - | No | planner input |
| `priority` | Selection | `1..5` | No | `3` | - | No | planner input |
| `fulfillment_batch_ids` | Many2many | `planning.batch` via `planning_batch_sale_order_rel` | No | - | - | relation indexes by ORM | readonly |
| `fulfillment_batch_count` | Integer | - | No | - | compute (non-store) | No | smart button count |
| `fulfillment_locked` | Boolean | - | No | - | compute (non-store) | No | lock flag from batch lines |
| `fulfillment_state` | Selection | new, planned, delivered, invoiced | No | - | compute/store | No | order-level derived status |

### `sale.order.line` (inherited)
| Field | Type | Values / Relation | Req | Default | Compute / Store | Index | Notes |
|---|---|---|---|---|---|---|---|
| `reserved` | Boolean | - | No | False | - | No | planner flag only |
| `planning_batch_line_ids` | One2many | `planning.batch.line` | No | - | - | No | linkage for lock/state |
| `fulfillment_state` | Selection | new, planned, delivered, invoiced | No | - | compute/store | No | line-level status |

## 5.3 Constraints and uniqueness rules

### Implemented
- **Python constraint:** only one Draft batch per company (`_check_single_draft_per_company`).

### Not implemented
- No SQL-level unique constraint for `(company_id, status='draft')`.
- No explicit SQL uniqueness on relation tables (handled by app flow).

## 5.4 Link storage between Batch <-> SO <-> SO line <-> MO <-> MO line

- Batch <-> SO: `planning_batch_sale_order_rel` (`sale_order_ids` / `fulfillment_batch_ids`).
- Batch <-> SO display row: `planning.batch.order` (`sale_order_id`, `batch_id`).
- Batch <-> SO line: `planning.batch.line` (`sale_order_line_id`, `batch_order_id`, `batch_id`).
- Batch <-> MO: `planning_batch_mrp_production_rel` (`mrp_production_ids`).
- Batch <-> MO component lines: `planning_batch_mo_line_rel` (`mo_line_ids` to `stock.move`).
- Shortage line <-> SO line drill-down: `planning_batch_shortage_sale_line_rel`.

## 5.5 `planning.batch.shortage` lifecycle
- Created fresh on each `Analyze Shortage`.
- Fully deleted on:
  - explicit reset methods (`_clear_shortage_data`, `_reset_to_draft`),
  - SO/SO-line content change paths,
  - stale-analysis reset after 30 minutes when batches are read.

---

## 6) Business Rules & Validation Rules (FULL)

### 6.1 Draft batch rule
- One Draft batch per company is enforced by Python constraint.
- Planning Batch tree view hides Create button when current company already has Draft.

### 6.2 30-minute stale shortage reset
- Trigger: any `read()` on `planning.batch` (open form/list fetch).
- Condition: `status = shortage_analyzed` and `shortage_last_run <= now - 30m`.
- Action: clear shortage lines + reset timestamps + set status Draft.
- No cron job; no background sweep.

### 6.3 Shortage clearing triggers
- `planning.batch._reset_shortage_on_sales_change()` is called after:
  - Wizard load/reload (`action_apply`),
  - removing SO from batch (`planning.batch.order.unlink`),
  - removing batch line (`planning.batch.line.unlink`),
  - SO line write/unlink (`sale.order.line` overrides).
- Behavior:
  - shortage data cleared always,
  - status reset to Draft only if previously `shortage_analyzed`.

### 6.4 SO locking
- SO considered locked when at least one of its lines exists in `planning.batch.line`.
- While locked:
  - `sale.order.write` blocks any change carrying `order_line`.
  - `sale.order.line.create` blocked.
  - `sale.order.line.unlink` blocked.
  - `sale.order.line.write` allows only: `price_unit`, `discount`, `tax_id`, `reserved`.
- Error message used:
  - `Sales order is already in planning batch - you cannot modify line items until it is removed.`

### 6.5 Deletion protections
- Cannot remove batch SO (`planning.batch.order.unlink`) if batch has linked MOs.
- Cannot remove batch line (`planning.batch.line.unlink`) if batch has linked MOs.
- Removing SO from batch also removes its batch lines.

### 6.6 Fulfillment statuses
- SO line status compute:
  - `invoiced` if `invoice_status == 'invoiced'`
  - else `delivered` if `qty_delivered >= product_uom_qty`
  - else `planned` if line linked to any planning batch line
  - else `new`
- SO status compute:
  - all non-display lines invoiced -> `invoiced`
  - all delivered -> `delivered`
  - all planned -> `planned`
  - otherwise `new`

---

## 7) Functional Behavior (User Journeys)

### 7.1 Morning planner run (standard flow)
1. Open Fulfillment Planner -> Planner -> Planning Batches.
2. Create/open Draft batch (if another Draft exists in same company, creation blocked).
3. Click `Select Sales Orders`.
4. In wizard, search/select SOs; review included products.
5. Click `Load Sales Orders` to rebuild batch SO/line content.
6. Review Dashboard KPIs and Selection tab summaries.
7. Click `Analyze Shortage`.
8. Review Shortage tab/table and drill-down lines.
9. Click `Create MOs` (for shortage only).
10. Review Manufacture tab:
    - created MOs,
    - raw material move lines,
    - created at/by.
11. If rollback needed and all linked MOs are draft -> `Undo MOs`.

### 7.2 Edge cases
- **Missing BOM:** MO creation blocked with explicit error listing missing products.
- **No selected SO lines:** shortage analysis blocked.
- **No shortage > 0:** MO creation blocked (`No shortages to create Manufacturing Orders.`).
- **Concurrent planners:** possible race on Draft uniqueness and MO duplicate prevention (application-level checks).
- **Multi-company:** selection domain constrained to batch company; one-Draft rule is per company.

---

## 8) Python Modules & Logical Controllers (FULL)

### 8.1 `hooks.py`
- `post_init_hook`:
  - sets all active internal users (`share=False`) home action to `action_planning_batch` after install.
  - side effect: user landing page forced to Fulfillment Planner action.

### 8.2 `models/planning_batch.py`
- Core aggregate model and orchestration methods.
- Key methods:
  - `fields_view_get`: hides list create when Draft exists (company scope).
  - `_check_single_draft_per_company`: Draft uniqueness guard.
  - `action_open_select_sales_orders`: opens modal wizard.
  - KPI computes: counts, totals, coverage metrics.
  - `_compute_product_summary_ids`, `_compute_bom_missing_ids`: persists derived helper lines.
  - `_reset_stale_shortage` + `read`: stale-analysis auto reset.
  - `action_analyze_shortage`: computes and persists shortage lines.
  - `action_create_suggested_mo`: creates MOs for shortage qty.
  - `action_undo_created_mo`: validates draft state and removes MOs.
  - `_get_bom_map`: wrapper over `mrp.bom._bom_find`.
- Side effects:
  - creates/deletes shortage lines, helper summary lines, and MOs.
  - mutates batch status and run metadata.

### 8.3 `models/planning_batch_order.py`
- Represents selected SO headers inside batch.
- `unlink`:
  - blocks removal when MOs exist,
  - deletes related batch lines,
  - removes SO relation from batch,
  - resets shortage data/state as needed.
- `action_remove_from_batch`: UI helper with soft reload.

### 8.4 `models/planning_batch_line.py`
- Represents selected SO lines for planning.
- `_compute_qty_product_uom`: converts SO UoM qty to product UoM.
- `unlink`:
  - blocks when MOs exist,
  - cleans empty parent batch-order rows,
  - resets shortage data/state.

### 8.5 `models/planning_batch_shortage.py`
- Product-level shortage result model with source type and SO line drill-down links.

### 8.6 `models/planning_batch_product_summary.py`
- Persisted helper model for selected product aggregation.

### 8.7 `models/planning_batch_bom_issue.py`
- Persisted helper model for products missing BOM.

### 8.8 `models/planning_batch_select_so.py` (wizard controller)
- On create:
  - auto-load candidate SOs,
  - compute included product summary.
- `_get_domain`:
  - open SOs only,
  - company filter,
  - excludes SOs linked to other batches,
  - optional text search.
- `action_select_all` / `action_deselect_all` / row actions:
  - update selected flags and refresh summary.
- `action_apply`:
  - full rebuild strategy for batch SOs and lines (reset then load).

### 8.9 `models/planning_batch_select_so_line.py`
- Wizard row state + row-level actions:
  - `action_select`, `action_deselect`,
  - `selection_state` compute for badge rendering.

### 8.10 `models/planning_batch_select_so_product.py`
- Wizard transient product summary lines.

### 8.11 `models/sale_order.py` (core overrides/extensions)
- `sale.order`:
  - custom fields and smart button (`action_view_fulfillment_batches`).
  - lock compute via `planning.batch.line.read_group`.
  - `write` override blocks line changes when locked.
- `sale.order.line`:
  - reserved + fulfillment status.
  - `create/write/unlink` overrides enforce lock policy and reset linked batch shortage.
  - create override uses `@api.model_create_multi` and dict/list normalization (delivery compatibility fix).

### 8.12 Scheduled actions
- **None implemented** in module.

---

## 9) Views, Actions, Menus, and UI Composition

### 9.1 Planning Batch views
- Tree: name, date, status.
- Form:
  - Header: statusbar + main actions (`Select Sales Orders`, `Analyze Shortage`, `Create MOs`).
  - Notebook pages:
    - Dashboard
    - Selection
    - Shortage
    - Manufacture
    - Procurement (placeholder)
    - Workflow overview

### 9.2 Dashboard KPI computation sources
| KPI | Source field / logic |
|---|---|
| Sales Orders Included | `sales_order_count` (len `batch_order_ids`) |
| Products Included | `product_count` (distinct selected line products) |
| Products without BOM | `bom_missing_count` |
| MO Coverage % | `(demand_total - shortage_total)/demand_total * 100` |
| Uncovered Demand Qty | total shortage qty |
| Shortage Count | len `shortage_line_ids` |
| Shortage Qty | sum of `shortage_qty` |
| MOs Created | len `mrp_production_ids` |
| Last Analyzed | `shortage_last_run` |

### 9.3 Wizard views
- Modal form with:
  - search input + Search button,
  - SO list with Select/Deselect row actions and status badge,
  - row-open read-only SO form with SO lines,
  - included products summary table,
  - footer actions: Select All, Deselect All, Load Sales Orders, Cancel.

### 9.4 Actions and menu composition
- Main action: `action_planning_batch` (`tree,form`).
- Root app menu: `menu_fulfillment_planner_root`.
- Nested app menus:
  - Planner / Sales / Manufacturing / Purchase / Inventory / Dashboards.

### 9.5 Default home action + Discuss hidden details
- `data/ui_defaults.xml`:
  - sets `base.default_user.action_id` to `action_planning_batch`,
  - deactivates `mail.menu_root_discuss`.
- `post_init_hook`:
  - sets existing active internal users’ `action_id` to planning batch action (install-time).

---

## 10) Dependencies

### 10.1 Manifest dependencies
- `base`, `sale`, `purchase`, `mrp`, `stock`, `spreadsheet_dashboard`

### 10.2 Python/external dependencies
- `lxml` (`etree`) used for dynamic view arch mutation in `fields_view_get`.
- Standard library: `datetime.timedelta`.
- No third-party external package declared by this module.

### 10.3 Cross-module coupling risks
- Strong coupling to Sales and MRP field semantics (`invoice_status`, `qty_delivered`, `_bom_find`, MO states).
- Dependence on Odoo view XML IDs in external modules.
- Depends on `spreadsheet_dashboard` availability for menu action reference.

---

## 11) Performance & Scalability Assessment (Estimated + Reasoned)

### 11.1 Complexity estimates

#### Shortage analysis (`action_analyze_shortage`)
- Let:
  - `L` = selected batch lines,
  - `P` = distinct products in selected lines,
  - `M` = MOs returned by domain query.
- Steps:
  - demand aggregation over lines: `O(L)`,
  - MO aggregation: `O(M)`,
  - shortage row creation: `O(P)`.
- Overall: `O(L + M + P)` plus ORM query overhead.

#### Wizard summary refresh
- Reads selected SO order lines and aggregates by product.
- Complexity: `O(SL)` where `SL` = selected SO lines in wizard scope.

### 11.2 Expected load assumptions (to validate in performance tests)
- Typical daily planning run:
  - 50–500 SO lines per batch.
- High-load scenario:
  - 5k+ SO lines, 500+ products, 1k+ open MOs.

### 11.3 Potential bottlenecks
- Rebuild strategy in `action_apply` deletes/recreates all batch lines each load.
- Stored compute One2many helper lines (`product_summary_ids`, `bom_missing_ids`) can amplify writes.
- Dashboard and notebook pages render multiple large trees in one form.
- `read()` stale reset check on every batch read call.

### 11.4 Concurrency risks
- One Draft per company guard is Python-level (race possible without SQL unique).
- MO duplicate prevention checks existing linked MOs before create; not transactionally protected against simultaneous users.
- SO lock checks are application-level and may race with near-simultaneous writes.

### 11.5 Performance test plan
Collect per scenario:
- SQL query count, total SQL time, ORM call count.
- Wall-clock time for:
  - wizard open/search/select/apply,
  - analyze shortage,
  - create MOs,
  - open Dashboard tab.
- Number of created records (batch lines, shortage lines, MOs).
- Browser render latency for form with all tabs.

Suggested scenarios:
1. 100 SO lines / 20 products / 20 MOs.
2. 1,000 SO lines / 200 products / 300 MOs.
3. 5,000 SO lines / 700 products / 1,000 MOs (stress).

---

## 12) Known Limitations & Technical Debt

1. Procurement tab is placeholder; no PO demand or PO line generation in v0.5.08.
2. Stock availability uses `qty_available` only; no warehouse-level strategy and no full forecast netting.
3. Stale shortage reset relies on `read()` access; no scheduled background enforcement.
4. Draft uniqueness is not SQL-hard; race windows remain.
5. `planning.batch.line.mrp_production_id` exists but current MO creation flow does not populate it.
6. `reserved` on SO line is not integrated into stock reservation mechanics in this module.
7. Locking exclusion in wizard uses all other batches, regardless of their lifecycle intent/history.
8. UI contains many embedded trees; readability and responsiveness can degrade with large batches.
9. No automated test suite detected in module repository.

---

## 13) Operational Considerations

### 13.1 Logging and audit
- User-facing notifications are present for analyze/create/undo actions.
- No dedicated audit log model for planning decisions.
- Chatter integration for planning events is not implemented.

### 13.2 Troubleshooting checklist
1. Validate batch status and company.
2. Check if SO is locked (linked planning batch lines).
3. Re-run shortage analysis if data changed or analysis is stale.
4. Verify BOM exists for shortage products.
5. Confirm MO states are draft before Undo.

### 13.3 Monitoring suggestions
- Add application logs around:
  - shortage runtime and row counts,
  - MO creation counts and failures,
  - lock violations.
- Track DB growth for batch helper models and shortage lines.

### 13.4 Backup/restore implications
- Planning objects are regular persisted records (except transient wizard data).
- Restoring older backups may desync operational reality (MOs/SOs changed externally); enforce post-restore re-analysis.

### 13.5 Multi-company and access pitfalls
- One Draft rule is per company; operators in wrong company context may see unexpected create restrictions.
- No record rules mean visibility depends mostly on broader Odoo access/groups; align group assignments carefully.

---

## 14) Acceptance Checklist (SIGN-OFF READY)

### 14.1 Pass/fail criteria
| ID | Criterion | Expected result |
|---|---|---|
| AC-01 | Create second Draft batch in same company | Blocked with error |
| AC-02 | Open planning batch list with existing Draft | Create/New hidden |
| AC-03 | Open selector wizard | Open SOs auto-loaded |
| AC-04 | Select/Deselect rows and Select All/Deselect All | State updates + product summary updates |
| AC-05 | Load Sales Orders | Batch SOs + batch lines rebuilt from selected SOs |
| AC-06 | Analyze without selected lines | UserError |
| AC-07 | Analyze with selected lines | Shortage rows created, timestamp/user set, status -> shortage_analyzed |
| AC-08 | Create MOs with no shortage | UserError |
| AC-09 | Create MOs with shortage + BOMs | MOs created for shortage qty, linked to batch, status -> calculated |
| AC-10 | Undo MOs with no MOs | Info notification |
| AC-11 | Undo MOs with non-draft MO | UserError |
| AC-12 | Undo MOs with draft-only MOs | MOs deleted, metadata cleared, batch -> draft |
| AC-13 | Modify SO line structure while locked | Blocked (except allowed pricing/reserved fields) |
| AC-14 | Delete SO from batch when MOs exist | Blocked |
| AC-15 | Delete SO line from batch when MOs exist | Blocked |
| AC-16 | Remove SO/SO line from batch (no MOs) | Shortage cleared/reset behavior applied |
| AC-17 | SO list optional columns | `schedule_date` and `priority` available |
| AC-18 | Login home action | Fulfillment Planner action default |
| AC-19 | Discuss app menu | Hidden |
| AC-20 | Dashboards menu | Available inside Fulfillment Planner root |

### 14.2 Smoke test scenarios
1. End-to-end happy path: Selection -> Analyze -> Create MOs -> Review.
2. Rollback path: Create MOs -> Undo MOs.
3. Locking path: SO in batch -> attempt SO line add/remove.
4. Stale analysis path: wait 30+ min, open batch -> reset to Draft.
5. Multi-company path: ensure one Draft per company isolation.

### 14.3 Data integrity checks
- No orphan batch lines after SO removal.
- `sale_order_ids`, `batch_order_ids`, and `line_ids` are consistent after each wizard apply.
- Shortage lines match selected batch lines demand basis after analysis.
- MO origin equals batch name for created MOs.

---

## 15) Appendix

### 15.1 Glossary
- **Planning Batch:** Planner-controlled working set of SO demand and execution actions.
- **Selected Sales Orders:** SO headers chosen into a batch.
- **Batch Lines:** SO lines currently included in planning calculations.
- **Shortage:** Uncovered demand quantity at product level after available supply calculation.
- **Coverage %:** Covered demand share from available quantity.
- **Undo MOs:** Reverts draft MOs created via batch action and resets batch to Draft.
- **Fulfillment Lock:** Constraint preventing structural SO line edits while order is part of planning.

### 15.2 Roadmap reference (NOT implemented in v0.6.10)
- **v0.7:** Procurement Planner MVP (separate planner scope, MO-driven procurement demand).
- **v0.8:** Procurement Planner full version + validation revamp.
- **v0.9:** Additional UI revamp + polishing.
- **v1.0:** Full automation + control points for near zero-touch daily fulfillment/procurement planning.

---

## Source Verification Note
This document is based on repository inspection of the implemented code baseline on branch `0.6.06-actions-20260224` (module version `17.0.0.6.10`) as of 2026-02-25.
