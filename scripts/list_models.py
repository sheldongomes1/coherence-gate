"""List live, text-capable model ids on both APIs so pins in config/models.yaml can be verified."""
import os

from dotenv import load_dotenv

load_dotenv()


def gemini() -> list[str]:
    from google import genai

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    skip = ("tts", "image", "audio", "live", "embedding", "robotics", "computer", "transcribe")
    return sorted(
        m.name.removeprefix("models/")
        for m in client.models.list()
        if "generateContent" in (m.supported_actions or [])
        and m.name.removeprefix("models/").startswith("gemini-")
        and not any(s in m.name for s in skip)
    )


def claude() -> list[str]:
    import anthropic

    return sorted(m.id for m in anthropic.Anthropic().models.list(limit=50))


if __name__ == "__main__":
    print("gemini:", *gemini(), sep="\n  ")
    print("claude:", *claude(), sep="\n  ")
