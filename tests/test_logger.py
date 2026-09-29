"""控制台日志初始化与宿主日志配置兼容性测试。"""

import io
import logging
import unittest
from unittest.mock import patch

from decision_models.logger import configure_logging


class LoggerTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.Logger('decision_models')
        self.output = io.StringIO()
        self.lookup = patch(
            'decision_models.logger.logging.getLogger',
            return_value=self.logger,
        )
        self.lookup.start()
        self.addCleanup(self.lookup.stop)
        self.stdout = patch('decision_models.logger.sys.stdout', self.output)
        self.stdout.start()
        self.addCleanup(self.stdout.stop)

    def test_repeated_configuration_emits_each_message_once(self):
        configure_logging()
        configure_logging()
        self.logger.info('样本完成')
        self.assertEqual(len(self.logger.handlers), 1)
        self.assertEqual(self.output.getvalue().count('样本完成'), 1)
        self.assertIn('INFO decision_models:', self.output.getvalue())

    def test_existing_handler_and_level_are_preserved(self):
        handler = logging.StreamHandler(self.output)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        configure_logging()
        self.assertEqual(self.logger.handlers, [handler])
        self.assertEqual(self.logger.level, logging.DEBUG)
        self.assertTrue(self.logger.propagate)

    def test_root_handler_is_reused(self):
        root = logging.Logger('root')
        root.addHandler(logging.StreamHandler(self.output))
        self.logger.parent = root
        configure_logging()
        self.assertEqual(self.logger.handlers, [])
        self.logger.warning('只输出一次')
        self.assertEqual(self.output.getvalue().count('只输出一次'), 1)


if __name__ == '__main__':
    unittest.main()
