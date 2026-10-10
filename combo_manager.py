import sqlite3, os, sys, datetime, tempfile, webbrowser, re, base64, urllib.parse, csv, types
import html as htmllib, math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import json, subprocess
BASE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
REG_FILE = os.path.join(BASE, "companies.json")
ARGS = sys.argv[1:]
VERSION = "2026.10.10.3"                               # bigger = newer; "Update Program" installs a downloaded file only if its VERSION is bigger
LEGACY_DB = "combo_data_v3.db"                         # the data file of the first company (kept as it is)

def load_registry():
    """companies.json = the list of companies. The existing data file becomes the first company automatically."""
    if os.path.exists(REG_FILE):
        try: return json.load(open(REG_FILE, encoding="utf-8"))
        except Exception: pass
    nm = "My Combo Business"
    try:
        c = sqlite3.connect(os.path.join(BASE, LEGACY_DB)); r = c.execute("SELECT value FROM settings WHERE name='Company Name'").fetchone(); c.close(); nm = (r[0] if r and r[0] else nm)
    except Exception: pass
    reg = {"last": "main", "companies": [{"key": "main", "name": nm, "db": LEGACY_DB, "dir": "", "combo": True, "shirting": False}]}
    save_registry(reg); return reg
def save_registry(reg):
    try: json.dump(reg, open(REG_FILE, "w", encoding="utf-8"), indent=1)
    except Exception: pass
def add_company(reg, name, combo, shirting):
    n = 2
    while any(c["key"] == f"c{n}" for c in reg["companies"]): n += 1
    co = {"key": f"c{n}", "name": name.strip() or f"Company {n}", "db": "data.db", "dir": f"companies/c{n}", "combo": bool(combo), "shirting": bool(shirting)}
    reg["companies"].append(co); save_registry(reg); return co
def relaunch(args):
    """Start the program again (another company / new work style). The caller closes this window."""
    subprocess.Popen([sys.executable] + ([] if getattr(sys, "frozen", False) else [os.path.abspath(__file__)]) + list(args))

def choose_company(reg):
    """'Select Company' window (like Tally). Returns the chosen company key, or None to quit."""
    root = tk.Tk(); root.title("Select Company"); root.geometry("640x520"); root.minsize(560, 460); root.configure(bg="#eef3f9"); res = [None]
    tk.Label(root, text="  Select Company", bg="#2f5d8a", fg="white", font=("Segoe UI", 15, "bold"), anchor="w", pady=10).pack(fill="x")
    tk.Label(root, text="Each company has its own separate data. To add a new firm click  'Create New Company'.", bg="#eef3f9", fg="#444444", font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=16, pady=(10, 0))
    lb = tk.Listbox(root, font=("Segoe UI", 13), height=8, activestyle="none", selectbackground="#ffcf56", selectforeground="black"); lb.pack(fill="both", expand=True, padx=16, pady=10)
    def fill():
        lb.delete(0, "end")
        for c in reg["companies"]: lb.insert("end", f"  {c['name']}     [{' + '.join(x for x, on in (('Combo', c.get('combo')), ('Shirting', c.get('shirting'))) if on) or 'no work style'}]")
        keys = [c["key"] for c in reg["companies"]]; lb.selection_set(keys.index(reg.get("last")) if reg.get("last") in keys else 0)
    def open_(e=None):
        sel = lb.curselection()
        if sel: res[0] = reg["companies"][sel[0]]["key"]; root.destroy()
    def create():
        win = tk.Toplevel(root); win.title("Create Company"); win.grab_set(); box = ttk.Frame(win, padding=14); box.pack()
        nm = tk.StringVar(); cb, sh = tk.BooleanVar(value=True), tk.BooleanVar(value=False)
        ttk.Label(box, text="Company name").grid(row=0, column=0, sticky="e", padx=6, pady=6); e = ttk.Entry(box, textvariable=nm, width=34); e.grid(row=0, column=1, pady=6); e.focus_set()
        ttk.Checkbutton(box, text="Combo work (combo creation, making, combo stock)", variable=cb).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(box, text="Shirting Fabrics work", variable=sh).grid(row=2, column=1, sticky="w")
        def ok(ev=None):
            if not nm.get().strip(): messagebox.showerror("Create Company", "Please enter the company name.", parent=win); return
            if not (cb.get() or sh.get()): messagebox.showerror("Create Company", "Select at least one work style (you can change it later in Company Profile).", parent=win); return
            co = add_company(reg, nm.get(), cb.get(), sh.get()); reg["last"] = co["key"]; save_registry(reg); res[0] = co["key"]; win.destroy(); root.destroy()   # the new company opens at once
        ttk.Button(box, text="Create", command=ok).grid(row=3, column=1, sticky="w", pady=10); win.bind("<Return>", ok); win.bind("<Escape>", lambda ev: win.destroy())
    bar = tk.Frame(root, bg="#eef3f9"); bar.pack(fill="x", padx=16, pady=(0, 14))
    ttk.Button(bar, text="Open Selected Company  (Enter)", command=open_).pack(side="left"); ttk.Button(bar, text="Create New Company", command=create).pack(side="left", padx=8); ttk.Button(bar, text="Quit", command=root.destroy).pack(side="right")
    lb.bind("<Double-Button-1>", open_); root.bind("<Return>", open_); root.bind("<Escape>", lambda e: root.destroy()); fill(); lb.focus_set(); root.mainloop()
    return res[0]

if os.environ.get("COMBO_NO_REGISTRY"):                # used by the automatic tests
    REG, CO = None, {"key": "test", "name": "My Combo Business", "db": ":memory:", "dir": "", "combo": True, "shirting": False}
else:
    REG = load_registry(); key = next((a.split("=", 1)[1] for a in ARGS if a.startswith("--company=")), None)
    if key not in [c["key"] for c in REG["companies"]]: key = None
    if key is None and len(REG["companies"]) == 1 and "--choose" not in ARGS: key = REG["companies"][0]["key"]
    if key is None: key = choose_company(REG)
    if key is None: sys.exit(0)
    CO = next(c for c in REG["companies"] if c["key"] == key); REG["last"] = key; save_registry(REG)
DATA = os.path.join(BASE, CO["dir"]) if CO["dir"] else BASE                          # this company's own folder (data, backups, PDFs)
if CO["db"] != ":memory:": os.makedirs(DATA, exist_ok=True)
db = sqlite3.connect(":memory:" if CO["db"] == ":memory:" else os.path.join(DATA, CO["db"]))
db.execute("PRAGMA foreign_keys=ON")
ROUNDING = [True]                                      # "Round Off" setting (Company Profile)
def rnd_py(x): return math.floor(x + 0.5) if (ROUNDING[0] and x is not None) else x
db.create_function("rnd", 1, rnd_py)
STATES = {"Andaman and Nicobar Islands": "35", "Andhra Pradesh": "37", "Arunachal Pradesh": "12", "Assam": "18", "Bihar": "10", "Chandigarh": "04",
  "Chhattisgarh": "22", "Dadra and Nagar Haveli and Daman and Diu": "26", "Delhi": "07", "Goa": "30", "Gujarat": "24", "Haryana": "06",
  "Himachal Pradesh": "02", "Jammu and Kashmir": "01", "Jharkhand": "20", "Karnataka": "29", "Kerala": "32", "Ladakh": "38", "Lakshadweep": "31",
  "Madhya Pradesh": "23", "Maharashtra": "27", "Manipur": "14", "Meghalaya": "17", "Mizoram": "15", "Nagaland": "13", "Odisha": "21",
  "Puducherry": "34", "Punjab": "03", "Rajasthan": "08", "Sikkim": "11", "Tamil Nadu": "33", "Telangana": "36", "Tripura": "16",
  "Uttar Pradesh": "09", "Uttarakhand": "05", "West Bengal": "19"}
TAXCOLS = "gst_rate REAL, cgst REAL, sgst REAL, igst REAL, total REAL"
db.executescript(f"""
CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY, name TEXT UNIQUE, value TEXT);
CREATE TABLE IF NOT EXISTS parties(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, type TEXT, phone TEXT, address TEXT, gst TEXT, state TEXT);
CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, type TEXT, design TEXT, color TEXT, min_stock REAL DEFAULT 0, hsn TEXT, gst_rate REAL);
CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY, date TEXT, supplier_id INTEGER REFERENCES parties(id),
  item_id INTEGER NOT NULL REFERENCES items(id), unit TEXT, qty REAL, rate REAL, amount REAL, {TAXCOLS});
CREATE TABLE IF NOT EXISTS purchase_returns(id INTEGER PRIMARY KEY, date TEXT, supplier_id INTEGER REFERENCES parties(id),
  item_id INTEGER NOT NULL REFERENCES items(id), unit TEXT, qty REAL, rate REAL, amount REAL, note TEXT, {TAXCOLS});
CREATE TABLE IF NOT EXISTS conversions(id INTEGER PRIMARY KEY, date TEXT, item_id INTEGER NOT NULL REFERENCES items(id),
  meters REAL, length REAL, pcs REAL, wastage REAL);
CREATE TABLE IF NOT EXISTS combos(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, hsn TEXT, gst_rate REAL);
CREATE TABLE IF NOT EXISTS combo_lines(id INTEGER PRIMARY KEY, combo_id INTEGER NOT NULL REFERENCES combos(id) ON DELETE CASCADE,
  item_id INTEGER NOT NULL REFERENCES items(id), qty REAL);
CREATE TABLE IF NOT EXISTS combo_makes(id INTEGER PRIMARY KEY, date TEXT, combo_id INTEGER NOT NULL REFERENCES combos(id), qty REAL, note TEXT);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, order_no TEXT, date TEXT, customer_id INTEGER REFERENCES parties(id),
  combo_id INTEGER REFERENCES combos(id), item_id INTEGER REFERENCES items(id), unit TEXT, qty REAL, rate REAL, amount REAL, status TEXT,
  disc_trade REAL, disc_cash REAL, disc_flat REAL, freight REAL, {TAXCOLS});
CREATE TABLE IF NOT EXISTS contra(id INTEGER PRIMARY KEY, vno TEXT, date TEXT, from_account_id INTEGER REFERENCES accounts(id), to_account_id INTEGER REFERENCES accounts(id), amount REAL, narration TEXT);
CREATE TABLE IF NOT EXISTS journal(id INTEGER PRIMARY KEY, vno TEXT, date TEXT, dr_party_id INTEGER REFERENCES parties(id), cr_party_id INTEGER REFERENCES parties(id), amount REAL, narration TEXT);
CREATE TABLE IF NOT EXISTS payment_allocs(id INTEGER PRIMARY KEY, payment_id INTEGER NOT NULL REFERENCES payments(id) ON DELETE CASCADE, ref_kind TEXT, ref_no TEXT, amount REAL);
CREATE TABLE IF NOT EXISTS challans(id INTEGER PRIMARY KEY, vno TEXT, date TEXT, party_id INTEGER REFERENCES parties(id), purpose TEXT, combo_id INTEGER REFERENCES combos(id), item_id INTEGER REFERENCES items(id),
  unit TEXT, qty REAL, remarks TEXT, vehicle_no TEXT, transport TEXT, lr_no TEXT, narration TEXT);
CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, type TEXT, opening REAL DEFAULT 0, details TEXT);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY, date TEXT, party_id INTEGER NOT NULL REFERENCES parties(id), amount REAL, note TEXT);
CREATE TABLE IF NOT EXISTS sales_returns(id INTEGER PRIMARY KEY, date TEXT, customer_id INTEGER REFERENCES parties(id),
  combo_id INTEGER REFERENCES combos(id), item_id INTEGER REFERENCES items(id), unit TEXT, qty REAL, rate REAL, amount REAL, note TEXT, return_type TEXT, {TAXCOLS});
CREATE TABLE IF NOT EXISTS sales_orders(id INTEGER PRIMARY KEY, order_no TEXT, date TEXT, customer_id INTEGER REFERENCES parties(id),
  combo_id INTEGER REFERENCES combos(id), item_id INTEGER REFERENCES items(id), unit TEXT, qty REAL, rate REAL, due_date TEXT,
  buyer_order_no TEXT, buyer_order_date TEXT, terms TEXT, note TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS pack_types(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, mode TEXT DEFAULT 'Fold');
CREATE TABLE IF NOT EXISTS fold_types(id INTEGER PRIMARY KEY, name TEXT NOT NULL, mode TEXT DEFAULT 'Fold', UNIQUE(name, mode));
DROP VIEW IF EXISTS order_pending; DROP VIEW IF EXISTS order_pick; DROP VIEW IF EXISTS job_work;
DROP VIEW IF EXISTS shade_stock; DROP VIEW IF EXISTS usage; DROP VIEW IF EXISTS stock; DROP VIEW IF EXISTS avgrate; DROP VIEW IF EXISTS combo_stock; DROP VIEW IF EXISTS combo_cost; DROP VIEW IF EXISTS invoice_totals;
""")
def addcol(t, c, typ):   # upgrade older data files
    try: db.execute(f"ALTER TABLE {t} ADD COLUMN {c} {typ}")
    except sqlite3.OperationalError: pass
for _c in ("pack_type", "fold_type"): addcol("sales_orders", _c, "TEXT")
addcol("sales_orders", "packs", "REAL"); addcol("sales_orders", "m_per_pack", "REAL"); addcol("pack_types", "approx_meters", "REAL"); addcol("fold_types", "cut_meters", "REAL")
if not db.execute("SELECT 1 FROM settings WHERE name='Pack Types Seeded 2'").fetchone():
    db.executemany("INSERT OR IGNORE INTO pack_types(name,mode,approx_meters) VALUES(?,?,?)", [("Roll", "Fold", 0), ("Lump", "Fold", 0), ("Pcs", "Cut", 0), ("Book Fold", "Fold", 0)])
    db.execute("INSERT INTO settings(name,value) VALUES('Pack Types Seeded 2','1')")
if not db.execute("SELECT 1 FROM settings WHERE name='Roll No Fold'").fetchone():
    db.execute("UPDATE pack_types SET mode='None' WHERE name='Roll'"); db.execute("INSERT INTO settings(name,value) VALUES('Roll No Fold','1')")
if not db.execute("SELECT 1 FROM settings WHERE name='Pack Types Seeded'").fetchone():      # starting lists - the user can add / edit / delete them in Masters
    db.executemany("INSERT OR IGNORE INTO pack_types(name,mode) VALUES(?,?)", [("Lump", "Fold"), ("Book Fold", "Fold"), ("Box Pack", "Cut"), ("Pcs Pack", "Cut")])
    db.executemany("INSERT OR IGNORE INTO fold_types(name,mode) VALUES(?,?)", [("Single Fold", "Fold"), ("Double Fold", "Fold"), ("Full Piece", "Cut"), ("Cut Piece", "Cut")])
    db.execute("INSERT INTO settings(name,value) VALUES('Pack Types Seeded','1')")
for _t in ("purchases", "orders", "sales_returns", "sales_orders", "conversions", "purchase_returns", "challans", "combo_lines"): addcol(_t, "shade", "TEXT")   # shade / design wise stock
for t in ("purchases", "orders", "sales_returns"):
    for c in ("gst_rate", "cgst", "sgst", "igst", "total"): addcol(t, c, "REAL")
for c in ("disc_trade", "disc_cash", "disc_flat", "freight"): addcol("orders", c, "REAL")
for c in ("transport", "lr_no", "vehicle_no", "lr_date"): addcol("orders", c, "TEXT")
addcol("sales_returns", "return_type", "TEXT"); addcol("parties", "state", "TEXT")
for t in ("items", "combos"): addcol(t, "hsn", "TEXT"); addcol(t, "gst_rate", "REAL")
addcol("items", "std_length", "REAL"); addcol("parties", "address2", "TEXT"); addcol("parties", "address3", "TEXT")
addcol("orders", "eway_no", "TEXT"); addcol("orders", "eway_date", "TEXT")
for c in ("buyer_order_no", "buyer_order_date", "terms"): addcol("orders", c, "TEXT")
addcol("orders", "order_id", "INTEGER REFERENCES sales_orders(id)")      # invoice made against a sales order
for c in ("ship_name", "ship_address", "ship_address2", "ship_address3", "ship_state"): addcol("parties", c, "TEXT")
for t in ("conversions", "combo_makes"): addcol(t, "contractor_id", "INTEGER REFERENCES parties(id)"); addcol(t, "job_rate", "REAL"); addcol(t, "job_amount", "REAL")
addcol("conversions", "job_basis", "TEXT"); addcol("payments", "account_id", "INTEGER REFERENCES accounts(id)")
db.execute("INSERT OR IGNORE INTO accounts(name,type,opening) VALUES('Cash','Cash',0)")
db.execute("UPDATE payments SET account_id=(SELECT id FROM accounts WHERE name='Cash') WHERE account_id IS NULL")
SERIES = {"purchases": "PUR", "sales_returns": "CN", "purchase_returns": "DN", "combo_makes": "CMK", "conversions": "FLD", "contra": "CTR", "journal": "JV", "challans": "DC"}   # every voucher type has its own number series
VNO_TABLES = set(SERIES) | {"payments"}
for _t in ("purchases", "payments", "sales_returns", "purchase_returns", "combo_makes", "conversions"): addcol(_t, "vno", "TEXT")
addcol("orders", "narration", "TEXT"); addcol("purchases", "narration", "TEXT"); addcol("purchases", "bill_no", "TEXT"); addcol("purchases", "bill_date", "TEXT")
for _t, _p in SERIES.items(): db.execute(f"UPDATE {_t} SET vno='{_p}/'||id WHERE COALESCE(vno,'')=''")
db.execute("UPDATE payments SET vno=CASE WHEN (SELECT type FROM parties WHERE id=party_id)='Customer' THEN 'RCT/' ELSE 'PAY/' END||id WHERE COALESCE(vno,'')=''")
db.executescript("""
CREATE VIEW usage AS
  SELECT 'make' src, m.id ref, m.date, cl.item_id, 'Pcs' unit, cl.qty*m.qty q, COALESCE(cl.shade,'') shade FROM combo_makes m JOIN combo_lines cl ON cl.combo_id=m.combo_id
  UNION ALL SELECT 'order', id, date, item_id, unit, qty, COALESCE(shade,'') FROM orders WHERE item_id IS NOT NULL AND status<>'Cancelled'
  UNION ALL SELECT 'return', id, date, item_id, unit, -qty, COALESCE(shade,'') FROM sales_returns WHERE item_id IS NOT NULL AND COALESCE(return_type,'Full') NOT LIKE 'Nothing%'
  UNION ALL SELECT 'return', r.id, r.date, cl.item_id, 'Pcs', -cl.qty*r.qty, COALESCE(cl.shade,'') FROM sales_returns r JOIN combo_lines cl ON cl.combo_id=r.combo_id
    JOIN items i ON i.id=cl.item_id WHERE r.combo_id IS NOT NULL AND r.return_type LIKE 'Fabrics%' AND i.type LIKE '%Fabric%'
  UNION ALL SELECT 'preturn', id, date, item_id, unit, qty, COALESCE(shade,'') FROM purchase_returns;
CREATE VIEW shade_stock AS SELECT item_id, shade, SUM(m) meters, SUM(p) pcs FROM (
  SELECT item_id, COALESCE(shade,'') shade, CASE WHEN unit='Meter' THEN qty ELSE 0 END m, CASE WHEN unit='Pcs' THEN qty ELSE 0 END p FROM purchases
  UNION ALL SELECT item_id, COALESCE(shade,''), -meters, pcs FROM conversions
  UNION ALL SELECT item_id, shade, -CASE WHEN unit='Meter' THEN q ELSE 0 END, -CASE WHEN unit='Pcs' THEN q ELSE 0 END FROM usage) GROUP BY item_id, shade;
CREATE VIEW stock AS SELECT i.id item_id,i.name,i.type,i.design,i.color,i.min_stock,
  COALESCE((SELECT SUM(qty) FROM purchases WHERE item_id=i.id AND unit='Meter'),0)
   -COALESCE((SELECT SUM(meters) FROM conversions WHERE item_id=i.id),0)
   -COALESCE((SELECT SUM(q) FROM usage WHERE item_id=i.id AND unit='Meter'),0) meters,
  COALESCE((SELECT SUM(qty) FROM purchases WHERE item_id=i.id AND unit='Pcs'),0)
   +COALESCE((SELECT SUM(pcs) FROM conversions WHERE item_id=i.id),0)
   -COALESCE((SELECT SUM(q) FROM usage WHERE item_id=i.id AND unit='Pcs'),0) pcs,
  COALESCE((SELECT SUM(wastage) FROM conversions WHERE item_id=i.id),0) wastage FROM items i;
CREATE VIEW order_pending AS SELECT o.id order_id,o.combo_id,o.item_id,o.unit,MAX(o.qty-COALESCE(i.q,0),0) pend,COALESCE(i.q,0) invoiced
  FROM sales_orders o LEFT JOIN (SELECT order_id,SUM(qty) q FROM orders WHERE status<>'Cancelled' AND order_id IS NOT NULL GROUP BY order_id) i ON i.order_id=o.id
  WHERE o.status<>'Cancelled';
CREATE VIEW order_pick AS SELECT o.id id,o.order_no||' | '||COALESCE(p.name,'')||' | '||COALESCE(c.name,it.name)||' | pending '||COALESCE(op.pend,0) name
  FROM sales_orders o LEFT JOIN order_pending op ON op.order_id=o.id LEFT JOIN parties p ON p.id=o.customer_id LEFT JOIN combos c ON c.id=o.combo_id LEFT JOIN items it ON it.id=o.item_id;
CREATE VIEW combo_stock AS SELECT combo_id,name,made,sold,returned,made-sold+returned bal,pending FROM
  (SELECT c.id combo_id,c.name,COALESCE((SELECT SUM(qty) FROM combo_makes WHERE combo_id=c.id),0) made,
   COALESCE((SELECT SUM(qty) FROM orders WHERE combo_id=c.id AND status<>'Cancelled'),0) sold,
   COALESCE((SELECT SUM(qty) FROM sales_returns WHERE combo_id=c.id AND COALESCE(return_type,'Full') LIKE 'Full%'),0) returned,
   COALESCE((SELECT SUM(pend) FROM order_pending WHERE combo_id=c.id),0) pending FROM combos c);
CREATE VIEW avgrate AS SELECT item_id, meter_rate,
  (pamt+cmeters*COALESCE(meter_rate,0)+cjob)/NULLIF(pqty+cpcs,0) pc_cost FROM
  (SELECT i.id item_id,
   (SELECT SUM(amount)/NULLIF(SUM(qty),0) FROM purchases WHERE item_id=i.id AND unit='Meter') meter_rate,
   COALESCE((SELECT SUM(amount) FROM purchases WHERE item_id=i.id AND unit='Pcs'),0) pamt,
   COALESCE((SELECT SUM(qty) FROM purchases WHERE item_id=i.id AND unit='Pcs'),0) pqty,
   COALESCE((SELECT SUM(meters) FROM conversions WHERE item_id=i.id),0) cmeters,
   COALESCE((SELECT SUM(pcs) FROM conversions WHERE item_id=i.id),0) cpcs,
   COALESCE((SELECT SUM(job_amount) FROM conversions WHERE item_id=i.id),0) cjob FROM items i);
CREATE VIEW invoice_totals AS SELECT customer_id, order_no, rnd(SUM(COALESCE(total,amount))) t FROM orders WHERE status<>'Cancelled' GROUP BY customer_id, order_no;
CREATE VIEW combo_cost AS SELECT cl.combo_id, SUM(cl.qty*COALESCE(a.pc_cost,0)) + COALESCE((SELECT SUM(job_amount)*1.0/NULLIF(SUM(qty),0) FROM combo_makes m WHERE m.combo_id=cl.combo_id),0) cost
  FROM combo_lines cl JOIN avgrate a ON a.item_id=cl.item_id GROUP BY cl.combo_id;
CREATE VIEW job_work AS
  SELECT c.id rid,'Fabric Folding' kind,c.date,c.contractor_id,i.name item,c.meters qty_in,c.pcs qty_out,c.wastage,c.job_rate,c.job_basis basis,COALESCE(c.job_amount,0) job_amount
    FROM conversions c JOIN items i ON i.id=c.item_id
  UNION ALL SELECT 1000000+m.id,'Combo Making',m.date,m.contractor_id,cb.name,NULL,m.qty,NULL,m.job_rate,'Per Combo',COALESCE(m.job_amount,0) FROM combo_makes m JOIN combos cb ON cb.id=m.combo_id;
""")
PROFILE = [("Company Name", "Company Name"), ("Address", "Address line 1"), ("Address 2", "Address line 2"), ("Address 3", "Address line 3 (city, pincode)"),
           ("State", "State (decides CGST+SGST / IGST)"), ("GST No", "GSTIN"), ("PAN", "PAN"), ("TAN", "TAN (Tax Deduction A/c No.)"), ("CIN", "CIN (Corporate Identity No.)"), ("Phone", "Phone / Mobile"), ("Email", "Email"),
           ("Account Holder", "Bank - A/c holder's name"), ("Bank Name", "Bank - Name"), ("Bank Account No", "Bank - A/c No."), ("Bank Branch", "Bank - Branch"),
           ("Bank IFSC", "Bank - IFS Code"), ("Bank Details", "Other bank info / UPI (optional)"), ("E-Way Limit", "E-Way bill needed above (Rs)"),
           ("Round Off", "Round off invoice total to nearest rupee (Yes/No)"), ("Jurisdiction", "Jurisdiction (e.g. Surat)"), ("Declaration", "Declaration (printed on invoice)"), ("Terms", "Terms & conditions (printed on invoice)")]
for k, v in [("Company Name", CO["name"]), ("Style Combo", "Yes" if CO.get("combo", True) else "No"), ("Style Shirting", "Yes" if CO.get("shirting", False) else "No"), ("Block Order If Stock Short (Yes/No)", "Yes"), ("Logo Data", ""), ("E-Way Limit", "50000"), ("Round Off", "Yes"), ("Page Paper", "A4"), ("Page Orientation", "Portrait"), ("Page Width (mm)", "210"), ("Page Height (mm)", "297"), ("Margin Top (mm)", "8"), ("Margin Bottom (mm)", "8"),
             ("Margin Left (mm)", "8"), ("Margin Right (mm)", "8"), ("Fill Full Page (Yes/No)", "Yes"), ("Print Font Size", "11"),
             ("Declaration", "We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.")] + [(k, "") for k, _ in PROFILE]:
    db.execute("INSERT OR IGNORE INTO settings(name,value) VALUES(?,?)", (k, v))
db.commit()
TODAY = lambda: datetime.date.today().isoformat()
def _fy_start():
    t = datetime.date.today(); return f"{t.year if t.month >= 4 else t.year - 1}-04-01"
def fy_of(iso): return int(iso[:4]) if int(iso[5:7]) >= 4 else int(iso[:4]) - 1
def fy_label(y): return f"{y}-{str(y + 1)[2:]}"
def fy_range(y): return f"{y}-04-01", f"{y + 1}-03-31"
_y0 = fy_of(TODAY())
WORK = {"date": TODAY(), "from": fy_range(_y0)[0], "to": fy_range(_y0)[1], "fy": _y0}   # F2 = working date, Alt+F2 = period, Ctrl+F2 = financial year
def in_period(iso): return bool(iso) and WORK["from"] <= iso <= WORK["to"]
def set_fy(y):
    WORK["fy"] = y; WORK["from"], WORK["to"] = fy_range(y); t = TODAY()
    WORK["date"] = t if WORK["from"] <= t <= WORK["to"] else (WORK["to"] if t > WORK["to"] else WORK["from"])
def fy_choices():
    cur = fy_of(TODAY()); d = db.execute("SELECT MIN(d) FROM (SELECT MIN(date) d FROM orders UNION ALL SELECT MIN(date) FROM purchases UNION ALL SELECT MIN(date) FROM payments UNION ALL SELECT MIN(date) FROM sales_orders)").fetchone()[0]
    return list(range(min(fy_of(d) if d else cur, cur), cur + 2))
STATUSBAR = [lambda: None]                                       # set by the main window; refreshes the bottom bar
def fmt_date(x):
    """'2026-10-05' -> '05/10/26' (screen / print format). Anything else is returned unchanged."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", x) if isinstance(x, str) else None
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)[2:]}" if m else ("" if x is None else x)
def parse_date(x):
    """DD/MM/YY (also DD/MM/YYYY, DD-MM-YY, DD.MM.YY, YYYY-MM-DD) -> 'YYYY-MM-DD' for the database; None if it is not a real date."""
    x = (x or "").strip()
    for f in ("%Y-%m-%d", "%d/%m/%y", "%d/%m/%Y", "%d-%m-%y", "%d-%m-%Y", "%d.%m.%y", "%d.%m.%Y"):
        try: return datetime.datetime.strptime(x, f).strftime("%Y-%m-%d")
        except ValueError: pass
    return None
def valid_date(x): return parse_date(x) is not None
def disp(v): return fmt_date(v) if isinstance(v, str) else v
def get(name): r = db.execute("SELECT value FROM settings WHERE name=?", (name,)).fetchone(); return r[0] or "" if r else ""
ROUNDING[0] = (get("Round Off") or "Yes").lower().startswith("y")
def style_on(name): return (get("Style " + name) or "").lower().startswith("y")
STYLE_ON = {"combo": style_on("Combo"), "shirting": style_on("Shirting")}
COMBO_ON, SHIRT_ON = STYLE_ON["combo"], STYLE_ON["shirting"]
PAGE_STYLE = {"Combo Master": "combo", "Combo Making": "combo", "Combo Stock": "combo", "Pcs Conversion": "combo", "Job Register": "combo", "Contractor Summary": "combo"}   # screens that belong to one work style
def page_on(name): r = PAGE_STYLE.get(name); return r is None or STYLE_ON[r]
ALERT = "(min_stock>0 AND pcs<=min_stock) OR pcs<0 OR meters<0"
RT = "choice:Full - all reusable|Fabrics only - packing damaged|Nothing reusable (all damaged)"
class Stop(Exception): pass
ON_CLOSE = [lambda: None]                      # set by the main window (backup + close)
ON_CHANGE_COMPANY = [lambda: None]             # set by the main window (F3)
ALLOC_HOOK = [lambda pid, parent: None]        # set by the main window: bill-wise adjustment after a payment / receipt is saved

def series_prefix(table, v=None):
    if table == "payments":
        r = db.execute("SELECT type FROM parties WHERE id=?", ((v or {}).get("party_id"),)).fetchone(); return "RCT" if r and r[0] == "Customer" else "PAY"
    return SERIES.get(table, "V")
def next_vno(table, prefix):
    n = db.execute(f"SELECT MAX(CAST(substr(vno,?) AS INTEGER)) FROM {table} WHERE vno LIKE ?", (len(prefix) + 2, prefix + "/%")).fetchone()[0] or 0
    return f"{prefix}/{n + 1}"
def suggest_vno(table, prefix=None): return next_vno(table, prefix or SERIES.get(table, "V"))
def assign_vno(table, v, rid):
    """Voucher number: typed by the user or the next one of its own series (PUR/5, PAY/12, RCT/3, CN/2 ...). Never the same twice."""
    x = (v.get("vno") or "").strip() or next_vno(table, series_prefix(table, v))
    if table == "challans":
        if db.execute("SELECT 1 FROM challans WHERE vno=? AND party_id IS NOT ? AND id IS NOT ?", (x, v.get("party_id"), rid)).fetchone(): raise Stop(f"Challan No {x} is already used for another party.")
    elif db.execute(f"SELECT 1 FROM {table} WHERE vno=? AND id IS NOT ?", (x, rid)).fetchone(): raise Stop(f"Voucher No {x} is already used. Every voucher has its own number.")
    return x
def VN(table, i): r = db.execute(f"SELECT vno FROM {table} WHERE id=?", (i,)).fetchone(); return r[0] if r else None

REPEAT_TABLES = {"orders", "sales_orders", "purchases", "payments", "sales_returns", "purchase_returns", "combo_makes", "conversions", "combo_lines"}   # vouchers: after Save the next blank entry opens (like Tally)
STOCK_TABLES = {"purchases", "conversions", "combo_makes", "combo_lines", "purchase_returns", "sales_returns", "orders"}    # deleting these must not leave stock negative
FORM_GUARD = {"purchases", "sales_returns", "combo_lines"}                                                                 # editing these is checked too (the other vouchers check stock themselves)
VKEYS = {}                                                                                                                  # F8 / F9 ... filled by the main window: switch voucher type inside an open voucher
def negative_stock():
    r = {n: (m, p) for n, m, p in db.execute("SELECT name,meters,pcs FROM stock WHERE meters<-0.000001 OR pcs<-0.000001")}
    r.update({n: (m, p) for n, m, p in db.execute("SELECT i.name||' ['||s.shade||']',s.meters,s.pcs FROM shade_stock s JOIN items i ON i.id=s.item_id WHERE s.shade<>'' AND (s.meters<-0.000001 OR s.pcs<-0.000001)")})
    return r
def norm_shade(item_id, text):
    """Tidy a shade / design name; reuse the spelling already in stock (Navy = navy = NAVY)."""
    t = " ".join((text or "").split())
    if not t: return ""
    r = db.execute("SELECT shade FROM shade_stock WHERE item_id IS ? AND LOWER(shade)=LOWER(?) LIMIT 1", (item_id, t)).fetchone()
    return r[0] if r else t
def shade_short(v, rid, src, item_name=None):
    """Stock of this item AND shade for an outgoing line (invoice / debit note)."""
    r = db.execute("SELECT meters,pcs FROM shade_stock WHERE item_id=? AND shade=?", (v["item_id"], v["shade"])).fetchone() or (0, 0)
    avail = r[0] if v["unit"] == "Meter" else r[1]
    if rid: avail += db.execute("SELECT COALESCE(SUM(q),0) FROM usage WHERE src=? AND ref=? AND item_id=? AND shade=? AND unit=?", (src, rid, v["item_id"], v["shade"], v["unit"])).fetchone()[0]
    nm = db.execute("SELECT name FROM items WHERE id=?", (v["item_id"],)).fetchone()[0]
    if v["qty"] > avail + 1e-9: confirm([f"{nm} [{v['shade']}]: need {v['qty']:g} {v['unit']}, available {avail:g}"])
def shade_asof(d):
    return f"""SELECT item_id, shade, SUM(m) meters, SUM(p) pcs FROM (
      SELECT item_id, COALESCE(shade,'') shade, CASE WHEN unit='Meter' THEN qty ELSE 0 END m, CASE WHEN unit='Pcs' THEN qty ELSE 0 END p FROM purchases WHERE date<='{d}'
      UNION ALL SELECT item_id, COALESCE(shade,''), -meters, pcs FROM conversions WHERE date<='{d}'
      UNION ALL SELECT item_id, shade, -CASE WHEN unit='Meter' THEN q ELSE 0 END, -CASE WHEN unit='Pcs' THEN q ELSE 0 END FROM usage WHERE date<='{d}') GROUP BY item_id, shade"""
def guard_stock(before, parent=None):
    after = negative_stock()
    worse = [f"{n}: {m:g} m, {p:g} pcs" for n, (m, p) in after.items() if n not in before or m < before[n][0] - 1e-9 or p < before[n][1] - 1e-9]
    if not worse: return
    msg = "This would make stock negative:\n" + "\n".join(worse)
    if get("Block Order If Stock Short (Yes/No)").lower().startswith("y"): raise Stop(msg)
    if not messagebox.askyesno("Stock goes negative", msg + "\n\nSave anyway?", parent=parent): raise Stop("Cancelled.")

GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
def check_gstin(g, state=""):
    g = (g or "").strip().upper()
    if not g: return None
    if not GSTIN_RE.match(g): return f"GSTIN '{g}' is not valid. It has 15 characters, like 24ABCDE1234F1Z5."
    code = STATES.get((state or "").strip())
    if code and g[:2] != code: return f"GSTIN starts with {g[:2]}, but {state} has state code {code}. Check the GSTIN or the State."
    return None
def pre_party(v, rid):
    v["gst"] = (v.get("gst") or "").strip().upper(); msg = check_gstin(v["gst"], v.get("state"))
    if msg: raise Stop(msg)

PAPERS = {"A4": (210, 297), "A5": (148, 210), "A3": (297, 420), "Letter": (215.9, 279.4), "Legal": (215.9, 355.6)}
def _num(x, default):
    try: return float(str(x).strip())
    except ValueError: return default
def page_conf(src=None):
    """Bill page settings (mm). src(key) -> text; default reads the saved settings."""
    g = src or get; paper = g("Page Paper") or "A4"
    w, h = PAPERS.get(paper) or (_num(g("Page Width (mm)"), 210), _num(g("Page Height (mm)"), 297))
    w, h = (max(w, h), min(w, h)) if (g("Page Orientation") or "Portrait").lower().startswith("l") else (min(w, h), max(w, h))
    return dict(w=w, h=h, t=_num(g("Margin Top (mm)"), 8), b=_num(g("Margin Bottom (mm)"), 8), l=_num(g("Margin Left (mm)"), 8), r=_num(g("Margin Right (mm)"), 8),
                fill=(g("Fill Full Page (Yes/No)") or "Yes").lower().startswith("y"), fs=_num(g("Print Font Size"), 11))
def page_css(fs=None):
    pc = page_conf()
    return (f"@page{{size:{pc['w']:g}mm {pc['h']:g}mm;margin:{pc['t']:g}mm {pc['r']:g}mm {pc['b']:g}mm {pc['l']:g}mm}}"
            f"html,body{{margin:0;padding:0}}body{{font-family:Arial,sans-serif;font-size:{(fs or pc['fs']):.2f}px}}")

def backup():
    """Copy the database to the 'backups' folder (keeps the newest 30)."""
    d = os.path.join(DATA, "backups"); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "combo_backup_" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".db")
    dest = sqlite3.connect(p); db.backup(dest); dest.close()
    for old in sorted(f for f in os.listdir(d) if f.startswith("combo_backup_"))[:-30]: os.remove(os.path.join(d, old))
    return p

ONES = "Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen Fifteen Sixteen Seventeen Eighteen Nineteen".split()
TENS = "_ _ Twenty Thirty Forty Fifty Sixty Seventy Eighty Ninety".split()
def words(amount):
    def below1000(n):
        w = []
        if n >= 100: w.append(ONES[n // 100] + " Hundred"); n %= 100
        if n >= 20: w.append(TENS[n // 10] + (" " + ONES[n % 10] if n % 10 else ""))
        elif n > 0: w.append(ONES[n])
        return " ".join(w)
    r = int(amount); ps = int(round((amount - r) * 100))
    if ps == 100: r, ps = r + 1, 0
    parts = []
    for div, nm in ((10**7, "Crore"), (10**5, "Lakh"), (1000, "Thousand")):
        if r >= div: parts.append(below1000(r // div) + " " + nm); r %= div
    if r or not parts: parts.append(below1000(r) if r else "Zero")
    out = "Rupees " + " ".join(parts) + (f" and {below1000(ps)} Paise" if ps else "") + " Only"
    return out

def confirm(short):
    if not short: return
    msg = "Stock is short:\n" + "\n".join(short)
    if get("Block Order If Stock Short (Yes/No)").lower().startswith("y"): raise Stop(msg)
    if not messagebox.askyesno("Stock short", msg + "\n\nSave anyway?"): raise Stop("Cancelled.")

def taxes(party_id, taxable, rate):
    """Same state (or state not set) -> CGST + SGST half each. Different state -> IGST."""
    ps = ((db.execute("SELECT COALESCE(NULLIF(ship_state,''),state) FROM parties WHERE id=?", (party_id,)).fetchone() or [""])[0] or "").strip().lower()   # place of supply = delivery state
    g = round(taxable * (rate or 0) / 100, 2)
    if not ps or ps == get("State").strip().lower(): c = round(g / 2, 2); return c, round(g - c, 2), 0.0
    return 0.0, 0.0, g
def set_tax(v, party_id, taxable, rate):
    c, s_, i = taxes(party_id, taxable, rate)
    v.update(gst_rate=rate or 0, cgst=c, sgst=s_, igst=i, total=round(taxable + c + s_ + i, 2))
def calc_line(qty, rate, tp, cp, fl, fr=0):
    gross = round(qty * rate, 2); dt = round(gross * (tp or 0) / 100, 2); dc = round((gross - dt) * (cp or 0) / 100, 2); df = fl or 0
    return gross, dt, dc, df, round(gross - dt - dc - df + (fr or 0), 2)
def prod_gst(combo_id, item_id):
    r = db.execute("SELECT gst_rate FROM combos WHERE id=?", (combo_id,)).fetchone() if combo_id else db.execute("SELECT gst_rate FROM items WHERE id=?", (item_id,)).fetchone()
    return (r[0] if r else 0) or 0

ST = "choice?:" + "|".join(sorted(STATES))
ITEM_FIELDS = [("name", "Item name", "text", ""), ("type", "Type", "choice:Shirt Fabric|Trouser Fabric|Shirting Fabric|Box|Inner Box|Outer Box|Other Packing|Watch|Handkerchief|Tie|Purse|Other", ""),
               ("design", "Design", "text", ""), ("color", "Color", "text", ""), ("hsn", "HSN Code", "text", ""), ("gst_rate", "GST Rate %", "num", "5"),
               ("std_length", "Std length of 1 Pc (m) - fabric only, for estimate", "num", "0"), ("min_stock", "Low-stock alert level (Pcs)", "num", "0")]
PARTY_FIELDS = [("name", "Name", "text", ""), ("type", "Type", "choice:Customer|Supplier|Contractor", ""), ("phone", "Phone", "text", ""),
                ("address", "Address line 1", "text", ""), ("address2", "Address line 2", "text", ""), ("address3", "Address line 3 (city, pincode)", "text", ""),
                ("gst", "GSTIN", "text", ""), ("state", "State", ST, ""),
                ("ship_name", "Ship-to name (only if different)", "text", ""), ("ship_address", "Ship-to address line 1", "text", ""), ("ship_address2", "Ship-to address line 2", "text", ""),
                ("ship_address3", "Ship-to address line 3 (city, pincode)", "text", ""), ("ship_state", "Ship-to State (decides GST type)", ST, "")]
COMBO_FIELDS = [("name", "Combo Name / Quality", "text", ""), ("hsn", "HSN Code", "text", ""), ("gst_rate", "GST Rate %", "num", "5")]
ACCOUNT_FIELDS = [("name", "Account name (e.g. Cash, SBI Current A/c)", "text", ""), ("type", "Type", "choice:Cash|Bank", "Bank"), ("opening", "Opening balance (Rs)", "num", "0"), ("details", "Bank / A/c No. / IFSC (optional)", "text", "")]
QUICK = {"items": ITEM_FIELDS, "parties": PARTY_FIELDS, "combos": COMBO_FIELDS, "accounts": ACCOUNT_FIELDS}   # tables that get a "+ New" button inside forms

def ask_dialog(parent, title, fields):
    """Small modal box. fields = [(label, default)]. Returns list of entered texts, or None if cancelled (Esc)."""
    win = tk.Toplevel(parent); win.title(title); win.grab_set(); win.resizable(False, False); box = ttk.Frame(win, padding=14); box.pack()
    res, vs = [None], []
    for i, (label, d) in enumerate(fields):
        ttk.Label(box, text=label).grid(row=i, column=0, sticky="e", padx=6, pady=6); v = tk.StringVar(value=d); vs.append(v)
        e = ttk.Entry(box, textvariable=v, width=16); e.grid(row=i, column=1, padx=6, pady=6)
        if i == 0: e.focus_set(); e.select_range(0, "end")
    def ok(e=None): res[0] = [v.get().strip() for v in vs]; win.destroy()
    ttk.Button(box, text="OK  (Enter)", command=ok, style="Accent.TButton").grid(row=len(fields), column=0, columnspan=2, pady=8)
    win.bind("<Return>", ok); win.bind("<Escape>", lambda e: win.destroy()); win.wait_window(); return res[0]

def setup_style(root):
    from tkinter import font as tkfont
    for n in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"): tkfont.nametofont(n).configure(family="Segoe UI", size=10)
    NAVY, BG = "#1f4e79", "#f3f5f8"; st = ttk.Style(); st.theme_use("clam")
    st.configure(".", font=("Segoe UI", 10)); st.configure("TFrame", background=BG); st.configure("TLabel", background=BG)
    st.configure("TCheckbutton", background=BG); st.configure("TNotebook", background=BG, borderwidth=0)
    st.configure("TNotebook.Tab", padding=(16, 7), font=("Segoe UI", 10, "bold"), background="#dfe6ee", foreground="#333333")
    st.map("TNotebook.Tab", background=[("selected", NAVY)], foreground=[("selected", "white")])
    st.configure("Main.TNotebook.Tab", padding=(22, 10), font=("Segoe UI", 11, "bold"))
    st.configure("Treeview", rowheight=28, background="white", fieldbackground="white", font=("Segoe UI", 10))
    st.configure("Treeview.Heading", background=NAVY, foreground="white", font=("Segoe UI", 10, "bold"), padding=6)
    st.map("Treeview.Heading", background=[("active", "#2b6cb0")])
    st.map("Treeview", background=[("selected", "#2b6cb0")], foreground=[("selected", "white")])
    st.configure("TButton", padding=(12, 6)); st.map("TButton", background=[("active", "#d0dcea")])
    st.configure("Accent.TButton", background=NAVY, foreground="white", padding=(14, 6)); st.map("Accent.TButton", background=[("active", "#2b6cb0")])
    root.configure(background=BG)

def _safe(fn):
    def w(*a, **k):
        try: return fn(*a, **k)
        except Exception: return None
    return w

def banner(parent, text, color):
    tk.Label(parent, text="  " + text, bg=color, fg="white", font=("Segoe UI", 12, "bold"), anchor="w", pady=7).pack(fill="x")

class SearchCombo(ttk.Combobox):
    """Dropdown you can TYPE in. As you type, the matching choices appear in a list under the box
    (Up/Down + Enter, or click one). The arrow button still opens the full list."""
    SKIP = ("Up", "Down", "Left", "Right", "Return", "Tab", "ISO_Left_Tab", "Escape", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Home", "End", "Caps_Lock")
    def __init__(s, parent, values, textvariable, width=30):
        super().__init__(parent, textvariable=textvariable, values=values, width=width)
        s.all = list(values); s._pop = None; s._lb = None
        for ev, fn in (("<KeyRelease>", s._key), ("<Down>", s._down), ("<Up>", s._up), ("<Return>", s._enter), ("<Escape>", s._esc), ("<<ComboboxSelected>>", s._reset), ("<FocusOut>", s._out)): s.bind(ev, fn)
        s.bind("<Tab>", lambda e: s._hide()); s.bind("<Destroy>", lambda e: s._hide())
    def set_all(s, values): s.all = list(values); s["values"] = s.all
    def matches(s, text):
        t = (text or "").strip().lower()
        if not t: return list(s.all)
        first = [v for v in s.all if v.lower().startswith(t)]
        return first + [v for v in s.all if t in v.lower() and v not in first]
    def _reset(s, e=None): s["values"] = s.all; s._hide()
    @_safe
    def _key(s, e):
        if e.keysym in s.SKIP or (e.keysym.startswith("F") and e.keysym[1:].isdigit()): return
        cur = s.get().strip(); m = s.matches(cur); s["values"] = m or s.all
        if cur and m and not (len(m) == 1 and m[0].lower() == cur.lower()): s._show(m)
        else: s._hide()
    @_safe
    def _show(s, m):
        if s._pop is None:
            s._pop = tk.Toplevel(s); s._pop.wm_overrideredirect(True)
            try: s._pop.attributes("-topmost", True)
            except Exception: pass
            s._lb = tk.Listbox(s._pop, exportselection=False, activestyle="none", takefocus=0, font=("Segoe UI", 10), width=max(int(str(s.cget("width"))), 24))
            s._lb.pack(); s._lb.bind("<Button-1>", s._click)
        lb = s._lb; lb.delete(0, "end")
        for v in m[:80]: lb.insert("end", v)
        lb.configure(height=min(lb.size(), 8)); lb.selection_clear(0, "end"); lb.selection_set(0); lb.activate(0)
        s._pop.geometry(f"+{s.winfo_rootx()}+{s.winfo_rooty() + s.winfo_height()}"); s._pop.lift()
    def _hide(s):
        if s._pop is not None:
            try: s._pop.destroy()
            except Exception: pass
            s._pop = s._lb = None
    def _step(s, d):
        lb = s._lb; i = (lb.curselection() or (-1 if d > 0 else 1,))[0] + d; i = max(0, min(i, lb.size() - 1))
        lb.selection_clear(0, "end"); lb.selection_set(i); lb.see(i)
    @_safe
    def _down(s, e):
        if s._pop is None: return None          # no suggestions showing: normal full list opens
        s._step(1); return "break"
    @_safe
    def _up(s, e):
        if s._pop is None: return None
        s._step(-1); return "break"
    @_safe
    def _enter(s, e):
        if s._pop is not None and s._lb.curselection(): s._pick(s._lb.get(s._lb.curselection()[0])); return "break"
        s._commit(); return None                # nothing showing: Enter just moves to the next field
    @_safe
    def _esc(s, e):
        if s._pop is not None: s._hide(); return "break"
    @_safe
    def _click(s, e): s._pick(s._lb.get(s._lb.nearest(e.y))); return "break"
    def _pick(s, v): s.set(v); s["values"] = s.all; s._hide(); s.icursor("end")
    @_safe
    def _out(s, e=None): s.after(150, s._hide); s._commit()
    def _commit(s):
        cur = s.get().strip()
        if not cur or cur in [v.strip() for v in s.all]: return
        m = s.matches(cur)
        if len(m) == 1: s.set(m[0])

def fk_options(kind):
    """kind = fk:table[:type] ; a type written as !Customer means 'everything except Customer'."""
    p = kind.split(":"); cond, args = "", []
    if len(p) > 2: cond = " WHERE type<>?" if p[2].startswith("!") else " WHERE type=?"; args = [p[2].lstrip("!")]
    return ([" "] if kind.startswith("fk?") else []) + [f"{a} - {b}" for a, b in db.execute(f"SELECT id,name FROM {p[1]}{cond} ORDER BY name", args)]

VLOOK = {"orders": ("Sales Invoice", "#e8f5ec", "#2e7d4f"), "sales_orders": ("Sales Order", "#e6f1fb", "#2f6fa8"), "purchases": ("Purchase Voucher", "#fdf0e0", "#c76b1a"),
         "sales_returns": ("Credit Note (Sales Return)", "#fbe9e9", "#b34a4a"), "purchase_returns": ("Debit Note (Purchase Return)", "#f1eafa", "#7a4fa3"),
         "payments": ("Payment / Receipt Voucher", "#fde8f1", "#b83280"), "combo_makes": ("Combo Making - Job Work", "#fff7d6", "#a07d00"),
         "conversions": ("Fabric Folding (Meter to Pcs) - Job Work", "#e3f6f5", "#23847f"), "combo_lines": ("Combo Master - Add Item to Combo", "#eef0fb", "#4a55a2"),
         "contra": ("Contra Voucher (Cash / Bank transfer)", "#e8f0fe", "#3f5bb5"), "journal": ("Journal Voucher (adjustment between parties)", "#f6ecf9", "#8e44ad"), "challans": ("Delivery Challan (no stock effect)", "#fff1e6", "#d9480f")}
MASTER_NAMES = {"pack_types": "Pack Type Master", "fold_types": "Fold / Cut Type Master", "accounts": "Bank / Cash Account Master", "items": "Item / Fabric Quality Master", "parties": "Customer / Supplier / Contractor Master", "combos": "Combo Master"}
def voucher_look(crud):
    """(title, light background, banner colour) - every voucher type has its own light colour, like Tally."""
    vt = getattr(crud, "vtype", None)
    if vt == "Payment": return ("Payment Voucher", "#fde8e8", "#c0392b")
    if vt == "Receipt": return ("Receipt Voucher", "#e3f6ee", "#1e8a5a")
    return VLOOK.get(crud.table) or (MASTER_NAMES.get(crud.table, "Entry"), "#eef3f9", "#2f5d8a")

class Form(tk.Toplevel):
    def __init__(s, crud, rowid=None, parent=None, initial=None):
        super().__init__(parent or crud)
        s.crud, s.rowid, s.vars, s.opts, s.widgets = crud, rowid, {}, {}, {}
        vtitle, vbg, vbar = voucher_look(crud); sty = "V" + vbar.lstrip("#")
        st = ttk.Style(); st.configure(sty + ".TFrame", background=vbg); st.configure(sty + ".TLabel", background=vbg)
        s.title(f"{vtitle} - " + ("Alter" if rowid else "Create")); s.grab_set(); s.resizable(False, False); s.configure(background=vbg)
        tk.Label(s, text=f"  {vtitle}    ({'Alter' if rowid else 'Create'})", bg=vbar, fg="white", font=("Segoe UI", 13, "bold"), anchor="w", padx=8, pady=9).pack(fill="x")
        body = ttk.Frame(s, padding=14, style=sty + ".TFrame"); body.pack()
        old = {}
        if rowid:
            cols = [f[0] for f in crud.fields]
            old = dict(zip(cols, db.execute(f"SELECT {','.join(cols)} FROM {crud.table} WHERE id=?", (rowid,)).fetchone()))
        n = len(crud.fields); per = (n + 1) // 2 if n > 12 else n                  # long forms use two columns
        for i, (col, label, kind, default) in enumerate(crud.fields):
            r, c0 = i % per, (i // per) * 3
            ttk.Label(body, text=label + (" (DD/MM/YY)" if kind.startswith("date") and "DD/MM" not in label else ""), style=sty + ".TLabel").grid(row=r, column=c0, sticky="e", padx=8, pady=4)
            v = tk.StringVar(); s.vars[col] = v
            d = default() if callable(default) else default
            if kind.startswith("fk"):
                opts = fk_options(kind); s.opts[col] = opts; w = SearchCombo(body, opts, v, 40)
                want = str(old[col]) if col in old else str(d)
                v.set(next((o for o in opts if o.split(" - ")[0] == want), ""))
                if kind.split(":")[1] in QUICK:
                    ttk.Button(body, text="+ New", width=7, takefocus=False, command=lambda c=col, k=kind: s.quick_add(c, k)).grid(row=r, column=c0 + 2, padx=4)
            elif kind.startswith("choice"):
                opts = ([" "] if kind.startswith("choice?") else []) + kind.split(":", 1)[1].split("|"); s.opts[col] = opts
                w = SearchCombo(body, opts, v, 40); v.set((old.get(col) or "") if rowid else d)
            else:
                w = ttk.Entry(body, textvariable=v, width=43)
                raw0 = old[col] if col in old and old[col] is not None else ("" if rowid else (WORK["date"] if kind == "date" else d)); v.set(fmt_date(raw0) if kind.startswith("date") else raw0)
            s.widgets[col] = w; w.grid(row=r, column=c0 + 1, padx=8, pady=4)
        bf = ttk.Frame(body, style=sty + ".TFrame"); bf.grid(row=per, column=0, columnspan=6, pady=10)
        ttk.Button(bf, text="Save  (Ctrl+A)", command=s.save, style="Accent.TButton").pack(side="left", padx=6)
        if getattr(crud, "header", None) and rowid is None and not initial: ttk.Button(bf, text="Save + Add Next Quality  (Ctrl+L)", command=lambda: s.save(True)).pack(side="left", padx=6)
        ttk.Label(body, text="Enter = next field   |   Backspace on an empty field = previous   |   Ctrl+A = save   |   Esc = close   |   F2 = date   |   Alt+C = + New", style=sty + ".TLabel").grid(row=per + 1, column=0, columnspan=6)
        s.msg = ttk.Label(body, text="", style=sty + ".TLabel", foreground="#1e7a46", font=("Segoe UI", 10, "bold")); s.msg.grid(row=per + 2, column=0, columnspan=6)
        s.repeat = crud.table in REPEAT_TABLES and rowid is None and not initial; s.saved = 0
        for col, val in (initial or {}).items():                      # prefilled values (e.g. invoice made from a sales order)
            kind = next((k for c, _, k, _ in crud.fields if c == col), None)
            if kind is None: continue
            if kind.startswith("fk"): s.vars[col].set(next((o for o in s.opts[col] if o.split(" - ")[0] == str(val)), ""))
            elif kind.startswith("date"): s.vars[col].set(fmt_date(val or ""))
            elif val is not None: s.vars[col].set(f"{val:g}" if isinstance(val, float) else str(val))
        s.init = {c: v.get() for c, v in s.vars.items()}
        s.bind("<Escape>", s.on_escape); s.bind("<Control-a>", lambda e: (s.save(), "break")[1]); s.bind("<Control-A>", lambda e: (s.save(), "break")[1])
        s.bind("<Control-l>", lambda e: (s.save(True), "break")[1]); s.bind("<Control-L>", lambda e: (s.save(True), "break")[1]); s.bind("<Return>", s.on_enter); s.bind("<F2>", s.change_date); s.bind("<Alt-c>", s.alt_c)
        for w in s.widgets.values(): w.bind("<BackSpace>", lambda e, w=w: s.prev_field(w))
        if s.repeat:
            for k in VKEYS: s.bind(k, lambda e, k=k: s.switch(k))
        first = next(iter(s.widgets.values()), None)
        if first is not None: s.after(80, first.focus_set)

    def prev_field(s, w):
        try:
            if not w.get(): w.tk_focusPrev().focus_set(); return "break"
        except Exception: pass
    def switch(s, key):
        if any(s.vars[c].get() != s.init.get(c) for c in s.vars) and not messagebox.askyesno("Switch voucher", "Discard this entry and open the other voucher?", parent=s): return "break"
        fn = VKEYS[key]; s.destroy(); fn(); return "break"
    def next_entry(s, more=False):
        s.saved += 1
        for col, label, kind, default in s.crud.fields:
            d = default() if callable(default) else default
            if kind == "date" or col in getattr(s.crud, "keep", ()) or (more and col in getattr(s.crud, "header", ())): continue   # the date (and, for a challan, its number / party / vehicle) stays, like Tally
            if kind.startswith("fk"): s.vars[col].set(next((o for o in s.opts[col] if o.split(" - ")[0] == str(d)), ""))
            else: s.vars[col].set("" if d is None else str(d))
        s.init = {c: v.get() for c, v in s.vars.items()}; s.msg.config(text=(f"Saved line {s.saved}.   Same document - enter the next quality / shade now." if more else f"Saved.   {s.saved} entr{'y' if s.saved == 1 else 'ies'} this session - the next one is ready."))
        first = next(iter(s.widgets.values()), None)
        if first is not None: first.focus_set()
    def on_escape(s, e=None):
        if any(s.vars[c].get() != s.init.get(c) for c in s.vars) and not messagebox.askyesno("Discard", "Close this entry without saving?", parent=s): return "break"
        s.destroy(); return "break"
    def on_enter(s, e=None):
        w = s.focus_get()
        if isinstance(w, ttk.Button): w.invoke()
        elif w is not None: w.tk_focusNext().focus_set()
        return "break"
    def change_date(s, e=None):
        col = next((c for c, _, k, _ in s.crud.fields if k == "date"), None)
        if col is None: return "break"
        r = ask_dialog(s, "Change Date (F2)", [("Date (DD/MM/YY)", s.vars[col].get())]); iso = parse_date(r[0]) if r else None
        if iso: s.vars[col].set(fmt_date(iso)); WORK["date"] = iso; STATUSBAR[0]()
        elif r: messagebox.showerror("Date", "Date must be DD/MM/YY.", parent=s)
        return "break"
    def alt_c(s, e=None):
        w = s.focus_get()
        for c, _, k, _ in s.crud.fields:
            if s.widgets.get(c) is w and k.startswith("fk") and k.split(":")[1] in QUICK: s.quick_add(c, k); break
        return "break"

    def quick_add(s, col, kind):
        """Add a new Item / Customer / Supplier / Combo without leaving this form; it gets selected automatically."""
        tb, parts = kind.split(":")[1], kind.split(":")
        fields = QUICK[tb]
        if tb == "parties" and len(parts) > 2 and not parts[2].startswith("!"): fields = [(c, l, k, parts[2] if c == "type" else d) for c, l, k, d in fields]
        q = types.SimpleNamespace(table=tb, fields=fields, pre=pre_party if tb == "parties" else None, after_save=None)
        def done():
            opts = fk_options(kind); s.opts[col] = opts; w = s.widgets[col]; w.all = opts; w["values"] = opts
            nid = db.execute(f"SELECT MAX(id) FROM {tb}").fetchone()[0]
            s.vars[col].set(next((o for o in opts if o.split(" - ")[0] == str(nid)), ""))
        q.refresh = done; Form(q, None, s)

    def save(s, more=False):
        vals = {}
        try:
            for w in s.widgets.values():
                if isinstance(w, SearchCombo): w._commit()
            for col, label, kind, _ in s.crud.fields:
                raw = s.vars[col].get().strip()
                if col in s.opts and raw and raw not in [o.strip() for o in s.opts[col]]: raise Stop(f"Please pick {label} from the list.")
                if kind.startswith("fk"):
                    if not raw and kind.startswith("fk?"): vals[col] = None; continue
                    if not raw: raise Stop(f"Please select {label}")
                    vals[col] = int(raw.split(" - ")[0])
                elif kind.startswith("choice"):
                    if not raw and not kind.startswith("choice?"): raise Stop(f"Please select {label}")
                    vals[col] = raw
                elif kind == "num": vals[col] = float(raw or 0)
                elif kind.startswith("date"):
                    iso = "" if (not raw and kind == "date?") else parse_date(raw)
                    if iso is None: raise Stop(f"{label}: enter the date as DD/MM/YY (for example 05/10/26).")
                    f0, f1 = fy_range(WORK["fy"])
                    if kind == "date" and not (f0 <= iso <= f1) and not messagebox.askyesno("Date outside the financial year", f"{fmt_date(iso)} is outside the selected financial year {fy_label(WORK['fy'])} ({fmt_date(f0)} to {fmt_date(f1)}).\n\nSave this entry anyway?", parent=s): raise Stop("Cancelled.")
                    vals[col] = iso
                else:
                    if not raw and col == "name": raise Stop(f"Please enter {label}")
                    vals[col] = raw
            if "vno" in vals: vals["vno"] = assign_vno(s.crud.table, vals, s.rowid)
            if s.crud.pre: s.crud.pre(vals, s.rowid)
            cols = list(vals); before = negative_stock() if s.crud.table in FORM_GUARD else None
            s.saved_id = s.rowid
            if s.rowid: db.execute(f"UPDATE {s.crud.table} SET {','.join(c+'=?' for c in cols)} WHERE id=?", [vals[c] for c in cols] + [s.rowid])
            else: s.saved_id = db.execute(f"INSERT INTO {s.crud.table}({','.join(cols)}) VALUES({','.join('?'*len(cols))})", [vals[c] for c in cols]).lastrowid
            if before is not None: guard_stock(before, s)
            db.commit()
        except Stop as e: db.rollback(); messagebox.showerror("Cannot save", str(e), parent=s); return
        except sqlite3.IntegrityError as e: db.rollback(); messagebox.showerror("Error", f"Duplicate or invalid entry.\n{e}", parent=s); return
        except ValueError: db.rollback(); messagebox.showerror("Error", "Invalid number or date (dates as DD/MM/YY).", parent=s); return
        s.crud.refresh(); (s.crud.after_save or (lambda: 0))()
        if s.crud.table == "payments": ALLOC_HOOK[0](s.saved_id, s)
        if s.repeat: s.next_entry(more and bool(getattr(s.crud, "header", None)))
        else: s.destroy()

class OrderVoucher(tk.Toplevel):
    """Sales Order voucher: common details on top, then the order lines below (quality, shade, qty, rate, pack type, fold / cut type)."""
    HEAD = [("order_no", "Order No", "text"), ("date", "Order Date", "date"), ("customer_id", "Customer", "fk:parties:Customer"),
            ("buyer_order_no", "Buyer's Order No. (PO)", "text"), ("buyer_order_date", "Buyer's Order Date", "date?"), ("due_date", "Delivery / Due Date", "date?"),
            ("terms", "Mode/Terms of Payment", "text"), ("note", "Note", "text"), ("status", "Status", "choice:Open|Cancelled")]
    COLS = ("Quality", "Shade / Design", "Pack Type", "Fold / Cut Type", "No. of Packs", "Mtr / Pack", "Approx Mtr", "Rate / Mtr", "Approx Amount")
    def __init__(s, crud, rowid=None, parent=None, initial=None):
        super().__init__(parent or crud)
        s.crud, s.rowid, s.vars, s.opts, s.widgets, s.lines, s.sel, s.saved, s.orig = crud, rowid, {}, {}, {}, [], None, 0, set()
        vtitle, vbg, vbar = voucher_look(crud); s.sty = sty = "V" + vbar.lstrip("#")
        st = ttk.Style(); st.configure(sty + ".TFrame", background=vbg); st.configure(sty + ".TLabel", background=vbg)
        st.configure(sty + ".Treeview", background="white", fieldbackground="white"); st.configure(sty + ".Treeview.Heading", background=vbar, foreground="white", font=("Segoe UI", 10, "bold"))
        s.title(f"{vtitle} - " + ("Alter" if rowid else "Create")); s.grab_set(); s.configure(background=vbg)
        tk.Label(s, text=f"  {vtitle}    ({'Alter' if rowid else 'Create'})", bg=vbar, fg="white", font=("Segoe UI", 13, "bold"), anchor="w", padx=8, pady=9).pack(fill="x")
        head = ttk.Frame(s, padding=(14, 10), style=sty + ".TFrame"); head.pack(fill="x")
        old = {}
        if rowid:
            r = db.execute("SELECT order_no,date,customer_id,buyer_order_no,buyer_order_date,due_date,terms,note,status FROM sales_orders WHERE id=?", (rowid,)).fetchone()
            old = dict(zip([h[0] for h in s.HEAD], r))
            for lid, cb, it, sh, q, u, rt, pk, fd, pc, mp in db.execute("SELECT id,combo_id,item_id,shade,qty,unit,rate,pack_type,fold_type,packs,m_per_pack FROM sales_orders WHERE order_no=? AND customer_id IS ? ORDER BY id", (old["order_no"], old["customer_id"])):
                s.lines.append(dict(id=lid, combo_id=cb, item_id=it, shade=sh or "", qty=q, unit=u, rate=rt or 0, pack_type=pk or "", fold_type=fd or "", packs=pc if pc else q, m_per_pack=mp or 0)); s.orig.add(lid)
        for i, (col, label, kind) in enumerate(s.HEAD):
            r, c0 = i // 3, (i % 3) * 3
            ttk.Label(head, text=label + (" (DD/MM/YY)" if kind.startswith("date") else ""), style=sty + ".TLabel").grid(row=r, column=c0, sticky="e", padx=6, pady=3)
            v = tk.StringVar(); s.vars[col] = v
            if kind.startswith("fk"):
                opts = fk_options(kind); s.opts[col] = opts; w = SearchCombo(head, opts, v, 26)
                v.set(next((o for o in opts if o.split(" - ")[0] == str(old.get(col, ""))), ""))
                ttk.Button(head, text="+ New", width=6, takefocus=False, command=lambda c=col, k=kind: s.quick_add(c, k)).grid(row=r, column=c0 + 2, padx=2)
            elif kind.startswith("choice"):
                opts = kind.split(":", 1)[1].split("|"); s.opts[col] = opts; w = SearchCombo(head, opts, v, 26); v.set(old.get(col) or "Open")
            else:
                w = ttk.Entry(head, textvariable=v, width=28)
                if kind.startswith("date"): v.set(fmt_date(old[col]) if old.get(col) else ("" if kind == "date?" or rowid else fmt_date((initial or {}).get("date") or WORK["date"])))
                elif col == "order_no": d = crud.fields[0][3]; v.set(old.get(col) or (d() if callable(d) else d))
                else: v.set(old.get(col) or "")
            s.widgets[col] = w; w.grid(row=r, column=c0 + 1, padx=4, pady=3)
        # lines
        mid = ttk.Frame(s, padding=(14, 0), style=sty + ".TFrame"); mid.pack(fill="both", expand=True)
        ttk.Label(mid, text="Order lines  -  ordered in Rolls / Lumps / Pcs; metres are approximate; rate is per metre and the same for the whole quality", style=sty + ".TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(2, 3))
        s.tree = ttk.Treeview(mid, columns=s.COLS, show="headings", height=8, style=sty + ".Treeview")
        for h, wd in zip(s.COLS, (210, 120, 100, 110, 90, 80, 90, 80, 110)): s.tree.heading(h, text=h); s.tree.column(h, width=wd, anchor="w" if h in ("Quality", "Shade / Design", "Pack Type", "Fold / Cut Type") else "e")
        s.tree.pack(fill="both", expand=True); s.tree.bind("<<TreeviewSelect>>", lambda e: s.pick()); s.tree.bind("<Delete>", lambda e: s.remove())
        ent = ttk.Frame(s, padding=(14, 6), style=sty + ".TFrame"); ent.pack(fill="x")
        s.ev = {k: tk.StringVar() for k in ("prod", "unit", "rate", "pack", "fold", "shade", "qty", "mpp")}
        s.po = prod_options(); s.ew = {}
        spec = [("prod", "Quality (Fabric / Combo)", 28, "c", s.po), ("shade", "Shade / Design", 14, "e", None), ("pack", "Pack Type", 12, "c", [r[0] for r in db.execute("SELECT name FROM pack_types ORDER BY name")]),
                ("fold", "Fold Type", 12, "c", []), ("qty", "No. of Packs", 9, "e", None), ("mpp", "Mtr / Pack (approx)", 10, "e", None), ("rate", "Rate / Mtr (excl. GST)", 10, "e", None), ("unit", "Unit (no pack)", 7, "c", ["Meter", "Pcs"])]
        for i, (k, lab, wd, typ, vals) in enumerate(spec):
            l = ttk.Label(ent, text=lab, style=sty + ".TLabel"); l.grid(row=0, column=i, sticky="w", padx=3)
            if k == "fold": s.fold_lbl = l
            if k == "qty": s.qty_lbl = l
            w = SearchCombo(ent, vals, s.ev[k], wd) if typ == "c" else ttk.Entry(ent, textvariable=s.ev[k], width=wd)
            w.grid(row=1, column=i, padx=3); s.ew[k] = w
        s.ev["unit"].set("Meter"); s.ew["pack"].bind("<<ComboboxSelected>>", lambda e: s.pack_changed(), add="+"); s.ew["pack"].bind("<FocusOut>", lambda e: s.pack_changed(), add="+")
        s.ew["fold"].bind("<<ComboboxSelected>>", lambda e: s.fold_changed(), add="+"); s.ew["fold"].bind("<FocusOut>", lambda e: s.fold_changed(), add="+")
        s.ew["prod"].bind("<<ComboboxSelected>>", lambda e: s.prod_changed(), add="+")
        s.ew["rate"].bind("<Return>", lambda e: (s.add_line(), "break")[1])
        s.hint = ttk.Label(s, text="", style=sty + ".TLabel", foreground="#7a4a00", padding=(14, 0)); s.hint.pack(anchor="w")
        bb = ttk.Frame(s, padding=(14, 2), style=sty + ".TFrame"); bb.pack(fill="x")
        s.addbtn = ttk.Button(bb, text="Add Line  (Enter on Rate)", command=s.add_line); s.addbtn.pack(side="left", padx=3)
        ttk.Button(bb, text="New Quality  (Ctrl+N)", command=s.new_quality).pack(side="left", padx=3)
        ttk.Button(bb, text="Remove Line  (Del)", command=s.remove).pack(side="left", padx=3)
        s.total = ttk.Label(bb, text="", style=sty + ".TLabel", font=("Segoe UI", 10, "bold")); s.total.pack(side="right", padx=6)
        sv = ttk.Frame(s, padding=(14, 6), style=sty + ".TFrame"); sv.pack(fill="x")
        ttk.Button(sv, text="Save Order  (Ctrl+A)", command=s.save, style="Accent.TButton").pack(side="left")
        s.msg = ttk.Label(sv, text="", style=sty + ".TLabel", foreground="#1e7a46", font=("Segoe UI", 10, "bold")); s.msg.pack(side="left", padx=12)
        ttk.Label(s, text="Pick quality + pack type (Roll / Lump / Pcs / Book Fold), then shade, number of packs and approx metres per pack   |   Ctrl+A = save   |   Esc = close   |   F2 = date", style=sty + ".TLabel").pack(pady=(0, 6))
        s.bind("<Escape>", s.on_escape); s.bind("<Control-a>", lambda e: (s.save(), "break")[1]); s.bind("<Control-A>", lambda e: (s.save(), "break")[1])
        s.bind("<Control-n>", lambda e: (s.new_quality(), "break")[1]); s.bind("<F2>", s.change_date)
        s.redraw(); s.snap = s.state()
        first = s.widgets["order_no"]; s.after(80, first.focus_set)
    def state(s): return (tuple(sorted((c, v.get()) for c, v in s.vars.items())), repr(s.lines))
    def on_escape(s, e=None):
        if s.state() != s.snap and not messagebox.askyesno("Discard", "Close this order without saving?", parent=s): return "break"
        s.destroy(); return "break"
    def change_date(s, e=None):
        r = ask_dialog(s, "Change Date (F2)", [("Date (DD/MM/YY)", s.vars["date"].get())]); iso = parse_date(r[0]) if r else None
        if iso: s.vars["date"].set(fmt_date(iso)); WORK["date"] = iso; STATUSBAR[0]()
        elif r: messagebox.showerror("Date", "Date must be DD/MM/YY.", parent=s)
        return "break"
    def quick_add(s, col, kind):
        tb = kind.split(":")[1]; parts = kind.split(":"); fields = QUICK[tb]
        if tb == "parties" and len(parts) > 2: fields = [(c, l, k, parts[2] if c == "type" else d) for c, l, k, d in fields]
        q = types.SimpleNamespace(table=tb, fields=fields, pre=pre_party if tb == "parties" else None, after_save=None)
        def done():
            opts = fk_options(kind); s.opts[col] = opts; w = s.widgets[col]; w.all = opts; w["values"] = opts
            nid = db.execute(f"SELECT MAX(id) FROM {tb}").fetchone()[0]; s.vars[col].set(next((o for o in opts if o.split(" - ")[0] == str(nid)), ""))
        q.refresh = done; Form(q, None, s)
    # ---- lines
    def label(s, l):
        if l["combo_id"]: return db.execute("SELECT name FROM combos WHERE id=?", (l["combo_id"],)).fetchone()[0]
        return db.execute("SELECT name FROM items WHERE id=?", (l["item_id"],)).fetchone()[0]
    def redraw(s):
        s.tree.delete(*s.tree.get_children()); tq = tv = tp = 0
        for n, l in enumerate(s.lines):
            s.tree.insert("", "end", iid=str(n), values=(s.label(l), l["shade"], l["pack_type"], l["fold_type"], f"{l['packs']:g}", f"{l['m_per_pack']:g}" if l["pack_type"] else "", f"{l['qty']:g}", f"{l['rate']:g}", f"{l['qty'] * l['rate']:,.2f}"))
            tq += l["qty"]; tv += l["qty"] * l["rate"]; tp += l["packs"] if l["pack_type"] else 0
        s.total.config(text=f"{len(s.lines)} line(s)   |   Packs {tp:g}   |   Approx qty {tq:g}   |   Approx value (excl. GST) {tv:,.2f}")
    def parse_prod(s):
        raw = s.ev["prod"].get().strip(); m = re.match(r"^([CI])(\d+) - ", raw)
        if not m or raw not in s.po: raise Stop("Please pick the Quality (fabric or combo) from the list.")
        return (int(m.group(2)), None) if m.group(1) == "C" else (None, int(m.group(2)))
    def prod_changed(s):
        try: cb, it = s.parse_prod()
        except Stop: return
        if cb: s.ev["unit"].set("Pcs"); s.ev["pack"].set(""); s.pack_changed()
        else:
            r = db.execute("SELECT rate FROM (SELECT rate FROM sales_orders WHERE item_id=? AND rate>0 ORDER BY id DESC LIMIT 1)", (it,)).fetchone()
            if r and not s.ev["rate"].get(): s.ev["rate"].set(f"{r[0]:g}")
    def pack_changed(s):
        pk = s.ev["pack"].get().strip(); r = db.execute("SELECT mode,approx_meters FROM pack_types WHERE name=?", (pk,)).fetchone(); mode = r[0] if r else "Fold"
        s.fold_lbl.config(text=("Cut Type" if mode == "Cut" else "Fold Type" if mode != "None" else "Fold (not needed)")); vals = [x[0] for x in db.execute("SELECT name FROM fold_types WHERE mode=? ORDER BY name", (mode,))]
        s.ew["fold"].set_all(vals)
        try: s.ew["fold"].config(state="disabled" if mode == "None" else "normal")
        except Exception: pass
        if mode == "None": s.ev["fold"].set("")
        s.qty_lbl.config(text=f"No. of {pk}" if pk else "Qty")
        if s.ev["fold"].get() and s.ev["fold"].get() not in vals: s.ev["fold"].set("")
        if r and r[1] and not s.ev["mpp"].get(): s.ev["mpp"].set(f"{r[1]:g}")
        s.hint.config(text=(f"Pcs / cut packs: metres per pc come from the Cut Type (Masters > Fold / Cut Types) - or type them in 'Mtr / Pack'." if mode == "Cut" and pk else ""))
        s.fold_changed()
    def fold_changed(s):
        pk, fd = s.ev["pack"].get().strip(), s.ev["fold"].get().strip()
        r = db.execute("SELECT f.cut_meters FROM fold_types f JOIN pack_types p ON p.mode=f.mode WHERE f.name=? AND p.name=?", (fd, pk)).fetchone() if fd and pk else None
        if r and r[0]: s.ev["mpp"].set(f"{r[0]:g}")
    def read_entry(s):
        for w in s.ew.values():
            if isinstance(w, SearchCombo): w._commit()
        cb, it = s.parse_prod()
        try: n = float(s.ev["qty"].get() or 0); rt = float(s.ev["rate"].get() or 0); mp = float(s.ev["mpp"].get() or 0)
        except ValueError: raise Stop("Packs, metres per pack and rate must be numbers.")
        if n <= 0: raise Stop("Number of packs / qty must be more than 0.")
        if rt < 0: raise Stop("Rate cannot be negative.")
        pk, fd = s.ev["pack"].get().strip(), s.ev["fold"].get().strip()
        if cb: pk = fd = ""
        if pk and (db.execute("SELECT mode FROM pack_types WHERE name=?", (pk,)).fetchone() or ("",))[0] == "None": fd = ""
        if pk and not db.execute("SELECT 1 FROM pack_types WHERE name=?", (pk,)).fetchone(): raise Stop("Please pick the Pack Type from the list (add new ones in Masters > Pack Types).")
        if fd and not db.execute("SELECT 1 FROM fold_types WHERE name=? AND mode=(SELECT mode FROM pack_types WHERE name=?)", (fd, pk)).fetchone(): raise Stop("Please pick the Fold / Cut Type from the list for this pack type.")
        if pk:
            if mp <= 0: raise Stop(f"Enter the approximate metres in one {pk} (Mtr / Pack).")
            qty, unit = round(n * mp, 3), "Meter"
        else: qty, unit, mp = n, ("Pcs" if cb else s.ev["unit"].get() or "Meter"), 0
        sh = norm_shade(it, s.ev["shade"].get()) if it else ""
        return dict(combo_id=cb, item_id=it, shade=sh, qty=qty, unit=unit, rate=rt, pack_type=pk, fold_type=fd, packs=n, m_per_pack=mp)
    def add_line(s):
        try:
            l = s.read_entry()
            for o in s.lines:
                if o is not s.cur() and (o["combo_id"], o["item_id"], o["shade"].lower()) == (l["combo_id"], l["item_id"], l["shade"].lower()): raise Stop("This quality and shade is already in the order. Select that line to change it.")
        except Stop as e: messagebox.showerror("Order line", str(e), parent=s); return
        cur = s.cur()
        if cur is not None: l["id"] = cur.get("id"); s.lines[s.lines.index(cur)] = l
        else: s.lines.append(l)
        for o in s.lines:                                   # one rate per metre for the whole quality
            if (o["combo_id"], o["item_id"]) == (l["combo_id"], l["item_id"]): o["rate"] = l["rate"]
        s.sel = None; s.addbtn.config(text="Add Line  (Enter on Rate)"); s.ev["shade"].set(""); s.ev["qty"].set(""); s.redraw(); s.ew["shade"].focus_set()   # quality, pack, fold, rate stay: next shade
    def cur(s): return s.lines[s.sel] if s.sel is not None and s.sel < len(s.lines) else None
    def pick(s):
        sel = s.tree.selection()
        if not sel: return
        s.sel = int(sel[0]); l = s.lines[s.sel]
        s.ev["prod"].set(next((o for o in s.po if o.startswith(("C" if l["combo_id"] else "I") + str(l["combo_id"] or l["item_id"]) + " - ")), ""))
        s.ev["unit"].set(l["unit"]); s.ev["pack"].set(l["pack_type"]); s.ev["shade"].set(l["shade"]); s.ev["mpp"].set(""); s.pack_changed()
        s.ev["fold"].set(l["fold_type"]); s.ev["mpp"].set(f"{l['m_per_pack']:g}" if l["pack_type"] else ""); s.ev["rate"].set(f"{l['rate']:g}"); s.ev["qty"].set(f"{l['packs']:g}"); s.addbtn.config(text="Update Line  (Enter on Rate)")
    def new_quality(s):
        s.sel = None; s.tree.selection_remove(*s.tree.selection()); s.addbtn.config(text="Add Line  (Enter on Rate)")
        for k in s.ev: s.ev[k].set("")
        s.ev["unit"].set("Meter"); s.pack_changed(); s.ew["prod"].focus_set()
    def remove(s):
        c = s.cur()
        if c is None: messagebox.showinfo("Remove", "Select a line first.", parent=s); return
        s.lines.remove(c); s.sel = None; s.redraw()
    # ---- save
    def save(s):
        try:
            for col in ("customer_id", "status"):
                if isinstance(s.widgets[col], SearchCombo): s.widgets[col]._commit()
            h = {}
            for col, label, kind in s.HEAD:
                raw = s.vars[col].get().strip()
                if kind.startswith("fk"):
                    if not raw or raw not in s.opts[col]: raise Stop(f"Please pick {label} from the list.")
                    h[col] = int(raw.split(" - ")[0])
                elif kind.startswith("date"):
                    iso = "" if (not raw and kind == "date?") else parse_date(raw)
                    if iso is None: raise Stop(f"{label}: enter the date as DD/MM/YY.")
                    if kind == "date":
                        f0, f1 = fy_range(WORK["fy"])
                        if not (f0 <= iso <= f1) and not messagebox.askyesno("Date outside the financial year", f"{fmt_date(iso)} is outside the selected financial year {fy_label(WORK['fy'])}.\n\nSave anyway?", parent=s): raise Stop("Cancelled.")
                    h[col] = iso
                else: h[col] = raw
            if not h["order_no"]: raise Stop("Please enter the Order No.")
            if not s.lines: raise Stop("Add at least one order line (quality, shade and qty).")
            same = {r[0] for r in db.execute("SELECT id FROM sales_orders WHERE order_no=? AND customer_id IS ?", (h["order_no"], h["customer_id"]))}
            if same - s.orig: raise Stop(f"Order No {h['order_no']} already exists for this customer. Open that order with Edit to change it, or use a new Order No.")
            gone = s.orig - {l.get("id") for l in s.lines}
            for gid in gone:
                if db.execute("SELECT COALESCE(SUM(qty),0) FROM orders WHERE order_id=? AND status<>'Cancelled'", (gid,)).fetchone()[0] > 0: raise Stop("A line you removed is already invoiced, so it cannot be removed.")
            rows = []
            for l in s.lines:
                v = dict(h); v.update({k: l[k] for k in ("combo_id", "item_id", "shade", "qty", "unit", "rate", "pack_type", "fold_type", "packs", "m_per_pack")})
                pre_sales_order(v, l.get("id")); rows.append((l.get("id"), v))
            for gid in gone: db.execute("DELETE FROM sales_orders WHERE id=?", (gid,))
            for lid, v in rows:
                cols = list(v)
                if lid: db.execute(f"UPDATE sales_orders SET {','.join(c + '=?' for c in cols)} WHERE id=?", [v[c] for c in cols] + [lid])
                else: db.execute(f"INSERT INTO sales_orders({','.join(cols)}) VALUES({','.join('?' * len(cols))})", [v[c] for c in cols])
            db.commit()
        except Stop as e: db.rollback(); messagebox.showerror("Cannot save", str(e), parent=s); return
        except sqlite3.IntegrityError as e: db.rollback(); messagebox.showerror("Error", f"Could not save.\n{e}", parent=s); return
        s.crud.refresh(); (s.crud.after_save or (lambda: 0))()
        par = s.master; d = h["date"]; new = s.rowid is None; s.destroy()
        if new: OrderVoucher(s.crud, None, par, initial={"date": d}).msg.config(text=f"Order {h['order_no']} saved - the next order is ready.")

def prod_options():
    o = [f"C{a} - {b}" for a, b in db.execute("SELECT id,name FROM combos ORDER BY name")] if COMBO_ON else []
    return o + [f"I{a} - {b}" for a, b in db.execute("SELECT id,name FROM items ORDER BY name")]

class Crud(ttk.Frame):
    def __init__(s, parent, table, fields, sql, heads, pre=None, extra=(), width=105, look=None, datecol=None):
        s_vno = fields is not None and table in VNO_TABLES
        if s_vno:
            fields = list(fields); at = next((i for i, f in enumerate(fields) if f[2].startswith("date")), 0) + 1
            fields.insert(at, ("vno", "Voucher No (blank = automatic)", "text", "" if table == "payments" else (lambda t=table: suggest_vno(t)))); heads = ("Voucher No",) + tuple(heads)
        vtitle, vbg, vbar = look or voucher_look(types.SimpleNamespace(table=table)); sty = "V" + vbar.lstrip("#"); st = ttk.Style()
        st.configure(sty + ".TFrame", background=vbg); st.configure(sty + ".Treeview", background="white", fieldbackground="white")
        st.configure(sty + ".Treeview.Heading", background=vbar, foreground="white", font=("Segoe UI", 10, "bold"), padding=6)
        st.map(sty + ".Treeview", background=[("selected", vbar)], foreground=[("selected", "white")]); st.map(sty + ".Treeview.Heading", background=[("active", vbar)])
        super().__init__(parent, style=sty + ".TFrame")
        s.form = Form
        s.table, s.fields, s.sql, s.pre, s.after_save, s.datecol, s.vno = table, fields, sql, pre, None, datecol, s_vno
        banner(s, vtitle + ("  -  Register" if fields else ""), vbar)
        bar = ttk.Frame(s, style=sty + ".TFrame"); bar.pack(fill="x", padx=6, pady=6)
        if fields:
            for t, f in (("Add  [Alt+A]", lambda: s.form(s)), ("Edit  [Enter]", s.edit), ("Delete  [Alt+D]", s.delete)): ttk.Button(bar, text=t, command=f, style="Accent.TButton" if t.startswith("Add") else "TButton").pack(side="left", padx=2)
        for label, fn in extra: ttk.Button(bar, text=label, command=lambda f=fn: f(s.selected())).pack(side="left", padx=2)
        ttk.Button(bar, text="Refresh", command=s.refresh).pack(side="right"); ttk.Button(bar, text="Export to Excel", command=s.export).pack(side="right", padx=4)
        s.tree = ttk.Treeview(s, columns=heads, show="headings", style=sty + ".Treeview"); s.tree.tag_configure("low", foreground="red"); s.tree.tag_configure("odd", background=vbg)
        for h in heads: s.tree.heading(h, text=h); s.tree.column(h, width=max(width, 9 * len(h) + 24))
        sb = ttk.Scrollbar(s, command=s.tree.yview); s.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); s.tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        if fields:
            s.tree.bind("<Double-1>", lambda e: s.edit()); s.tree.bind("<Return>", lambda e: s.edit())
            for k in ("<Insert>", "<Alt-a>"): s.tree.bind(k, lambda e: s.form(s))
            for k in ("<Delete>", "<Alt-d>"): s.tree.bind(k, lambda e: s.delete())
        if extra: s.tree.bind("<Control-p>", lambda e: extra[0][1](s.selected()))
        s.refresh()
    def export(s): export_table(s.table, list(s.tree["columns"]), [s.tree.item(i, "values") for i in s.tree.get_children()])
    def selected(s):
        sel = s.tree.selection()
        if not sel: messagebox.showinfo("Select", "Please select a row first."); return None
        return int(sel[0])
    def edit(s):
        i = s.selected()
        if i: s.form(s, i)
    def delete(s):
        i = s.selected()
        if i and messagebox.askyesno("Delete", "Delete this record?"):
            if s.table == "combo_lines" and db.execute("SELECT 1 FROM combo_makes WHERE combo_id=(SELECT combo_id FROM combo_lines WHERE id=?) LIMIT 1", (i,)).fetchone() and not messagebox.askyesno("Recipe changes past stock", "This combo has already been made. Removing an item also changes the stock figures of past production.\n\nContinue?"): return
            try:
                before = negative_stock() if s.table in STOCK_TABLES else None
                db.execute(f"DELETE FROM {s.table} WHERE id=?", (i,))
                if before is not None: guard_stock(before)
                db.commit()
            except sqlite3.IntegrityError: db.rollback(); messagebox.showerror("In use", "This record is used elsewhere; delete those entries first.")
            except Stop as e: db.rollback(); messagebox.showerror("Cannot delete", str(e))
            s.refresh(); (s.after_save or (lambda: 0))()
    def refresh(s):
        s.tree.delete(*s.tree.get_children())
        rows = [r for r in db.execute(s.sql() if callable(s.sql) else s.sql) if s.datecol is None or in_period(r[s.datecol])]   # voucher lists show only the selected period / year
        if s.vno: vm = dict(db.execute(f"SELECT id,vno FROM {s.table}")); rows = [(r[0], vm.get(r[0], "")) + tuple(r[1:]) for r in rows]
        for n, r in enumerate(rows):
            vals = [("" if x is None else disp(round(x, 3) if isinstance(x, float) else x)) for x in r[1:]]
            s.tree.insert("", "end", iid=str(r[0]), values=vals, tags=(("low",) if ("LOW STOCK" in vals or "Incomplete (min 2)" in vals) else ()) + (("odd",) if n % 2 else ()))

class ComboMaster(ttk.Frame):
    def __init__(s, parent):
        super().__init__(parent)
        s.sel = None; banner(s, "Combo Master  -  Combo Creation", "#4a55a2")
        top = ttk.Frame(s); top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text=f"COMBO MASTER - select a combo (quality) on the left, then add the {MIN_ITEMS} to {MAX_ITEMS} items it consumes per 1 combo on the right.").pack(side="left")
        ttk.Button(top, text="Consumption Estimate", command=s.estimate, style="Accent.TButton").pack(side="right")
        s.info = ttk.Label(s, text="", font=("Segoe UI", 10, "bold")); s.info.pack(anchor="w", padx=10, pady=(0, 4))
        s.left = Crud(s, "combos", COMBO_FIELDS,
                      f"SELECT id,name,hsn,gst_rate,n,CASE WHEN n<{MIN_ITEMS} THEN 'Incomplete (min {MIN_ITEMS})' ELSE 'OK' END FROM (SELECT c.*,(SELECT COUNT(*) FROM combo_lines WHERE combo_id=c.id) n FROM combos c) ORDER BY name",
                      ("Combo", "HSN", "GST %", "Items", "Status"), width=80)
        s.right = Crud(s, "combo_lines", [("combo_id", "Combo", "fk:combos", lambda: s.sel or ""), ("item_id", "Item (shirt / trouser / box / watch / tie...)", "fk:items", ""),
                       ("shade", "Shade / Design (blank = any)", "text", ""), ("qty", "Qty consumed per 1 combo (Pcs)", "num", "1")], "", ("Item", "Type", "Design", "Color", "Pcs per combo", "Std length/Pc (m)", "Est. meters per combo"), pre=pre_line)
        s.left.pack(side="left", fill="both", expand=True); s.right.pack(side="left", fill="both", expand=True)
        s.left.tree.bind("<<TreeviewSelect>>", lambda e: s.pick())
        s.left.after_save = s.refresh; s.right.after_save = s.refresh; s.pick()
    def pick(s):
        sel = s.left.tree.selection(); s.sel = sel[0] if sel else s.sel
        cid = int(s.sel or 0)
        s.right.sql = ("SELECT l.id,i.name||CASE WHEN COALESCE(l.shade,'')<>'' THEN ' ['||l.shade||']' ELSE '' END,i.type,i.design,i.color,l.qty,CASE WHEN i.type LIKE '%Fabric%' THEN i.std_length END,"
                       "CASE WHEN i.type LIKE '%Fabric%' THEN l.qty*i.std_length END FROM combo_lines l JOIN items i ON i.id=l.item_id "
                       f"WHERE l.combo_id={cid} ORDER BY i.type")
        s.right.refresh()
        if not s.sel: s.info.config(text="Select a combo on the left."); return
        n, m = db.execute("SELECT COUNT(*),COALESCE(SUM(CASE WHEN i.type LIKE '%Fabric%' THEN l.qty*COALESCE(i.std_length,0) END),0) FROM combo_lines l JOIN items i ON i.id=l.item_id WHERE l.combo_id=?", (cid,)).fetchone()
        warn = f"   -  needs at least {MIN_ITEMS} items before it can be made or sold" if n < MIN_ITEMS else ""
        s.info.config(text=f"Items: {n} (allowed {MIN_ITEMS} to {MAX_ITEMS})   |   Fabric needed for 1 combo: about {m:,.2f} m{warn}", foreground="#b00020" if n < MIN_ITEMS else "#1f4e79")
    def estimate(s):
        if not s.sel: messagebox.showinfo("Estimate", "Select a combo on the left first."); return
        show_estimate(s, int(s.sel))
    def refresh(s): s.left.refresh(); s.pick()

class Profile(ttk.Frame):
    def __init__(s, parent):
        super().__init__(parent); s.v = {}
        ttk.Label(s, text="COMPANY PROFILE - printed on every invoice, credit note and debit note.").grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=8)
        rows = [("Style Combo", "Work style: COMBO  (combo creation, making, combo stock, folding)"), ("Style Shirting", "Work style: SHIRTING FABRICS")] + PROFILE + [("Block Order If Stock Short (Yes/No)", "Block if stock is short (Yes/No)")]
        half = (len(rows) + 1) // 2
        for i, (k, label) in enumerate(rows):
            r, c = i % half + 1, (i // half) * 2
            ttk.Label(s, text=label).grid(row=r, column=c, sticky="e", padx=8, pady=3); s.v[k] = tk.StringVar()
            if k == "State": w = s.state_cb = SearchCombo(s, sorted(STATES), s.v[k], 38)
            elif k.startswith("Block") or k == "Round Off" or k.startswith("Style "): w = ttk.Combobox(s, textvariable=s.v[k], values=["Yes", "No"], state="readonly", width=38)
            else: w = ttk.Entry(s, textvariable=s.v[k], width=41)
            w.grid(row=r, column=c + 1, sticky="w", padx=8, pady=3)
        bar = ttk.Frame(s); bar.grid(row=half + 1, column=0, columnspan=4, sticky="w", padx=8, pady=(12, 4))
        for t, f, st in (("Save Profile", s.save, "Accent.TButton"), ("Backup Now", lambda: messagebox.showinfo("Backup", "Saved to:\n" + backup()), "TButton"),
                         ("Choose Logo...", s.pick_logo, "TButton"), ("Remove Logo", s.rm_logo, "TButton"), ("Page Setup...", lambda: PageSetup(s, test_print), "TButton"),
                         ("Select / Create Company  (F3)", lambda: ON_CHANGE_COMPANY[0](), "TButton")): ttk.Button(bar, text=t, command=f, style=st).pack(side="left", padx=4)
        s.logo_lbl = ttk.Label(s, text=""); s.logo_lbl.grid(row=half + 2, column=0, columnspan=4, sticky="w", padx=12)
        ttk.Label(s, text="A backup is also taken every time you open or close the program (last 30 kept in this company's 'backups' folder).  To add another firm: Select / Create Company.").grid(row=half + 3, column=0, columnspan=4, sticky="w", padx=12, pady=4)
        s.refresh()
    def pick_logo(s):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not p: return
        data = open(p, "rb").read()
        if len(data) > 1000000: messagebox.showerror("Logo", "Logo file is too big (max 1 MB)."); return
        mime = "image/png" if p.lower().endswith(".png") else "image/jpeg"
        db.execute("UPDATE settings SET value=? WHERE name='Logo Data'", ("data:%s;base64,%s" % (mime, base64.b64encode(data).decode()),)); db.commit(); s.refresh()
    def rm_logo(s): db.execute("UPDATE settings SET value='' WHERE name='Logo Data'"); db.commit(); s.refresh()
    def refresh(s):
        for k, v in s.v.items(): v.set(get(k))
        s.logo_lbl.config(text="Logo is set and will print on invoices." if get("Logo Data") else "No logo set.")
    def save(s):
        s.state_cb._commit(); st = s.v["State"].get().strip()
        if st and st not in STATES: messagebox.showerror("State", "Please pick the State from the list (type a few letters, then choose)."); return
        was = dict(STYLE_ON); now = {"combo": s.v["Style Combo"].get().lower().startswith("y"), "shirting": s.v["Style Shirting"].get().lower().startswith("y")}
        if not (now["combo"] or now["shirting"]): messagebox.showerror("Work style", "Please keep at least one work style Yes (Combo or Shirting Fabrics)."); return
        msg = check_gstin(s.v["GST No"].get(), s.v["State"].get().strip())
        if msg: messagebox.showerror("GSTIN", msg); return
        for k, v in s.v.items(): db.execute("INSERT OR REPLACE INTO settings(id,name,value) VALUES((SELECT id FROM settings WHERE name=?),?,?)", (k, k, v.get().strip()))
        db.commit(); ROUNDING[0] = (get("Round Off") or "Yes").lower().startswith("y"); nm = get("Company Name"); s.winfo_toplevel().title((nm + " - " if nm else "") + "Combo Manager"); 
        if REG is not None:
            for c in REG["companies"]:
                if c["key"] == CO["key"]: c["name"] = s.v["Company Name"].get().strip() or c["name"]; c["combo"], c["shirting"] = now["combo"], now["shirting"]
            save_registry(REG)
        if was != now and messagebox.askyesno("Work style changed", "The work style was changed.\n\nThe program must restart to show / hide the screens for this company.\nRestart now?"):
            relaunch(["--company=" + CO["key"]]); ON_CLOSE[0](); return
        messagebox.showinfo("Saved", "Company profile saved.")

def pre_contra(v, rid):
    if v["from_account_id"] == v["to_account_id"]: raise Stop("From account and To account must be different.")
    if v["amount"] <= 0: raise Stop("Amount must be more than 0.")
    old = db.execute("SELECT amount FROM contra WHERE id=? AND from_account_id=?", (rid, v["from_account_id"])).fetchone() if rid else None
    left = account_balance(v["from_account_id"]) + (old[0] if old else 0) - v["amount"]
    if left < -1e-9 and not messagebox.askyesno("Balance goes negative", f"The balance of '{db.execute('SELECT name FROM accounts WHERE id=?', (v['from_account_id'],)).fetchone()[0]}' will become negative ({left:,.2f}).\n\nSave anyway?"): raise Stop("Cancelled.")

def pre_journal(v, rid):
    if v["dr_party_id"] == v["cr_party_id"]: raise Stop("Debit party and Credit party must be different.")
    if v["amount"] <= 0: raise Stop("Amount must be more than 0.")

def pre_payment(v, rid):
    if v["amount"] <= 0: raise Stop("Amount must be more than 0.")
    typ = db.execute("SELECT type FROM parties WHERE id=?", (v["party_id"],)).fetchone()[0]
    if typ != "Customer":                     # money going out: warn if the cash / bank balance would go negative
        old = db.execute("SELECT amount FROM payments WHERE id=? AND account_id=?", (rid, v["account_id"])).fetchone() if rid else None
        left = account_balance(v["account_id"]) + (old[0] if old else 0) - v["amount"]
        if left < -1e-9 and not messagebox.askyesno("Balance goes negative", f"This payment makes the balance of '{db.execute('SELECT name FROM accounts WHERE id=?', (v['account_id'],)).fetchone()[0]}' negative ({left:,.2f}).\n\nSave anyway?"): raise Stop("Cancelled.")

def pre_purchase(v, rid):
    v["shade"] = norm_shade(v["item_id"], v.get("shade"))
    if v.get("bill_date") is None: v["bill_date"] = ""
    if v["qty"] <= 0: raise Stop("Quantity must be more than 0.")
    if v["rate"] < 0: raise Stop("Rate cannot be negative.")
    v["amount"] = round(v["qty"] * v["rate"], 2)
    set_tax(v, v["supplier_id"], v["amount"], db.execute("SELECT gst_rate FROM items WHERE id=?", (v["item_id"],)).fetchone()[0])

def pre_preturn(v, rid):
    if v["qty"] <= 0: raise Stop("Qty returned must be more than 0.")
    v["shade"] = norm_shade(v["item_id"], v.get("shade"))
    v["amount"] = round(v["qty"] * v["rate"], 2)
    set_tax(v, v["supplier_id"], v["amount"], db.execute("SELECT gst_rate FROM items WHERE id=?", (v["item_id"],)).fetchone()[0])
    name, m, p = db.execute("SELECT name,meters,pcs FROM stock WHERE item_id=?", (v["item_id"],)).fetchone()
    o = db.execute("SELECT q FROM usage WHERE src='preturn' AND ref=?", (rid,)).fetchone() if rid else None
    avail = (m if v["unit"] == "Meter" else p) + (o[0] if o else 0)
    if v["shade"]: shade_short(v, rid, "preturn")
    elif v["qty"] > avail + 1e-9: confirm([f"{name}: returning {v['qty']:g} {v['unit']}, in stock {avail:g}"])

def pre_convert(v, rid):
    name, typ, meters = db.execute("SELECT name,type,meters FROM stock WHERE item_id=?", (v["item_id"],)).fetchone()
    if "Fabric" not in (typ or ""): raise Stop("Pcs conversion is only for Shirt / Trouser fabric items.")
    if v["length"] <= 0: v["length"] = db.execute("SELECT std_length FROM items WHERE id=?", (v["item_id"],)).fetchone()[0] or 0   # blank -> item's std length
    if v["length"] <= 0 or v["meters"] <= 0: raise Stop("Meters and Length must be more than 0 (or set a 'Std length of 1 Pc' for this item in Items).")
    v["pcs"] = int(v["meters"] / v["length"] + 1e-9)
    if v["pcs"] < 1: raise Stop("Meters is less than one piece length.")
    v["shade"] = norm_shade(v["item_id"], v.get("shade"))
    v["wastage"] = round(v["meters"] - v["pcs"] * v["length"], 3)
    job_charge(v, v["pcs"] if (v.get("job_basis") or "Per Pc") == "Per Pc" else v["meters"])
    old = db.execute("SELECT meters FROM conversions WHERE id=?", (rid,)).fetchone() if rid else None
    avail = meters + (old[0] if old else 0)
    if v["shade"]:
        sm = (db.execute("SELECT meters FROM shade_stock WHERE item_id=? AND shade=?", (v["item_id"], v["shade"])).fetchone() or (0,))[0]
        so = db.execute("SELECT meters FROM conversions WHERE id=? AND COALESCE(shade,'')=?", (rid, v["shade"])).fetchone() if rid else None
        sm += so[0] if so else 0
        if v["meters"] > sm + 1e-9: confirm([f"{name} [{v['shade']}]: need {v['meters']:g} m, available {sm:g} m"])
    elif v["meters"] > avail + 1e-9: confirm([f"{name}: need {v['meters']:g} m, available {avail:g} m"])

MIN_ITEMS, MAX_ITEMS = 2, 5
def pre_line(v, rid):
    v["shade"] = norm_shade(v["item_id"], v.get("shade"))
    if db.execute("SELECT 1 FROM combo_makes WHERE combo_id=? LIMIT 1", (v["combo_id"],)).fetchone() and not messagebox.askyesno("Recipe changes past stock", "This combo has already been made. Changing its items also changes the stock figures of past production.\n\nContinue?"): raise Stop("Cancelled.")
    """Recipe line rules: no duplicate item in a combo, at most 5 items per combo."""
    if v["qty"] <= 0: raise Stop("Qty per combo must be more than 0.")
    if db.execute("SELECT 1 FROM combo_lines WHERE combo_id=? AND item_id=? AND id IS NOT ?", (v["combo_id"], v["item_id"], rid)).fetchone():
        raise Stop("This item is already in the combo. Edit its quantity instead of adding it again.")
    if db.execute("SELECT COUNT(*) FROM combo_lines WHERE combo_id=? AND id IS NOT ?", (v["combo_id"], rid)).fetchone()[0] >= MAX_ITEMS:
        raise Stop(f"A combo can have at most {MAX_ITEMS} items.")

def need_complete(combo_id):
    n = db.execute("SELECT COUNT(*) FROM combo_lines WHERE combo_id=?", (combo_id,)).fetchone()[0]
    if n < MIN_ITEMS: raise Stop(f"This combo has only {n} item(s). A combo needs {MIN_ITEMS} to {MAX_ITEMS} items - complete it in Combo Master.")

def estimate_rows(combo_id, qty):
    """What `qty` combos will consume, fabric in meters (using each fabric's Std length of 1 Pc), compared with stock."""
    rows, total_m = [], 0.0
    for name, typ, per, std, sm, sp in db.execute("SELECT i.name,i.type,l.qty,COALESCE(i.std_length,0),st.meters,st.pcs FROM combo_lines l JOIN items i ON i.id=l.item_id "
                                                 "JOIN stock st ON st.item_id=i.id WHERE l.combo_id=? ORDER BY i.type", (combo_id,)):
        need = per * qty; short = max(need - sp, 0); fab = "Fabric" in (typ or "")
        if fab and std > 0: nm = round(need * std, 3); total_m += nm
        else: nm = None
        if short <= 1e-9: act = "Stock OK"
        elif not fab: act = f"Buy {short:g} pcs"
        elif std <= 0: act = "Set 'Std length of 1 Pc' for this fabric in Items"
        else:
            conv = round(short * std, 3)
            have = max(sm, 0)
            act = f"Convert {conv:g} m into {short:g} pcs" if conv <= have + 1e-9 else (f"Buy {conv:g} m fabric (no meter stock)" if have <= 0 else f"Convert {have:g} m + buy {round(conv - have, 3):g} m more")
        rows.append((name, typ, round(need, 3), std if fab else "", nm if nm is not None else "", round(sp, 3), round(sm, 3) if fab else "", round(short, 3), act))
    return rows, round(total_m, 3)

def show_estimate(parent, cid):
    name = db.execute("SELECT name FROM combos WHERE id=?", (cid,)).fetchone()[0]
    win = tk.Toplevel(parent); win.title(f"Consumption Estimate - {name}"); win.geometry("1100x430"); win.grab_set()
    top = ttk.Frame(win, padding=8); top.pack(fill="x"); ttk.Label(top, text="How many combos?").pack(side="left")
    q = tk.StringVar(value="1"); e = ttk.Entry(top, textvariable=q, width=9); e.pack(side="left", padx=6); e.focus_set()
    heads = ("Item", "Type", "Pcs needed", "Std length/Pc (m)", "Meters needed", "Stock Pcs", "Stock Meters", "Short Pcs", "What to do")
    tree = ttk.Treeview(win, columns=heads, show="headings")
    for h in heads: tree.heading(h, text=h); tree.column(h, width=330 if h == "What to do" else 110)
    info = ttk.Label(win, text="", padding=8, font=("Segoe UI", 11, "bold"))
    def calc(ev=None):
        try: n = float(q.get())
        except ValueError: messagebox.showerror("Estimate", "Enter a number of combos.", parent=win); return
        rows, tot = estimate_rows(cid, n); tree.delete(*tree.get_children())
        for r in rows: tree.insert("", "end", values=r)
        info.config(text=f"For {n:g} combo(s): fabric needed about {tot:,.2f} meters   (set 'Std length of 1 Pc' in Items for every fabric)")
    ttk.Button(top, text="Calculate  (Enter)", command=calc, style="Accent.TButton").pack(side="left")
    ttk.Button(top, text="Export to Excel", command=lambda: export_table("estimate_" + name, list(heads), [tree.item(i, "values") for i in tree.get_children()])).pack(side="right")
    tree.pack(fill="both", expand=True, padx=8); info.pack(anchor="w"); e.bind("<Return>", calc); win.bind("<Escape>", lambda ev: win.destroy()); calc()

def job_charge(v, per_what):
    """Contractor job charge: rate x quantity. No contractor = own staff = no charge."""
    if not v.get("contractor_id"):
        if v.get("job_rate"): raise Stop("Select the Contractor for a job charge (or make the rate 0 for your own staff).")
        v["job_rate"] = 0; v["job_amount"] = 0; return
    if (v.get("job_rate") or 0) < 0: raise Stop("Job rate cannot be negative.")
    v["job_amount"] = round(per_what * (v.get("job_rate") or 0), 2)

def pre_make(v, rid):
    if v["qty"] <= 0: raise Stop("Qty of combos must be more than 0.")
    job_charge(v, v["qty"])
    lines = db.execute("SELECT item_id,qty FROM combo_lines WHERE combo_id=?", (v["combo_id"],)).fetchall()
    need_complete(v["combo_id"])
    old = dict(db.execute("SELECT item_id,q FROM usage WHERE src='make' AND ref=?", (rid,)).fetchall()) if rid else {}
    short = []
    for it, q in lines:
        n = q * v["qty"]; name, pcs = db.execute("SELECT name,pcs FROM stock WHERE item_id=?", (it,)).fetchone()
        if n > pcs + old.get(it, 0) + 1e-9: short.append(f"{name}: need {n:g} pcs, available {pcs + old.get(it, 0):g}")
    for it, q, sh in db.execute("SELECT item_id,qty,shade FROM combo_lines WHERE combo_id=? AND COALESCE(shade,'')<>''", (v["combo_id"],)).fetchall():
        n = q * v["qty"]; have = (db.execute("SELECT pcs FROM shade_stock WHERE item_id=? AND shade=?", (it, sh)).fetchone() or (0,))[0]
        if rid: have += db.execute("SELECT COALESCE(SUM(q),0) FROM usage WHERE src='make' AND ref=? AND item_id=? AND shade=?", (rid, it, sh)).fetchone()[0]
        if n > have + 1e-9: short.append(f"{db.execute('SELECT name FROM items WHERE id=?', (it,)).fetchone()[0]} [{sh}]: need {n:g} pcs, available {have:g}")
    confirm(short)

def pre_order(v, rid):
    if not (v["order_no"] or "").strip(): raise Stop("Please enter the Invoice No.")
    v["shade"] = norm_shade(v.get("item_id"), v.get("shade")) if v.get("item_id") else ""
    if v["qty"] <= 0: raise Stop("Qty must be more than 0.")
    if v["rate"] < 0: raise Stop("Rate cannot be negative.")
    if db.execute("SELECT 1 FROM orders WHERE order_no=? AND customer_id IS NOT ? AND id IS NOT ? AND status<>'Cancelled' LIMIT 1", (v["order_no"], v["customer_id"], rid)).fetchone(): raise Stop(f"Invoice No {v['order_no']} is already used for another customer. Every invoice needs its own number.")
    if v["rate"] == 0 and not messagebox.askyesno("Rate is 0", "The rate is 0. Continue (for example a free sample)?"): raise Stop("Cancelled.")
    if bool(v.setdefault("combo_id", None)) == bool(v["item_id"]): raise Stop("Select either a Combo OR a Single Item (not both, not none)." if COMBO_ON else "Please select the Item.")
    if v.get("order_id"):
        so = db.execute("SELECT order_no,customer_id,combo_id,item_id,qty,status,COALESCE(shade,'') FROM sales_orders WHERE id=?", (v["order_id"],)).fetchone()
        if so[6] and v["shade"] and so[6].lower() != v["shade"].lower(): raise Stop(f"Sales Order {so[0]} is for shade / design '{so[6]}', but this invoice line says '{v['shade']}'.")
        if so[6] and not v["shade"] and v["item_id"]: v["shade"] = so[6]
        if so[5] == "Cancelled": raise Stop(f"Sales Order {so[0]} is cancelled.")
        if so[1] != v["customer_id"] or so[2] != v["combo_id"] or so[3] != v["item_id"]: raise Stop(f"This invoice does not match Sales Order {so[0]} (customer or product is different).")
        done = db.execute("SELECT COALESCE(SUM(qty),0) FROM orders WHERE order_id=? AND status<>'Cancelled' AND id IS NOT ?", (v["order_id"], rid)).fetchone()[0]
        if v["qty"] + done > so[4] + 1e-9 and not messagebox.askyesno("More than ordered", f"Sales Order {so[0]}: ordered {so[4]:g}, already invoiced {done:g}, this invoice {v['qty']:g}.\n\nSave anyway?"): raise Stop("Cancelled.")
        for col in ("buyer_order_no", "buyer_order_date", "terms"):
            if not v.get(col): v[col] = db.execute(f"SELECT {col} FROM sales_orders WHERE id=?", (v["order_id"],)).fetchone()[0] or ""
    if v["combo_id"]: need_complete(v["combo_id"]); v["unit"] = "Pcs"   # combo stock may go negative: combos are usually made after the order arrives
    else:
        name, m, p = db.execute("SELECT name,meters,pcs FROM stock WHERE item_id=?", (v["item_id"],)).fetchone()
        o = db.execute("SELECT q FROM usage WHERE src='order' AND ref=? AND item_id=? AND unit=?", (rid, v["item_id"], v["unit"])).fetchone()
        avail = (m if v["unit"] == "Meter" else p) + (o[0] if o else 0)
        if v["shade"]: shade_short(v, rid, "order")
        elif v["qty"] > avail + 1e-9: confirm([f"{name}: need {v['qty']:g} {v['unit']}, available {avail:g}"])
    if v.get("buyer_order_date") and not valid_date(v["buyer_order_date"]): raise Stop("Buyer's Order Date must be DD/MM/YY (or leave it blank).")
    for col in ("buyer_order_no", "buyer_order_date", "terms"):          # same invoice, other lines: fill it in only once
        if not v.get(col):
            r = db.execute(f"SELECT MAX({col}) FROM orders WHERE order_no=? AND customer_id IS ? AND id IS NOT ?", (v["order_no"], v["customer_id"], rid)).fetchone()
            v[col] = r[0] or "" if r else ""
    taxable = calc_line(v["qty"], v["rate"], v["disc_trade"], v["disc_cash"], v["disc_flat"], v["freight"])[4]
    if taxable < 0: raise Stop("Discount is more than the amount.")
    v["amount"] = taxable
    set_tax(v, v["customer_id"], taxable, prod_gst(v["combo_id"], v["item_id"]))

def pre_sales_order(v, rid):
    v["shade"] = norm_shade(v.get("item_id"), v.get("shade")) if v.get("item_id") else ""
    if not (v["order_no"] or "").strip(): raise Stop("Please enter the Order No.")
    if db.execute("SELECT 1 FROM sales_orders WHERE order_no=? AND customer_id IS NOT ? AND id IS NOT ? AND status<>'Cancelled' LIMIT 1", (v["order_no"], v["customer_id"], rid)).fetchone(): raise Stop(f"Order No {v['order_no']} is already used for another customer.")
    if bool(v.setdefault("combo_id", None)) == bool(v["item_id"]): raise Stop("Select either a Combo OR a Single Item (not both, not none)." if COMBO_ON else "Please select the Item.")
    if v["combo_id"]: v["unit"] = "Pcs"
    if v["qty"] <= 0: raise Stop("Qty must be more than 0.")
    done = db.execute("SELECT COALESCE(SUM(qty),0) FROM orders WHERE order_id=? AND status<>'Cancelled'", (rid,)).fetchone()[0] if rid else 0
    if v["qty"] < done - 1e-9: raise Stop(f"{done:g} is already invoiced against this order, so the qty cannot be less than that.")

def pre_return(v, rid):
    v["shade"] = norm_shade(v.get("item_id"), v.get("shade")) if v.get("item_id") else ""
    if v["qty"] <= 0: raise Stop("Qty returned must be more than 0.")
    if bool(v.setdefault("combo_id", None)) == bool(v["item_id"]): raise Stop("Select either a Combo OR a Single Item (not both, not none)." if COMBO_ON else "Please select the Item.")
    if v["combo_id"]: v["unit"] = "Pcs"
    v["amount"] = round(v["qty"] * v["rate"], 2)
    set_tax(v, v["customer_id"], v["amount"], prod_gst(v["combo_id"], v["item_id"]))

STATUS = ["Pending", "Packed", "Dispatched", "Delivered"]
def next_status(oid):
    if not oid: return
    cur = db.execute("SELECT status FROM orders WHERE id=?", (oid,)).fetchone()[0]
    if cur == "Cancelled": messagebox.showinfo("Cancelled", "This order is cancelled. Use Edit to change its status."); return
    nxt = STATUS[(STATUS.index(cur) + 1) % 4] if cur in STATUS else STATUS[0]
    db.execute("UPDATE orders SET status=? WHERE id=?", (nxt, oid)); db.commit(); tabs["Sales Invoices"].refresh()

def mkline(name, hsn, qty, rate, tp, cp, fl, gr, cg, sg, ig, fr=0, unit="Pcs"):
    gross, dt, dc, df, tx = calc_line(qty, rate, tp, cp, fl, fr)
    return dict(name=name, hsn=hsn or "", qty=qty, rate=rate, gross=gross, dt=dt, dc=dc, df=df, tx=tx, fr=fr or 0, unit=unit or "Pcs", gr=gr or 0, cg=cg or 0, sg=sg or 0, ig=ig or 0)

def to_pdf(html_path, name):
    import shutil, subprocess
    d = os.path.join(DATA, "PDFs"); os.makedirs(d, exist_ok=True); pdf = os.path.join(d, name + ".pdf")
    cands = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"] + \
            [shutil.which(x) for x in ("msedge", "chrome", "google-chrome", "chromium")]
    for exe in [c for c in cands if c and os.path.exists(c)]:
        try:
            subprocess.run([exe, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={tempfile.mkdtemp()}",
                            f"--print-to-pdf={pdf}", "file:///" + html_path.replace("\\", "/")], timeout=90, capture_output=True)
            if os.path.exists(pdf): return pdf
        except Exception: pass
    messagebox.showwarning("PDF", "Could not create the PDF automatically (Microsoft Edge or Chrome is needed).\nThe print page will open - choose 'Save as PDF' there.")
    webbrowser.open(html_path); return None

def fit_script(avail_mm, fs, fill, mode):
    """Runs when the page loads: measures the real bill; if it is taller than the printable height the text is shrunk a little at a time,
    and any space left over is added as blank space inside the item table, so the bill always ends exactly at the bottom of the page."""
    js = ("function fit(){var t=document.getElementById('pgt'),c=document.getElementById('fillc');if(!t||!c)return;var d=document.createElement('div');"
          "d.style.cssText='position:absolute;visibility:hidden;width:100mm;height:1px';document.body.appendChild(d);var k=d.offsetWidth/100;document.body.removeChild(d);"
          "var a=AVAIL*k,f=FS,n=0;c.style.height='0px';while(t.offsetHeight>a+1&&n<80){f=f*0.97;document.body.style.fontSize=f+'px';n++;}"
          "var g=a-t.offsetHeight;if(g>0)c.style.height=g+'px';}"
          "window.onload=function(){" + ("fit();" if fill else "") + ("window.print();" if mode == "print" else "") + "};")
    return "<script>" + js.replace("AVAIL", f"{avail_mm:g}").replace("FS", f"{fs:.2f}") + "</script>"

def render(title, no, dt, party, lines, tag, meta=None, mode="print"):
    """Tally-style tax invoice / credit note / debit note."""
    dt = fmt_date(dt); meta = {k: (fmt_date(v) if k.endswith("date") else v) for k, v in (meta or {}).items()}; E = lambda x: htmllib.escape(str(x or "")); f = lambda x: f"{x:,.2f}"
    inter = any(l["ig"] for l in lines)
    bst = (party[4] or "").strip() or get("State"); bcode = STATES.get(bst, ""); cst = get("State"); ccode = STATES.get(cst, "")
    has_ship = bool(party[5] or party[6]); sst = (party[7] or "").strip() or bst; scode = STATES.get(sst, "")
    pst, pcode = sst, scode                      # place of supply = where the goods are delivered
    S = lambda k: sum(l[k] for l in lines)
    dtt, dcc, dff, frr, tx, cg, sg, ig = S("dt"), S("dc"), S("df"), S("fr"), S("tx"), S("cg"), S("sg"), S("ig")
    raw = round(tx + cg + sg + ig, 2); grand = rnd_py(raw); roff = round(grand - raw, 2)
    inr = lambda x: words(x).replace("Rupees", "INR", 1)
    label = {"Invoice": "Invoice No.", "CreditNote": "Credit Note No.", "DebitNote": "Debit Note No.", "SalesOrder": "Order No."}.get(tag, "No.")
    logo = f"<img src='{get('Logo Data')}' style='height:60px'>" if get("Logo Data") else ""
    caddr = "<br>".join(E(x) for x in (get("Address"), get("Address 2"), get("Address 3")) if x)
    company = (f"<div style='display:flex;gap:0.909em;align-items:center'>{logo}<div><b style='font-size:1.273em'>{E(get('Company Name'))}</b><br>{caddr}<br>GSTIN/UIN : {E(get('GST No'))}<br>"
               f"State Name : {E(cst)}, Code : {ccode}<br>Contact : {E(get('Phone'))}<br>E-Mail : {E(get('Email'))}" + "".join(f"<br>{k} : {E(get(k))}" for k in ("CIN", "TAN") if get(k)) + "</div></div>")
    head = "Supplier (Bill from)" if tag == "DebitNote" else "Buyer (Bill to)"
    pb = lambda h, nm, ad, stt, cd: (f"<div class=k>{h}</div><b>{E(nm)}</b><br>{ad}<br>GSTIN/UIN : {E(party[3])}<br>State Name : {E(stt)}, Code : {cd}<br>Contact : {E(party[1])}")
    cell = lambda k, v: f"<td class=m><span class=k>{k}</span><br><b>{E(v) or '&nbsp;'}</b></td>"
    mrows = [(label, no, "Dated", dt)]
    if tag == "Invoice": mrows += [("Buyer's Order No.", meta.get("buyer_order_no"), "Buyer's Order Date", meta.get("buyer_order_date")), ("E-Way Bill No.", meta.get("eway_no"), "E-Way Bill Date", meta.get("eway_date")), ("Dispatched through", meta.get("transport"), "Dispatch Doc No. (LR No.)", meta.get("lr_no")),
                                  ("Motor Vehicle No.", meta.get("vehicle"), "LR Date", meta.get("lr_date"))]
    if tag == "SalesOrder": mrows += [("Buyer's Order No.", meta.get("buyer_order_no"), "Buyer's Order Date", meta.get("buyer_order_date")), ("Delivery Due Date", meta.get("due_date"), "", "")]
    mrows += [("Place of Supply", f"{pst} ({pcode})" if pcode else pst, "Mode/Terms of Payment", meta.get("terms"))]
    meta_html = "<table class=meta>" + "".join(f"<tr>{cell(a, b)}{cell(c, d)}</tr>" for a, b, c, d in mrows) + "</table>"
    rows = ""
    for i, l in enumerate(lines, 1):
        rows += (f"<tr><td align=center>{i}</td><td><b>{E(l['name'])}</b></td><td>{E(l['hsn'])}</td><td align=right><b>{l['qty']:g} {l['unit']}</b></td>"
                 f"<td align=right>{f(l['rate'])}</td><td>{l['unit']}</td><td align=right><b>{f(l['gross'])}</b></td></tr>")
    adj = lambda text, amt: f"<tr><td></td><td align=right><i>{text}</i></td><td></td><td></td><td></td><td></td><td align=right><b>{amt}</b></td></tr>"
    if dtt: rows += adj("Less : Trade Discount", "(-) " + f(dtt))
    if dcc: rows += adj("Less : Cash Discount", "(-) " + f(dcc))
    if dff: rows += adj("Less : Special Discount", "(-) " + f(dff))
    if frr: rows += adj("Add : Freight / Courier", f(frr))
    if dtt or dcc or dff or frr: rows += adj("Taxable Value", f(tx))
    for rate in sorted({l["gr"] for l in lines}):
        sub = [l for l in lines if l["gr"] == rate]
        if not (sum(l["cg"] + l["sg"] + l["ig"] for l in sub) or rate): continue
        if inter: rows += adj(f"IGST @ {rate:g}%", f(sum(l["ig"] for l in sub)))
        else: rows += adj(f"CGST @ {rate / 2:g}%", f(sum(l["cg"] for l in sub))) + adj(f"SGST @ {rate / 2:g}%", f(sum(l["sg"] for l in sub)))
    if roff: rows += adj("Round Off", ("(-) " if roff < 0 else "") + f(abs(roff)))
    pc = page_conf(); fill = pc["fill"]; avail = max(60.0, pc["h"] - pc["t"] - pc["b"] - 3)
    # fit the bill to the page: estimate its height (mm); too tall -> shrink the text (everything is in em, so the whole layout shrinks); too short -> add blank space so it fills the page
    fs_eff = pc["fs"]; filler = 0.0       # the real fitting is done by the small script at the bottom of the page (measures the actual text)
    rows += ("<tr><td id=fillc style='height:0;padding:0'></td>" + "<td></td>" * 6 + "</tr>") if fill else f"<tr style='height:{max(0, 9 - len(lines)) * 2}em'>" + "<td></td>" * 7 + "</tr>"
    pg_open = "<table id=pgt class=pg><tr><td>" if fill else f"<div style='width:{pc['w'] - pc['l'] - pc['r']:g}mm'>"; pg_close = "</td></tr></table>" if fill else "</div>"
    mid_open = "</td></tr><tr><td>" if fill else ""; mid_close = "</td></tr><tr><td>" if fill else ""; items_style = ""
    units = {l["unit"] for l in lines}; tq = f"{S('qty'):g} {next(iter(units))}" if len(units) == 1 else ""
    rows += f"<tr class=tot><td></td><td align=right><b>Total</b></td><td></td><td align=right><b>{tq}</b></td><td></td><td></td><td align=right><b>&#8377; {f(grand)}</b></td></tr>"
    grp = {}
    for l in lines:
        g = grp.setdefault((l["hsn"], l["gr"]), [0.0, 0.0, 0.0, 0.0]); g[0] += l["tx"]; g[1] += l["cg"]; g[2] += l["sg"]; g[3] += l["ig"]
    if inter:
        hh = "<tr><th>HSN/SAC</th><th>Taxable Value</th><th>IGST Rate</th><th>IGST Amount</th><th>Total Tax Amount</th></tr>"
        hr = "".join(f"<tr><td>{E(h)}</td><td align=right>{f(g[0])}</td><td align=right>{r:g}%</td><td align=right>{f(g[3])}</td><td align=right>{f(g[3])}</td></tr>" for (h, r), g in grp.items())
        hr += f"<tr class=tot><td align=right><b>Total</b></td><td align=right><b>{f(tx)}</b></td><td></td><td align=right><b>{f(ig)}</b></td><td align=right><b>{f(ig)}</b></td></tr>"
    else:
        hh = "<tr><th>HSN/SAC</th><th>Taxable Value</th><th>CGST Rate</th><th>CGST Amount</th><th>SGST/UTGST Rate</th><th>SGST/UTGST Amount</th><th>Total Tax Amount</th></tr>"
        hr = "".join(f"<tr><td>{E(h)}</td><td align=right>{f(g[0])}</td><td align=right>{r / 2:g}%</td><td align=right>{f(g[1])}</td><td align=right>{r / 2:g}%</td><td align=right>{f(g[2])}</td><td align=right>{f(g[1] + g[2])}</td></tr>" for (h, r), g in grp.items())
        hr += f"<tr class=tot><td align=right><b>Total</b></td><td align=right><b>{f(tx)}</b></td><td></td><td align=right><b>{f(cg)}</b></td><td></td><td align=right><b>{f(sg)}</b></td><td align=right><b>{f(cg + sg)}</b></td></tr>"
    bank = [(a, get(k)) for a, k in (("A/c Holder's Name", "Account Holder"), ("Bank Name", "Bank Name"), ("A/c No.", "Bank Account No")) if get(k)]
    if get("Bank Branch") or get("Bank IFSC"): bank.append(("Branch &amp; IFS Code", E(get("Bank Branch")) + (" &amp; " if get("Bank Branch") and get("Bank IFSC") else "") + E(get("Bank IFSC"))))
    bank_html = "".join(f"{a} : <b>{E(b) if a != 'Branch &amp; IFS Code' else b}</b><br>" for a, b in bank) + (E(get("Bank Details")).replace("\n", "<br>") + "<br>" if get("Bank Details") else "")
    css = (page_css(fs_eff) + f".pg{{width:{pc['w'] - pc['l'] - pc['r']:g}mm}}" + ".pg{border-collapse:collapse}.pg>tbody>tr>td{padding:0;vertical-align:top;border:0}table{border-collapse:collapse;width:100%;font-size:inherit}.box td,.box th{border:1px solid #000;padding:0.455em 0.636em;vertical-align:top}"
           ".k{font-size:0.818em;color:#444}.meta td{border:1px solid #000;padding:0.273em 0.545em;width:50%}.meta{height:100%}.items{border:1px solid #000}.items th{border:1px solid #000;padding:0.364em;background:#f1f1f1}"
           ".items td{border-left:1px solid #000;border-right:1px solid #000;padding:0.273em 0.636em}.items td:nth-child(n+3){white-space:nowrap}.items tr.tot td,.hsn tr.tot td{border:1px solid #000;padding:0.364em 0.636em}.hsn td,.hsn th{border:1px solid #000;padding:0.273em 0.636em}.hsn th{background:#f1f1f1}")
    html = (f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{pg_open}<div align=center><b style='font-size:1.364em'>{title.title()}</b></div>"
            f"<table class=box style='margin-top:0.364em'><tr><td style='width:55%;padding:0'><div style='padding:0.545em 0.727em'>{company}</div>"
            f"<div style='padding:0.545em 0.727em;border-top:1px solid #000'>{pb('Consignee (Ship to)', party[5] or party[0], party[6] if has_ship else party[2], sst, scode)}</div><div style='padding:0.545em 0.727em;border-top:1px solid #000'>{pb(head, party[0], party[2], bst, bcode)}</div></td>"
            f"<td style='padding:0'>{meta_html}</td></tr></table>"
            f"{mid_open}<table class=items{items_style}><tr><th style='width:5%'>Sl No.</th><th>Description of Goods</th><th style='width:11%'>HSN/SAC</th><th style='width:13%'>Quantity</th><th style='width:11%'>Rate</th><th style='width:7%'>per</th><th style='width:17%'>Amount</th></tr>{rows}</table>{mid_close}"
            f"<table class=box><tr><td>Amount Chargeable (in words)<br><b style='font-size:1.091em'>{inr(grand)}</b></td><td align=right style='width:12%'>E. &amp; O.E</td></tr></table>"
            f"<table class=hsn>{hh}{hr}</table><table class=box><tr><td>Tax Amount (in words) : <b>{inr(round(cg + sg + ig, 2))}</b></td></tr></table>"
            f"<table class=box><tr><td style='width:50%'><div class=k>Company's PAN</div><b>{E(get('PAN'))}</b><br><br>{('<div class=k>Narration</div>' + E(meta.get('narration')) + '<br><br>') if meta.get('narration') else ''}<u>Declaration</u><br>{E(get('Declaration'))}<br>{E(get('Terms'))}</td>"
            f"<td><u>Company's Bank Details</u><br>{bank_html}<div align=right style='margin-top:0.727em'>for <b>{E(get('Company Name'))}</b><br><br><br><br>Authorised Signatory</div></td></tr></table>"
            f"<div align=center style='margin-top:0.364em'>{('SUBJECT TO ' + E(get('Jurisdiction')).upper() + ' JURISDICTION<br>') if get('Jurisdiction') else ''}This is a Computer Generated {title.title()}</div>{pg_close}"
            + fit_script(avail, fs_eff, fill, mode) + "</body></html>")
    p = os.path.join(tempfile.gettempdir(), f"{tag}_{no}.html".replace("/", "_")); open(p, "w", encoding="utf-8").write(html)
    if mode == "print": webbrowser.open(p); return p
    pdf = to_pdf(p, f"{tag}_{no}_{party[0]}".replace("/", "_").replace(" ", "_"))
    if pdf:
        try: os.startfile(pdf)
        except Exception: pass
        messagebox.showinfo("PDF saved", "Saved:\n" + pdf)
    return pdf

def test_print():
    r = db.execute("SELECT id FROM orders ORDER BY id DESC LIMIT 1").fetchone()
    if r: invoice(r[0])
    else: messagebox.showinfo("Test print", "No invoice yet - make one invoice first, then use Test Print.")

def party_row(pid):
    r = db.execute("SELECT name,phone,address,address2,address3,gst,state,ship_name,ship_address,ship_address2,ship_address3,ship_state FROM parties WHERE id=?", (pid,)).fetchone()
    if not r: return ("", "", "", "", "", "", "", "")
    br = lambda *xs: "<br>".join(htmllib.escape(x) for x in xs if x and x.strip())
    return (r[0], r[1] or "", br(r[2], r[3], r[4]), r[5] or "", r[6] or "", r[7] or "", br(r[8], r[9], r[10]), r[11] or "")

def invoice(oid, mode="print"):
    if not oid: return
    no, cid, dt = db.execute("SELECT order_no,customer_id,date FROM orders WHERE id=?", (oid,)).fetchone()
    rows = db.execute("SELECT COALESCE(c.name,i.name),COALESCE(c.hsn,i.hsn),o.qty,o.rate,o.disc_trade,o.disc_cash,o.disc_flat,o.gst_rate,o.cgst,o.sgst,o.igst,o.freight,o.unit "
                      "FROM orders o LEFT JOIN combos c ON c.id=o.combo_id LEFT JOIN items i ON i.id=o.item_id "
                      "WHERE o.order_no=? AND o.customer_id IS ? AND o.status<>'Cancelled'", (no, cid)).fetchall()
    tr = db.execute("SELECT MAX(transport),MAX(lr_no),MAX(vehicle_no),MAX(lr_date),MAX(eway_no),MAX(eway_date),MAX(buyer_order_no),MAX(buyer_order_date),MAX(terms) FROM orders WHERE order_no=? AND customer_id IS ? AND status<>'Cancelled'", (no, cid)).fetchone()
    nar = db.execute("SELECT MAX(narration) FROM orders WHERE order_no=? AND customer_id IS ? AND status<>'Cancelled'", (no, cid)).fetchone()[0]
    meta = dict(narration=nar, transport=tr[0], lr_no=tr[1], vehicle=tr[2], lr_date=tr[3], eway_no=tr[4], eway_date=tr[5], buyer_order_no=tr[6], buyer_order_date=tr[7], terms=tr[8])
    merged = {}                          # shades of one quality print as one line with the total qty
    for r in rows:
        k = (r[0], r[1], r[3], r[4], r[5], r[7], r[12])
        if k in merged:
            m = merged[k]; m[2] = (m[2] or 0) + (r[2] or 0)
            for j in (6, 8, 9, 10, 11): m[j] = (m[j] or 0) + (r[j] or 0)
        else: merged[k] = list(r)
    return render("TAX INVOICE", no, dt, party_row(cid), [mkline(*r) for r in merged.values()], "Invoice", meta, mode)

def sales_order_doc(oid, mode="print"):
    if not oid: return
    no, cid = db.execute("SELECT order_no,customer_id FROM sales_orders WHERE id=?", (oid,)).fetchone()
    rows = db.execute("SELECT o.date,COALESCE(c.name,i.name),COALESCE(o.shade,''),COALESCE(c.hsn,i.hsn),o.qty,o.rate,o.unit,o.buyer_order_no,o.buyer_order_date,o.terms,o.due_date,COALESCE(c.gst_rate,i.gst_rate),"
                      "COALESCE(o.pack_type,''),COALESCE(o.fold_type,''),o.packs,o.m_per_pack FROM sales_orders o LEFT JOIN combos c ON c.id=o.combo_id LEFT JOIN items i ON i.id=o.item_id "
                      "WHERE o.order_no=? AND o.customer_id IS ? AND o.status<>'Cancelled' ORDER BY o.id", (no, cid)).fetchall()
    if not rows: messagebox.showinfo("Sales Order", "This order is cancelled."); return
    lines = []
    for dt, nm, sh, hsn, q, rt, un, bn, bd, tm, due, gr, pk, fd, pc, mp in rows:
        t = {}; set_tax(t, cid, round(q * rt, 2), gr)
        extra = ", ".join(x for x in (sh, f"{pc:g} {pk}" if pk and pc else pk, fd, f"approx {mp:g} m each" if pk and mp else "") if x)
        lines.append(mkline(nm + (f" ({extra})" if extra else ""), hsn, q, rt, 0, 0, 0, t["gst_rate"], t["cgst"], t["sgst"], t["igst"], unit=un))
    r = rows[0]; meta = dict(buyer_order_no=r[7], buyer_order_date=r[8], terms=r[9], due_date=r[10])
    return render("SALES ORDER", no, r[0], party_row(cid), lines, "SalesOrder", meta, mode)

def whatsapp_invoice(oid):
    if not oid: return
    no, cid, dt = db.execute("SELECT order_no,customer_id,date FROM orders WHERE id=?", (oid,)).fetchone()
    tot = db.execute("SELECT rnd(SUM(COALESCE(total,amount))) FROM orders WHERE order_no=? AND customer_id IS ? AND status<>'Cancelled'", (no, cid)).fetchone()[0] or 0
    pty = party_row(cid); ph = re.sub(r"\D", "", pty[1] or ""); ph = "91" + ph if len(ph) == 10 else ph
    invoice(oid, "pdf")
    msg = f"Dear {pty[0]}, your invoice #{no} dated {fmt_date(dt)} for Rs. {tot:,.2f} is attached. - {get('Company Name')}"
    webbrowser.open(f"https://wa.me/{ph}?text={urllib.parse.quote(msg)}")
    messagebox.showinfo("WhatsApp", "WhatsApp is opening with the message.\nAttach the invoice PDF from the 'PDFs' folder (it is saved there).")

def credit_note(rid, mode="print"):
    if not rid: return
    r = db.execute("SELECT r.customer_id,r.date,COALESCE(c.name,i.name||CASE WHEN COALESCE(r.shade,'')<>'' THEN ' ['||r.shade||']' ELSE '' END),COALESCE(c.hsn,i.hsn),r.qty,r.rate,r.gst_rate,r.cgst,r.sgst,r.igst,r.unit,r.vno FROM sales_returns r "
                   "LEFT JOIN combos c ON c.id=r.combo_id LEFT JOIN items i ON i.id=r.item_id WHERE r.id=?", (rid,)).fetchone()
    render("CREDIT NOTE", (r[11] or f"CN-{rid}"), r[1], party_row(r[0]), [mkline(r[2], r[3], r[4], r[5], 0, 0, 0, *r[6:10], unit=r[10])], "CreditNote", {}, mode)

def debit_note(rid, mode="print"):
    if not rid: return
    r = db.execute("SELECT r.supplier_id,r.date,i.name,i.hsn,r.qty,r.rate,r.gst_rate,r.cgst,r.sgst,r.igst,r.unit,r.vno FROM purchase_returns r JOIN items i ON i.id=r.item_id WHERE r.id=?", (rid,)).fetchone()
    render("DEBIT NOTE", (r[11] or f"DN-{rid}"), r[1], party_row(r[0]), [mkline(r[2], r[3], r[4], r[5], 0, 0, 0, *r[6:10], unit=r[10])], "DebitNote", {}, mode)

def export_table(name, heads, rows):
    """Saves as .xlsx if the 'openpyxl' package is installed, otherwise as .csv (Excel opens both)."""
    try: import openpyxl; xl = True
    except ImportError: xl = False
    ext = ".xlsx" if xl else ".csv"
    path = filedialog.asksaveasfilename(defaultextension=ext, initialfile=f"{name}_{TODAY()}{ext}", filetypes=[("Excel" if xl else "CSV (opens in Excel)", "*" + ext)])
    if not path: return
    try:
        if xl:
            wb = openpyxl.Workbook(); ws = wb.active; ws.append(list(heads))
            for r in rows: ws.append(list(r))
            for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = min(45, max(len(str(c.value or "")) for c in col) + 2)
            wb.save(path)
        else:
            with open(path, "w", newline="", encoding="utf-8-sig") as f: w = csv.writer(f); w.writerow(heads); w.writerows(rows)
    except OSError as e: messagebox.showerror("Export", f"Could not save the file (is it open in Excel?).\n{e}"); return
    messagebox.showinfo("Export", "Saved:\n" + path)

BILL_NAME = {"INV": "Invoice ", "PUR": "Purchase ", "JOB": "Job "}
def party_bills(pid, own_payment=None, asof=None):
    """Bills of one party with adjusted / pending amounts (customer: invoices, supplier: purchase vouchers, contractor: job vouchers).
    own_payment = a payment whose own adjustments are not counted (used while editing it)."""
    ptype = db.execute("SELECT type FROM parties WHERE id=?", (pid,)).fetchone()[0]; lim = " AND date<='%s'" % asof if asof else ""
    if ptype == "Customer": src = [("INV", no, d, t, "") for d, no, t in db.execute(f"SELECT MIN(date),order_no,rnd(SUM(COALESCE(total,amount))) FROM orders WHERE customer_id=? AND status<>'Cancelled'{lim} GROUP BY order_no", (pid,))]
    elif ptype == "Contractor": src = [("JOB", vno, d, t, "") for vno, d, t in db.execute(f"SELECT vno,date,job_amount FROM combo_makes WHERE contractor_id=? AND COALESCE(job_amount,0)>0{lim} UNION ALL SELECT vno,date,job_amount FROM conversions WHERE contractor_id=? AND COALESCE(job_amount,0)>0{lim}", (pid, pid))]
    else: src = [("PUR", vno, d, t, bn or "") for vno, d, t, bn in db.execute(f"SELECT vno,date,COALESCE(total,amount),bill_no FROM purchases WHERE supplier_id=?{lim}", (pid,))]
    out = []; ex = " AND y.date<='%s'" % asof if asof else ""
    for kind, no, d, t, extra in sorted(src, key=lambda x: (x[2], str(x[1]))):
        done = db.execute("SELECT COALESCE(SUM(a.amount),0) FROM payment_allocs a JOIN payments y ON y.id=a.payment_id WHERE y.party_id=? AND a.ref_kind=? AND a.ref_no=? AND a.payment_id IS NOT ?" + ex, (pid, kind, str(no), own_payment)).fetchone()[0]
        out.append(dict(kind=kind, no=str(no), date=d, amount=round(t or 0, 2), done=round(done, 2), pending=round((t or 0) - done, 2), extra=extra))
    return out

def bills_sql():
    """Bill-wise outstanding of every party as on the end of the selected period. A last line per party ('On account') makes the total equal the party balance."""
    asof = WORK["to"]; ref = min(TODAY(), asof); rows = []; bal = {r[0]: r for r in db.execute(balances_sql())}
    for pid, name, ptype in db.execute("SELECT id,name,type FROM parties ORDER BY type,name").fetchall():
        tot = 0.0
        for b in party_bills(pid, None, asof):
            if abs(b["pending"]) > 0.005:
                days = (datetime.date.fromisoformat(ref) - datetime.date.fromisoformat(b["date"])).days
                rows.append((name, ptype, BILL_NAME[b["kind"]] + b["no"] + (f" / {b['extra']}" if b["extra"] else ""), b["date"], b["amount"], b["done"], b["pending"], days)); tot += b["pending"]
        diff = (bal[pid][5] if pid in bal else 0) - tot
        if abs(diff) > 0.005: rows.append((name, ptype, "On account (advance / credit note / journal)", "", 0, 0, round(diff, 2), ""))
    if not rows: return "SELECT 0,'','','','',0,0,0,'' WHERE 0"
    q = lambda x: "'" + str(x).replace("'", "''") + "'"
    return " UNION ALL ".join(f"SELECT {i + 1},{q(r[0])},{q(r[1])},{q(r[2])},{q(r[3])},{r[4]},{r[5]},{r[6]},{r[7] if isinstance(r[7], int) else q(r[7])}" for i, r in enumerate(rows))

class AllocDialog(tk.Toplevel):
    """Adjust a payment / receipt against the party's pending bills (like Tally's bill-wise allocation)."""
    def __init__(s, parent, pid):
        super().__init__(parent); s.pid = pid; s.grab_set(); s.configure(background="#eef3f9")
        pay = db.execute("SELECT y.party_id,y.amount,p.name,p.type,y.vno FROM payments y JOIN parties p ON p.id=y.party_id WHERE y.id=?", (pid,)).fetchone()
        s.party, s.amount = pay[0], pay[1]; s.title("Adjust against bills")
        tk.Label(s, text=f"  {'Receipt' if pay[3] == 'Customer' else 'Payment'} {pay[4] or ''}    {pay[2]}    Rs {s.amount:,.2f}", bg="#2f5d8a", fg="white", font=("Segoe UI", 12, "bold"), anchor="w", pady=8).pack(fill="x")
        body = ttk.Frame(s, padding=10); body.pack(fill="both", expand=True)
        s.bills = [b for b in party_bills(s.party, pid) if b["pending"] > 0.005]
        mine = {(k, n): a for k, n, a in db.execute("SELECT ref_kind,ref_no,amount FROM payment_allocs WHERE payment_id=?", (pid,))}
        for j, h in enumerate(("Bill", "Date", "Bill Amount", "Pending", "Adjust now")): ttk.Label(body, text=h, font=("Segoe UI", 10, "bold")).grid(row=0, column=j, padx=8, pady=4)
        s.vars = []
        for i, b in enumerate(s.bills, 1):
            lab = BILL_NAME[b["kind"]] + b["no"] + (f" / {b['extra']}" if b["extra"] else "")
            for j, t in enumerate((lab, fmt_date(b["date"]), f"{b['amount']:,.2f}", f"{b['pending']:,.2f}")): ttk.Label(body, text=t).grid(row=i, column=j, padx=8, pady=2, sticky="w")
            m = mine.get((b["kind"], b["no"])); v = tk.StringVar(value=f"{m:g}" if m else ""); s.vars.append(v); ttk.Entry(body, textvariable=v, width=14, justify="right").grid(row=i, column=4, padx=8)
        s.info = ttk.Label(body, text=""); s.info.grid(row=len(s.bills) + 1, column=0, columnspan=5, pady=6, sticky="w")
        bar = ttk.Frame(s); bar.pack(pady=8)
        for t, f in (("Auto (oldest first)", s.auto), ("Clear", s.clear), ("Save  (Ctrl+A)", s.save), ("Skip  (Esc)", s.destroy)): ttk.Button(bar, text=t, command=f).pack(side="left", padx=4)
        s.bind("<Control-a>", lambda e: s.save()); s.bind("<Escape>", lambda e: s.destroy())
        for v in s.vars: v.trace_add("write", lambda *a: s.recalc())
        s.recalc()
    def values(s):
        out = []
        for v in s.vars:
            try: out.append(max(0.0, float((v.get() or "0").replace(",", ""))))
            except ValueError: out.append(0.0)
        return out
    def recalc(s):
        t = sum(s.values()); s.info.config(text=f"Adjusted {t:,.2f} of {s.amount:,.2f}      On account (not adjusted): {s.amount - t:,.2f}", foreground="#b00020" if t > s.amount + 0.005 else "#1f4e79")
    def auto(s):
        left = s.amount
        for b, v in zip(s.bills, s.vars): take = min(b["pending"], max(left, 0)); v.set(f"{take:g}" if take > 0 else ""); left -= take
    def clear(s):
        for v in s.vars: v.set("")
    def save(s):
        vals = s.values()
        if sum(vals) > s.amount + 0.005: messagebox.showerror("Adjust", f"Adjusted {sum(vals):,.2f} is more than the amount {s.amount:,.2f}.", parent=s); return
        for b, x in zip(s.bills, vals):
            if x > b["pending"] + 0.005: messagebox.showerror("Adjust", f"{BILL_NAME[b['kind']]}{b['no']}: only {b['pending']:,.2f} is pending.", parent=s); return
        db.execute("DELETE FROM payment_allocs WHERE payment_id=?", (s.pid,))
        for b, x in zip(s.bills, vals):
            if x > 0: db.execute("INSERT INTO payment_allocs(payment_id,ref_kind,ref_no,amount) VALUES(?,?,?,?)", (s.pid, b["kind"], b["no"], round(x, 2)))
        db.commit(); s.destroy()

def alloc_after_save(pid, parent):
    r = db.execute("SELECT party_id FROM payments WHERE id=?", (pid,)).fetchone() if pid else None
    if r and any(b["pending"] > 0.005 for b in party_bills(r[0], pid)) and messagebox.askyesno("Bill-wise adjustment", "Adjust this against the party's pending bills now?", parent=parent): AllocDialog(parent, pid)
ALLOC_HOOK[0] = alloc_after_save

# ===== delivery challan =====
def pre_challan(v, rid):
    v.setdefault("combo_id", None); v["shade"] = norm_shade(v.get("item_id"), v.get("shade")) if v.get("item_id") else ""
    if bool(v["combo_id"]) == bool(v["item_id"]): raise Stop("Select either a Combo OR a Single Item (not both, not none)." if COMBO_ON else "Please select the Item.")
    if v["qty"] <= 0: raise Stop("Qty must be more than 0.")
    if v["combo_id"]: v["unit"] = "Pcs"

def challan_doc(cid, mode="print"):
    """Delivery challan: goods only, no prices. All lines with the same challan no. and party print together."""
    if not cid: return
    h = db.execute("SELECT vno,date,party_id,purpose,vehicle_no,transport,lr_no,narration FROM challans WHERE id=?", (cid,)).fetchone()
    lines = db.execute("SELECT COALESCE(cb.name,i.name||CASE WHEN COALESCE(c.shade,'')<>'' THEN ' ['||c.shade||']' ELSE '' END),COALESCE(cb.hsn,i.hsn,''),c.unit,c.qty,COALESCE(c.remarks,'') FROM challans c LEFT JOIN combos cb ON cb.id=c.combo_id LEFT JOIN items i ON i.id=c.item_id WHERE c.vno=? AND c.party_id IS ? ORDER BY c.id", (h[0], h[2])).fetchall()
    E = lambda x: htmllib.escape(str(x or "")); party = party_row(h[2]); pc = page_conf(); fill = pc["fill"]; avail = max(60.0, pc["h"] - pc["t"] - pc["b"] - 3); cst = get("State")
    logo = f"<img src='{get('Logo Data')}' style='height:60px'>" if get("Logo Data") else ""
    caddr = "<br>".join(E(x) for x in (get("Address"), get("Address 2"), get("Address 3")) if x)
    company = (f"<div style='display:flex;gap:10px;align-items:center'>{logo}<div><b style='font-size:1.3em'>{E(get('Company Name'))}</b><br>{caddr}<br>GSTIN/UIN : {E(get('GST No'))}<br>State : {E(cst)}, Code : {STATES.get(cst, '')}<br>"
               f"Contact : {E(get('Phone'))}  E-Mail : {E(get('Email'))}" + "".join(f"<br>{k} : {E(get(k))}" for k in ("CIN", "TAN") if get(k)) + "</div></div>")
    note = {"Job Work": "Goods sent for JOB WORK - not for sale. To be returned after processing.", "Sample": "Sample goods - not for sale.", "Return": "Goods returned."}.get(h[3] or "", "")
    cell = lambda k, v: f"<td class=m><span class=k>{k}</span><br><b>{E(v) or '&nbsp;'}</b></td>"
    meta = "<table class=meta>" + "".join(f"<tr>{cell(a, b)}{cell(c, d)}</tr>" for a, b, c, d in (("Challan No.", h[0], "Dated", fmt_date(h[1])), ("Purpose", h[3], "Vehicle No.", h[4]), ("Transport", h[5], "LR No.", h[6]))) + "</table>"
    rows = "".join(f"<tr><td align=center>{i}</td><td><b>{E(n)}</b></td><td>{E(hs)}</td><td align=right><b>{q:g} {u}</b></td><td>{E(r)}</td></tr>" for i, (n, hs, u, q, r) in enumerate(lines, 1))
    tot = {}
    for n, hs, u, q, r in lines: tot[u] = tot.get(u, 0) + q
    css = (page_css() + f".pg{{width:{pc['w'] - pc['l'] - pc['r']:g}mm;border-collapse:collapse}}.pg>tbody>tr>td{{padding:0;border:0;vertical-align:top}}table{{border-collapse:collapse;width:100%;font-size:inherit}}"
           ".box td{border:1px solid #000;padding:6px 8px;vertical-align:top}.meta td{border:1px solid #000;padding:4px 7px;width:50%}.k{font-size:.8em;color:#444}.items{border:1px solid #000}.items th{border:1px solid #000;padding:5px;background:#f1f1f1}"
           ".items td{border-left:1px solid #000;border-right:1px solid #000;padding:4px 8px}.items tr.tot td{border:1px solid #000}")
    pg_open = "<table id=pgt class=pg><tr><td>" if fill else f"<div style='width:{pc['w'] - pc['l'] - pc['r']:g}mm'>"; pg_close = "</td></tr></table>" if fill else "</div>"
    html = (f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{pg_open}<div align=center><b style='font-size:1.4em'>DELIVERY CHALLAN</b></div>"
            f"<table class=box style='margin-top:4px'><tr><td style='width:55%;padding:0'><div style='padding:8px'>{company}</div><div style='padding:8px;border-top:1px solid #000'><div class=k>To (Consignee)</div><b>{E(party[0])}</b><br>{party[2]}<br>GSTIN/UIN : {E(party[3])}<br>State : {E(party[4])}<br>Contact : {E(party[1])}</div></td>"
            f"<td style='padding:0'>{meta}</td></tr></table>"
            f"<table class=items><tr><th style='width:6%'>Sl No.</th><th>Description of Goods</th><th style='width:14%'>HSN/SAC</th><th style='width:18%'>Quantity</th><th style='width:24%'>Remarks</th></tr>{rows}"
            f"<tr><td colspan=5 style='padding:0'><div id=fillc style='height:0'></div></td></tr><tr class=tot><td></td><td align=right><b>Total</b></td><td></td><td align=right><b>{' + '.join(f'{q:g} {u}' for u, q in tot.items())}</b></td><td></td></tr></table>"
            f"<table class=box><tr><td>{('<b>' + E(note) + '</b><br>') if note else ''}{('Narration: ' + E(h[7]) + '<br>') if h[7] else ''}<span class=k>This challan is not a tax invoice. Rate and GST are shown on the invoice.</span></td></tr></table>"
            f"<table class=box><tr><td style='width:50%;height:70px'>Receiver's signature &amp; stamp</td><td align=right>for <b>{E(get('Company Name'))}</b><br><br><br>Authorised Signatory</td></tr></table>{pg_close}"
            f"{fit_script(avail, pc['fs'], fill, mode)}</body></html>")
    p = os.path.join(tempfile.gettempdir(), f"Challan_{h[0]}.html".replace("/", "_")); open(p, "w", encoding="utf-8").write(html)
    if mode == "print": webbrowser.open(p); return p
    pdf = to_pdf(p, f"Challan_{h[0]}_{party[0]}".replace("/", "_").replace(" ", "_"))
    if pdf:
        try: os.startfile(pdf)
        except Exception: pass
        messagebox.showinfo("PDF saved", "Saved:\n" + pdf)
    return pdf

def ledger_rows(pid, a, b):
    """Statement of one customer/supplier. Customer: bills = Debit, balance = they owe you. Supplier: bills = Credit, balance = you owe them."""
    ptype = db.execute("SELECT type FROM parties WHERE id=?", (pid,)).fetchone()[0]; ev = []
    if ptype == "Customer":
        for d, no, t in db.execute("SELECT MIN(date),order_no,rnd(SUM(COALESCE(total,amount))) FROM orders WHERE customer_id=? AND status<>'Cancelled' GROUP BY order_no", (pid,)): ev.append((d, 0, "Sales Invoice", f"Inv {no}", t, 0))
        for d, i, t in db.execute("SELECT date,id,rnd(COALESCE(total,amount)) FROM sales_returns WHERE customer_id=?", (pid,)): ev.append((d, 1, "Credit Note (return)", VN("sales_returns", i) or f"CN-{i}", 0, t))
        for d, i, t, n in db.execute("SELECT date,id,amount,note FROM payments WHERE party_id=?", (pid,)): ev.append((d, 2, "Payment received " + (n or ""), VN("payments", i) or f"Pay-{i}", 0, t))
    elif ptype == "Contractor":
        for d, k, i, t in db.execute("SELECT date,kind,rid,job_amount FROM job_work WHERE contractor_id=? AND job_amount>0", (pid,)): ev.append((d, 0, "Job Work - " + k, ("CM-" if k == "Combo Making" else "FF-") + str(i % 1000000), 0, t))
        for d, i, t, n in db.execute("SELECT date,id,amount,note FROM payments WHERE party_id=?", (pid,)): ev.append((d, 2, "Payment made " + (n or ""), VN("payments", i) or f"Pay-{i}", t, 0))
    else:
        for d, i, t in db.execute("SELECT date,id,COALESCE(total,amount) FROM purchases WHERE supplier_id=?", (pid,)): ev.append((d, 0, "Purchase", VN("purchases", i) or f"P-{i}", 0, t))
        for d, i, t in db.execute("SELECT date,id,rnd(COALESCE(total,amount)) FROM purchase_returns WHERE supplier_id=?", (pid,)): ev.append((d, 1, "Debit Note (return)", VN("purchase_returns", i) or f"DN-{i}", t, 0))
        for d, i, t, n in db.execute("SELECT date,id,amount,note FROM payments WHERE party_id=?", (pid,)): ev.append((d, 2, "Payment made " + (n or ""), VN("payments", i) or f"Pay-{i}", t, 0))
    for d, i, vn, dr_id, cr_id, amt, nar in db.execute("SELECT date,id,vno,dr_party_id,cr_party_id,amount,narration FROM journal WHERE dr_party_id=? OR cr_party_id=?", (pid, pid)):
        ev.append((d, 3, "Journal" + (f" ({nar})" if nar else ""), vn or f"JV-{i}", amt if dr_id == pid else 0, amt if cr_id == pid else 0))
    ev.sort(key=lambda e: (e[0], e[1])); sg = 1 if ptype == "Customer" else -1; bal = 0.0; opening = None; rows = []
    for d, _, part, ref, dr, cr in ev:
        if d < a: bal += sg * (dr - cr); continue
        if opening is None: opening = bal
        if d > b: break
        bal += sg * (dr - cr); rows.append((d, part, ref, round(dr, 2), round(cr, 2), round(bal, 2)))
    if opening is None: opening = bal
    return ptype, round(opening, 2), rows, round(bal if not rows else rows[-1][5], 2)

class Ledger(ttk.Frame):
    HEADS = ("Date", "Particulars", "Ref", "Debit", "Credit", "Balance")
    def __init__(s, parent):
        super().__init__(parent); s.p = tk.StringVar(); s.data = None; t = datetime.date.today(); banner(s, "Account Statement (Ledger)", "#7a4fa3")
        s.a, s.b = tk.StringVar(value=fmt_date(WORK["from"])), tk.StringVar(value=fmt_date(WORK["to"]))
        bar = ttk.Frame(s); bar.pack(fill="x", padx=6, pady=6)
        s.cb = SearchCombo(bar, [], s.p, 38); s.cb.pack(side="left", padx=4)
        for lbl, v in (("From", s.a), ("To", s.b)): ttk.Label(bar, text=lbl).pack(side="left"); ttk.Entry(bar, textvariable=v, width=11).pack(side="left", padx=3)
        for lbl, f in (("Show Statement", s.show), ("Export to Excel", s.export), ("Print", s.print)): ttk.Button(bar, text=lbl, command=f).pack(side="left", padx=3)
        s.info = ttk.Label(s, text="Select a customer / supplier / contractor, or a Cash / Bank account, then click Show Statement."); s.info.pack(anchor="w", padx=8)
        s.tree = ttk.Treeview(s, columns=s.HEADS, show="headings")
        for h in s.HEADS: s.tree.heading(h, text=h); s.tree.column(h, width=250 if h == "Particulars" else 110)
        s.tree.pack(fill="both", expand=True, padx=6, pady=6); s.refresh()
    def refresh(s):
        s.cb.all = [f"{i} - {n} ({t})" for i, n, t in db.execute("SELECT id,name,type FROM parties ORDER BY type,name")] + [f"A{i} - {n} ({t} account)" for i, n, t in db.execute("SELECT id,name,type FROM accounts ORDER BY type,name")]; s.cb["values"] = s.cb.all
    def show(s):
        s.cb._commit()
        if s.p.get().strip() not in s.cb.all: messagebox.showinfo("Ledger", "Please select a party from the list."); return
        a, b = parse_date(s.a.get()), parse_date(s.b.get())
        if not a or not b: messagebox.showerror("Ledger", "Dates must be DD/MM/YY."); return
        tok = s.p.get().split(" - ")[0]; ptype, op, rows, cl = account_rows(int(tok[1:]), a, b) if tok.startswith("A") else ledger_rows(int(tok), a, b)
        s.data = (s.p.get().split(" - ", 1)[1], ptype, a, b, op, rows, cl); s.tree.delete(*s.tree.get_children())
        s.tree.insert("", "end", values=(fmt_date(a), "Opening Balance", "", "", "", op))
        for r in rows: s.tree.insert("", "end", values=[disp(x) for x in r])
        s.tree.insert("", "end", values=(fmt_date(b), "Closing Balance", "", "", "", cl))
        s.info.config(text=({"Customer": "Balance = amount they owe you.", "Account": "Debit = money received, Credit = money paid, Balance = cash / bank balance."}.get(ptype, "Balance = amount you owe them.")) + f"   Closing: {cl:,.2f}")
    def export(s):
        if not s.data: messagebox.showinfo("Ledger", "Click Show Statement first."); return
        export_table("ledger", list(s.HEADS), [s.tree.item(i, "values") for i in s.tree.get_children()])
    def print(s):
        if not s.data: messagebox.showinfo("Ledger", "Click Show Statement first."); return
        n, t, a, b, op, rows, cl = s.data; f = lambda x: f"{x:,.2f}"; a, b = fmt_date(a), fmt_date(b)
        tr = f"<tr><td>{a}</td><td>Opening Balance</td><td></td><td></td><td></td><td align=right>{f(op)}</td></tr>" + "".join(
            f"<tr><td>{fmt_date(d)}</td><td>{p}</td><td>{r}</td><td align=right>{f(dr) if dr else ''}</td><td align=right>{f(cr) if cr else ''}</td><td align=right>{f(bl)}</td></tr>" for d, p, r, dr, cr, bl in rows) + \
            f"<tr><td>{b}</td><td><b>Closing Balance</b></td><td></td><td></td><td></td><td align=right><b>{f(cl)}</b></td></tr>"
        html = f"""<!DOCTYPE html><html><head><style>{page_css()}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #444;padding:5px}}th{{background:#eee}}</style></head><body>
<h2>{get('Company Name')}</h2><div>{get('Address')}<br>GSTIN: {get('GST No')} &nbsp; Phone: {get('Phone')}</div><hr><h3>Account Statement - {n} ({t})</h3><p>Period: {a} to {b}<br>
{'Balance = amount payable to us' if t == 'Customer' else 'Balance = amount payable by us'}</p><table><tr><th>Date</th><th>Particulars</th><th>Ref</th><th>Debit</th><th>Credit</th><th>Balance</th></tr>{tr}</table><script>window.print()</script></body></html>"""
        p = os.path.join(tempfile.gettempdir(), "ledger.html"); open(p, "w", encoding="utf-8").write(html); webbrowser.open(p)

class LRForm(tk.Toplevel):
    def __init__(s, tab, oid):
        super().__init__(tab); s.tab = tab; s.grab_set(); s.title("LR / E-Way Bill Update"); s.configure(background="#fff1de")
        ttk.Style().configure("LRV.TLabel", background="#fff1de")
        s.no, s.cid = db.execute("SELECT order_no,customer_id FROM orders WHERE id=?", (oid,)).fetchone()
        cur = db.execute("SELECT MAX(transport),MAX(lr_no),MAX(vehicle_no),MAX(lr_date),MAX(eway_no),MAX(eway_date) FROM orders WHERE order_no=? AND customer_id IS ?", (s.no, s.cid)).fetchone()
        tk.Label(s, text=f"  LR / E-Way Bill Update  -  Invoice No: {s.no}  ", bg="#c76b1a", fg="white", font=("Segoe UI", 12, "bold"), pady=8).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8)); s.v = []
        for i, (label, val) in enumerate((("Transport name", cur[0]), ("LR No", cur[1]), ("Vehicle No", cur[2]), ("LR Date (DD/MM/YY)", fmt_date(cur[3] or TODAY())),
                                          ("E-Way Bill No (12 digits)", cur[4]), ("E-Way Bill Date (DD/MM/YY)", fmt_date(cur[5] or TODAY()))), 1):
            ttk.Label(s, text=label, style="LRV.TLabel").grid(row=i, column=0, sticky="e", padx=8, pady=4); v = tk.StringVar(value=val or ""); s.v.append(v)
            ttk.Entry(s, textvariable=v, width=30).grid(row=i, column=1, padx=8, pady=4)
        ttk.Button(s, text="Save  (Enter)", command=s.save, style="Accent.TButton").grid(row=7, column=0, columnspan=2, pady=10)
        s.bind("<Return>", lambda e: s.save()); s.bind("<Escape>", lambda e: s.destroy())
    def save(s):
        tr, lr, vh, ld, ew, ed = (v.get().strip() for v in s.v)
        ld, ed = (parse_date(x) if x else "" for x in (ld, ed))
        if ld is None or ed is None: messagebox.showerror("Error", "Dates must be DD/MM/YY.", parent=s); return
        if ew and not (ew.isdigit() and len(ew) == 12) and not messagebox.askyesno("E-Way Bill", "An E-Way Bill number is normally 12 digits.\nSave anyway?", parent=s): return
        db.execute("UPDATE orders SET transport=?,lr_no=?,vehicle_no=?,lr_date=?,eway_no=?,eway_date=? WHERE order_no=? AND customer_id IS ?", (tr, lr, vh, ld, ew, ed if ew else "", s.no, s.cid)); db.commit()
        s.destroy(); s.tab.refresh()

class LRTab(ttk.Frame):
    """One row per invoice. Default view = pending: LR blank, or E-Way Bill missing on bills above the E-Way limit."""
    HEADS = ("Invoice No", "Date", "Customer", "Total (with GST)", "Status", "Transport", "LR No", "Vehicle No", "LR Date", "E-Way Bill No", "E-Way Date", "E-Way Status")
    def __init__(s, parent):
        super().__init__(parent); s.only = tk.BooleanVar(value=True); banner(s, "LR / E-Way Bill Update", "#c76b1a")
        bar = ttk.Frame(s); bar.pack(fill="x", padx=6, pady=6)
        ttk.Checkbutton(bar, text="Show only pending (LR blank / E-Way Bill required)", variable=s.only, command=s.refresh).pack(side="left", padx=4)
        for t, f in (("Enter / Update LR + E-Way", s.update), ("Print Invoice", lambda: s.do(invoice)), ("Invoice PDF", lambda: s.do(lambda i: invoice(i, "pdf")))):
            ttk.Button(bar, text=t, command=f).pack(side="left", padx=2)
        ttk.Button(bar, text="Refresh", command=s.refresh).pack(side="right")
        ttk.Button(bar, text="Export to Excel", command=lambda: export_table("lr_eway", list(s.HEADS), [s.tree.item(i, "values") for i in s.tree.get_children()])).pack(side="right", padx=4)
        s.tree = ttk.Treeview(s, columns=s.HEADS, show="headings"); s.tree.tag_configure("req", foreground="#b00020")
        for h in s.HEADS: s.tree.heading(h, text=h); s.tree.column(h, width=110)
        s.tree.pack(fill="both", expand=True, padx=6, pady=(0, 6)); s.tree.bind("<Double-1>", lambda e: s.update()); s.tree.bind("<Return>", lambda e: s.update()); s.refresh()
    def refresh(s):
        s.tree.delete(*s.tree.get_children())
        lim = get("E-Way Limit").replace(",", "").strip(); limit = float(lim) if re.fullmatch(r"\d+(\.\d+)?", lim) else 50000.0
        for r in db.execute("""SELECT g.mid,g.order_no,g.d,p.name,g.tot,(SELECT status FROM orders WHERE id=g.mid),g.tr,g.lr,g.vh,g.ld,g.ew,g.ed FROM
            (SELECT MIN(o.id) mid,o.order_no,o.customer_id,MIN(o.date) d,rnd(SUM(COALESCE(o.total,o.amount))) tot,MAX(o.transport) tr,MAX(o.lr_no) lr,
              MAX(o.vehicle_no) vh,MAX(o.lr_date) ld,MAX(o.eway_no) ew,MAX(o.eway_date) ed FROM orders o WHERE o.status<>'Cancelled' GROUP BY o.order_no,o.customer_id) g
            LEFT JOIN parties p ON p.id=g.customer_id ORDER BY g.d,g.mid"""):
            est = "Done" if r[10] else ("Required" if (r[4] or 0) >= limit else "Not required")
            if s.only.get() and r[7] and est != "Required": continue
            s.tree.insert("", "end", iid=str(r[0]), values=[disp(round(x, 2) if isinstance(x, float) else (x or "")) for x in r[1:]] + [est], tags=("req",) if est == "Required" else ())
    def sel(s):
        x = s.tree.selection()
        if not x: messagebox.showinfo("Select", "Please select an invoice first."); return None
        return int(x[0])
    def update(s):
        i = s.sel()
        if i: LRForm(s, i)
    def do(s, fn):
        i = s.sel()
        if i: fn(i)

PASTEL = {"blue": ("#dbeafe", "#1e40af"), "green": ("#dcfce7", "#166534"), "yellow": ("#fef9c3", "#854d0e"), "pink": ("#fce7f3", "#9d174d"),
          "orange": ("#ffedd5", "#9a3412"), "teal": ("#ccfbf1", "#115e59"), "purple": ("#ede9fe", "#5b21b6"), "red": ("#fee2e2", "#991b1b")}
inr0 = lambda x: f"\u20b9 {x:,.0f}"
def short_money(v): return f"{v / 1e7:.1f}Cr" if v >= 1e7 else f"{v / 1e5:.1f}L" if v >= 1e5 else f"{v / 1e3:.0f}K" if v >= 1e3 else f"{v:.0f}"
def eway_limit():
    lim = get("E-Way Limit").replace(",", "").strip(); return float(lim) if re.fullmatch(r"\d+(\.\d+)?", lim) else 50000.0

def stock_asof(d):
    """Stock position on date d - same rules as the live 'stock' view, but only vouchers dated on or before d."""
    return f"""SELECT i.id item_id,i.name,i.type,i.design,i.color,i.min_stock,
      COALESCE((SELECT SUM(qty) FROM purchases WHERE item_id=i.id AND unit='Meter' AND date<='{d}'),0)
       -COALESCE((SELECT SUM(meters) FROM conversions WHERE item_id=i.id AND date<='{d}'),0)
       -COALESCE((SELECT SUM(q) FROM usage WHERE item_id=i.id AND unit='Meter' AND date<='{d}'),0) meters,
      COALESCE((SELECT SUM(qty) FROM purchases WHERE item_id=i.id AND unit='Pcs' AND date<='{d}'),0)
       +COALESCE((SELECT SUM(pcs) FROM conversions WHERE item_id=i.id AND date<='{d}'),0)
       -COALESCE((SELECT SUM(q) FROM usage WHERE item_id=i.id AND unit='Pcs' AND date<='{d}'),0) pcs,
      COALESCE((SELECT SUM(wastage) FROM conversions WHERE item_id=i.id AND date<='{d}'),0) wastage FROM items i"""

def combo_stock_asof(d):
    return f"""SELECT combo_id,name,made,sold,returned,made-sold+returned bal,pending FROM (SELECT c.id combo_id,c.name,
      COALESCE((SELECT SUM(qty) FROM combo_makes WHERE combo_id=c.id AND date<='{d}'),0) made,
      COALESCE((SELECT SUM(qty) FROM orders WHERE combo_id=c.id AND status<>'Cancelled' AND date<='{d}'),0) sold,
      COALESCE((SELECT SUM(qty) FROM sales_returns WHERE combo_id=c.id AND COALESCE(return_type,'Full') LIKE 'Full%' AND date<='{d}'),0) returned,
      COALESCE((SELECT SUM(op.pend) FROM order_pending op JOIN sales_orders so ON so.id=op.order_id WHERE op.combo_id=c.id AND so.date<='{d}'),0) pending FROM combos c)"""

def balances_sql():
    """Outstanding of every customer / supplier / contractor as on the end of the selected period (opening balances carry forward). Journal entries are included."""
    d = WORK["to"]; jd = f"COALESCE((SELECT SUM(amount) FROM journal WHERE dr_party_id=p.id AND date<='{d}'),0)"; jc = f"COALESCE((SELECT SUM(amount) FROM journal WHERE cr_party_id=p.id AND date<='{d}'),0)"
    return f"""SELECT id,name,type,total,paid,total-paid,CASE WHEN type='Customer' THEN 'They owe you' ELSE 'You owe them' END FROM
      (SELECT p.id,p.name,p.type,CASE WHEN p.type='Customer' THEN COALESCE(inv.b,0)-COALESCE((SELECT SUM(rnd(COALESCE(total,amount))) FROM sales_returns WHERE customer_id=p.id AND date<='{d}'),0)+{jd}-{jc}
        WHEN p.type='Contractor' THEN COALESCE((SELECT SUM(job_amount) FROM job_work WHERE contractor_id=p.id AND date<='{d}'),0)+{jc}-{jd}
        ELSE COALESCE((SELECT SUM(COALESCE(total,amount)) FROM purchases WHERE supplier_id=p.id AND date<='{d}'),0)-COALESCE((SELECT SUM(rnd(COALESCE(total,amount))) FROM purchase_returns WHERE supplier_id=p.id AND date<='{d}'),0)+{jc}-{jd} END total,
        COALESCE((SELECT SUM(amount) FROM payments WHERE party_id=p.id AND date<='{d}'),0) paid
        FROM parties p LEFT JOIN (SELECT customer_id,SUM(billed) b FROM (SELECT customer_id,order_no,rnd(SUM(COALESCE(total,amount))) billed FROM orders WHERE status<>'Cancelled' AND date<='{d}' GROUP BY customer_id,order_no) GROUP BY customer_id) inv ON inv.customer_id=p.id) ORDER BY type,name"""

def bank_sql():
    d = WORK["to"]
    side = lambda cmp: f"(SELECT y.account_id aid,SUM(y.amount) t FROM payments y JOIN parties q ON q.id=y.party_id WHERE q.type{cmp}'Customer' AND y.date<='{d}' GROUP BY y.account_id)"
    cin = f"(SELECT to_account_id aid,SUM(amount) t FROM contra WHERE date<='{d}' GROUP BY to_account_id)"
    cout = f"(SELECT from_account_id aid,SUM(amount) t FROM contra WHERE date<='{d}' GROUP BY from_account_id)"
    return (f"SELECT a.id,a.name,a.type,a.opening,COALESCE(r.t,0)+COALESCE(ci.t,0),COALESCE(p.t,0)+COALESCE(co.t,0),a.opening+COALESCE(r.t,0)+COALESCE(ci.t,0)-COALESCE(p.t,0)-COALESCE(co.t,0) FROM accounts a "
            f"LEFT JOIN {side('=')} r ON r.aid=a.id LEFT JOIN {side('<>')} p ON p.aid=a.id LEFT JOIN {cin} ci ON ci.aid=a.id LEFT JOIN {cout} co ON co.aid=a.id ORDER BY a.type,a.name")

def account_balance(aid, upto=None):
    ex = " AND y.date<=?" if upto else ""; args = (aid, upto) if upto else (aid,)
    q = lambda cmp: db.execute(f"SELECT COALESCE(SUM(y.amount),0) FROM payments y JOIN parties q ON q.id=y.party_id WHERE y.account_id=? AND q.type{cmp}'Customer'" + ex, args).fetchone()[0]
    c = lambda col: db.execute(f"SELECT COALESCE(SUM(y.amount),0) FROM contra y WHERE y.{col}=?" + ex, args).fetchone()[0]
    return db.execute("SELECT opening FROM accounts WHERE id=?", (aid,)).fetchone()[0] + q("=") - q("<>") + c("to_account_id") - c("from_account_id")

def account_rows(aid, a, b):
    """Cash / Bank book: money in (receipts, transfers in) = Debit, money out = Credit, balance = money in hand / in bank."""
    op = db.execute("SELECT opening FROM accounts WHERE id=?", (aid,)).fetchone()[0]; ev = []
    for d, i, amt, note, nm, typ, vn in db.execute("SELECT y.date,y.id,y.amount,y.note,q.name,q.type,y.vno FROM payments y JOIN parties q ON q.id=y.party_id WHERE y.account_id=?", (aid,)):
        ev.append((d, i, ("Receipt from " if typ == "Customer" else "Payment to ") + nm + (f" ({note})" if note else ""), vn or f"Pay-{i}", amt if typ == "Customer" else 0, 0 if typ == "Customer" else amt))
    for d, i, amt, nar, f_id, t_id, fn, tn, vn in db.execute("SELECT c.date,c.id,c.amount,c.narration,c.from_account_id,c.to_account_id,f.name,t.name,c.vno FROM contra c JOIN accounts f ON f.id=c.from_account_id JOIN accounts t ON t.id=c.to_account_id WHERE c.from_account_id=? OR c.to_account_id=?", (aid, aid)):
        inn = t_id == aid; ev.append((d, i, ("Transfer from " + fn) if inn else ("Transfer to " + tn) + (f" ({nar})" if nar else ""), vn or f"CTR-{i}", amt if inn else 0, 0 if inn else amt))
    ev.sort(key=lambda e: (e[0], e[1])); bal, opening, rows = op, None, []
    for d, i, part, ref, dr, cr in ev:
        if d < a: bal += dr - cr; continue
        if opening is None: opening = bal
        if d > b: break
        bal += dr - cr; rows.append((d, part, ref, round(dr, 2), round(cr, 2), round(bal, 2)))
    if opening is None: opening = bal
    return "Account", round(opening, 2), rows, round(bal if not rows else rows[-1][5], 2)

def data_check():
    """Looks for the usual data problems; returns a list of text blocks (empty = all fine)."""
    out = []; q = lambda sql, *a: db.execute(sql, a).fetchall()
    def add(title, rows):
        if rows: out.append(title + ":\n     " + "\n     ".join(str(r) for r in rows[:12]) + (f"\n     ... and {len(rows) - 12} more" if len(rows) > 12 else ""))
    if not get("GST No") or not get("State") or not get("Address"): out.append("Company Profile: GSTIN, State or Address is empty - invoices will print incomplete.")
    m = check_gstin(get("GST No"), get("State"))
    if m: out.append("Company GSTIN: " + m)
    add("Items with no HSN code or GST rate (GST on invoices will be wrong)", [r[0] for r in q("SELECT name FROM items WHERE COALESCE(hsn,'')='' OR gst_rate IS NULL ORDER BY name")])
    add("Combos with no HSN code or GST rate", [r[0] for r in q("SELECT name FROM combos WHERE COALESCE(hsn,'')='' OR gst_rate IS NULL ORDER BY name")])
    add(f"Combos that do not have {MIN_ITEMS} to {MAX_ITEMS} items", [f"{n} ({c} item(s))" for n, c in q("SELECT c.name,(SELECT COUNT(*) FROM combo_lines WHERE combo_id=c.id) FROM combos c") if not MIN_ITEMS <= c <= MAX_ITEMS])
    add("Fabrics with no 'Std length of 1 Pc' (consumption estimate cannot be made)", [r[0] for r in q("SELECT name FROM items WHERE type LIKE '%Fabric%' AND COALESCE(std_length,0)<=0 ORDER BY name")])
    add("Shade / design stock gone negative", [f"{n}: {m:g} m, {p:g} pcs" for n, (m, p) in negative_stock().items() if n.endswith("]")])
    add("Customers with no State (GST is charged as same-state)", [r[0] for r in q("SELECT name FROM parties WHERE type='Customer' AND COALESCE(state,'')='' ORDER BY name")])
    add("Parties with a wrong GSTIN", [f"{n}: {m}" for n, g, st in q("SELECT name,gst,state FROM parties WHERE COALESCE(gst,'')<>''") for m in [check_gstin(g, st)] if m])
    add("Negative stock", [f"{n}: {mm:g} m, {p:g} pcs" for n, (mm, p) in negative_stock().items()])
    add("Invoice numbers used for more than one customer", [r[0] for r in q("SELECT order_no FROM orders WHERE status<>'Cancelled' GROUP BY order_no HAVING COUNT(DISTINCT COALESCE(customer_id,0))>1")])
    a0, a1 = fy_range(WORK["fy"]); outside = []
    for tb, lab in (("orders", "Invoices"), ("purchases", "Purchases"), ("payments", "Payments / Receipts"), ("sales_returns", "Credit Notes"), ("purchase_returns", "Debit Notes"), ("combo_makes", "Combo Making"), ("conversions", "Fabric Folding")):
        n = q(f"SELECT COUNT(*) FROM {tb} WHERE date<? OR date>?", a0, a1)[0][0]
        if n: outside.append(f"{lab}: {n} dated outside FY {fy_label(WORK['fy'])}  (normal if you keep several years of data)")
    add("Vouchers outside the selected financial year", outside)
    bal = db.execute(balances_sql()).fetchall()
    add("Customers who have paid MORE than billed (credit balance)", [f"{r[1]}: {-r[5]:,.2f} excess" for r in bal if r[2] == "Customer" and r[5] < -0.005])
    add("Suppliers / contractors paid MORE than billed", [f"{r[1]}: {-r[5]:,.2f} excess" for r in bal if r[2] != "Customer" and r[5] < -0.005])
    add("Sales orders past their delivery date and not fully invoiced", [f"Order {r[0]} - {r[1]} (due {fmt_date(r[2])}, pending {r[3]:g})" for r in q("SELECT so.order_no,COALESCE(p.name,''),so.due_date,op.pend FROM sales_orders so JOIN order_pending op ON op.order_id=so.id LEFT JOIN parties p ON p.id=so.customer_id WHERE op.pend>0 AND COALESCE(so.due_date,'')<>'' AND so.due_date<?", TODAY())])
    lim = eway_limit()
    add(f"Invoices of Rs {lim:,.0f} or more with no E-Way Bill number (selected year)", [f"Invoice {no}: {t:,.0f}" for no, t, ew in q("SELECT order_no,rnd(SUM(COALESCE(total,amount))),MAX(eway_no) FROM orders WHERE status<>'Cancelled' AND date BETWEEN ? AND ? GROUP BY COALESCE(customer_id,0),order_no", WORK["from"], WORK["to"]) if (t or 0) >= lim and not ew])
    return out

def dashboard_data(): return [c for c in _dashboard_all() if page_on(c[4])]          # cards of screens this company does not use are hidden
def _dashboard_all():
    """Cards for the Gateway, for the SELECTED financial year / period: (title, value, small text, colour, screen it opens)."""
    a, b = WORK["from"], WORK["to"]; today = TODAY(); ref = min(max(today, a), b); mon = ref[:7]; fy = fy_label(WORK["fy"]); tot = "COALESCE(total,amount)"
    one = lambda sql, *x: (db.execute(sql, x).fetchone()[0] or 0); mlab = datetime.date(int(mon[:4]), int(mon[5:]), 1).strftime("%b %y")
    s_ref = one(f"SELECT SUM({tot}) FROM orders WHERE status<>'Cancelled' AND date=?", ref)
    s_fy = one(f"SELECT SUM({tot}) FROM orders WHERE status<>'Cancelled' AND date BETWEEN ? AND ?", a, b)
    inv_fy = one("SELECT COUNT(DISTINCT COALESCE(customer_id,0)||'-'||order_no) FROM orders WHERE status<>'Cancelled' AND date BETWEEN ? AND ?", a, b)
    p_fy = one(f"SELECT SUM({tot}) FROM purchases WHERE date BETWEEN ? AND ?", a, b) - one(f"SELECT SUM({tot}) FROM purchase_returns WHERE date BETWEEN ? AND ?", a, b)
    p_mon = one(f"SELECT SUM({tot}) FROM purchases WHERE substr(date,1,7)=?", mon) - one(f"SELECT SUM({tot}) FROM purchase_returns WHERE substr(date,1,7)=?", mon)
    rec = lambda *x: one("SELECT SUM(p.amount) FROM payments p JOIN parties t ON t.id=p.party_id WHERE t.type='Customer' AND " + x[0], *x[1:])
    rec_fy, rec_mon = rec("p.date BETWEEN ? AND ?", a, b), rec("substr(p.date,1,7)=?", mon)
    bal = db.execute(balances_sql()).fetchall(); cust = sum(r[5] for r in bal if r[2] == "Customer"); supp = sum(r[5] for r in bal if r[2] != "Customer")
    npend, qpend = db.execute("SELECT COUNT(*),COALESCE(SUM(op.pend),0) FROM order_pending op JOIN sales_orders so ON so.id=op.order_id WHERE op.pend>0 AND so.date BETWEEN ? AND ?", (a, b)).fetchone()
    make = sum(max((p or 0) - (bb or 0), 0) for p, bb in db.execute(f"SELECT pending,bal FROM ({combo_stock_asof(b)})"))
    made_fy = one("SELECT SUM(qty) FROM combo_makes WHERE date BETWEEN ? AND ?", a, b)
    low = one(f"SELECT COUNT(*) FROM ({stock_asof(b)}) WHERE {ALERT}"); lim = eway_limit(); lr_blank = eway_req = 0
    for lr, ew, t in db.execute("SELECT MAX(lr_no),MAX(eway_no),rnd(SUM(COALESCE(total,amount))) FROM orders WHERE status<>'Cancelled' AND date BETWEEN ? AND ? GROUP BY COALESCE(customer_id,0),order_no", (a, b)):
        if not lr: lr_blank += 1
        if not ew and (t or 0) >= lim: eway_req += 1
    return [(f"Sales - FY {fy}", inr0(s_fy), f"{inv_fy:g} invoice(s), incl. GST", "blue", "Sales Invoices"), ("Today's Sales" if ref == today else f"Sales on {fmt_date(ref)}", inr0(s_ref), "invoices, incl. GST", "green", "Sales Invoices"),
            (f"Purchases - FY {fy}", inr0(p_fy), f"{mlab}: {inr0(p_mon)}", "orange", "Purchases"), ("Customers Owe You", inr0(cust), f"as on {fmt_date(b)}", "teal", "Balances"),
            ("You Owe Suppliers / Contractors", inr0(supp), f"as on {fmt_date(b)}", "pink", "Balances"), (f"Received - FY {fy}", inr0(rec_fy), f"{mlab}: {inr0(rec_mon)}", "purple", "Payments"),
            ("Sales Orders Pending", f"{npend}", f"{qpend:g} qty still to invoice", "yellow", "Sales Orders"), ("Combos Still To Make", f"{make:g}", f"for pending orders, as on {fmt_date(b)}", "blue", "Combo Stock"),
            (f"Combos Made - FY {fy}", f"{made_fy:g}", "production", "green", "Combo Making"), ("Low Stock Items", f"{low}", f"as on {fmt_date(b)}", "red", "Stock"),
            ("LR Pending", f"{lr_blank}", "invoices without LR no.", "orange", "LR Update"), ("E-Way Bill Pending", f"{eway_req}", f"bills of {inr0(lim)} or more", "yellow", "LR Update")]

def monthly_series(n=12):
    """[(label, sales, purchases)] for every month of the selected period (a full financial year = 12 bars), without GST, after returns."""
    y, m, ks = int(WORK["from"][:4]), int(WORK["from"][5:7]), []
    while len(ks) < n and f"{y:04d}-{m:02d}" <= WORK["to"][:7]:
        ks.append(f"{y:04d}-{m:02d}"); m += 1
        if m == 13: y, m = y + 1, 1
    one = lambda sql, k: (db.execute(sql, (k,)).fetchone()[0] or 0)
    return [(datetime.date(int(k[:4]), int(k[5:]), 1).strftime("%b %y"),
             one("SELECT SUM(amount) FROM orders WHERE status<>'Cancelled' AND substr(date,1,7)=?", k) - one("SELECT SUM(amount) FROM sales_returns WHERE substr(date,1,7)=?", k),
             one("SELECT SUM(amount) FROM purchases WHERE substr(date,1,7)=?", k) - one("SELECT SUM(amount) FROM purchase_returns WHERE substr(date,1,7)=?", k)) for k in ks]

class Gateway(ttk.Frame):
    """Tally-style Gateway: numbered menu on the left (Up/Down + Enter, number key, or click; Esc = back) and colourful dashboard cards on the right."""
    BG = "#f6f1e4"
    def __init__(s, parent, menus, on_open):
        super().__init__(parent); s.menus, s.stack, s.on_open = menus, ["root"], on_open
        head = tk.Frame(s, bg="#2f5d8a"); head.pack(fill="x")
        s.title_lbl = tk.Label(head, text="", bg="#2f5d8a", fg="white", font=("Segoe UI", 15, "bold"), anchor="w", padx=14, pady=10); s.title_lbl.pack(side="left")
        s.date_lbl = tk.Label(head, text="", bg="#2f5d8a", fg="#ffe9a8", font=("Segoe UI", 10, "bold"), anchor="e", justify="right", padx=14); s.date_lbl.pack(side="right")
        body = tk.Frame(s, bg=s.BG); body.pack(fill="both", expand=True)
        left = tk.Frame(body, bg="#fff6d6", bd=2, relief="groove"); left.pack(side="left", fill="y", padx=14, pady=14)
        s.menu_title = tk.Label(left, text="", bg="#f0b429", fg="#3b2f00", font=("Segoe UI", 12, "bold"), pady=7); s.menu_title.pack(fill="x")
        s.lb = tk.Listbox(left, font=("Consolas", 12), width=42, height=15, bg="#fffbea", fg="#222222", selectbackground="#ff9f43", selectforeground="black", activestyle="none", bd=0, highlightthickness=0)
        s.lb.pack(padx=6, pady=6)
        tk.Label(left, text="Up/Down + Enter, or press the number.   Esc = back", bg="#fff6d6", fg="#6b5b00", font=("Segoe UI", 9)).pack(pady=(0, 6))
        right = tk.Frame(body, bg=s.BG); right.pack(side="left", fill="both", expand=True, padx=(0, 14), pady=14)
        s.cards = tk.Frame(right, bg=s.BG); s.cards.pack(fill="x")
        s.chart = tk.Canvas(right, height=220, bg="white", highlightthickness=1, highlightbackground="#d9dee7"); s.chart.pack(fill="both", expand=True, pady=(12, 0))
        s.chart.bind("<Configure>", lambda e: s.draw_chart())
        for ev, fn in (("<Return>", s.go), ("<Double-Button-1>", s.go), ("<Key>", s.key), ("<Escape>", s.back), ("<BackSpace>", s.back)): s.lb.bind(ev, fn)
        s.show("root")
    def show(s, name):
        title, items = s.menus[name]; s.menu_title.config(text=title); s.lb.delete(0, "end")
        for i, (label, hint, act) in enumerate(items, 1):
            s.lb.insert("end", f"{i % 10}. {label + ('   >' if isinstance(act, str) else ''):<38}{hint:>8}")
        s.lb.selection_clear(0, "end"); s.lb.selection_set(0); s.lb.activate(0)
    def run(s, idx):
        items = s.menus[s.stack[-1]][1]
        if not 0 <= idx < len(items): return
        act = items[idx][2]
        if isinstance(act, str): s.stack.append(act); s.show(act)
        else: act()
    def go(s, e=None):
        sel = s.lb.curselection()
        if sel: s.run(sel[0])
        return "break"
    def key(s, e):
        if e.char and e.char.isdigit(): s.run((int(e.char) - 1) % 10); return "break"
    def back(s, e=None):
        if len(s.stack) > 1: s.stack.pop(); s.show(s.stack[-1]); return "break"
    def refresh(s):
        nm = get("Company Name"); s.title_lbl.config(text=f"Gateway of {nm}" if nm else "Gateway")
        s.date_lbl.config(text=f"Work style : {' + '.join(n for n, on in (('Combo', COMBO_ON), ('Shirting Fabrics', SHIRT_ON)) if on)}      Financial Year : {fy_label(WORK['fy'])}\nCurrent Date : {fmt_date(WORK['date'])}      Period : {fmt_date(WORK['from'])} to {fmt_date(WORK['to'])}")
        for w in s.cards.winfo_children(): w.destroy()
        try: data = dashboard_data()
        except Exception as e: data = []; tk.Label(s.cards, text=f"Dashboard could not be loaded: {e}", bg=s.BG, fg="#991b1b").pack()
        for c in range(3): s.cards.grid_columnconfigure(c, weight=1, uniform="c")
        for i, (title, val, sub, color, page) in enumerate(data):
            bg, fg = PASTEL[color]; f = tk.Frame(s.cards, bg=bg, bd=1, relief="solid", cursor="hand2"); f.grid(row=i // 3, column=i % 3, sticky="nsew", padx=6, pady=6)
            parts = [tk.Label(f, text=title, bg=bg, fg=fg, font=("Segoe UI", 10, "bold"), anchor="w"), tk.Label(f, text=val, bg=bg, fg=fg, font=("Segoe UI", 20, "bold"), anchor="w"),
                     tk.Label(f, text=sub, bg=bg, fg=fg, font=("Segoe UI", 9), anchor="w")]
            for w in parts: w.pack(fill="x", padx=12, pady=(6 if w is parts[0] else 0, 6 if w is parts[2] else 0))
            for w in [f] + parts: w.bind("<Button-1>", lambda e, p=page: s.on_open(p))
        s.draw_chart(); s.lb.focus_set()
    def draw_chart(s):
        c = s.chart; c.delete("all")
        try: data = monthly_series()
        except Exception: return
        w, h = max(int(c.winfo_width()), 560), max(int(c.winfo_height()), 200); top, bot, left = 44, 28, 26; mx = max([1] + [v for _, a, b in data for v in (a, b)]); n = len(data)
        c.create_text(14, 14, anchor="w", text=f"Sales vs Purchases - FY {fy_label(WORK['fy'])} (without GST)", font=("Segoe UI", 11, "bold"), fill="#1f4e79")
        c.create_rectangle(w - 250, 8, w - 238, 20, fill="#86efac", outline="#16a34a"); c.create_text(w - 233, 14, anchor="w", text="Sales", font=("Segoe UI", 9))
        c.create_rectangle(w - 180, 8, w - 168, 20, fill="#fdba74", outline="#ea580c"); c.create_text(w - 163, 14, anchor="w", text="Purchases", font=("Segoe UI", 9))
        gw = (w - left - 20) / n; bw = gw / 3
        for i, (lab, a, b) in enumerate(data):
            x = left + i * gw + bw * 0.5
            for k, (v, fill, line) in enumerate(((a, "#86efac", "#16a34a"), (b, "#fdba74", "#ea580c"))):
                hh = (h - top - bot) * v / mx; x0 = x + k * bw
                c.create_rectangle(x0, h - bot - hh, x0 + bw - 3, h - bot, fill=fill, outline=line)
                if v and bw >= 18: c.create_text(x0 + (bw - 3) / 2, h - bot - hh - 7, text=short_money(v), font=("Segoe UI", 8), fill="#444444")
            c.create_text(x + bw, h - bot + 12, text=lab, font=("Segoe UI", 9), fill="#444444")
        c.create_line(left, h - bot, w - 10, h - bot, fill="#9aa5b1")

class PageSetup(tk.Toplevel):
    """Bill / page setup: paper, orientation, margins, stretch-to-full-page and text size. Used by invoice, credit/debit note, sales order and ledger prints."""
    KEYS = [("Page Paper", "Paper size", ["A4", "A5", "A3", "Letter", "Legal", "Custom"]), ("Page Orientation", "Orientation", ["Portrait", "Landscape"]),
            ("Page Width (mm)", "Custom paper width (mm)", None), ("Page Height (mm)", "Custom paper height (mm)", None),
            ("Margin Top (mm)", "Top margin (mm)", None), ("Margin Bottom (mm)", "Bottom margin (mm)", None), ("Margin Left (mm)", "Left margin (mm)", None), ("Margin Right (mm)", "Right margin (mm)", None),
            ("Fill Full Page (Yes/No)", "Stretch bill to full page height", ["Yes", "No"]), ("Print Font Size", "Text size (px, normal = 11)", None)]
    def __init__(s, parent, test=None):
        super().__init__(parent); s.test = test; s.title("Page Setup - Bill Size and Margins"); s.grab_set(); s.resizable(False, False); s.configure(background="#eef3f9")
        ttk.Style().configure("PS.TLabel", background="#eef3f9")
        tk.Label(s, text="  Page Setup  -  Bill size and margins", bg="#2f5d8a", fg="white", font=("Segoe UI", 13, "bold"), anchor="w", pady=9).grid(row=0, column=0, columnspan=3, sticky="ew")
        s.v = {}
        for i, (k, label, opts) in enumerate(s.KEYS, 1):
            ttk.Label(s, text=label, style="PS.TLabel").grid(row=i, column=0, sticky="e", padx=10, pady=4); s.v[k] = tk.StringVar(value=get(k))
            (ttk.Combobox(s, textvariable=s.v[k], values=opts, state="readonly", width=16) if opts else ttk.Entry(s, textvariable=s.v[k], width=18)).grid(row=i, column=1, padx=6, pady=4, sticky="w")
        s.info = ttk.Label(s, text="", style="PS.TLabel", font=("Segoe UI", 10, "bold")); s.info.grid(row=len(s.KEYS) + 1, column=0, columnspan=3, pady=6)
        bar = ttk.Frame(s); bar.grid(row=len(s.KEYS) + 2, column=0, columnspan=3, pady=10)
        for t, f in (("Save  (Enter)", s.save), ("Reset to A4", s.reset), ("Save + Test Print", s.save_test)): ttk.Button(bar, text=t, command=f, style="Accent.TButton" if t.startswith("Save  ") else "TButton").pack(side="left", padx=4)
        for v in s.v.values(): v.trace_add("write", lambda *a: s.preview())
        s.bind("<Return>", lambda e: s.save()); s.bind("<Escape>", lambda e: s.destroy()); s.preview()
    def conf(s): return page_conf(lambda k: s.v[k].get())
    def preview(s):
        c = s.conf(); s.info.config(text=f"Paper {c['w']:g} x {c['h']:g} mm     Printable area {c['w'] - c['l'] - c['r']:g} x {c['h'] - c['t'] - c['b']:g} mm")
    def reset(s):
        for k, v in (("Page Paper", "A4"), ("Page Orientation", "Portrait"), ("Margin Top (mm)", "8"), ("Margin Bottom (mm)", "8"), ("Margin Left (mm)", "8"), ("Margin Right (mm)", "8"), ("Fill Full Page (Yes/No)", "Yes"), ("Print Font Size", "11")): s.v[k].set(v)
    def check(s):
        c = s.conf(); g = lambda k: s.v[k].get()
        if any(_num(g(k), None) is None for k in ("Page Width (mm)", "Page Height (mm)", "Margin Top (mm)", "Margin Bottom (mm)", "Margin Left (mm)", "Margin Right (mm)", "Print Font Size")): return "Please enter numbers only (mm)."
        if min(c["t"], c["b"], c["l"], c["r"]) < 0: return "Margins cannot be negative."
        if min(c["w"], c["h"]) < 50: return "Paper size must be at least 50 mm."
        if c["l"] + c["r"] >= c["w"] - 80 or c["t"] + c["b"] >= c["h"] - 80: return "Margins are too big for this paper size (at least 80 mm must stay printable)."
        if not 7 <= c["fs"] <= 20: return "Text size must be between 7 and 20."
    def save(s):
        err = s.check()
        if err: messagebox.showerror("Page Setup", err, parent=s); return False
        for k, v in s.v.items():
            db.execute("INSERT OR IGNORE INTO settings(name,value) VALUES(?,?)", (k, v.get().strip())); db.execute("UPDATE settings SET value=? WHERE name=?", (v.get().strip(), k))
        db.commit(); s.destroy(); return True
    def save_test(s):
        if s.save() and s.test: s.test()

class Reports(ttk.Frame):
    def __init__(s, parent):
        super().__init__(parent)
        banner(s, "Sales, Purchase and Profit Report", "#23847f")
        bar = ttk.Frame(s); bar.pack(fill="x", padx=6, pady=6)
        s.a, s.b = tk.StringVar(value=fmt_date(WORK["from"])), tk.StringVar(value=fmt_date(WORK["to"]))
        for t, v in (("From", s.a), ("To", s.b)): ttk.Label(bar, text=t).pack(side="left"); ttk.Entry(bar, textvariable=v, width=12).pack(side="left", padx=4)
        ttk.Button(bar, text="Show Report", command=s.run).pack(side="left", padx=6)
        ttk.Button(bar, text="Export to Excel", command=lambda: export_table("report", ["Report"], [[l] for l in s.out.get("1.0", "end").splitlines()])).pack(side="left")
        s.out = tk.Text(s, font=("Consolas", 10)); s.out.pack(fill="both", expand=True, padx=6, pady=6)
    def refresh(s): pass
    def run(s):
        a, b = parse_date(s.a.get()), parse_date(s.b.get())
        if not a or not b: messagebox.showerror("Report", "Dates must be DD/MM/YY."); return
        q = lambda sql: db.execute(sql, (a, b)).fetchall()
        one = lambda sql: q(sql)[0][0] or 0
        G = "COALESCE(cgst,0)+COALESCE(sgst,0)+COALESCE(igst,0)"
        sales = one("SELECT SUM(amount) FROM orders WHERE status<>'Cancelled' AND date BETWEEN ? AND ?")
        buy = one("SELECT SUM(amount) FROM purchases WHERE date BETWEEN ? AND ?") - one("SELECT SUM(amount) FROM purchase_returns WHERE date BETWEEN ? AND ?")
        cogs = one("SELECT SUM(o.qty*cc.cost) FROM orders o JOIN combo_cost cc ON cc.combo_id=o.combo_id WHERE o.status<>'Cancelled' AND o.date BETWEEN ? AND ?") + \
               one("SELECT SUM(o.qty*COALESCE(CASE WHEN o.unit='Meter' THEN a.meter_rate ELSE a.pc_cost END,0)) FROM orders o JOIN avgrate a ON a.item_id=o.item_id WHERE o.status<>'Cancelled' AND o.date BETWEEN ? AND ?")
        rets = one("SELECT SUM(amount) FROM sales_returns WHERE date BETWEEN ? AND ?")
        cogs -= one("SELECT SUM(r.qty*cc.cost) FROM sales_returns r JOIN combo_cost cc ON cc.combo_id=r.combo_id WHERE COALESCE(r.return_type,'Full') LIKE 'Full%' AND r.date BETWEEN ? AND ?") + \
                one("SELECT SUM(r.qty*cl.qty*COALESCE(a.pc_cost,0)) FROM sales_returns r JOIN combo_lines cl ON cl.combo_id=r.combo_id JOIN items i ON i.id=cl.item_id JOIN avgrate a ON a.item_id=cl.item_id WHERE r.return_type LIKE 'Fabrics%' AND i.type LIKE '%Fabric%' AND r.date BETWEEN ? AND ?") + \
                one("SELECT SUM(r.qty*COALESCE(CASE WHEN r.unit='Meter' THEN a.meter_rate ELSE a.pc_cost END,0)) FROM sales_returns r JOIN avgrate a ON a.item_id=r.item_id WHERE COALESCE(r.return_type,'Full') NOT LIKE 'Nothing%' AND r.date BETWEEN ? AND ?")
        sales -= rets
        outg = one(f"SELECT SUM({G}) FROM orders WHERE status<>'Cancelled' AND date BETWEEN ? AND ?") - one(f"SELECT SUM({G}) FROM sales_returns WHERE date BETWEEN ? AND ?")
        ing = one(f"SELECT SUM({G}) FROM purchases WHERE date BETWEEN ? AND ?") - one(f"SELECT SUM({G}) FROM purchase_returns WHERE date BETWEEN ? AND ?")
        rec = one("SELECT SUM(p.amount) FROM payments p JOIN parties t ON t.id=p.party_id WHERE t.type='Customer' AND p.date BETWEEN ? AND ?")
        paid = one("SELECT SUM(p.amount) FROM payments p JOIN parties t ON t.id=p.party_id WHERE t.type='Supplier' AND p.date BETWEEN ? AND ?")
        made = one("SELECT SUM(qty) FROM combo_makes WHERE date BETWEEN ? AND ?"); job = one("SELECT SUM(job_amount) FROM job_work WHERE date BETWEEN ? AND ?")
        t = [f"REPORT  {fmt_date(a)}  to  {fmt_date(b)}   (amounts without GST)", "=" * 60, f"Net Purchases        : {buy:12,.2f}  (after purchase returns)", f"Sales Returns        : {rets:12,.2f}",
             f"Net Sales            : {sales:12,.2f}", f"Cost of goods sold   : {cogs:12,.2f}  (avg cost)", f"Gross Profit         : {sales - cogs:12,.2f}", "",
             f"GST on sales (output): {outg:12,.2f}", f"GST on purchase (in) : {ing:12,.2f}", f"Net GST payable      : {outg - ing:12,.2f}", "",
             f"Received from cust.  : {rec:12,.2f}", f"Paid to suppliers    : {paid:12,.2f}", f"Combos made          : {made:12g}", f"Job work charges    : {job:12,.2f}  (contractors; included in cost)", "", "SALES BY PRODUCT", "-" * 60]
        for n, qty, amt in q("SELECT COALESCE(c.name,i.name||' ('||o.unit||')'),SUM(o.qty),SUM(o.amount) FROM orders o LEFT JOIN combos c ON c.id=o.combo_id "
                             "LEFT JOIN items i ON i.id=o.item_id WHERE o.status<>'Cancelled' AND o.date BETWEEN ? AND ? GROUP BY 1"): t.append(f"{n:30}{qty:8g} {amt:14,.2f}")
        t += ["", "PURCHASES BY ITEM", "-" * 60]
        for n, u, qty, amt in q("SELECT i.name,p.unit,SUM(p.qty),SUM(p.amount) FROM purchases p JOIN items i ON i.id=p.item_id WHERE p.date BETWEEN ? AND ? GROUP BY i.name,p.unit"):
            t.append(f"{n:30}{qty:8g} {u:5} {amt:12,.2f}")
        t += ["", "PCS CONVERSION & WASTAGE", "-" * 60]
        for n, m, p, w in q("SELECT i.name,SUM(c.meters),SUM(c.pcs),SUM(c.wastage) FROM conversions c JOIN items i ON i.id=c.item_id WHERE c.date BETWEEN ? AND ? GROUP BY i.name"):
            t.append(f"{n:24}{m:8g} m -> {p:6g} pcs, wastage {w:g} m")
        if not COMBO_ON:
            t = [l for l in t if not l.startswith("Combos made")]
            if "PCS CONVERSION & WASTAGE" in t: t = t[:t.index("PCS CONVERSION & WASTAGE") - 1]
        s.out.delete("1.0", "end"); s.out.insert("1.0", "\n".join(t))

if __name__ == "__main__":
    root = tk.Tk(); root.title("Combo Manager"); root.geometry("1250x680"); setup_style(root)
    try: root.state("zoomed")
    except Exception: pass
    sbv = tk.StringVar()
    ttk.Label(root, textvariable=sbv, anchor="w", padding=(10, 5), background="#1f4e79", foreground="white", font=("Segoe UI", 9, "bold")).pack(side="bottom", fill="x")
    def update_status():
        sbv.set(f"FY {fy_label(WORK['fy'])} [Ctrl+F2]   |   Date: {fmt_date(WORK['date'])} [F2]   |   Period: {fmt_date(WORK['from'])} to {fmt_date(WORK['to'])} [Alt+F2]   |   F8 Sales  F9 Purchase  F5 Payment  F6 Receipt  Alt+G Go To  F1 All shortcuts")
    STATUSBAR[0] = update_status; update_status()
    nb = ttk.Notebook(root, style="Main.TNotebook"); nb.pack(fill="both", expand=True, padx=6, pady=6)
    GROUPS = {"Sales": ["Sales Orders", "Sales Invoices", "Delivery Challans", "LR Update"], "Job Work (Contract)": ["Combo Making", "Pcs Conversion", "Job Register", "Contractor Summary"], "Stock": ["Combo Stock", "Stock", "Shade Stock"],
              "Returns & Notes": ["Sales Returns", "Purchase Returns"], "Accounts": ["Payments", "Contra", "Journal", "Cash/Bank Balance", "Bills Outstanding", "Balances", "Ledger"],
              "Masters": ["Items", "Customers/Suppliers", "Combo Master", "Pack Types", "Fold / Cut Types", "Bank/Cash Master", "Company Profile"]}
    LABEL = {"Sales Returns": "Credit Notes", "Purchase Returns": "Debit Notes", "LR Update": "LR / E-Way Bill", "Pcs Conversion": "Fabric Folding", "Job Register": "Job Work Register", "Customers/Suppliers": "Parties",
             "Contra": "Contra", "Journal": "Journal", "Bills Outstanding": "Bills Outstanding", "Cash/Bank Balance": "Cash / Bank", "Bank/Cash Master": "Bank Accounts", "Delivery Challans": "Challans",
             "Sales Orders": "Sales Orders", "Sales Invoices": "Sales Invoices", "Combo Master": "Combo Master", "Company Profile": "Company Profile", "Contractor Summary": "Contractors"}
    G = {g: ttk.Notebook(nb) for g in GROUPS}
    PARENT = {k: G[g] for g, ks in GROUPS.items() for k in ks}
    nextord = lambda: str((db.execute("SELECT COALESCE(MAX(CAST(order_no AS INTEGER)),0) FROM sales_orders").fetchone()[0]) + 1)
    def create_invoice(oid):
        """Invoice for every pending line (quality + shade) of the selected sales order."""
        if not oid: return
        no, cid, st0 = db.execute("SELECT order_no,customer_id,status FROM sales_orders WHERE id=?", (oid,)).fetchone()
        if st0 == "Cancelled": messagebox.showinfo("Sales Order", "This order is cancelled."); return
        rows = db.execute("SELECT so.id,so.combo_id,so.item_id,so.unit,so.rate,so.buyer_order_no,so.buyer_order_date,so.terms,COALESCE(so.shade,''),op.pend FROM sales_orders so JOIN order_pending op ON op.order_id=so.id "
                          "WHERE so.order_no=? AND so.customer_id IS ? AND so.status<>'Cancelled' AND op.pend>0 ORDER BY so.id", (no, cid)).fetchall()
        if not rows: messagebox.showinfo("Sales Order", "This order is already fully invoiced."); return
        r = ask_dialog(root, f"Invoice for Order {no}", [("Invoice No", nextno()), ("Invoice Date (DD/MM/YY)", fmt_date(WORK["date"]))])
        if not r: return
        iso = parse_date(r[1])
        if not r[0] or not iso: messagebox.showerror("Invoice", "Enter the Invoice No and a date as DD/MM/YY."); return
        try:
            for sid, cb, it, un, rt, bno, bdt, tm, sh, pend in rows:
                v = dict(order_no=r[0], date=iso, customer_id=cid, order_id=sid, combo_id=cb, item_id=it, shade=sh, unit=un, qty=pend, rate=rt or 0, disc_trade=0, disc_cash=0, disc_flat=0, freight=0,
                         buyer_order_no=bno or "", buyer_order_date=bdt or "", terms=tm or "", status="Pending")
                pre_order(v, None); cols = list(v)
                db.execute(f"INSERT INTO orders({','.join(cols)}) VALUES({','.join('?' * len(cols))})", [v[c] for c in cols])
            db.commit()
        except Stop as e: db.rollback(); messagebox.showerror("Cannot create invoice", str(e)); return
        tabs["Sales Invoices"].refresh(); tabs["Sales Orders"].refresh()
        messagebox.showinfo("Invoice created", f"Invoice {r[0]} made with {len(rows)} line(s). Open it in Sales Invoices to change qty, discount or freight.")
    def make_from_stock(cid):
        if not cid: return
        pend, bal = db.execute("SELECT pending,bal FROM combo_stock WHERE combo_id=?", (cid,)).fetchone()
        Form(tabs["Combo Making"], None, root, initial=dict(combo_id=cid, qty=max(pend - bal, 0) or 1))
    def fold_from_stock(iid):
        if not iid: return
        typ, m = db.execute("SELECT type,meters FROM stock WHERE item_id=?", (iid,)).fetchone()
        if "Fabric" not in (typ or ""): messagebox.showinfo("Fabric Folding", "Folding / pcs conversion is only for Shirt or Trouser fabric."); return
        Form(tabs["Pcs Conversion"], None, root, initial=dict(item_id=iid, meters=max(m, 0)))
    nextno = lambda: str((db.execute("SELECT COALESCE(MAX(CAST(order_no AS INTEGER)),0) FROM orders").fetchone()[0]) + 1)
    tabs = {
     "Sales Orders": Crud(PARENT["Sales Orders"], "sales_orders", [("order_no", "Order No", "text", nextord), ("date", "Order Date", "date", ""),
        ("customer_id", "Customer", "fk:parties:Customer", ""), ("combo_id", "Combo", "fk?:combos", ""), ("item_id", "OR Single Fabric/Item", "fk?:items", ""), ("shade", "Shade / Design", "text", ""), 
        ("unit", "Unit (single item only)", "choice:Pcs|Meter", "Pcs"), ("qty", "Qty ordered", "num", "1"), ("rate", "Agreed rate (excl. GST)", "num", ""),
        ("due_date", "Delivery / Due Date", "date?", ""), ("buyer_order_no", "Buyer's Order No. (customer PO)", "text", ""), ("buyer_order_date", "Buyer's Order Date", "date?", ""),
        ("terms", "Mode/Terms of Payment (e.g. 30 days)", "text", ""), ("note", "Note", "text", ""), ("status", "Status", "choice:Open|Cancelled", "Open")],
        "SELECT o.id,o.order_no,o.date,p.name,COALESCE(c.name,i.name||CASE WHEN COALESCE(o.shade,'')<>'' THEN ' ['||o.shade||']' ELSE '' END||' ('||o.unit||')'),o.qty,o.rate,COALESCE(o.pack_type,''),COALESCE(o.fold_type,''),COALESCE(o.packs,''),COALESCE(op.invoiced,0),COALESCE(op.pend,0),o.due_date,"
        "CASE WHEN o.status='Cancelled' THEN 'Cancelled' WHEN COALESCE(op.invoiced,0)<=0 THEN 'Open' WHEN op.pend>0 THEN 'Part Invoiced' ELSE 'Fully Invoiced' END,o.buyer_order_no "
        "FROM sales_orders o LEFT JOIN parties p ON p.id=o.customer_id LEFT JOIN combos c ON c.id=o.combo_id LEFT JOIN items i ON i.id=o.item_id LEFT JOIN order_pending op ON op.order_id=o.id ORDER BY o.date DESC,o.id DESC",
        ("Order No", "Date", "Customer", "Product", "Approx Qty (Mtr)", "Rate", "Pack Type", "Fold / Cut", "No. of Packs", "Invoiced", "Pending", "Due Date", "Status", "Buyer PO"), pre_sales_order,
        [("Print Order", sales_order_doc), ("Order PDF", lambda i: sales_order_doc(i, "pdf")), ("Create Invoice", create_invoice)]),
     "Sales Invoices": Crud(PARENT["Sales Invoices"], "orders", [("order_no", "Invoice No", "text", nextno), ("date", "Invoice Date", "date", ""),
        ("customer_id", "Customer", "fk:parties:Customer", ""), ("order_id", "Against Sales Order (optional)", "fk?:order_pick", ""), ("combo_id", "Combo (from combo stock)", "fk?:combos", ""),
        ("item_id", "OR Single Fabric/Item", "fk?:items", ""), ("shade", "Shade / Design", "text", ""), ("unit", "Unit (for single item only)", "choice:Pcs|Meter", "Pcs"), ("qty", "Qty", "num", "1"), ("rate", "Rate (excl. GST)", "num", ""),
        ("disc_trade", "Trade Discount %", "num", "0"), ("disc_cash", "Cash Discount %", "num", "0"), ("disc_flat", "Special Discount (flat Rs)", "num", "0"), ("freight", "Freight / Courier (Rs, added before GST)", "num", "0"),
        ("buyer_order_no", "Buyer's Order No. (customer PO)", "text", ""), ("buyer_order_date", "Buyer's Order Date", "date?", ""),
        ("terms", "Mode/Terms of Payment (e.g. 30 days)", "text", ""), ("status", "Dispatch Status", "choice:" + "|".join(STATUS + ["Cancelled"]), "Pending")],
        "SELECT o.id,o.order_no,o.date,p.name,COALESCE(c.name,i.name||CASE WHEN COALESCE(o.shade,'')<>'' THEN ' ['||o.shade||']' ELSE '' END||' ('||o.unit||')'),o.qty,o.rate,o.amount,COALESCE(o.total,o.amount),o.status,COALESCE(so.order_no,'') FROM orders o LEFT JOIN parties p ON p.id=o.customer_id "
        "LEFT JOIN combos c ON c.id=o.combo_id LEFT JOIN items i ON i.id=o.item_id LEFT JOIN sales_orders so ON so.id=o.order_id ORDER BY o.date DESC,o.id DESC",
        ("Invoice No", "Date", "Customer", "Product", "Qty", "Rate", "Taxable", "Total (with GST)", "Status", "Order No"), pre_order,
        [("Print Invoice", invoice), ("Invoice PDF", lambda i: invoice(i, "pdf")), ("WhatsApp", whatsapp_invoice), ("Next Status", next_status)]),
     "LR Update": LRTab(PARENT["LR Update"]),
     "Sales Returns": Crud(PARENT["Sales Returns"], "sales_returns", [("date", "Date", "date", ""), ("customer_id", "Customer", "fk:parties:Customer", ""), ("combo_id", "Combo returned", "fk?:combos", ""),
        ("item_id", "OR Single Item returned", "fk?:items", ""), ("shade", "Shade / Design", "text", ""), ("unit", "Unit (single item only)", "choice:Pcs|Meter", "Pcs"), ("qty", "Qty returned", "num", "1"),
        ("rate", "Credit rate (excl. GST)", "num", ""), ("return_type", "Condition of returned goods", RT, "Full - all reusable"), ("note", "Reason / Note", "text", "")],
        "SELECT r.id,r.date,p.name,COALESCE(c.name,i.name||CASE WHEN COALESCE(r.shade,'')<>'' THEN ' ['||r.shade||']' ELSE '' END||' ('||r.unit||')'),r.qty,r.amount,COALESCE(r.total,r.amount),r.return_type,r.note FROM sales_returns r LEFT JOIN parties p ON p.id=r.customer_id "
        "LEFT JOIN combos c ON c.id=r.combo_id LEFT JOIN items i ON i.id=r.item_id ORDER BY r.date DESC,r.id DESC",
        ("Date", "Customer", "Product", "Qty", "Taxable", "Credit (with GST)", "Condition", "Note"), pre_return, [("Print Credit Note", credit_note), ("Credit Note PDF", lambda i: credit_note(i, "pdf"))]),
     "Purchase Returns": Crud(PARENT["Purchase Returns"], "purchase_returns", [("date", "Date", "date", ""), ("supplier_id", "Supplier", "fk:parties:Supplier", ""), ("item_id", "Item", "fk:items", ""), ("shade", "Shade / Design", "text", ""), 
        ("unit", "Unit", "choice:Meter|Pcs", "Meter"), ("qty", "Qty returned", "num", ""), ("rate", "Rate (excl. GST)", "num", ""), ("note", "Reason / Note", "text", "")],
        "SELECT r.id,r.date,s.name,i.name||CASE WHEN COALESCE(r.shade,'')<>'' THEN ' ['||r.shade||']' ELSE '' END,r.unit,r.qty,r.amount,COALESCE(r.total,r.amount),r.note FROM purchase_returns r JOIN items i ON i.id=r.item_id LEFT JOIN parties s ON s.id=r.supplier_id ORDER BY r.date DESC,r.id DESC",
        ("Date", "Supplier", "Item", "Unit", "Qty", "Taxable", "Debit (with GST)", "Note"), pre_preturn, [("Print Debit Note", debit_note), ("Debit Note PDF", lambda i: debit_note(i, "pdf"))]),
     "Combo Making": Crud(PARENT["Combo Making"], "combo_makes", [("date", "Date", "date", ""), ("combo_id", "Combo", "fk:combos", ""), ("qty", "Qty of combos made", "num", "1"),
        ("contractor_id", "Contractor (blank = own staff)", "fk?:parties:Contractor", ""), ("job_rate", "Job charge per combo (Rs)", "num", "0"), ("note", "Note", "text", "")],
        "SELECT m.id,m.date,c.name,m.qty,COALESCE(p.name,'Own staff'),m.job_rate,COALESCE(m.job_amount,0),m.note FROM combo_makes m JOIN combos c ON c.id=m.combo_id LEFT JOIN parties p ON p.id=m.contractor_id ORDER BY m.date DESC,m.id DESC",
        ("Date", "Combo", "Combos Made", "Contractor", "Rate", "Job Charges", "Note"), pre_make),
     "Combo Stock": Crud(PARENT["Combo Stock"], "combos", None, "SELECT combo_id,name,made,sold,returned,bal,pending,CASE WHEN pending-bal>0 THEN pending-bal ELSE 0 END FROM combo_stock ORDER BY name",
        ("Combo", "Made", "Invoiced (Sold)", "Returned (reusable)", "Ready Stock", "Orders Pending", "Still To Make"), extra=[("Make Combos (Job Work)", make_from_stock)] if COMBO_ON else (), look=("Combo Stock and Orders to Make", "#fff7d6", "#a07d00")),
     "Combo Master": ComboMaster(PARENT["Combo Master"]),
     "Purchases": Crud(nb, "purchases", [("date", "Date", "date", ""), ("supplier_id", "Supplier", "fk:parties:Supplier", ""), ("item_id", "Item", "fk:items", ""), ("shade", "Shade / Design", "text", ""), 
        ("unit", "Received in", "choice:Meter|Pcs", "Meter"), ("qty", "Quantity (in chosen unit)", "num", ""), ("rate", "Rate (excl. GST, per Meter or per Pc)", "num", "")],
        "SELECT p.id,p.date,s.name,i.name||CASE WHEN COALESCE(p.shade,'')<>'' THEN ' ['||p.shade||']' ELSE '' END,p.unit,p.qty,p.rate,p.amount,COALESCE(p.total,p.amount) FROM purchases p JOIN items i ON i.id=p.item_id LEFT JOIN parties s ON s.id=p.supplier_id ORDER BY p.date DESC,p.id DESC",
        ("Date", "Supplier", "Item", "Unit", "Qty", "Rate", "Taxable", "Total (with GST)"), pre_purchase),
     "Pcs Conversion": Crud(PARENT["Pcs Conversion"], "conversions", [("date", "Date", "date", ""), ("item_id", "Fabric item", "fk:items", ""), ("shade", "Shade / Design", "text", ""), ("meters", "Meters received to fold / convert", "num", ""),
        ("length", "Length of 1 Pc (meters)", "num", ""), ("contractor_id", "Contractor (blank = own staff)", "fk?:parties:Contractor", ""), ("job_rate", "Job charge rate (Rs)", "num", "0"),
        ("job_basis", "Charge is", "choice:Per Pc|Per Meter", "Per Pc")],
        "SELECT c.id,c.date,i.name||CASE WHEN COALESCE(c.shade,'')<>'' THEN ' ['||c.shade||']' ELSE '' END,c.meters,c.length,c.pcs,c.wastage,COALESCE(p.name,'Own staff'),c.job_rate,COALESCE(c.job_basis,''),COALESCE(c.job_amount,0) FROM conversions c JOIN items i ON i.id=c.item_id LEFT JOIN parties p ON p.id=c.contractor_id ORDER BY c.date DESC,c.id DESC",
        ("Date", "Fabric", "Meters Used", "Length / Pc", "Pcs Made", "Wastage (m)", "Contractor", "Rate", "Basis", "Job Charges"), pre_convert),
     "Job Register": Crud(PARENT["Job Register"], "combo_makes", None,
        "SELECT j.rid,j.date,j.kind,COALESCE(p.name,'Own staff'),j.item,j.qty_in,j.qty_out,j.wastage,j.job_rate,j.basis,j.job_amount FROM job_work j LEFT JOIN parties p ON p.id=j.contractor_id ORDER BY j.date DESC,j.rid DESC",
        ("Date", "Job", "Contractor", "Fabric / Combo", "Meters In", "Pcs / Combos Out", "Wastage (m)", "Rate", "Basis", "Job Charges"), look=("Job Work Register", "#fff3e0", "#c76b1a")),
     "Contractor Summary": Crud(PARENT["Contractor Summary"], "parties", None,
        """SELECT id,name,fm,pcs,combos,chg,paid,chg-paid FROM (SELECT p.id,p.name,COALESCE((SELECT SUM(meters) FROM conversions WHERE contractor_id=p.id),0) fm,
        COALESCE((SELECT SUM(pcs) FROM conversions WHERE contractor_id=p.id),0) pcs,COALESCE((SELECT SUM(qty) FROM combo_makes WHERE contractor_id=p.id),0) combos,
        COALESCE((SELECT SUM(job_amount) FROM job_work WHERE contractor_id=p.id),0) chg,COALESCE((SELECT SUM(amount) FROM payments WHERE party_id=p.id),0) paid
        FROM parties p WHERE p.type='Contractor') ORDER BY name""",
        ("Contractor", "Fabric Folded (m)", "Pcs Received", "Combos Made", "Job Charges", "Paid", "Balance To Pay"), look=("Contractor Summary", "#fce8f3", "#b83280")),
     "Payments": Crud(PARENT["Payments"], "payments", [("date", "Date", "date", ""), ("account_id", "Cash / Bank account", "fk:accounts", lambda: db.execute("SELECT id FROM accounts WHERE name='Cash'").fetchone()[0]),
        ("party_id", "Party", "fk:parties", ""), ("amount", "Amount", "num", ""), ("note", "Narration", "text", "")],
        "SELECT y.id,y.date,COALESCE(a.name,'Cash'),p.name,p.type,CASE WHEN p.type='Customer' THEN 'Receipt' ELSE 'Payment' END,y.amount,y.note FROM payments y JOIN parties p ON p.id=y.party_id LEFT JOIN accounts a ON a.id=y.account_id ORDER BY y.date DESC,y.id DESC",
        ("Date", "Cash / Bank", "Party", "Type", "Voucher", "Amount", "Narration"), pre_payment, [("Adjust Against Bills", lambda i: AllocDialog(root, i) if i else None)]),
     "Contra": Crud(PARENT["Contra"], "contra", [("date", "Date", "date", ""), ("from_account_id", "From account (money goes out)", "fk:accounts", ""), ("to_account_id", "To account (money comes in)", "fk:accounts", ""),
        ("amount", "Amount", "num", ""), ("narration", "Narration", "text", "")],
        "SELECT c.id,c.date,f.name,t.name,c.amount,c.narration FROM contra c JOIN accounts f ON f.id=c.from_account_id JOIN accounts t ON t.id=c.to_account_id ORDER BY c.date DESC,c.id DESC",
        ("Date", "From", "To", "Amount", "Narration"), pre_contra),
     "Journal": Crud(PARENT["Journal"], "journal", [("date", "Date", "date", ""), ("dr_party_id", "Debit party (owes more / gets credit used)", "fk:parties", ""), ("cr_party_id", "Credit party (owes less / is owed more)", "fk:parties", ""),
        ("amount", "Amount", "num", ""), ("narration", "Narration", "text", "")],
        "SELECT j.id,j.date,d.name,c.name,j.amount,j.narration FROM journal j JOIN parties d ON d.id=j.dr_party_id JOIN parties c ON c.id=j.cr_party_id ORDER BY j.date DESC,j.id DESC",
        ("Date", "Debit", "Credit", "Amount", "Narration"), pre_journal),
     "Delivery Challans": Crud(PARENT["Delivery Challans"], "challans", [("date", "Date", "date", ""), ("party_id", "Party (to)", "fk:parties", ""), ("purpose", "Purpose", "choice:Delivery / Sale|Job Work|Sample|Return|Other", "Delivery / Sale"),
        ("combo_id", "Combo", "fk?:combos", ""), ("item_id", "OR Single Item", "fk?:items", ""), ("shade", "Shade / Design", "text", ""), ("unit", "Unit (single item only)", "choice:Pcs|Meter", "Pcs"), ("qty", "Qty", "num", "1"), ("remarks", "Remarks for this line", "text", ""),
        ("vehicle_no", "Vehicle No.", "text", ""), ("transport", "Transport", "text", ""), ("lr_no", "LR No.", "text", ""), ("narration", "Narration", "text", "")],
        "SELECT c.id,c.date,p.name,c.purpose,COALESCE(cb.name,i.name||CASE WHEN COALESCE(c.shade,'')<>'' THEN ' ['||c.shade||']' ELSE '' END),c.unit,c.qty,c.vehicle_no,c.transport,c.lr_no FROM challans c LEFT JOIN parties p ON p.id=c.party_id LEFT JOIN combos cb ON cb.id=c.combo_id LEFT JOIN items i ON i.id=c.item_id ORDER BY c.date DESC,c.id DESC",
        ("Date", "Party", "Purpose", "Product", "Unit", "Qty", "Vehicle", "Transport", "LR No"), pre_challan, [("Print Challan", challan_doc), ("Challan PDF", lambda i: challan_doc(i, "pdf"))]),
     "Bills Outstanding": Crud(PARENT["Bills Outstanding"], "parties", None, bills_sql, ("Party", "Type", "Bill", "Bill Date", "Bill Amount", "Adjusted", "Pending", "Days"), look=("Bills Outstanding (bill-wise)", "#e3f6f5", "#23847f")),
     "Bank/Cash Master": Crud(PARENT["Bank/Cash Master"], "accounts", ACCOUNT_FIELDS, "SELECT id,name,type,opening,details FROM accounts ORDER BY type,name", ("Account", "Type", "Opening Balance", "Details")),
     "Cash/Bank Balance": Crud(PARENT["Cash/Bank Balance"], "accounts", None, bank_sql, ("Account", "Type", "Opening", "Receipts (In)", "Payments (Out)", "Balance"), look=("Cash / Bank Balance", "#e6f4ea", "#2e7d4f")),
     "Stock": Crud(PARENT["Stock"], "items", None, f"SELECT item_id,name,type,design,color,meters,pcs,wastage,CASE WHEN {ALERT} THEN 'LOW STOCK' ELSE 'OK' END FROM stock ORDER BY type,name",
        ("Item", "Type", "Design", "Color", "Stock (Meters)", "Stock (Pcs)", "Total Wastage (m)", "Alert"), extra=[("Fold to Pcs (Job Work)", fold_from_stock)] if COMBO_ON else (), look=("Stock Summary", "#e6f4ea", "#2e7d4f")),
     "Shade Stock": Crud(PARENT["Shade Stock"], "items", None, "SELECT 0,'','',0,0,0", ("Item", "Type", "Shade / Design", "Stock (Meters)", "Stock (Pcs)"), look=("Shade / Design wise Stock", "#fdecef", "#b03a56")),
     "Pack Types": Crud(PARENT["Pack Types"], "pack_types", [("name", "Pack Type (e.g. Roll, Lump, Pcs, Book Fold)", "text", ""), ("mode", "This pack needs", "choice:Fold|Cut|None", "Fold"), ("approx_meters", "Approx metres in 1 pack (default; can be changed per order line)", "num", "0")],
        "SELECT id,name,mode,approx_meters FROM pack_types ORDER BY name", ("Pack Type", "Needs (Fold type / Cut type)", "Approx Mtr / Pack")),
     "Fold / Cut Types": Crud(PARENT["Fold / Cut Types"], "fold_types", [("mode", "Belongs to packs that need", "choice:Fold|Cut", "Fold"), ("name", "Fold Type / Cut Type name", "text", ""), ("cut_meters", "Metres per pc for this cut (Cut types only; 0 = enter in the order)", "num", "0")],
        "SELECT id,mode,name,cut_meters FROM fold_types ORDER BY mode,name", ("Kind", "Fold / Cut Type", "Metres per Pc")),
     "Items": Crud(PARENT["Items"], "items", ITEM_FIELDS,
        "SELECT id,name,type,design,color,hsn,gst_rate,std_length,min_stock FROM items ORDER BY name", ("Name", "Type", "Design", "Color", "HSN", "GST %", "Std Length/Pc (m)", "Alert level")),
     "Customers/Suppliers": Crud(PARENT["Customers/Suppliers"], "parties", PARTY_FIELDS,
        "SELECT id,name,type,phone,address,gst,state FROM parties ORDER BY type,name", ("Name", "Type", "Phone", "Address", "GSTIN", "State")),
     "Balances": Crud(PARENT["Balances"], "parties", None, """SELECT id,name,type,total,paid,total-paid,CASE WHEN type='Customer' THEN 'They owe you' ELSE 'You owe them' END FROM
        (SELECT p.id,p.name,p.type,CASE WHEN p.type='Customer' THEN
          COALESCE((SELECT SUM(t) FROM invoice_totals WHERE customer_id=p.id),0)-COALESCE((SELECT SUM(rnd(COALESCE(total,amount))) FROM sales_returns WHERE customer_id=p.id),0)
        WHEN p.type='Contractor' THEN COALESCE((SELECT SUM(job_amount) FROM job_work WHERE contractor_id=p.id),0)
        ELSE COALESCE((SELECT SUM(COALESCE(total,amount)) FROM purchases WHERE supplier_id=p.id),0)-COALESCE((SELECT SUM(rnd(COALESCE(total,amount))) FROM purchase_returns WHERE supplier_id=p.id),0) END total,
        COALESCE((SELECT SUM(amount) FROM payments WHERE party_id=p.id),0) paid FROM parties p) ORDER BY type,name""",
        ("Name", "Type", "Net Bill (with GST, after returns)", "Paid", "Balance", "Meaning"), look=("Outstanding Balances", "#e3f6f5", "#23847f")),
     "Ledger": Ledger(PARENT["Ledger"]),
     "Reports": Reports(nb),
     "Company Profile": Profile(PARENT["Company Profile"]),
    }
    for nm_, ix in {"Sales Orders": 2, "Sales Invoices": 2, "Purchases": 1, "Payments": 1, "Sales Returns": 1, "Purchase Returns": 1, "Combo Making": 1, "Pcs Conversion": 1, "Job Register": 1, "Contra": 1, "Journal": 1, "Delivery Challans": 1}.items(): tabs[nm_].datecol = ix
    tabs["Sales Orders"].form = OrderVoucher
    tabs["Sales Orders"].header = {"order_no", "date", "customer_id", "due_date", "buyer_order_no", "buyer_order_date", "terms", "note", "status"}
    tabs["Sales Invoices"].header = {"order_no", "date", "customer_id", "buyer_order_no", "buyer_order_date", "terms", "narration", "status"}
    tabs["Delivery Challans"].keep = {"vno", "party_id", "purpose", "vehicle_no", "transport", "lr_no", "narration"}
    tabs["Sales Invoices"].fields = tabs["Sales Invoices"].fields + [("narration", "Narration", "text", "")]
    tabs["Purchases"].fields = tabs["Purchases"].fields + [("bill_no", "Supplier Bill No.", "text", ""), ("bill_date", "Supplier Bill Date", "date?", ""), ("narration", "Narration", "text", "")]
    tabs["Stock"].sql = lambda: f"SELECT item_id,name,type,design,color,meters,pcs,wastage,CASE WHEN {ALERT} THEN 'LOW STOCK' ELSE 'OK' END FROM ({stock_asof(WORK['to'])}) ORDER BY type,name"
    tabs["Shade Stock"].sql = lambda: f"SELECT i.id||'|'||s.shade,i.name,i.type,CASE WHEN s.shade='' THEN '(no shade)' ELSE s.shade END,s.meters,s.pcs FROM ({shade_asof(WORK['to'])}) s JOIN items i ON i.id=s.item_id WHERE ABS(s.meters)>0.000001 OR ABS(s.pcs)>0.000001 ORDER BY i.name,s.shade"
    tabs["Combo Stock"].sql = lambda: f"SELECT combo_id,name,made,sold,returned,bal,pending,CASE WHEN pending-bal>0 THEN pending-bal ELSE 0 END FROM ({combo_stock_asof(WORK['to'])}) ORDER BY name"
    tabs["Balances"].sql = balances_sql; tabs["Customers/Suppliers"].pre = pre_party
    if not COMBO_ON:
        for nm_ in ("Sales Orders", "Sales Invoices", "Sales Returns", "Delivery Challans"):
            tabs[nm_].fields = [(c, l, k, "Meter" if c == "unit" else d) for c, l, k, d in tabs[nm_].fields if c != "combo_id"]
    for nm_ in ("Stock", "Shade Stock", "Combo Stock", "Balances"): tabs[nm_].refresh()
    for name in ["Sales", "Purchases", "Job Work (Contract)", "Stock", "Returns & Notes", "Accounts", "Masters", "Reports"]:
        if name in GROUPS:
            shown = [k for k in GROUPS[name] if page_on(k)]
            for k in shown: G[name].add(tabs[k], text=LABEL.get(k, k))
            if shown: nb.add(G[name], text=name)
        elif page_on(name): nb.add(tabs[name], text=name)
    def on_tab(e):
        w = e.widget.nametowidget(e.widget.select())
        if hasattr(w, "select"): w = w.nametowidget(w.select())
        w.refresh()
    nb.bind("<<NotebookTabChanged>>", on_tab)
    for g in G.values(): g.bind("<<NotebookTabChanged>>", on_tab)
    nm = get("Company Name"); root.title((nm + " - " if nm else "") + "Combo Manager")
    if not get("State") or not get("GST No"): messagebox.showinfo("Company Profile", "Please fill your Company Profile (GSTIN and State) so GST invoices print correctly.")
    low = db.execute(f"SELECT name,meters,pcs FROM stock WHERE {ALERT}").fetchall()
    if low: messagebox.showwarning("Low stock", "\n".join(f"{n}: {m:g} m, {p:g} pcs" for n, m, p in low))
    try: backup()
    except Exception: pass
    def on_close():
        try: backup()
        except Exception: pass
        root.destroy()
    ON_CLOSE[0] = on_close
    root.protocol("WM_DELETE_WINDOW", on_close)

    # ---------------- Tally-style shortcut keys ----------------
    SHORTCUTS = [("F8", "Sales Invoice (new)"), ("Alt+F5", "Sales Order (new)"), ("F9", "Purchase voucher"), ("Ctrl+F8", "Credit Note (sales return)"),
                 ("Ctrl+F9", "Debit Note (purchase return)"), ("F5", "Payment (to supplier)"), ("F6", "Receipt (from customer)"),
                 ("Ctrl+F4", "Combo Making voucher (Combo style)"), ("Ctrl+F7", "Fabric Folding voucher (Combo style)"), ("F3", "Select / change company"), ("F4", "Contra voucher (Cash / Bank transfer)"), ("F7", "Journal voucher"), ("Alt+F8", "Delivery Challan"), ("F2", "Change date (working date; inside a voucher: that voucher's date)"),
                 ("Ctrl+F2", "Change financial year (all lists, reports, balances and dashboard follow it)"), ("Alt+F2", "Change period inside the year (lists, reports, ledger)"), ("Alt+G", "Go To any screen (type its name)"), ("F12", "Configure: Company Profile"),
                 ("Esc", "Back to Gateway (when no entry window is open)"), ("F1", "This help"), ("Ctrl+Q", "Quit"), ("", ""), ("In a voucher / form", ""), ("Enter", "next field"), ("Ctrl+A", "accept / save"),
                 ("Esc", "close (asks if something was typed)"), ("Alt+C", "create new master (+ New) for the field you are on"), ("", ""),
                 ("In a list", ""), ("Alt+A / Insert", "add"), ("Enter", "edit selected"), ("Alt+D / Delete", "delete selected"), ("Ctrl+P", "print (first print button of the screen)")]
    def goto(page):
        if page == "Gateway": nb.select(gw); gw.refresh(); return
        if page in PARENT: nb.select(PARENT[page]); PARENT[page].select(tabs[page])
        else: nb.select(tabs[page])
        tabs[page].refresh()
    def free(fn):                       # global keys do nothing while a voucher/form is open
        return lambda e=None: None if root.grab_current() else fn()
    def open_form(page): tabs[page].form(tabs[page], None, root)
    def pay_form(kind):
        base = tabs["Payments"]
        fields = [(c, l, (("fk:parties:!Customer" if kind == "Supplier" else "fk:parties:Customer") if c == "party_id" else k), ("Payment made" if kind == "Supplier" else "Receipt") if c == "note" else ((lambda: suggest_vno("payments", "PAY" if kind == "Supplier" else "RCT")) if c == "vno" else d)) for c, l, k, d in base.fields]
        Form(types.SimpleNamespace(table="payments", fields=fields, pre=pre_payment, after_save=None, refresh=base.refresh, vtype="Payment" if kind == "Supplier" else "Receipt"), None, root)
    def change_date():
        r = ask_dialog(root, "Change working date (F2)", [("Date (DD/MM/YY)", fmt_date(WORK["date"]))]); iso = parse_date(r[0]) if r else None
        if iso: WORK["date"] = iso; update_status()
        elif r: messagebox.showerror("Date", "Date must be DD/MM/YY.")
    def change_period():
        r = ask_dialog(root, "Change period (Alt+F2)", [("From (DD/MM/YY)", fmt_date(WORK["from"])), ("To (DD/MM/YY)", fmt_date(WORK["to"]))])
        if not r: return
        a, b = parse_date(r[0]), parse_date(r[1])
        if not a or not b or a > b: messagebox.showerror("Period", "Enter valid dates as DD/MM/YY. From must not be after To."); return
        WORK["from"], WORK["to"] = a, b; update_status()
        for t in ("Reports", "Ledger"): tabs[t].a.set(fmt_date(a)); tabs[t].b.set(fmt_date(b))
        refresh_all()
    def refresh_all():
        try: w = nb.nametowidget(nb.select()); w = w.nametowidget(w.select()) if hasattr(w, "select") else w; w.refresh()
        except Exception: pass
    def apply_fy(y):
        set_fy(y); update_status()
        for t in ("Reports", "Ledger"): tabs[t].a.set(fmt_date(WORK["from"])); tabs[t].b.set(fmt_date(WORK["to"]))
        refresh_all()
        try: gw.refresh()
        except Exception: pass
    def change_fy():
        years = fy_choices(); labels = [fy_label(y) for y in years]
        win = tk.Toplevel(root); win.title("Change Financial Year (Ctrl+F2)"); win.grab_set(); win.resizable(False, False); box = ttk.Frame(win, padding=16); box.pack()
        ttk.Label(box, text="Financial Year (1 April to 31 March)").grid(row=0, column=0, padx=6, pady=8); v = tk.StringVar(value=fy_label(WORK["fy"]))
        cb = ttk.Combobox(box, textvariable=v, values=labels, state="readonly", width=10); cb.grid(row=0, column=1, padx=6); cb.focus_set()
        def ok(e=None): win.destroy(); apply_fy(years[labels.index(v.get())])
        ttk.Button(box, text="OK  (Enter)", command=ok, style="Accent.TButton").grid(row=1, column=0, columnspan=2, pady=8); win.bind("<Return>", ok); win.bind("<Escape>", lambda e: win.destroy())
    def show_data_check():
        found = data_check()
        if not found: messagebox.showinfo("Check Data", "No problems found."); return
        win = tk.Toplevel(root); win.title("Check Data - problems found"); win.geometry("760x520"); win.bind("<Escape>", lambda e: win.destroy())
        tk.Label(win, text=f"  {len(found)} thing(s) to look at", bg="#b34a4a", fg="white", font=("Segoe UI", 13, "bold"), anchor="w", pady=8).pack(fill="x")
        t = tk.Text(win, font=("Consolas", 10), wrap="word", padx=10, pady=8); t.pack(fill="both", expand=True); t.insert("1.0", "\n\n".join(found)); t.config(state="disabled")
    def go_to():
        win = tk.Toplevel(root); win.title("Go To (Alt+G)"); win.grab_set(); box = ttk.Frame(win, padding=12); box.pack()
        v = tk.StringVar(); e = ttk.Entry(box, textvariable=v, width=40); e.pack(fill="x"); e.focus_set()
        lb = tk.Listbox(box, width=40, height=14, font=("Segoe UI", 10)); lb.pack(pady=6)
        names = [LABEL.get(k, k) for k in tabs if page_on(k)] ; keyof = {LABEL.get(k, k): k for k in tabs if page_on(k)}
        def fill(*a):
            lb.delete(0, "end")
            for n in names:
                if v.get().strip().lower() in n.lower(): lb.insert("end", n)
            if lb.size(): lb.selection_set(0)
        def pick(ev=None):
            sel = lb.curselection()
            if sel: name = lb.get(sel[0]); win.destroy(); goto(keyof[name])
        v.trace_add("write", fill); fill()
        e.bind("<Return>", pick); lb.bind("<Return>", pick); lb.bind("<Double-1>", pick); e.bind("<Down>", lambda ev: (lb.focus_set(), "break")[1])
        win.bind("<Escape>", lambda ev: win.destroy())
    def show_help(): messagebox.showinfo("Shortcut keys", "\n".join(f"{k:<16}{d}" if k else d for k, d in SHORTCUTS))
    def update_program(online_path=None, online_ver=None):
        """Install a newly downloaded combo_manager.py over this one (old copy is kept in 'old_versions'), then restart. Data is never touched."""
        import glob, shutil, py_compile
        me = os.path.abspath(__file__) if not getattr(sys, "frozen", False) else None
        if not me or not me.lower().endswith(".py"): messagebox.showinfo("Update", "Update works only when running combo_manager.py directly."); return
        def ver(p):
            try: m = re.search(r'^VERSION\s*=\s*"([^"]+)"', open(p, encoding="utf-8", errors="ignore").read(200000), re.M); return m.group(1) if m else None
            except Exception: return None
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
        if online_path: best = (online_ver, online_path)
        cands = sorted({os.path.abspath(p) for p in glob.glob(os.path.join(dl, "combo_manager*.py")) + glob.glob(os.path.join(BASE, "combo_manager*.py"))} - {os.path.abspath(me)}, key=os.path.getmtime, reverse=True)
        cands = [(ver(p), p) for p in cands if ver(p)]
        if not online_path: best = max(cands, default=None)
        if not online_path and (not best or best[0] <= VERSION):
            if not messagebox.askyesno("Update Program", f"No newer file found in your Downloads folder.\nThis program: {VERSION}\n\nDo you want to choose the downloaded file yourself?"): return
            p = filedialog.askopenfilename(title="Choose the new combo_manager.py", filetypes=[("Python file", "*.py")])
            if not p: return
            v = ver(p)
            if not v: messagebox.showerror("Update", "This file is not a Combo Manager program file."); return
            best = (v, p)
        v, p = best
        if v <= VERSION and not messagebox.askyesno("Update Program", f"That file (version {v}) is not newer than this program ({VERSION}).\n\nInstall it anyway?"): return
        if v > VERSION and not messagebox.askyesno("Update Program", f"New version found:\n{p}\n\nInstalled: {VERSION}\nNew: {v}\n\nInstall it now? The program will restart. Your data is not changed and the old program is saved in 'old_versions'."): return
        try:
            py_compile.compile(p, cfile=os.path.join(tempfile.gettempdir(), "cm_check.pyc"), doraise=True)
            od = os.path.join(BASE, "old_versions"); os.makedirs(od, exist_ok=True); shutil.copy2(me, os.path.join(od, f"combo_manager_{VERSION}.py")); shutil.copy2(p, me)
        except Exception as e: messagebox.showerror("Update failed", f"Nothing was changed.\n{e}"); return
        try:
            if (os.path.dirname(p) == dl or online_path) and os.path.abspath(p) != os.path.abspath(me): os.remove(p)      # tidy the Downloads folder / temp file
        except Exception: pass
        relaunch(["--company=" + CO["key"]]); on_close()
    UPD_FILE = os.path.join(BASE, "update_url.txt")
    def fetch_remote(url, token=""):
        import urllib.request
        rq = urllib.request.Request(url, headers={"User-Agent": "ComboManager", **({"Authorization": "token " + token} if token else {})})
        with urllib.request.urlopen(rq, timeout=15) as r: return r.read().decode("utf-8")
    def remote_info():
        """(url, token) saved in update_url.txt (line 1 = link of combo_manager.py on GitHub 'Raw', line 2 = optional access token for a private repository)."""
        try: ls = [x.strip() for x in open(UPD_FILE, encoding="utf-8").read().splitlines() if x.strip()]
        except OSError: ls = []
        return (ls[0], ls[1] if len(ls) > 1 else "") if ls else (None, "")
    def online_check(silent=False):
        url, tok = remote_info()
        if not url:
            if silent: return None
            r = ask_dialog(root, "Update link (one time)", [("GitHub Raw link of combo_manager.py", ""), ("Access token (private repo only, else blank)", "")])
            if not r or not r[0]: return None
            url, tok = r[0].strip(), r[1]
            m_ = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/blob/(.+)$", url)            # a normal GitHub page link -> make it the Raw link
            if m_: url = f"https://raw.githubusercontent.com/{m_.group(1)}/{m_.group(2)}/{m_.group(3)}"
            if re.match(r"^https?://github\.com/[^/]+/[^/]+/?$", url):
                messagebox.showerror("Update", "That is the repository page link, not the file.\nOpen combo_manager.py on GitHub, click the 'Raw' button, and copy the address of that page."); return None
        try: txt = fetch_remote(url, tok)
        except Exception as e:
            if not silent: messagebox.showerror("Update", f"Could not reach the update link.\nCheck the internet and the link in update_url.txt.\n\n{e}")
            return None
        m = re.search(r'^VERSION\s*=\s*"([^"]+)"', txt, re.M)
        if not m or "def choose_company" not in txt:
            if not silent:
                why = "the file on GitHub is an OLD version without a version number - upload the newest combo_manager.py there" if "def choose_company" in txt else "the link does not open the program file (it must be the GitHub 'Raw' link)"
                messagebox.showerror("Update", f"Cannot use this link: {why}.\n\nWhat the link returned starts with:\n{txt[:80]!r}\n\nLink: {url}")
            return None
        try: open(UPD_FILE, "w", encoding="utf-8").write(url + ("\n" + tok if tok else "") + "\n")      # remember the link only after it worked
        except OSError: pass
        return m.group(1), txt
    def update_online():
        got = online_check()
        if not got: return
        v, txt = got
        if v <= VERSION: messagebox.showinfo("Update", f"You already have the latest version ({VERSION})."); return
        tp = os.path.join(tempfile.gettempdir(), "combo_manager_new.py"); open(tp, "w", encoding="utf-8", newline="\n").write(txt)
        update_program(tp, v)
    def startup_update_check():
        import threading
        def work():
            got = online_check(True)
            if got and got[0] > VERSION: root.after(0, lambda: messagebox.showinfo("New version available", f"A new version ({got[0]}) of the program is ready.\nYou have {VERSION}.\n\nUpdate: Gateway > Utilities > Update Program (online)."))
        threading.Thread(target=work, daemon=True).start()
    def change_company():
        relaunch(["--choose"]); on_close()
    ON_CHANGE_COMPANY[0] = change_company
    keys = {"<F8>": lambda: open_form("Sales Invoices"), "<Alt-F5>": lambda: open_form("Sales Orders"), "<F9>": lambda: open_form("Purchases"), "<Control-F8>": lambda: open_form("Sales Returns"),
            "<Control-F9>": lambda: open_form("Purchase Returns"), "<F5>": lambda: pay_form("Supplier"), "<F6>": lambda: pay_form("Customer"),
            "<F2>": change_date, "<F3>": change_company, "<F4>": lambda: open_form("Contra"), "<F7>": lambda: open_form("Journal"), "<Alt-F8>": lambda: open_form("Delivery Challans"), "<Alt-F2>": change_period,
            "<Control-F2>": change_fy, "<Alt-g>": go_to, "<Alt-G>": go_to, "<F12>": lambda: goto("Company Profile")}
    if COMBO_ON: keys.update({"<Control-F4>": lambda: open_form("Combo Making"), "<Control-F7>": lambda: open_form("Pcs Conversion")})
    for k, fn in keys.items(): root.bind_all(k, free(fn))
    VKEYS.update({k: keys[k] for k in ("<F8>", "<F9>", "<F5>", "<F6>", "<Control-F8>", "<Control-F9>", "<Alt-F5>", "<Control-F4>", "<Control-F7>", "<F4>", "<F7>", "<Alt-F8>") if k in keys})
    root.bind_all("<F1>", lambda e: show_help()); root.bind_all("<Control-q>", lambda e: on_close()); root.bind_all("<Control-Q>", lambda e: on_close())
    root.bind_all("<Escape>", free(lambda: goto("Gateway")))

    # ---------------- Gateway menus (Tally style) ----------------
    def tag(fn, page): fn.page = page; return fn
    V = lambda page: tag(lambda: open_form(page), page); L = lambda page: tag(lambda: goto(page), page)

    def do_backup(): messagebox.showinfo("Backup", "Saved to:\n" + backup())
    MENUS = {
      "root": ("Gateway", [("Masters", "", "masters"), ("Vouchers (Entry)", "", "vouchers"), ("Day Books / Registers", "", "lists"), ("Reports & Stock", "", "reports"), ("Utilities", "", "utils"), ("Companies - Select / Create New", "F3", change_company), ("Quit", "Ctrl+Q", on_close)]),
      "masters": ("Masters - Create / Alter", [("Item / Fabric Quality", "", L("Items")), ("Combo Master (Combo Creation)", "", L("Combo Master")), ("Pack Types", "", L("Pack Types")), ("Fold / Cut Types", "", L("Fold / Cut Types")), ("Customers & Suppliers", "", L("Customers/Suppliers")), ("Bank / Cash Accounts", "", L("Bank/Cash Master")), ("Company Profile", "F12", L("Company Profile"))]),
      "vouchers": ("Vouchers - Entry", [("Sales Invoice", "F8", V("Sales Invoices")), ("Sales Order", "Alt+F5", V("Sales Orders")), ("Purchase", "F9", V("Purchases")), ("Credit Note", "Ctrl+F8", V("Sales Returns")),
                                        ("Debit Note", "Ctrl+F9", V("Purchase Returns")), ("Payment", "F5", lambda: pay_form("Supplier")), ("Receipt", "F6", lambda: pay_form("Customer")),
                                        ("Contra", "F4", V("Contra")), ("Journal", "F7", V("Journal")), ("Delivery Challan", "Alt+F8", V("Delivery Challans")),
                                        ("Combo Making (Job Work)", "Ctrl+F4", V("Combo Making")), ("Fabric Folding (Job Work)", "Ctrl+F7", V("Pcs Conversion")), ("LR / E-Way Bill Update", "", L("LR Update"))]),
      "lists": ("Day Books / Registers", [("Sales Orders", "", L("Sales Orders")), ("Sales Invoices", "", L("Sales Invoices")), ("Purchases", "", L("Purchases")), ("Payments / Receipts", "", L("Payments")),
                                          ("Credit Notes", "", L("Sales Returns")), ("Debit Notes", "", L("Purchase Returns")), ("Combo Making", "", L("Combo Making")), ("Pcs Conversion", "", L("Pcs Conversion")), ("Contra", "", L("Contra")), ("Journal", "", L("Journal")), ("Delivery Challans", "", L("Delivery Challans"))]),
      "reports": ("Reports & Stock", [("Sales, Purchase & Profit", "", L("Reports")), ("Stock Summary", "", L("Stock")), ("Shade / Design wise Stock", "", L("Shade Stock")), ("Combo Stock & Orders to Make", "", L("Combo Stock")), ("Account Statement (Ledger)", "", L("Ledger")),
                                      ("Outstanding (Balances)", "", L("Balances")), ("Bills Outstanding (bill-wise)", "", L("Bills Outstanding")), ("Cash / Bank Balance", "", L("Cash/Bank Balance")), ("LR / E-Way Bill Pending", "", L("LR Update")), ("Combo Consumption Estimate", "", L("Combo Master")), ("Job Work Register", "", L("Job Register")), ("Contractor Summary", "", L("Contractor Summary"))]),
      "utils": ("Utilities", [("Select / Change Company", "F3", change_company), ("Change Working Date", "F2", change_date), ("Change Financial Year", "Ctrl+F2", change_fy), ("Change Period", "Alt+F2", change_period), ("Backup Now", "", do_backup), ("Update Program (online - GitHub)", "", update_online), ("Update Program (from downloaded file)", "", update_program), ("Check Data for Problems", "", show_data_check), ("Page Setup (Bill Size / Margins)", "", lambda: PageSetup(root, test_print)), ("Go To any screen", "Alt+G", go_to), ("Shortcut Keys", "F1", show_help)])}
    for nm_, (ttl, its) in list(MENUS.items()): MENUS[nm_] = (ttl, [it for it in its if not (callable(it[2]) and getattr(it[2], "page", None) and not page_on(it[2].page))])
    root.after(1500, startup_update_check)
    gw = Gateway(nb, MENUS, goto); nb.insert(0, gw, text="Gateway"); nb.select(gw); gw.refresh()
    root.mainloop()
