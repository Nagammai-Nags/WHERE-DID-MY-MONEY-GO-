"""Canonical 17-row fixture from PROTOTYPE_WORK_SPLIT.md §14.2."""

_raw = [
("t_b776134dc9cb","ref:600000000001","2026-10-01",45000,"EXPENSE","Swiggy","Food","UPI-SWIGGY-swiggy@icici","swiggy@icici","SWIGGY","DICTIONARY","600000000001","CSV","DEBIT"),
("t_c40b412d3376","ref:600000000002","2026-10-01",2000,"EXPENSE","Tea stall","Food","UPI-Q8812@ybl","q8812@ybl",None,"USER","600000000002","CSV","DEBIT"),
("t_447f9774e89f","ref:600000000003","2026-10-02",38000,"EXPENSE","Zomato","Food","UPI-ZOMATO-zomato@hdfcbank","zomato@hdfcbank","ZOMATO","DICTIONARY","600000000003","CSV","DEBIT"),
("t_3b25e882075c","ref:600000000004","2026-10-02",2000,"EXPENSE","Tea stall","Food","UPI-Q8812@ybl","q8812@ybl",None,"USER","600000000004","CSV","DEBIT"),
("t_30284b7365ca","ref:600000000005","2026-10-03",22000,"EXPENSE","Uber","Transport","UPI-UBER-uber@axisbank","uber@axisbank","UBER","DICTIONARY","600000000005","CSV","DEBIT"),
("t_2bb536eda223","ref:600000000006","2026-10-03",120000,"EXPENSE","IRCTC","Transport","UPI-IRCTC-irctc@sbi","irctc@sbi","IRCTC","DICTIONARY","600000000006","CSV","DEBIT"),
("t_17330e6ee61b","ref:600000000007","2026-10-04",64900,"EXPENSE","Netflix","Entertainment","UPI-NETFLIX-netflix@icici","netflix@icici","NETFLIX","DICTIONARY","600000000007","CSV","DEBIT"),
("t_f0ed153d6cfe","ref:600000000008","2026-10-04",15000,"EXPENSE","Unknown: rajesh77@oksbi","Uncategorized","UPI-RAJESH K-rajesh77@oksbi","rajesh77@oksbi","RAJESH K","UNKNOWN","600000000008","CSV","DEBIT"),
("t_07219f283ca6","ref:600000000009","2026-10-05",135000,"EXPENSE","BigBasket","Groceries","UPI-BIGBASKET-bigbasket@hdfcbank","bigbasket@hdfcbank","BIGBASKET","DICTIONARY","600000000009","CSV","DEBIT"),
("t_e93f71cc5cd1","fp:014b892fbda44859f467674fdb5fb1bf7211f05352496b10747dc80c678448ed","2026-10-05",800000,"INCOME","NEFT ALLOWANCE FROM PARENTS","Uncategorized","NEFT-ALLOWANCE FROM PARENTS",None,"NEFT ALLOWANCE FROM PARENTS","UNKNOWN",None,"CSV","CREDIT"),
("t_cd668fd3ae4c","ref:600000000011","2026-10-06",200000,"TRANSFER_OUT","SELF TRANSFER TO OWN A C","Uncategorized","SELF TRANSFER TO OWN A/C 4455",None,"SELF TRANSFER TO OWN A C","UNKNOWN","600000000011","CSV","DEBIT"),
("t_924ee0388798","ref:600000000012","2026-10-06",3000,"EXPENSE","Tea stall","Food","UPI-Q8812@ybl","q8812@ybl",None,"USER","600000000012","CSV","DEBIT"),
("t_5e7427f46b9c","ref:600000000013","2026-10-07",79900,"EXPENSE","Amazon Pay","Shopping","UPI-AMAZON PAY-amazonpay@apl","amazonpay@apl","AMAZON PAY","DICTIONARY","600000000013","CSV","DEBIT"),
("t_c614985b054a","ref:600000000014","2026-10-07",9000,"EXPENSE","Swiggy","Food","UPI-SWIGGY-swiggy@icici","swiggy@icici","SWIGGY","DICTIONARY","600000000014","CSV","DEBIT"),
("t_3e467660a3c4","ref:600000000015","2026-10-08",6000,"EXPENSE","Tea stall","Food","q8812@ybl","q8812@ybl",None,"USER","600000000015","PASTE","DEBIT"),
("t_54e51da13794","ref:600000000016","2026-10-08",50000,"EXPENSE","Jio","Bills","jio@icici (JIO PREPAID)","jio@icici","JIO PREPAID","DICTIONARY","600000000016","PASTE","DEBIT"),
("t_3976afc5245f","ref:600000000017","2026-10-08",25000,"INCOME","AMIT S","Uncategorized","friend@okaxis (AMIT S)","friend@okaxis","AMIT S","UNKNOWN","600000000017","PASTE","CREDIT"),
]

def _rows(before_alias: bool) -> list[dict]:
    out = []
    for tid, dedup, day, amount, typ, merchant, category, raw, vpa, name, source, ref, origin, direction in _raw:
        row = dict(transaction_id=tid, dedup_key=dedup, date=day, amount_minor=amount,
                   currency="INR", direction=direction, txn_type=typ, display_merchant=merchant,
                   category=category, counterparty_raw=raw, vpa=vpa, name_key=name,
                   merchant_source=source, upi_ref=ref, source=origin)
        if before_alias and tid in {"t_c40b412d3376", "t_3b25e882075c", "t_924ee0388798", "t_3e467660a3c4"}:
            row.update(display_merchant="Unknown: q8812@ybl", category="Uncategorized", merchant_source="UNKNOWN")
        out.append(row)
    return out

ROWS_BEFORE_ALIAS = _rows(True)
ROWS_AFTER_ALIAS = _rows(False)
