"""Parse observed Transfermarkt snapshots, never infer historical effective dates."""
import re
import pandas as pd
from bs4 import BeautifulSoup


def money_eur(text):
    """Unknown/loan is missing; free transfer only becomes zero if explicit."""
    text=str(text).strip()
    if text.lower() in {'free transfer', 'free'}:
        return 0
    m=re.fullmatch(r'€\s*([\d,.]+)\s*([mk]?)',text)
    if not m:
        return None
    value=float(m[1].replace(',',''))
    return round(value*{'':1,'k':1000,'m':1000000}[m[2]])


def market_snapshot(html):
    soup=BeautifulSoup(html,'lxml')
    table=soup.select_one('table.items')
    if table is None:
        raise ValueError('Transfermarkt items table absent')
    rows=[]
    for tr in table.select('tbody > tr.odd, tbody > tr.even'):
        link=tr.find('a',href=re.compile(r'/profil/spieler/\d+'))
        if not link:
            continue
        cells=tr.find_all('td',recursive=False)
        value=tr.select_one('td.rechts.hauptlink')
        club=tr.find('a',href=re.compile(r'/startseite/verein/'))
        inline=tr.select_one('table.inline-table')
        position=inline.select('tr')[-1].get_text(' ',strip=True) if inline else None
        rows.append(dict(source_player_id=link['href'].split('/spieler/')[1].split('/')[0],
            player=link.get_text(strip=True),profile_path=link['href'],pos=position,
            team=club.get('title') if club else None,
            age=pd.to_numeric(cells[3].get_text(strip=True),errors='coerce') if len(cells)>3 else None,
            market_value_eur=money_eur(value.get_text(' ',strip=True)) if value else None,
            currency='EUR',valuation_date=None, temporal_scope='current_snapshot_not_historical'))
    if not rows:
        raise ValueError('No market rows')
    return pd.DataFrame(rows).drop_duplicates('source_player_id')


def profile(html):
    soup=BeautifulSoup(html,'lxml')
    info={}
    for label in soup.select('.info-table__content--label, .info-table__content--regular'):
        value=label.find_next_sibling('span')
        if not value:
            continue
        key=label.get_text(' ',strip=True).lower()
        text=value.get_text(' ',strip=True)
        if 'date of birth' in key:
            date=re.sub(r'\s*\(\d+\)\s*$', '',text)
            parsed=pd.to_datetime(date,dayfirst=True,errors='coerce')
            info['date_of_birth']=parsed.date().isoformat() if pd.notna(parsed) else None
        elif 'height' in key:
            m=re.fullmatch(r'(\d[,.]\d{2})\s*m',text)
            info['height_cm']=float(m[1].replace(',','.'))*100 if m else None
        elif key in {'position:', 'foot:', 'citizenship:'}:
            info[key.rstrip(':').replace('citizenship','nation')]=text
    if not info:
        raise ValueError('No supported profile fields parsed')
    return info
