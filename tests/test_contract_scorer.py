import copy
import unittest

from brickbench.contract import EPSILON, apply_actions, assembly
from brickbench.scorer import maximum_matching, score


def piece(id="a", x=0, y=0, z=0, yaw=0, part="brick-1x2", color="red"):
    return {"id": id, "part": part, "color": color, "position_mm": [x, y, z], "yaw_deg": yaw}


class ScorerTests(unittest.TestCase):
    def setUp(self):
        self.reference = [piece(), piece("b", x=24)]

    def test_exact_ignores_order_and_ids(self):
        self.assertTrue(score([piece("other", x=24), piece("another")], self.reference)["exact_geometry"])

    def test_duplicate_every_piece_penalized(self):
        prediction = self.reference + [piece("c"), piece("d", x=24)]
        result = score(prediction, self.reference)
        self.assertEqual(result["pose"]["precision"], .5)
        self.assertEqual(result["pose"]["recall"], 1)
        self.assertAlmostEqual(result["pose"]["f1"], 2/3)
        self.assertAlmostEqual(result["inventory"]["f1"], 2/3)
        self.assertFalse(result["exact_geometry"])

    def test_small_errors_are_not_snapped(self):
        for p in [piece(x=4), piece(z=3.2), piece(yaw=90), piece(color="blue"), piece(part="brick-1x1")]:
            with self.subTest(p=p):
                self.assertEqual(score([p], [piece()])["pose"]["f1"], 0)

    def test_inventory_and_pose_are_separate(self):
        result = score([piece(x=4)], [piece()])
        self.assertEqual(result["inventory"]["f1"], 1)
        self.assertEqual(result["pose"]["f1"], 0)

    def test_epsilon_only_for_numeric_noise(self):
        self.assertTrue(score([piece(x=EPSILON/2)], [piece()])["exact_geometry"])
        self.assertFalse(score([piece(x=EPSILON*2)], [piece()])["exact_geometry"])

    def test_declared_symmetries(self):
        self.assertTrue(score([piece(yaw=180)], [piece()])["exact_geometry"])
        self.assertTrue(score([piece(part="brick-2x2", yaw=90)], [piece(part="brick-2x2")])["exact_geometry"])

    def test_missing_and_empty(self):
        self.assertAlmostEqual(score([piece()], self.reference)["pose"]["f1"], 2/3)
        self.assertEqual(score([], self.reference)["pose"]["f1"], 0)
        self.assertEqual(score([], [])["pose"]["f1"], 1)
        self.assertFalse(score([piece()], [])["exact_geometry"])

    def test_maximum_matching_does_not_use_greedy_first_hit(self):
        self.assertEqual(maximum_matching([[0, 1], [0]], 2), 2)
        # Both predictions can reach r0; only p0 can reach r1 within epsilon.
        result = score([piece(x=.5*EPSILON), piece("b", x=-.5*EPSILON)],
                       [piece(), piece("b", x=1.4*EPSILON)])
        self.assertEqual(result["pose"]["matched"], 2)

    def test_fixed_frame_and_mirror_not_aligned(self):
        ref = [piece("a", x=8, color="red"), piece("b", y=8, color="blue")]
        self.assertFalse(score([piece("a", x=-8, color="red"), piece("b", y=8, color="blue")], ref)["exact_geometry"])

    def test_physical_truth_never_inferred_from_reference_match(self):
        floating = [piece(z=100)]
        result = score(floating, floating)
        self.assertTrue(result["exact_geometry"])
        self.assertEqual(set(result["physical_checks"].values()), {"unknown"})


class ContractTests(unittest.TestCase):
    def test_reject_malformed_placements(self):
        for patch in [{"position_mm": [float("nan"),0,0]}, {"position_mm": [float("inf"),0,0]},
                      {"position_mm": [True,0,0]}, {"yaw_deg": 45}, {"yaw_deg": True},
                      {"rotation": [-1,0,0,0,1,0,0,0,1]}, {"part": "unknown"}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                assembly([{**piece(), **patch}])
        with self.assertRaises(ValueError):
            assembly([piece(), piece()])

    def test_actions_and_atomic_failure(self):
        seed = [piece()]
        before = copy.deepcopy(seed)
        moved = apply_actions(seed, {"actions": [{"op":"move", "id":"a", "position_mm":[8,0,0], "yaw_deg":90}]}, 3)
        self.assertEqual(moved[0]["position_mm"], [8,0,0])
        self.assertEqual(seed, before)
        with self.assertRaises(ValueError):
            apply_actions(seed, {"actions": [{"op":"remove", "id":"a"}, {"op":"remove", "id":"a"}]}, 3)
        self.assertEqual(seed, before)
        self.assertEqual(apply_actions(seed, {"actions": [{"op":"remove", "id":"a"}]}, 1), [])

    def test_budget_and_duplicate_id(self):
        for actions in [[{"op":"add", "piece":piece()}], [{"op":"remove", "id":"a"}]*2]:
            with self.assertRaises(ValueError):
                apply_actions([piece()], {"actions":actions}, 1)


if __name__ == "__main__":
    unittest.main()
