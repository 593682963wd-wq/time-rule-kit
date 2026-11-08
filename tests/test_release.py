"""作者：Wangyuan；日期：2026-11-08。职责：通过合成输入复验已确认缺陷。"""
import unittest
from monitor import distribution,monitor_milestones,compare_plan
class ReleaseTests(unittest.TestCase):
 def test_old_samples_positive_normalized_weights(self) -> None:
  r=distribution([{'timestamp':'2020-01-01T00:00:00Z','duration':20}],'2030-01-01T00:00:00Z',half_life_days=1,levels=[{'minimum_samples':1}],probabilities=[.5],cutoff='2030-01-01T00:00:00Z')
  self.assertEqual(r['quantiles']['0.5'],20)
 def test_future_observation_never_yields_future_actual_delta(self) -> None:
  r=monitor_milestones([{'id':'a','planned_at':'2030-01-01T00:00:00Z','observed_at':'2030-01-02T01:00:00Z','actual_at':'2030-01-02T01:00:00Z'}],['a'],'2030-01-01T01:00:00Z',max_age_seconds=3600)
  self.assertEqual(r['items'][0]['state'],'future_observation');self.assertIsNone(r['items'][0]['deviation_seconds'])
 def test_bool_not_number(self) -> None:self.assertEqual(len(compare_plan([{'id':'a','enabled':True}],[{'id':'a','enabled':1}],['id'])['changed']),1)
