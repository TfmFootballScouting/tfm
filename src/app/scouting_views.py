"""Plain football labels and exploratory groups; never mutate trained artifacts."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

LABELS = {
    'player': 'Jugador', 'team': 'Equipo', 'league': 'Liga', 'season': 'Temporada',
    'pos': 'Posición', 'pos_main': 'Posición', 'age': 'Edad', 'minutes': 'Minutos',
    'affinity': 'Afinidad con el estilo', 'similarity': 'Similitud de perfil',
    'distance': 'Distancia de perfil', 'partial_season': 'Temporada incompleta',
    'gls': 'Goles', 'ast': 'Asistencias', 'gls_p90': 'Goles por 90 min',
    'ast_p90': 'Asistencias por 90 min', 'ga_p90': 'Goles + asistencias por 90 min',
    'sh_p90': 'Tiros por 90 min', 'sot_p90': 'Tiros a puerta por 90 min',
    'xg_p90': 'Goles esperados por 90 min', 'xag_p90': 'Asistencias esperadas por 90 min',
    'crs_p90': 'Centros por 90 min', 'int_p90': 'Intercepciones por 90 min',
    'tklw_p90': 'Entradas ganadas por 90 min', 'fld_p90': 'Faltas recibidas por 90 min',
    'fls_p90': 'Faltas cometidas por 90 min', 'crdy_p90': 'Amarillas por 90 min',
    'crdr_p90': 'Rojas por 90 min', 'group': 'Grupo',
    'reported_market_value_eur': 'Valor de mercado reportado (€)',
    'reported_valuation_date': 'Fecha de valoración', 'reported_value_source': 'Fuente del valor',
    'price_identity_status': 'Identidad pendiente de revisión',
    'reported_value_status': 'Disponibilidad del valor',
}
POSITIONS = {'DF': 'Defensa', 'MF': 'Centrocampista', 'FW': 'Delantero', 'GK': 'Portero', 'Todas': 'Todas'}


def field_label(name):
    return LABELS.get(name, name.replace('_', ' ').capitalize())


def display_frame(frame):
    result = frame.copy()
    for column in ['pos', 'pos_main']:
        if column in result:
            result[column] = result[column].map(lambda v: ', '.join(POSITIONS.get(p.strip(), p.strip()) for p in str(v).split(',')))
    if 'reported_market_value_eur' in result:
        result['reported_market_value_eur'] = result.reported_market_value_eur.where(result.reported_market_value_eur.gt(0))
    if 'price_identity_status' in result:
        result['price_identity_status'] = result.price_identity_status.map({
            'provisional_not_reviewed': 'Pendiente de revisión', 'unmatched': 'Sin asociación'})
    return result.rename(columns={c: field_label(c) for c in result})


def group_profiles(matrix, players, number):
    """Explore the selected observed pool with frozen training preprocessing."""
    matrix = np.asarray(matrix)
    if len(matrix) != len(players) or not 2 <= number <= min(len(players), len(np.unique(matrix, axis=0))):
        raise ValueError('Not enough distinct profiles for the requested groups')
    labels = KMeans(n_clusters=number, random_state=42, n_init=10).fit_predict(matrix)
    # Canonical labels by centroid ordering avoid arbitrary numbering between reruns.
    centers = [(int(label), tuple(matrix[labels == label].mean(axis=0))) for label in np.unique(labels)]
    mapping = {label: index + 1 for index, (label, _) in enumerate(sorted(centers, key=lambda item: item[1]))}
    result = players.copy()
    result['group'] = [mapping[int(label)] for label in labels]
    return result
