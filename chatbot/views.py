
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


# Backward compatibility with the old function name
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

    # Use only the latest 12 messages
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

        # Convert frontend role names into Gemini role names
        if role in ["user"]:

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

    # Check API key
    if client is None:

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Gemini API key is missing or the client "
                    "could not be initialized. Check your .env file."
                )
            },
            status=503
        )

    # Read request body
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

    # Get user question
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

    # Build conversation history
    contents = build_chat_history(history)

    # Add the current user question
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
    # STREAM GEMINI RESPONSE
    # ========================================================

    def generate_response():

        answer_generated = False

        try:

            print("\n========== FITAI CHAT ==========")

            print("User:", request.user.username)

            print("Question:", user_message)

            print("Gemini model:", GEMINI_MODEL)

            print("Generating response...")

            # Call Gemini streaming API
            response_stream = client.models.generate_content_stream(

                model=GEMINI_MODEL,

                contents=contents,

                config=types.GenerateContentConfig(

                    system_instruction=SYSTEM_INSTRUCTION,

                    temperature=0.7,

                    max_output_tokens=2048

                )

            )

            # Receive response chunks
            for chunk in response_stream:

                answer = chunk.text

                if answer:

                    answer_generated = True

                    event_data = json.dumps(
                        {
                            "type": "text",
                            "text": answer
                        }
                    )

                    yield (
                        "data: "
                        + event_data
                        + "\n\n"
                    )

            # Check whether Gemini returned an answer
            if answer_generated:

                yield (
                    'data: {"type": "done"}\n\n'
                )

                print("FITAI: Response completed.")

            else:

                yield (
                    'data: {"type": "error",'
                    '"message":"Gemini returned an empty response. Please try again."}'
                    '\n\n'
                )

                print("FITAI: Empty response received.")

        except Exception as error:

            # Print complete error in terminal
            print("\n========== GEMINI ERROR ==========")

            print("Error:", str(error))

            traceback.print_exc()

            print("==================================\n")

            error_text = str(error).lower()

            # Identify common Gemini errors
            if (
                "429" in error_text
                or "resource_exhausted" in error_text
            ):

                error_message = (
                    "Gemini API quota exceeded. "
                    "Please check your API usage and try again later."
                )

            elif (
                "503" in error_text
                or "unavailable" in error_text
            ):

                error_message = (
                    "Gemini is temporarily unavailable. "
                    "Please try again later."
                )

            elif (
                "404" in error_text
                or "not_found" in error_text
            ):

                error_message = (
                    "Gemini model not found. "
                    "Please check your GEMINI_MODEL configuration."
                )

            elif (
                "403" in error_text
                or "permission_denied" in error_text
            ):

                error_message = (
                    "Gemini API access denied. "
                    "Please check your API key and permissions."
                )

            elif (
                "api key" in error_text
                or "api_key" in error_text
            ):

                error_message = (
                    "Gemini API key error. "
                    "Please check your .env configuration."
                )

            else:

                error_message = (
                    "FitAI could not connect to Gemini. "
                    "Please check the VS Code terminal for details."
                )

            event_data = json.dumps(
                {
                    "type": "error",
                    "message": error_message
                }
            )

            yield (
                "data: "
                + event_data
                + "\n\n"
            )

    # Return server-sent events response
    response = StreamingHttpResponse(

        generate_response(),

        content_type="text/event-stream"

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
