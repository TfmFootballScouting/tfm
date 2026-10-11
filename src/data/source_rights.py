"""Enforce the observed Transfermarkt use restriction, pending a reviewed licence.

Keeping previously acquired files is evidence preservation, not permission to
collect more data, train models, or redistribute provider content.
"""
TERMS_URL = 'https://www.transfermarkt.com/intern/anb'
TERMS_SHA256 = '7c46c0514a311f4bbb6af63b08c9be1d2011be06c22ceb8c30b4bed0cc3927d3'
RESTRICTED = 'restricted_pending_explicit_license'


class SourceUseRestricted(ValueError):
    pass


def require_source_use(source, purpose):
    if 'transfermarkt' in str(source).lower():
        raise SourceUseRestricted(
            f'Transfermarkt {purpose} blocked: terms section 11.1 prohibits '
            f'automated copying and AI/ML use. A reviewed provider licence is '
            f'required; user confirmation alone does not grant it. See {TERMS_URL}'
        )


def require_model_data_use(players):
    """Check retained source labels and explicit restrictions before fitting."""
    for column in ('source', 'original_source', 'valuation_source', 'mapping_source'):
        if column in players:
            for source in players[column].dropna().unique():
                require_source_use(source, 'model use')
    if 'ml_use_status' in players and players.ml_use_status.eq(RESTRICTED).any():
        raise SourceUseRestricted('Dataset is restricted pending an explicit licence')
