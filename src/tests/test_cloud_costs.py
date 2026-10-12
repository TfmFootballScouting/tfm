import pytest
from src.process.cloud_costs import estimate


def test_missing_rate_blocks_total():
    result=estimate([dict(quantity=730,usd_per_unit='',source_url='',price_date='',region='eu-west-1')])
    assert not result['complete'] and result['monthly_usd'] is None


def test_evidenced_units_and_exchange_direction():
    line=dict(quantity=10,usd_per_unit=2,source_url='https://aws.amazon.com/',price_date='2026-10-12',region='eu-west-1')
    result=estimate([line],usd_per_eur=1.25)
    assert result['monthly_usd']==20 and result['monthly_eur']==16
    with pytest.raises(ValueError):
        estimate([line],usd_per_eur=0)
