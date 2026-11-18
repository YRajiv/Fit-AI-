import json
import os
import traceback

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from google import genai
from google.genai import types

from nutrition.ai_fallback import call_groq, call_openai


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_API_KEY = getattr(
    settings,
    "GEMINI_API_KEY",
    None
) or os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = getattr(
    settings,
    "GEMINI_MODEL",
    None
) or os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash"
)

client = None

if GEMINI_API_KEY:
    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        print("FITAI: Gemini client initialized successfully.")

    except Exception:
        print("FITAI: Gemini client initialization failed.")
        traceback.print_exc()


# ============================================================
# CHAT PAGE
# ============================================================

@login_required
def chat_page(request):

    return render(
        request,
        "chatbot/chat.html"
    )


# Backward compatibility
chat = chat_page


# ============================================================
# FITAI SYSTEM INSTRUCTION
# ============================================================

SYSTEM_INSTRUCTION = """
You are FitAI Assistant, an intelligent, friendly and helpful AI assistant.

You can answer questions about ANY topic.

YOUR KNOWLEDGE AREAS:

1. General knowledge and education.
2. Python programming.
3. Django web development.
4. JavaScript, HTML and CSS.
5. SQL and databases.
6. Artificial Intelligence and Machine Learning.
7. Data Structures and Algorithms.
8. Software development and debugging.
9. Career guidance and interview preparation.
10. Mathematics and science.
11. Fitness and exercise.
12. Nutrition, protein and calories.
13. Workout plans and muscle building.
14. Diet planning and BMI explanations.
15. Everyday questions and problem solving.
16. Writing, communication and explanations.

IMPORTANT RULES:

- Answer the actual question asked by the user.
- Do not restrict your answers to fitness topics.
- Answer general questions too.
- Use simple and understandable English.
- Explain difficult concepts step by step.
- Give examples whenever useful.
- For programming questions, provide working code when appropriate.
- For calculations, show the calculation steps.
- Use headings and bullet points when useful.
- Do not make up facts.
- If you are uncertain, explain that clearly.
- Do not recommend dangerous diets or unsafe exercises.
- Do not prescribe medicines.
- For medical questions, provide general information and recommend
  professional medical advice when appropriate.

Be friendly, accurate and helpful.

You are FitAI Assistant. Help the user with whatever they ask.
"""


# ============================================================
# BUILD CONVERSATION HISTORY
# ============================================================

def build_chat_history(history):

    contents = []

    if not isinstance(history, list):
        return contents

    # Use latest 12 messages
    history = history[-12:]

    for item in history:

        if not isinstance(item, dict):
            continue

        role = item.get("role")

        message = item.get(
            "content",
            item.get("text", "")
        )

        if not isinstance(message, str):
            continue

        message = message.strip()

        if not message:
            continue

        # Convert frontend roles into Gemini roles
        if role == "user":

            gemini_role = "user"

        elif role in ["assistant", "model", "bot"]:

            gemini_role = "model"

        else:

            continue

        contents.append(
            types.Content(
                role=gemini_role,
                parts=[
                    types.Part.from_text(
                        text=message
                    )
                ]
            )
        )

    return contents


# ============================================================
# SEND MESSAGE API
# ============================================================

@login_required
@require_POST
def send_message(request):

    # ========================================================
    # READ REQUEST BODY
    # ========================================================

    try:

        data = json.loads(
            request.body.decode("utf-8")
        )

    except (json.JSONDecodeError, UnicodeDecodeError):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON request."
            },
            status=400
        )

    if not isinstance(data, dict):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid request data."
            },
            status=400
        )

    # ========================================================
    # GET USER MESSAGE
    # ========================================================

    user_message = data.get(
        "message",
        ""
    )

    history = data.get(
        "history",
        []
    )

    if not isinstance(user_message, str):

        return JsonResponse(
            {
                "success": False,
                "error": "Message must be text."
            },
            status=400
        )

    user_message = user_message.strip()

    if not user_message:

        return JsonResponse(
            {
                "success": False,
                "error": "Please enter a message."
            },
            status=400
        )

    if len(user_message) > 4000:

        return JsonResponse(
            {
                "success": False,
                "error": "Maximum message length is 4000 characters."
            },
            status=400
        )

    # ========================================================
    # BUILD GEMINI CONVERSATION
    # ========================================================

    contents = build_chat_history(history)

    # Add current question
    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=user_message
                )
            ]
        )
    )

    # ========================================================
    # GENERATE RESPONSE
    # ========================================================

    def generate_response():
        """Generate AI response with provider fallback.

        Attempts Gemini (streaming). If Gemini fails or returns no output,
        falls back to Groq and then OpenAI using the predefined wrappers.
        """
        answer_generated = False
        print("\n========== FITAI CHAT ===========")
        print("User:", request.user.username)
        print("Question:", user_message)
        print("Starting AI provider fallback...")

        # ----------------------------------------------------
        # Build message payloads for Gemini and for the other providers
        # ----------------------------------------------------
        # Gemini uses the internal `contents` list built earlier.
        # Groq/OpenAI expect a list of dict messages.
        fallback_messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION}
        ]
        if isinstance(history, list):
            for item in history[-12:]:
                if not isinstance(item, dict):
                    continue
                role = item.get("role")
                message = item.get("content", item.get("text", ""))
                if not isinstance(message, str):
                    continue
                message = message.strip()
                if not message:
                    continue
                if role == "user":
                    fallback_messages.append({"role": "user", "content": message})
                elif role in ["assistant", "model", "bot"]:
                    fallback_messages.append({"role": "assistant", "content": message})
        fallback_messages.append({"role": "user", "content": user_message})

        # ----------------------------------------------------
        # Provider call definitions for fallback_chain
        # ----------------------------------------------------
        from nutrition.ai_fallback import fallback_chain

        steps = []
        # Gemini step (non‑streaming for simplicity)
        if client is not None:
            def gemini_call():
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.7,
                        max_output_tokens=2048,
                    ),
                )
                # The SDK returns a GenerationResponse; extract text
                return response.candidates[0].content.parts[0].text if response.candidates else ""
            steps.append(("gemini", gemini_call))
        else:
            # Force failure to trigger next provider
            def no_gemini():
                raise RuntimeError("Gemini client unavailable")
            steps.append(("gemini", no_gemini))

        # Groq step
        steps.append(("groq", lambda: call_groq(messages=fallback_messages, timeout=30)))
        # OpenAI step
        steps.append(("openai", lambda: call_openai(messages=fallback_messages, timeout=30)))

        # ----------------------------------------------------
        # Execute fallback chain
        # ----------------------------------------------------
        try:
            response, provider = fallback_chain(steps)
            # Normalise the answer text depending on provider
            if provider == "gemini":
                answer_text = response
            elif provider == "groq":
                answer_text = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            elif provider == "openai":
                answer_text = response.choices[0].message.content
            else:
                answer_text = ""

            if answer_text and answer_text.strip():
                answer_generated = True
                event_data = json.dumps({"type": "text", "text": answer_text})
                yield "data: " + event_data + "\n\n"
                yield "data: {\"type\": \"done\"}\n\n"
                return
            else:
                print(f"FITAI: {provider.capitalize()} returned empty response.")
        except Exception as exc:
            # If Gemini produced partial output we already yielded it, the
            # fallback_chain will have raised after the Gemini step. In that
            # case we surface an error to the client.
            if answer_generated:
                event_data = json.dumps({
                    "type": "error",
                    "message": (
                        "The response was interrupted. Please try sending your message again."
                    ),
                })
                yield "data: " + event_data + "\n\n"
                return
            print(f"FITAI: {provider if 'provider' in locals() else 'provider'} failed: {exc}")
            traceback.print_exc()

        # ----------------------------------------------------
        # All providers failed – send error to client
        # ----------------------------------------------------
        print("FITAI: All AI providers failed.")
        error_message = (
            "All AI services are currently unavailable. "
            "Please try again in a few minutes."
        )
        event_data = json.dumps({"type": "error", "message": error_message})
        yield "data: " + event_data + "\n\n"

    # ========================================================
    # RETURN STREAMING RESPONSE
    # ========================================================

    response = StreamingHttpResponse(
        generate_response(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache, no-transform"
    response["X-Accel-Buffering"] = "no"
    return response


# ============================================================
# CLEAR CHAT API
# ============================================================

@login_required
@require_POST
def clear_chat(request):

    return JsonResponse(
        {
            "success": True,
            "message": "Chat cleared successfully."
        }
    )