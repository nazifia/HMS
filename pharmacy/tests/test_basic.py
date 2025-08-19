from django.test import TestCase

class PharmacyBasicTest(TestCase):
    def test_basic_setup(self):
        """Test that the basic setup is working"""
        self.assertEqual(1, 1)