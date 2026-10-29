"""Choosing where the model lives. Plain dictionaries in, plain dictionaries out."""
import pytest
import smol_demo as sd


def test_default_is_groq_with_its_key():
    p = sd.get_profile({"GROQ_API_KEY": "k"})
    assert p["name"] == "groq" and p["api_key"] == "k" and "groq" in p["api_base"] and p["pause"] > 0

def test_missing_key_gives_a_helpful_message():
    with pytest.raises(sd.SetupError, match="GROQ_API_KEY"):
        sd.get_profile({})

def test_ollama_needs_no_key_and_no_pause():
    p = sd.get_profile({"PROFILE": "ollama"})
    assert p["pause"] == 0 and "11434" in p["api_base"]

def test_openai_needs_a_model_name():
    with pytest.raises(sd.SetupError, match="SMOL_MODEL"):
        sd.get_profile({"PROFILE": "openai", "OPENAI_API_KEY": "k"})
    p = sd.get_profile({"PROFILE": "openai", "OPENAI_API_KEY": "k", "SMOL_MODEL": "m"})
    assert p["model"] == "m"

def test_model_can_be_overridden():
    p = sd.get_profile({"PROFILE": "ollama", "SMOL_MODEL": "llama3.1"})
    assert p["model"] == "llama3.1"

def test_custom_needs_a_base_url():
    with pytest.raises(sd.SetupError, match="SMOL_API_BASE"):
        sd.get_profile({"PROFILE": "custom", "SMOL_MODEL": "m"})
    p = sd.get_profile({"PROFILE": "custom", "SMOL_MODEL": "m", "SMOL_API_BASE": "http://x/v1",
                        "SMOL_API_KEY": "k"})
    assert p["api_base"] == "http://x/v1" and p["api_key"] == "k"

def test_unknown_profile_lists_the_choices():
    with pytest.raises(sd.SetupError, match="groq"):
        sd.get_profile({"PROFILE": "nope"})

def test_pause_can_be_overridden():
    assert sd.get_profile({"GROQ_API_KEY": "k", "SMOL_PAUSE": "3"})["pause"] == 3

def test_profile_name_is_case_and_space_tolerant():
    assert sd.get_profile({"PROFILE": " Ollama "})["name"] == "ollama"

def test_the_model_object_can_be_built_without_calling_anything():
    p = sd.get_profile({"GROQ_API_KEY": "k"})
    model = sd.make_model(p)
    assert model.model_id == "openai/gpt-oss-120b"


def test_huggingface_profile_uses_the_hf_router_and_token():
    p = sd.get_profile({"PROFILE": "huggingface", "HF_TOKEN": "hf_x"})
    assert p["api_base"] == "https://router.huggingface.co/v1"
    assert p["api_key"] == "hf_x" and p["model"]

def test_huggingface_profile_without_a_token_says_which_one_is_missing():
    with pytest.raises(sd.SetupError, match="HF_TOKEN"):
        sd.get_profile({"PROFILE": "huggingface"})

def test_huggingface_model_can_pick_a_provider():
    p = sd.get_profile({"PROFILE": "huggingface", "HF_TOKEN": "t",
                        "SMOL_MODEL": "openai/gpt-oss-120b:cheapest"})
    assert p["model"].endswith(":cheapest")


# ---- the .env.example template must really work for every profile ------------------------
from pathlib import Path
from dotenv import dotenv_values
import io

EXAMPLE = Path(__file__).parent.parent / ".env.example"


def _env_for(profile):
    """Uncomment one profile's section of .env.example, the way a student would, and parse it."""
    if not EXAMPLE.is_file():
        pytest.skip(".env.example is not in this folder (it may have been renamed to .env). "
                    "These tests check the template, so they are skipped.")
    keep, section = [], None
    for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("# ---"):
            section = line.split()[2]
            continue
        if section == profile or (profile == "groq" and section == "groq"):
            if line.startswith("# ") and "=" in line and not line.startswith("# PROFILE"):
                line = line[2:]
            elif line.startswith("# PROFILE"):
                line = line[2:]
            keep.append(line)
    if profile != "groq":
        keep = [l for l in keep if not l.startswith("PROFILE=groq")]
    return dict(dotenv_values(stream=io.StringIO("\n".join(keep))))


def test_example_groq_section_only_needs_the_key():
    env = _env_for("groq")
    env.setdefault("PROFILE", "groq")
    assert sd.get_profile(env)["name"] == "groq"

def test_example_ollama_section_works_as_is():
    env = _env_for("ollama")
    p = sd.get_profile(env)
    assert p["name"] == "ollama" and p["model"] == "gpt-oss:20b"      # no stray comment text in the name

def test_example_huggingface_section_works_with_a_token():
    env = _env_for("huggingface")
    p = sd.get_profile(env)
    assert p["name"] == "huggingface"

def test_example_openai_section_works():
    p = sd.get_profile(_env_for("openai"))
    assert p["name"] == "openai" and p["model"] == "the-model-name"

def test_example_custom_section_works():
    p = sd.get_profile(_env_for("custom"))
    assert p["name"] == "custom" and p["api_base"] == "https://.../v1"
