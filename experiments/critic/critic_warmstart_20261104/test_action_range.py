import pytest
from action_range import paired,passes,plan


def test_ladder_is_ordered_and_confirmation_families_are_separate():
    p=plan()
    assert p['action_limits']==sorted(set(p['action_limits']))
    assert not set(p['development_seeds'])&set(p['confirmation_seeds'])
    assert not set(p['development_seeds']+p['confirmation_seeds'])&set(range(2026111600,2026111650))


def test_paired_counts_do_not_cancel_losses_and_check_initial_states():
    base=[dict(success=True,initial_sha256='a'),dict(success=False,initial_sha256='b')]
    current=[dict(success=False,initial_sha256='a'),dict(success=True,initial_sha256='b')]
    r=paired(base,current)
    assert r['paired_losses']==r['paired_wins']==1
    with pytest.raises(AssertionError):paired(base,current[::-1])


def test_ladder_rejects_aggregate_loss_despite_per_parent_tolerance():
    r=dict(paired_losses=1,drift=dict(finite=True,max_abs_action_delta=.05))
    rows={str(s):dict(r) for s in (1,2,3)}
    assert not passes(rows,plan()['gate'],.05)
    rows['1']['paired_losses']=rows['2']['paired_losses']=0
    assert passes(rows,plan()['gate'],.05)
    assert not passes(rows,plan()['gate'],.02)


def test_expanded_pilot_is_blocked_without_confirmation(tmp_path):
    from prepare_range_pilot import prepare
    folder=tmp_path/'range';folder.mkdir()
    (folder/'decision.json').write_text('{"confirmed":false,"next_test_ready":false}')
    with pytest.raises(AssertionError,match='confirmation did not pass'):
        prepare(tmp_path/'source',folder,tmp_path/'output')
    assert not (tmp_path/'output').exists()
