"""The agent must recognise its own messages in the shape the Slack connector returns them, so a notice it posted in
the control channel never comes back as an order from the owner (2026-11-26: 318 of 685 order runs were the agent
answering itself)."""
import json
import unittest

from lib import slack
from lib.conversations import is_pepper
from lib.settings import CONFIG

CLAUDE = CONFIG["claude_app_user_id"]
NAME = CONFIG["agent_name"]
# Shape of a control-channel thread as slack_read_thread returned it (2026-11-26), with this install's name.
THREAD = json.dumps({"messages": (
    "=== THREAD PARENT MESSAGE ===\nFrom: Owner (U1)\nMessage TS: 1795645068.935329\n"
    f"> :robot_face: {NAME}: :twisted_rightwards_arrows: Seu PR web-api#451\n"
    f"> *O envio foi feito usando* <@{CLAUDE}|Claude>\n\n"
    "=== THREAD REPLIES (2 total) ===\n\n--- Reply 1 of 2 ---\nFrom: Owner (U1)\nMessage TS: 1795736246.066199\n"
    f"> :wing: {NAME}: :double_vertical_bar: web-api#451 aprovado, mas não mergeei: mergeStateStatus UNKNOWN\n"
    f"> *O envio foi feito usando* <@{CLAUDE}|Claude>\n"
    "--- Reply 2 of 2 ---\nFrom: Owner (U1)\nMessage TS: 1795736300.000001\n"
    f"> > :wing: {NAME}: Quer que eu mergeie?\n> sim\n")})


class OwnMessages(unittest.TestCase):
    def test_own_notice_is_pepper_in_connector_shape(self):
        self.assertTrue(is_pepper(f"> :robot_face: {NAME}: :double_vertical_bar: web-api#451 aprovado"))
        self.assertTrue(is_pepper(f"&gt; :wing: {NAME}: x"))
        self.assertTrue(is_pepper(CONFIG["prefix"] + " x"))

    def test_owner_quoting_the_agent_or_naming_it_is_not_pepper(self):
        self.assertFalse(is_pepper(f"> > :wing: {NAME}: Quer que eu mergeie?\n> sim"))
        self.assertFalse(is_pepper("> sim, pode mergear"))
        self.assertFalse(is_pepper(f"> {NAME}: faz o deploy em dev"))

    def test_footer_found_in_connector_shape(self):
        flags = {m["ts"]: m["sent_using_claude"] for m in slack.parse_thread_messages(THREAD)}
        self.assertEqual(flags, {"1795645068.935329": True, "1795736246.066199": True, "1795736300.000001": False})


if __name__ == "__main__":
    unittest.main()
