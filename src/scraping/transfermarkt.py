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


def scorer_sample(html, season):
    """Parse the already retained Segunda sample offline; never fetch a page.

    A goalscorer leaderboard is not a complete player universe or verified club
    stint. Age(today) and a dash in a numeric cell are not historical facts/zeros.
    """
    soup = BeautifulSoup(html, 'lxml')
    year = int(season[:4])
    label = f'{year % 100:02d}/{(year+1) % 100:02d}'
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    selected = soup.select_one('select[name=saison_id] option[selected]')
    if 'LaLiga2' not in title or label not in title or selected is None or selected.get('value') != str(year):
        raise ValueError('Retained scorer response does not confirm the requested Segunda season')
    table = soup.select_one('table.items')
    if table is None:
        raise ValueError('Scorer items table missing')
    labels = []
    for th in table.select('thead th'):
        icon = th.select_one('[title]')
        labels.append(th.get_text(' ', strip=True) or (icon.get('title') if icon else ''))
    needed = ['Player','Club','Appearances','Assists','Minutes played','Goals']
    if not all(label in labels for label in needed):
        raise ValueError('Scorer header schema changed; do not parse columns by guess')
    def number(text):
        text = text.strip().rstrip("'")
        if not re.fullmatch(r'\d+(?:\.\d{3})*', text):
            return None
        return int(text.replace('.', ''))
    rows = []
    for tr in table.select(':scope > tbody > tr'):
        cells = tr.find_all('td', recursive=False)
        if len(cells) != len(labels):
            continue
        player_cell, club_cell = cells[labels.index('Player')], cells[labels.index('Club')]
        link = player_cell.find('a', href=re.compile(r'/profil/spieler/\d+'))
        if not link:
            continue
        club = club_cell.find('a', href=re.compile(r'/startseite/verein/'))
        inline = player_cell.select_one('table.inline-table')
        position = inline.select('tr')[-1].get_text(' ',strip=True) if inline else None
        rows.append(dict(source_player_id=re.search(r'/spieler/(\d+)',link['href'])[1],
            player=link.get_text(strip=True),team=club.get('title') if club else None,
            pos_source=position,league='Segunda',season=season,source='transfermarkt',
            mp=number(cells[labels.index('Appearances')].get_text(strip=True)),
            ast=number(cells[labels.index('Assists')].get_text(strip=True)),
            minutes=number(cells[labels.index('Minutes played')].get_text(strip=True)),
            gls=number(cells[labels.index('Goals')].get_text(strip=True)),
            age_reported_text=cells[labels.index('Age (today)')].get_text(' ',strip=True) if 'Age (today)' in labels else None,
            observation_scope='first-page goalscorer league-season totals; reported club is not a verified stint',
            ml_use_status='restricted_pending_explicit_license'))
    result = pd.DataFrame(rows)
    if result.empty or result.source_player_id.duplicated().any():
        raise ValueError('Missing or duplicate scorer player IDs')
    return result
