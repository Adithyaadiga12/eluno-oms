from dotenv import load_dotenv
import os

load_dotenv()


def list_gemini_models():
    try:
        import google.generativeai as genai

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        print("Gemini models available to your key:")
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                print(f"  - {m.name}")
    except Exception as e:
        print(f"  Gemini list models: FAILED -> {type(e).__name__}: {str(e)[:200]}")


def test_gemini_call(model_name):
    try:
        import google.generativeai as genai

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel(model_name)
        r = model.generate_content("Reply with exactly: OK")
        print(f"\nGemini call ({model_name}): OK -> {r.text.strip()!r}")
    except Exception as e:
        print(f"\nGemini call ({model_name}): FAILED -> {type(e).__name__}: {str(e)[:200]}")


def test_supabase():
    try:
        from supabase import create_client

        client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        )
        try:
            client.table("_health_check_table").select("*").limit(1).execute()
        except Exception as inner:
            msg = str(inner)
            auth_ok_signals = ["relation", "does not exist", "PGRST205", "PGRST125", "Invalid path"]
            if any(sig in msg for sig in auth_ok_signals):
                print("\nSupabase: OK -> auth works (table doesn't exist yet, which is expected)")
                return
            raise
    except Exception as e:
        print(f"\nSupabase: FAILED -> {type(e).__name__}: {str(e)[:200]}")


test_gemini_call("gemini-2.5-flash")
test_supabase()
