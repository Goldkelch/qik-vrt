class ActiveWriterHistoryIndependenceTests(unittest.TestCase):
    """Issue #1075: execute the real observer against a filtering API double."""

    WRITER = "QIK-VRT autonomous bounded self-heal"
    STATES = ("queued", "in_progress", "waiting", "requested", "pending")

    def row(self, identifier, *, head=HEAD_SHA, status="completed", name=None):
        return {
            "id": identifier, "head_sha": head, "status": status,
            "name": self.WRITER if name is None else name,
            "workflow_id": 41, "path": ".github/workflows/qikvrt_autonomous_self_heal.yml",
            "event": "push", "run_number": identifier, "run_attempt": 1,
        }

    def api(self, rows, calls):
        from urllib.parse import parse_qs, urlsplit

        def read(endpoint):
            calls.append(endpoint)
            parsed = urlsplit(endpoint)
            self.assertEqual(parsed.path, "repos/example/qik-vrt/actions/runs")
            query = parse_qs(parsed.query)
            self.assertEqual(set(query), {"head_sha", "status", "per_page", "page"})
            self.assertEqual(query["per_page"], ["100"])
            self.assertEqual(query["page"], ["1"])
            self.assertIn(query["head_sha"][0], {MAIN_SHA, HEAD_SHA})
            self.assertIn(query["status"][0], self.STATES)
            selected = [row for row in rows if
                        row["head_sha"] == query["head_sha"][0]
                        and row["status"] == query["status"][0]]
            return {"total_count": len(selected), "workflow_runs": copy.deepcopy(selected[:100])}

        return read

    def observe(self, read, heads=None):
        with mock.patch.object(MODULE, "_gh_one", side_effect=read), \
             mock.patch.object(MODULE.subprocess, "run", side_effect=AssertionError("history scan forbidden")):
            return MODULE._active_writer_observation(
                "example/qik-vrt", 999, {self.WRITER},
                {MAIN_SHA, HEAD_SHA} if heads is None else heads,
            )

    def test_more_than_100_completed_runs_do_not_hide_zero_active_writers(self):
        for count in (101, 250, 1001):
            with self.subTest(completed_per_head=count):
                history = [self.row(10000 + offset + index * count, head=head)
                           for index, head in enumerate((MAIN_SHA, HEAD_SHA))
                           for offset in range(count)]
                calls = []
                self.assertEqual(self.observe(self.api(history, calls)), [])
                self.assertEqual(len(calls), 10)
                self.assertEqual(len(set(calls)), 10)

    def test_old_active_writer_beyond_first_history_page_is_observed(self):
        for head in (MAIN_SHA, HEAD_SHA):
            for state in self.STATES:
                with self.subTest(head=head, state=state):
                    history = [self.row(10000 + offset, head=head) for offset in range(250)]
                    history.append(self.row(7, head=head, status=state))
                    self.assertNotIn(7, [row["id"] for row in history[:100]])
                    calls = []
                    observed = self.observe(self.api(history, calls))
                    self.assertEqual([row["id"] for row in observed], [7])
                    self.assertEqual(observed[0]["head_sha"], head)
                    self.assertEqual(observed[0]["status"], state)
                    self.assertEqual(len(calls), 10)

    def test_self_nonwriters_and_predecessor_heads_are_not_writer_evidence(self):
        rows = [self.row(999, status="queued"),
                self.row(8, status="pending", name="QIKVRT live status watch"),
                self.row(9, head="f" * 40, status="in_progress")]
        calls = []
        self.assertEqual(self.observe(self.api(rows, calls)), [])
        self.assertEqual(len(calls), 10)
        self.assertFalse(any("f" * 40 in call for call in calls))

    def test_identical_head_roles_are_read_once(self):
        calls = []
        self.assertEqual(self.observe(self.api([], calls), {MAIN_SHA}), [])
        self.assertEqual(len(calls), 5)

    def test_100_active_rows_are_complete_but_101_hold_without_pagination(self):
        for count in (100, 101):
            with self.subTest(active_count=count):
                rows = [self.row(10000 + offset, head=MAIN_SHA, status="queued")
                        for offset in range(count)]
                calls = []
                if count == 100:
                    self.assertEqual(len(self.observe(self.api(rows, calls))), 100)
                    self.assertEqual(len(calls), 10)
                else:
                    with self.assertRaisesRegex(MODULE.ReviewObservationError, "incomplete"):
                        self.observe(self.api(rows, calls))
                    self.assertEqual(len(calls), 1)

    def test_malformed_or_incomplete_projection_never_means_empty(self):
        projections = [None, [], {}, {"total_count": True, "workflow_runs": []},
                       {"total_count": -1, "workflow_runs": []},
                       {"total_count": "0", "workflow_runs": []},
                       {"total_count": 1, "workflow_runs": []},
                       {"total_count": 0, "workflow_runs": None},
                       {"total_count": 1, "workflow_runs": [None]},
                       {"total_count": 101, "workflow_runs": [self.row(7)] * 101}]
        for projection in projections:
            with self.subTest(projection=projection):
                with mock.patch.object(MODULE, "_gh_one", return_value=projection) as read:
                    with self.assertRaises(MODULE.ReviewObservationError):
                        MODULE._active_writer_observation("example/qik-vrt", 999, {self.WRITER}, {MAIN_SHA})
                    self.assertEqual(read.call_count, 1)

    def test_wrong_head_wrong_state_and_malformed_identity_fail_closed(self):
        valid = self.row(7, head=MAIN_SHA, status="queued")
        cases = [("head_sha", "f" * 40), ("status", "completed"),
                 ("status", "unknown"), ("id", True), ("id", 0),
                 ("id", "7"), ("name", None), ("name", "")]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                row = dict(valid, **{field: value})
                with mock.patch.object(MODULE, "_gh_one", return_value={
                    "total_count": 1, "workflow_runs": [row],
                }) as read:
                    with self.assertRaises(MODULE.ReviewObservationError):
                        MODULE._active_writer_observation("example/qik-vrt", 999, {self.WRITER}, {MAIN_SHA})
                    self.assertEqual(read.call_count, 1)

    def test_duplicate_run_does_not_fabricate_page_completeness(self):
        row = self.row(7, head=MAIN_SHA, status="queued")
        with mock.patch.object(MODULE, "_gh_one", return_value={
            "total_count": 2, "workflow_runs": [row, dict(row)],
        }) as read:
            with self.assertRaisesRegex(MODULE.ReviewObservationError, "duplicate"):
                MODULE._active_writer_observation("example/qik-vrt", 999, {self.WRITER}, {MAIN_SHA})
            self.assertEqual(read.call_count, 1)

    def test_cross_state_run_drift_is_indeterminate_not_silently_overwritten(self):
        replies = [{"total_count": 1, "workflow_runs": [self.row(7, head=MAIN_SHA, status=state)]}
                   for state in self.STATES[:2]]
        with mock.patch.object(MODULE, "_gh_one", side_effect=replies) as read:
            with self.assertRaisesRegex(MODULE.ReviewObservationError, "duplicate"):
                MODULE._active_writer_observation("example/qik-vrt", 999, {self.WRITER}, {MAIN_SHA})
            self.assertEqual(read.call_count, 2)

    def test_quota_and_api_failure_abort_without_retry_or_cached_positive_result(self):
        for status in (403, 429, 500):
            for failure_index in (0, 4, 9):
                with self.subTest(status=status, failure_index=failure_index):
                    replies = [{"total_count": 0, "workflow_runs": []} for _ in range(failure_index)]
                    failure = MODULE.ReviewObservationError(
                        f"API rate limit exceeded for installation. (HTTP {status})"
                    )
                    replies.append(failure)
                    with mock.patch.object(MODULE, "_gh_one", side_effect=replies) as read:
                        with self.assertRaises(MODULE.ReviewObservationError) as raised:
                            MODULE._active_writer_observation("example/qik-vrt", 999, {self.WRITER}, {MAIN_SHA, HEAD_SHA})
                        self.assertIs(raised.exception, failure)
                        self.assertEqual(read.call_count, failure_index + 1)

    def test_more_than_two_heads_is_rejected_before_io(self):
        with mock.patch.object(MODULE, "_gh_one") as read:
            with self.assertRaisesRegex(MODULE.ReviewObservationError, "relevant-head binding"):
                MODULE._active_writer_observation("example/qik-vrt", 999, {self.WRITER}, {MAIN_SHA, HEAD_SHA, "f" * 40})
            read.assert_not_called()
