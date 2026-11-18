import json
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from chatbot.views import build_chat_history


class ChatbotTestBase(TestCase):
    """Shared setup for chatbot API tests."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="chatuser",
            password="TestPassword123"
        )

        self.client.login(
            username="chatuser",
            password="TestPassword123"
        )

        self.chat_url = reverse("chatbot:chat")
        self.send_url = reverse("chatbot:send_message")
        self.clear_url = reverse("chatbot:clear_chat")

    def send_json(self, data):
        return self.client.post(
            self.send_url,
            data=json.dumps(data),
            content_type="application/json"
        )

    def read_stream(self, response):
        """Read the complete Server-Sent Event response."""
        content = b"".join(response.streaming_content)
        return content.decode("utf-8")


class ChatbotPageTests(ChatbotTestBase):
    """Tests for chatbot page."""

    def test_chat_page_requires_login(self):
        self.client.logout()

        response = self.client.get(self.chat_url)

        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_can_open_chat_page(self):
        response = self.client.get(self.chat_url)

        self.assertEqual(response.status_code, 200)

    def test_chat_page_uses_correct_template(self):
        response = self.client.get(self.chat_url)

        self.assertTemplateUsed(response, "chatbot/chat.html")


class ChatHistoryBuilderTests(TestCase):
    """Tests for converting frontend chat history."""

    def test_empty_history_returns_empty_list(self):
        result = build_chat_history([])

        self.assertEqual(result, [])

    def test_invalid_history_type_returns_empty_list(self):
        result = build_chat_history("invalid history")

        self.assertEqual(result, [])

    def test_non_dictionary_items_are_skipped(self):
        result = build_chat_history([
            "invalid",
            None,
            123
        ])

        self.assertEqual(result, [])

    def test_empty_messages_are_skipped(self):
        result = build_chat_history([
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "   "}
        ])

        self.assertEqual(result, [])

    def test_unknown_roles_are_skipped(self):
        result = build_chat_history([
            {"role": "system", "content": "Ignore this"},
            {"role": "unknown", "content": "Ignore this too"}
        ])

        self.assertEqual(result, [])

    def test_user_message_is_supported(self):
        result = build_chat_history([
            {"role": "user", "content": "Hello"}
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].role, "user")

    def test_assistant_role_is_converted_to_model(self):
        result = build_chat_history([
            {"role": "assistant", "content": "Hi"}
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].role, "model")

    def test_bot_role_is_converted_to_model(self):
        result = build_chat_history([
            {"role": "bot", "content": "Hi"}
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].role, "model")

    def test_model_role_is_supported(self):
        result = build_chat_history([
            {"role": "model", "content": "Hi"}
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].role, "model")

    def test_text_key_is_supported(self):
        result = build_chat_history([
            {"role": "user", "text": "Hello"}
        ])

        self.assertEqual(len(result), 1)

    def test_non_string_content_is_skipped(self):
        result = build_chat_history([
            {"role": "user", "content": 123}
        ])

        self.assertEqual(result, [])

    def test_only_latest_12_messages_are_used(self):
        history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(15)
        ]

        result = build_chat_history(history)

        self.assertEqual(len(result), 12)


class SendMessageValidationTests(ChatbotTestBase):
    """Tests for request validation."""

    def test_send_message_requires_login(self):
        self.client.logout()

        response = self.send_json({
            "message": "Hello"
        })

        self.assertEqual(response.status_code, 302)

    def test_get_request_is_rejected(self):
        response = self.client.get(self.send_url)

        self.assertEqual(response.status_code, 405)

    def test_invalid_json_is_rejected(self):
        response = self.client.post(
            self.send_url,
            data="{invalid json}",
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_json_array_is_rejected(self):
        response = self.client.post(
            self.send_url,
            data=json.dumps(["Hello"]),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_json_string_is_rejected(self):
        response = self.client.post(
            self.send_url,
            data=json.dumps("Hello"),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_message_is_rejected(self):
        response = self.send_json({})

        self.assertEqual(response.status_code, 400)

    def test_empty_message_is_rejected(self):
        response = self.send_json({
            "message": ""
        })

        self.assertEqual(response.status_code, 400)

    def test_whitespace_message_is_rejected(self):
        response = self.send_json({
            "message": "     "
        })

        self.assertEqual(response.status_code, 400)

    def test_non_string_message_is_rejected(self):
        response = self.send_json({
            "message": 123
        })

        self.assertEqual(response.status_code, 400)

    def test_message_over_4000_characters_is_rejected(self):
        response = self.send_json({
            "message": "a" * 4001
        })

        self.assertEqual(response.status_code, 400)

    def test_message_of_4000_characters_is_accepted(self):
        with patch("chatbot.views.client", None), \
             patch("chatbot.views.call_groq") as mock_groq, \
             patch("chatbot.views.call_openai") as mock_openai:

            mock_groq.return_value = {
                "choices": [{
                    "message": {
                        "content": "Valid response"
                    }
                }]
            }

            response = self.send_json({
                "message": "a" * 4000
            })

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.streaming)

            stream = self.read_stream(response)

            self.assertIn("Valid response", stream)
            self.assertIn('"type": "done"', stream)

            mock_groq.assert_called_once()
            mock_openai.assert_not_called()


class ChatbotAIProviderTests(ChatbotTestBase):
    """Tests for Gemini, Groq, OpenAI and fallback behavior."""

    def test_gemini_success(self):
        mock_client = MagicMock()

        mock_client.models.generate_content_stream.return_value = [
            SimpleNamespace(text="Hello "),
            SimpleNamespace(text="from Gemini!")
        ]

        with patch("chatbot.views.client", mock_client), \
             patch("chatbot.views.call_groq") as mock_groq, \
             patch("chatbot.views.call_openai") as mock_openai:

            response = self.send_json({
                "message": "Hello"
            })

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.streaming)

            stream = self.read_stream(response)

            self.assertIn("Hello ", stream)
            self.assertIn("from Gemini!", stream)
            self.assertIn('"type": "done"', stream)

            mock_groq.assert_not_called()
            mock_openai.assert_not_called()

    def test_groq_success_when_gemini_unavailable(self):
        with patch("chatbot.views.client", None), \
             patch("chatbot.views.call_groq") as mock_groq, \
             patch("chatbot.views.call_openai") as mock_openai:

            mock_groq.return_value = {
                "choices": [{
                    "message": {
                        "content": "Groq response"
                    }
                }]
            }

            response = self.send_json({
                "message": "Explain BMI"
            })

            self.assertEqual(response.status_code, 200)

            stream = self.read_stream(response)

            self.assertIn("Groq response", stream)
            self.assertIn('"type": "done"', stream)

            mock_groq.assert_called_once()
            mock_openai.assert_not_called()

    def test_openai_success_when_groq_fails(self):
        mock_openai_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="OpenAI response"
                    )
                )
            ]
        )

        with patch("chatbot.views.client", None), \
             patch("chatbot.views.call_groq") as mock_groq, \
             patch("chatbot.views.call_openai") as mock_openai:

            mock_groq.side_effect = Exception("Groq unavailable")
            mock_openai.return_value = mock_openai_response

            response = self.send_json({
                "message": "Explain Python"
            })

            self.assertEqual(response.status_code, 200)

            stream = self.read_stream(response)

            self.assertIn("OpenAI response", stream)
            self.assertIn('"type": "done"', stream)

            mock_groq.assert_called_once()
            mock_openai.assert_called_once()

    def test_all_ai_providers_fail(self):
        with patch("chatbot.views.client", None), \
             patch("chatbot.views.call_groq") as mock_groq, \
             patch("chatbot.views.call_openai") as mock_openai:

            mock_groq.side_effect = Exception("Groq failed")
            mock_openai.side_effect = Exception("OpenAI failed")

            response = self.send_json({
                "message": "Hello"
            })

            self.assertEqual(response.status_code, 200)

            stream = self.read_stream(response)

            self.assertIn('"type": "error"', stream)
            self.assertIn(
                "All AI services are currently unavailable",
                stream
            )

            mock_groq.assert_called_once()
            mock_openai.assert_called_once()

    def test_groq_empty_response_uses_openai(self):
        mock_openai_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="OpenAI backup response"
                    )
                )
            ]
        )

        with patch("chatbot.views.client", None), \
             patch("chatbot.views.call_groq") as mock_groq, \
             patch("chatbot.views.call_openai") as mock_openai:

            mock_groq.return_value = {
                "choices": [{
                    "message": {
                        "content": ""
                    }
                }]
            }

            mock_openai.return_value = mock_openai_response

            response = self.send_json({
                "message": "Help me"
            })

            stream = self.read_stream(response)

            self.assertIn("OpenAI backup response", stream)
            mock_openai.assert_called_once()

    def test_gemini_failure_uses_groq(self):
        mock_client = MagicMock()

        mock_client.models.generate_content_stream.side_effect = (
            Exception("Gemini unavailable")
        )

        with patch("chatbot.views.client", mock_client), \
             patch("chatbot.views.call_groq") as mock_groq, \
             patch("chatbot.views.call_openai") as mock_openai:

            mock_groq.return_value = {
                "choices": [{
                    "message": {
                        "content": "Groq fallback response"
                    }
                }]
            }

            response = self.send_json({
                "message": "Test fallback"
            })

            stream = self.read_stream(response)

            self.assertIn("Groq fallback response", stream)
            self.assertIn('"type": "done"', stream)

            mock_groq.assert_called_once()
            mock_openai.assert_not_called()

    def test_gemini_partial_response_then_failure_returns_error(self):
        mock_client = MagicMock()

        mock_client.models.generate_content_stream.return_value = iter([
            SimpleNamespace(text="Partial answer"),
            SimpleNamespace(
                text=None
            )
        ])

        # Simulate an error after the first streamed chunk.
        def stream_with_error():
            yield SimpleNamespace(text="Partial answer")
            raise Exception("Connection interrupted")

        mock_client.models.generate_content_stream.return_value = (
            stream_with_error()
        )

        with patch("chatbot.views.client", mock_client), \
             patch("chatbot.views.call_groq") as mock_groq, \
             patch("chatbot.views.call_openai") as mock_openai:

            response = self.send_json({
                "message": "Test interruption"
            })

            stream = self.read_stream(response)

            self.assertIn("Partial answer", stream)
            self.assertIn('"type": "error"', stream)
            self.assertIn("response was interrupted", stream)

            mock_groq.assert_not_called()
            mock_openai.assert_not_called()


class ChatHistoryRequestTests(ChatbotTestBase):
    """Tests for chat history supplied by the frontend."""

    def test_history_is_accepted(self):
        history = [
            {"role": "user", "content": "What is BMI?"},
            {"role": "assistant", "content": "BMI measures body mass."}
        ]

        with patch("chatbot.views.client", None), \
             patch("chatbot.views.call_groq") as mock_groq, \
             patch("chatbot.views.call_openai"):

            mock_groq.return_value = {
                "choices": [{
                    "message": {
                        "content": "BMI calculation response"
                    }
                }]
            }

            response = self.send_json({
                "message": "How do I calculate it?",
                "history": history
            })

            stream = self.read_stream(response)

            self.assertIn("BMI calculation response", stream)

            sent_messages = mock_groq.call_args.kwargs["messages"]

            self.assertEqual(sent_messages[-3]["content"], "What is BMI?")
            self.assertEqual(
                sent_messages[-2]["content"],
                "BMI measures body mass."
            )
            self.assertEqual(
                sent_messages[-1]["content"],
                "How do I calculate it?"
            )

    def test_invalid_history_does_not_crash(self):
        with patch("chatbot.views.client", None), \
             patch("chatbot.views.call_groq") as mock_groq, \
             patch("chatbot.views.call_openai"):

            mock_groq.return_value = {
                "choices": [{
                    "message": {
                        "content": "Response"
                    }
                }]
            }

            response = self.send_json({
                "message": "Hello",
                "history": "invalid history"
            })

            self.assertEqual(response.status_code, 200)

            stream = self.read_stream(response)

            self.assertIn("Response", stream)


class ClearChatTests(ChatbotTestBase):
    """Tests for clearing chat."""

    def test_clear_chat_requires_login(self):
        self.client.logout()

        response = self.client.post(self.clear_url)

        self.assertEqual(response.status_code, 302)

    def test_clear_chat_get_is_rejected(self):
        response = self.client.get(self.clear_url)

        self.assertEqual(response.status_code, 405)

    def test_clear_chat_success(self):
        response = self.client.post(self.clear_url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(
            data["message"],
            "Chat cleared successfully."
        )
