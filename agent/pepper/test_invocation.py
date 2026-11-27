"""The owner calls the agent from any internal conversation by tagging the control channel in a message he typed.
The order is answered in that conversation; nobody else can call it that way."""
import unittest

from lib import conversations
from lib.settings import CONFIG, OWNER

CONTROL = CONFIG["control_channel_id"]
TAG = f"<#{CONTROL}|control>"


def message(text, user=OWNER, channel="C0OTHER1", ts="1795800000.000100", thread_ts="1795799000.000100"):
    return {"channel": channel, "user": user, "ts": ts, "thread_ts": thread_ts, "text": text, "bot": False,
            "permalink": f"https://example.slack.com/archives/{channel}/p{ts.replace('.', '')}", "sources": ["mine"]}


class CalledFromAnotherConversation(unittest.TestCase):
    def test_owner_tagging_the_channel_is_an_order(self):
        for tag in (TAG, f"<#{CONTROL}>"):
            self.assertEqual(1, len(conversations.control_messages([message(f"{tag} revisa esses PRs")], set())), tag)

    def test_others_and_untagged_messages_are_not(self):
        for m in (message(f"{TAG} revisa esses PRs", user="U0SOMEONE1"), message("revisa esses PRs"),
                  message(f"{TAG} já vi", ts="1"), message(f"<#C0OTHER2|random> revisa")):
            seen = {f"{m['channel']}:1"}
            self.assertEqual([], conversations.control_messages([m], seen), m["text"])

    def test_control_channel_orders_still_count(self):
        self.assertEqual(1, len(conversations.control_messages([message("status?", channel=CONTROL, thread_ts="")], set())))

    def test_prompt_answers_there_without_the_tag(self):
        prompt = conversations.prompt_for({"kind": "order", "message": message(f"{TAG} revisa esses PRs"), "question": None})
        self.assertIn("Answer in that thread", prompt)
        self.assertIn("thread_ts 1795799000.000100", prompt)
        self.assertNotIn(CONTROL, prompt.split("His words", 1)[1])

    def test_a_question_record_never_matches_an_outside_thread(self):
        state = {"talk_queue": [], "questions": {"1795799000.000100": {"origin_channel": "X"}}, "bot_replies": {}}
        conversations.plan(state, [message(f"{TAG} revisa")], [], lambda _: None)
        self.assertEqual("order", state["talk_queue"][0]["kind"])


if __name__ == "__main__":
    unittest.main()
