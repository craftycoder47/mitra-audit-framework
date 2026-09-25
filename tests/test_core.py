import unittest

from mitra_audit import AuditState, audit_payload, theoretical_margin_pct


BASE = {
    "same_event": True,
    "same_rules": True,
    "best_outcome_odds": {"A": 2.2, "B": 3.6, "C": 4.8},
    "source_span_s": 5.0,
    "max_stale_s": 12.0,
    "hard_stale_s": 60.0,
    "stakeability": {
        "quotes_available": True,
        "acceptance_verified": None,
        "capacity_verified": None,
    },
    "costs": {"known": True, "extra_cost_pct": 0.0},
    "db": {"record_present": True, "formula_match": True},
}


class TestEconomics(unittest.TestCase):
    def test_margin_formula(self):
        result = theoretical_margin_pct({"A": 2.2, "B": 3.6, "C": 4.8})
        self.assertAlmostEqual(result, 6.308725, places=5)

    def test_invalid_odds_fail(self):
        with self.assertRaises(ValueError):
            theoretical_margin_pct({"A": 1.0, "B": 2.0})


class TestFailClosedAudit(unittest.TestCase):
    def test_good_timing_is_still_partial_without_executability_proof(self):
        result = audit_payload(BASE)
        self.assertEqual(result.stages["SYNC"].state, AuditState.PARTIAL)
        self.assertEqual(result.stages["STAKEABILITY"].state, AuditState.PARTIAL)
        self.assertEqual(result.overall, AuditState.PARTIAL)

    def test_event_mismatch_fails(self):
        payload = dict(BASE, same_event=False)
        result = audit_payload(payload)
        self.assertEqual(result.stages["REAL"].state, AuditState.FAILED)
        self.assertEqual(result.overall, AuditState.FAILED)

    def test_hard_staleness_fails(self):
        payload = dict(BASE, max_stale_s=61.0)
        result = audit_payload(payload)
        self.assertEqual(result.stages["SYNC"].state, AuditState.FAILED)
        self.assertEqual(result.overall, AuditState.FAILED)

    def test_missing_timestamps_are_unproven(self):
        payload = dict(BASE)
        payload.pop("source_span_s")
        result = audit_payload(payload)
        self.assertEqual(result.stages["SYNC"].state, AuditState.UNPROVEN)
        self.assertEqual(result.overall, AuditState.UNPROVEN)

    def test_db_disagreement_fails(self):
        payload = dict(BASE, db={"record_present": True, "formula_match": False})
        result = audit_payload(payload)
        self.assertEqual(result.stages["DB"].state, AuditState.FAILED)

    def test_full_evidence_can_pass_except_sync_conservatism(self):
        payload = dict(
            BASE,
            stakeability={
                "quotes_available": True,
                "acceptance_verified": True,
                "capacity_verified": True,
            },
        )
        result = audit_payload(payload)
        self.assertEqual(result.stages["STAKEABILITY"].state, AuditState.PASS)
        self.assertEqual(result.overall, AuditState.PARTIAL)


if __name__ == "__main__":
    unittest.main()
