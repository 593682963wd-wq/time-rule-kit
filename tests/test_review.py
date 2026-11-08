"""作者：Wangyuan；日期：2026-10-29。职责：未来完成时间不得判成已完成。"""
import unittest
from monitor import monitor_milestones


class ReviewTests(unittest.TestCase):
    def test_future_actual_not_completed(self):
        result = monitor_milestones([{'id': 'sample', 'planned_at': '2030-01-01T00:00:00Z', 'observed_at': '2030-01-01T01:00:00Z', 'actual_at': '2030-01-02T01:00:00Z'}], ['sample'], '2030-01-01T01:00:00Z', max_age_seconds=3600)
        self.assertEqual(result['items'][0]['state'], 'future_actual')
        self.assertIsNone(result['items'][0]['deviation_seconds'])


if __name__ == '__main__': unittest.main()
