"""Regression checks for the desktop chat layout (requires a desktop session)."""
import unittest
from app import FAQChatApp


class ChatLayoutTests(unittest.TestCase):
    def setUp(self):
        self.app = FAQChatApp()
        self.app.update()

    def tearDown(self):
        self.app.destroy()

    def test_last_reply_visible_after_resize(self):
        for _ in range(14):
            self.app.history.extend([
                ('user', 'Where should I upload my project?'),
                ('bot', 'Upload your complete source code to GitHub. ' * 8),
            ])
        for geometry in ('1180x820', '760x600', '1500x900'):
            with self.subTest(geometry=geometry):
                self.app.geometry(geometry)
                self.app.update()
                self.app._render()
                self.app.update()
                self.assertLessEqual(self.app.message_bounds[-1][3],
                                     self.app.canvas.canvasy(self.app.canvas.winfo_height()))
                self.assertGreater(self.app.canvas.yview()[1], .99)
                self.app._wheel_units(-10)
                self.assertFalse(self.app.follow_bottom)
                self.app.follow_bottom = True

    def test_short_messages_fit_text_and_reset_returns_home(self):
        self.app.history = [('user', '?'), ('bot', 'Please type a question.')]
        self.app._render()
        self.app.update()
        self.assertLess(self.app.message_bounds[0][2] - self.app.message_bounds[0][0], 60)
        self.app._reset()
        self.app.update()
        self.assertFalse(self.app.history)
        self.assertFalse(self.app.message_bounds)


if __name__ == '__main__':
    unittest.main()
