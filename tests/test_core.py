"""作者：Wangyuan；日期：2026-10-29；职责：仅以从零合成输入验证核心与异常路径。"""

import unittest
from monitor import *
class MonitorTests(unittest.TestCase):
    def test_quantile_zero_weight_and_decimal_boundary(self):
        self.assertEqual(weighted_quantile([0,1,2],[0,1,9],0),1)
        self.assertEqual(weighted_quantile([1,2],[1,9],0.1),1)
        for weights in [[0,0],[-1,2],[float('nan'),1]]:
            with self.assertRaises(ValueError): weighted_quantile([1,2],weights,0.5)
    def test_distribution_filters_future_and_reports_missing(self):
        samples=[{'timestamp':'2030-01-01T10:00:00+00:00','duration':20},{'timestamp':'2030-01-03T10:00:00+00:00','duration':900}]
        result=distribution(samples,'2030-01-04T10:00:00+00:00',half_life_days=10,levels=[{'minimum_samples':1,'same_month':True,'hour_radius':1}],probabilities=[0.5],cutoff='2030-01-02T00:00:00+00:00')
        self.assertEqual(result['quantiles']['0.5'],20); self.assertEqual(result['samples'],1)
        result=distribution([], '2030-01-04T00:00:00+00:00',half_life_days=10,levels=[{'minimum_samples':1}],probabilities=[0.5],cutoff='2030-01-02T00:00:00+00:00')
        self.assertEqual(result['status'],'missing'); self.assertIsNone(result['quantiles'])
    def test_three_state_bounds_and_large_integers(self):
        self.assertEqual(interval_truth(2,2,10,30),'unknown'); self.assertEqual(interval_truth(3,0,10,30),'true'); self.assertEqual(interval_truth(2,0,10,30),'false')
        self.assertEqual(interval_truth(0,0,0,30),'not_applicable'); self.assertEqual(interval_truth(10**30,0,10**31,10),'true')
        with self.assertRaises(ValueError): interval_truth(True,0,10,30)
    def test_tiers_keep_possible_distinct(self):
        result=tier_bounds([{'id':'low','branches':['true']},{'id':'high','branches':['unknown','false']}])
        self.assertEqual(result,{'proven':'low','possible':'high','requires_review':True})
    def test_milestones_missing_overdue_and_total(self):
        result=monitor_milestones([{'id':'a','observed_at':'2030-01-01T12:00:00+00:00','planned_at':'2030-01-01T11:00:00+00:00','actual_at':None}],['a','b'],'2030-01-01T12:00:00+00:00',max_age_seconds=1)
        self.assertEqual(result['counts'],{'missing':1,'overdue':1}); self.assertEqual(sum(result['counts'].values()),result['total'])
        self.assertTrue(all(x['deviation_seconds'] is None for x in result['items']))
    def test_escalation_once_monotonic_and_unknown_block(self):
        first=escalate(0,[],21,[10,20],source_ready=True); self.assertEqual(first['new_levels'],[1,2])
        second=escalate(2,[1,2],5,[10,20],source_ready=True); self.assertEqual(second['level'],2); self.assertEqual(second['new_levels'],[])
        self.assertEqual(escalate(0,[],None,[10],source_ready=False)['state'],'blocked')
    def test_chain_propagation_and_missing(self):
        rows=[{'id':'a','asset':'r','start':'2030-01-01T10:00:00+00:00','end':'2030-01-01T11:00:00+00:00','delay_seconds':600},{'id':'b','asset':'r','start':'2030-01-01T11:05:00+00:00','end':'2030-01-01T12:00:00+00:00','delay_seconds':0}]
        result=chain_windows(rows,'2030-01-01T00:00:00+00:00','2030-01-02T00:00:00+00:00'); self.assertEqual(result['chains']['r'][1]['projected_delay_seconds'],300)
        rows[0]['delay_seconds']=None; self.assertIsNone(chain_windows(rows,'2030-01-01T00:00:00+00:00','2030-01-02T00:00:00+00:00')['chains']['r'][1]['projected_delay_seconds'])
    def test_chain_carries_pre_window_evidence(self):
        rows=[{'id':'a','asset':'r','start':'2030-01-01T10:00:00+00:00','end':'2030-01-01T11:00:00+00:00','delay_seconds':600},{'id':'b','asset':'r','start':'2030-01-01T11:05:00+00:00','end':'2030-01-01T12:00:00+00:00','delay_seconds':0}]
        result=chain_windows(rows,'2030-01-01T11:01:00+00:00','2030-01-02T00:00:00+00:00')['chains']['r']
        self.assertEqual(len(result),1); self.assertEqual(result[0]['projected_delay_seconds'],300)
    def test_plan_duplicates_and_version_changes(self):
        result=compare_plan([{'id':'a','value':1}],[{'id':'a','value':2}],['id']); self.assertEqual(len(result['changed']),1)
        with self.assertRaises(ValueError): compare_plan([], [{'id':'a'},{'id':'a'}],['id'])
    def test_affected_window_half_open_and_location(self):
        windows=[{'id':'w','location':'place-A','start':'2030-01-01T23:00:00+00:00','end':'2030-01-02T01:00:00+00:00','value':5}]
        events=[{'id':'yes','location':'place-A','timestamp':'2030-01-02T00:00:00+00:00'},{'id':'no','location':'place-A','timestamp':'2030-01-02T01:00:00+00:00'}]
        self.assertEqual(affected_events(windows,events,3)['matches'][0]['event'],'yes'); self.assertEqual(len(affected_events(windows,events,3)['matches']),1)

if __name__ == "__main__":
    unittest.main()
