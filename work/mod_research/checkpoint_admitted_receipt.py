"""Strict diagnostic classification; never a game load or world permission.

The private runtime client verifies process birth and transport binding first.
This second boundary checks that an internally contradictory partial result
cannot become IDENTITY_RESTORED or WAITING_WORLD in the network room.
"""


class ReceiptRejected(ValueError):
    pass


def require(value, message):
    if not value:
        raise ReceiptRejected(message)


def classify(row, *, binding, fixture_case, archive_sha256, archive_size):
    require(type(row) is dict and type(binding) is dict, 'Object evidence required')
    require(fixture_case in ('success-new', 'report-state', 'entry-pending', 'late-pending'),
            'Unsupported integrated case')
    require(row.get('schema') == 'san14.admitted-runtime-fixture.v1' and
            row.get('provenance') == 'FIXTURE_ONLY' and row.get('fixture_case') == fixture_case,
            'Unexpected evidence source')
    require(binding and all(row.get(k) == v for k, v in binding.items()), 'Load binding differs')
    require(row.get('fixture_checks_passed') is True and row.get('native_binding_matches') is True and
            row.get('admission_wired') is True and row.get('fixed_archive_only') is True and
            row.get('consumed_world_source') == 'verified_workspace_stage', 'Missing runtime evidence')
    require(all(row.get(k) is False for k in ('fullWorldVerified', 'inputExclusionProven',
        'pixelPresentationProven', 'native_gameplay_enabled', 'game_access',
        'native_game_code_executed', 'upstream_receipts_fabricated')), 'Unsupported authority claim')

    def number(key, expected):
        require(type(row.get(key)) is int and row[key] == expected, 'Unexpected counter: ' + key)

    for key in ('fixture_failures', 'session_exception', 'session_active_dispatch',
                'session_active_worker', 'session_active_read', 'dispatch_unpaired',
                'admission_original_abnormal', 'admission_reentry', 'planning_inflight'):
        number(key, 0)
    number('armed', 1)
    number('admission_scope_started', 1)
    number('admission_scope_finished', 1)
    number('old_user_calls', 1)
    number('user_controller_calls', 1)
    require(row.get('admission_prefetched') is True, 'Original never reached the observed input fetch')

    if fixture_case in ('entry-pending', 'late-pending'):
        require(row.get('admission_blocked') is True and row.get('admission_eligible') is False,
                'Player input did not reject load admission')
        require(type(row.get('admission_error')) is int and row['admission_error'] != 0,
                'Rejection lacks a reason')
        for key in ('admission_queue_authorizations', 'admission_queue_calls',
                    'admission_queue_returned', 'admission_commit_succeeded', 'admission_menu_bound',
                    'cas_attempts', 'cas_published', 'bytesReady', 'lifecycleReady', 'identityReady',
                    'planningBoundaryObserved', 'actual_archive_read_bytes', 'new_user_calls',
                    'planning_before', 'planning_after'):
            number(key, 0)
        outcome = 'ADMISSION_REJECTED'
    else:
        require(row.get('admission_blocked') is False and row.get('admission_eligible') is True,
                'Loaded result lacks successful input admission')
        for key in ('session_error', 'admission_error'):
            number(key, 0)
        for key in ('admission_queue_authorizations', 'admission_queue_calls',
                    'admission_queue_returned', 'admission_commit_succeeded', 'admission_menu_bound',
                    'cas_attempts', 'cas_published', 'bytesReady', 'lifecycleReady', 'identityReady',
                    'new_user_calls', 'planning_before', 'planning_after'):
            number(key, 1)
        number('actual_archive_read_bytes', archive_size)
        number('identity_force', 2)
        number('identity_ruler', 952)
        require(row.get('actual_archive_read_sha256') == archive_sha256 and
                row.get('request_intent_durable') is True, 'Wrong bytes or undurable request')
        number('planningBoundaryObserved', int(fixture_case == 'success-new'))
        if fixture_case == 'success-new':
            number('planning_error', 0)
            require(row.get('planning_upstream_links_match') is True,
                    'Planning observation is not linked to this load')
        outcome = 'WAITING_WORLD' if fixture_case == 'success-new' else 'WAITING_PLANNING'
    return dict(outcome=outcome, source='OWNED_PROCESS_DIAGNOSTIC',
                full_world_verified=False, native_gameplay_enabled=False,
                release_input=False, reveal_map=False, grants_permission=False)
