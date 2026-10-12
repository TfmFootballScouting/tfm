"""Cost formulas with evidence checks; blank rates are never treated as free."""
import math


def estimate(rows, usd_per_eur=None):
    evaluated=[]
    for row in rows:
        item=dict(row)
        quantity=float(row['quantity'])
        if not math.isfinite(quantity) or quantity<0:
            raise ValueError('Quantity must be finite and nonnegative')
        rate=row.get('usd_per_unit')
        evidence=all(row.get(k) for k in ['source_url','price_date','region'])
        if rate in (None,'') or not evidence:
            item.update(status='pending_price_evidence',monthly_usd=None)
        else:
            rate=float(rate)
            if not math.isfinite(rate) or rate<0:
                raise ValueError('Price must be finite and nonnegative')
            item.update(status='priced',monthly_usd=quantity*rate)
        evaluated.append(item)
    complete=all(x['status']=='priced' for x in evaluated) and bool(evaluated)
    total=sum(x['monthly_usd'] for x in evaluated) if complete else None
    if usd_per_eur is not None and (not math.isfinite(float(usd_per_eur)) or float(usd_per_eur)<=0):
        raise ValueError('Exchange quote must be positive USD per EUR')
    return dict(lines=evaluated,complete=complete,monthly_usd=total,
                monthly_eur=total/float(usd_per_eur) if total is not None and usd_per_eur else None)
