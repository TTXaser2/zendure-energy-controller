"""Historical V17.0.2 Fast Capture evidence remains readable after V17.1.1."""
from tools.fast_capture_field_analysis import _config_version_evidence, describe_contract


def test_analyzer_reports_new_version_to_v17_1_1_field_acceptance():
    assert describe_contract()['expected_controller_version']=='17.1.2'


def test_analyzer_accepts_new_and_historical_v17_evidence_only():
    for version in ('17.0.2', '17.1.0', '17.1.1', '17.1.2'):
        res=_config_version_evidence([{'config_control_hash':'h'}],
                    {'snapshots':[{'config_control_hash':'h','controller_version':version}]})
        assert res['status']=='PASS'
    res=_config_version_evidence([{'config_control_hash':'h'}],
                {'snapshots':[{'config_control_hash':'h','controller_version':'16.2.5'}]})
    assert res['status']=='FAIL'
