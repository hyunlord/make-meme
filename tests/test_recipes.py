from __future__ import annotations

import pytest

from make_meme.comfy.validate import check_recipe
from make_meme.recipes.loader import RecipeError, all_recipes, get_recipe


def test_builtin_recipes_load():
    recipes = all_recipes()
    assert {"mocha_swap", "sam3_detect", "wan_text_cache"} <= set(recipes)
    assert recipes["mocha_swap"].kind == "swap"
    assert recipes["sam3_detect"].kind == "detect"
    assert recipes["wan_text_cache"].kind == "cache"


def test_wan_text_cache_builds_prompt_and_profile_override():
    r = get_recipe("wan_text_cache")
    wf = r.build({"prompt": "a shiba inu dancing", "negative_prompt": "blurry"}, profile="mps")
    assert wf["1"]["inputs"]["positive_prompt"] == "a shiba inu dancing"
    assert wf["1"]["inputs"]["negative_prompt"] == "blurry"
    assert wf["1"]["inputs"]["model_name"] == "umt5-xxl-enc-bf16.safetensors"
    assert wf["1"]["inputs"]["device"] == "gpu"
    assert wf["2"]["class_type"] == "MakeMemeSink"

    wf_lowvram = r.build({"prompt": "x"}, profile="cuda_lowvram")
    assert wf_lowvram["1"]["inputs"]["device"] == "cpu"


def test_wan_text_cache_negative_prompt_defaults_to_empty():
    wf = get_recipe("wan_text_cache").build({"prompt": "a dog"}, profile="mps")
    assert wf["1"]["inputs"]["negative_prompt"] == ""


def test_build_applies_inputs_preset_and_profile():
    r = get_recipe("mocha_swap")
    wf = r.build(
        {"video": "v.mp4", "mask": "m.png", "ref1": "a.png", "ref2": "b.png", "prompt": "a shiba inu dancing", "seed": 7},
        profile="mps",
        preset="high",
    )
    assert wf["1"]["inputs"]["file"] == "v.mp4"
    assert wf["13"]["inputs"]["positive_prompt"] == "a shiba inu dancing"
    assert wf["15"]["inputs"]["seed"] == 7
    assert wf["15"]["inputs"]["steps"] == 6  # "high" preset, Mac override
    assert wf["5"]["inputs"]["target_width"] == 832 and wf["7"]["inputs"]["target_height"] == 480
    assert wf["11"]["inputs"]["model"] == "WanVideo/mocha-Q4_K_M.gguf"
    assert wf["11"]["inputs"]["attention_mode"] == "comfy"  # split attention on MPS
    assert wf["10"]["inputs"]["lora_0"].endswith("rank64_bf16.safetensors")
    # template untouched
    assert r.workflow["1"]["inputs"]["file"] == "__video__"


def test_cuda_profile_uses_fp8_model():
    wf = get_recipe("mocha_swap").build({"video": "v", "mask": "m", "ref1": "a"}, profile="cuda")
    assert "fp8" in wf["11"]["inputs"]["model"]
    assert wf["11"]["inputs"]["quantization"] == "fp8_e4m3fn_scaled"
    high = get_recipe("mocha_swap").build({"video": "v", "mask": "m", "ref1": "a"}, profile="cuda", preset="high")
    assert high["15"]["inputs"]["steps"] == 8 and high["5"]["inputs"]["target_width"] == 1280


def test_cuda_lowvram_profile_uses_gguf_and_cpu_text_encoder():
    wf = get_recipe("mocha_swap").build({"video": "v", "mask": "m", "ref1": "a"}, profile="cuda_lowvram")
    assert wf["11"]["inputs"]["model"].endswith(".gguf")
    assert wf["13"]["inputs"]["device"] == "cpu"


def test_optional_input_unlinks_when_missing():
    wf = get_recipe("mocha_swap").build({"video": "v", "mask": "m", "ref1": "a"}, profile="mps")
    assert "ref2" not in wf["14"]["inputs"]
    assert "6" not in wf and "7" not in wf  # orphaned ref2 loader/resizer pruned
    assert "17" in wf and "1" in wf


def test_missing_required_and_unknown_inputs():
    r = get_recipe("mocha_swap")
    with pytest.raises(RecipeError, match="requires input 'mask'"):
        r.build({"video": "v", "ref1": "a"}, profile="mps")
    with pytest.raises(RecipeError, match="does not accept"):
        r.build({"video": "v", "mask": "m", "ref1": "a", "bogus": 1}, profile="mps")
    with pytest.raises(RecipeError, match="Unknown quality"):
        r.build({"video": "v", "mask": "m", "ref1": "a"}, profile="mps", preset="ultra")


def test_magcache_unlinked_and_pruned_when_omitted():
    wf = get_recipe("mocha_swap").build({"video": "v", "mask": "m", "ref1": "a"}, profile="mps")
    assert "cache_args" not in wf["15"]["inputs"]
    assert "18" not in wf  # orphaned WanVideoMagCache node pruned


def test_magcache_links_sampler_when_given():
    wf = get_recipe("mocha_swap").build(
        {"video": "v", "mask": "m", "ref1": "a", "magcache_thresh": 0.12}, profile="mps"
    )
    assert wf["15"]["inputs"]["cache_args"] == ["18", 0]
    assert wf["18"]["inputs"]["magcache_thresh"] == 0.12
    assert wf["18"]["class_type"] == "WanVideoMagCache"


def _object_info(models: list[str], with_wrapper: bool = True) -> dict:
    info = {
        "LoadVideo": {}, "GetVideoComponents": {}, "LoadImageMask": {}, "LoadImage": {},
        "ResizeAndPadImage": {}, "SaveImage": {}, "MakeMemeInfo": {},
    }
    if with_wrapper:
        info.update({
            "WanVideoLoraSelectMulti": {"input": {"required": {"lora_0": [["none", *models]]}}},
            "WanVideoModelLoader": {"input": {"required": {"model": [models]}}},
            "WanVideoVAELoader": {"input": {"required": {"model_name": [models]}}},
            "WanVideoTextEncodeCached": {"input": {"required": {"model_name": [models]}}},
            "MochaEmbeds": {}, "WanVideoSampler": {}, "WanVideoDecode": {}, "WanVideoMagCache": {},
        })
    return info


def test_validate_reports_missing_models_and_nodes():
    r = get_recipe("mocha_swap")
    res = check_recipe(r, _object_info(["Wan2_1_VAE_bf16.safetensors"]), profile="mps")
    assert not res.ready
    missing = {m.file for m in res.missing_models}
    assert "WanVideo/mocha-Q4_K_M.gguf" in missing and "umt5-xxl-enc-bf16.safetensors" in missing
    assert res.summary()["fix"] == "make-meme install mocha_swap"

    res2 = check_recipe(r, _object_info([], with_wrapper=False), profile="mps")
    assert "WanVideoSampler" in res2.missing_nodes
    assert res2.missing_node_packs == ["https://github.com/kijai/ComfyUI-WanVideoWrapper"]

    no_companion = _object_info([])
    del no_companion["MakeMemeInfo"]
    res3 = check_recipe(r, no_companion, profile="mps")
    assert "builtin:make_meme_nodes" in res3.missing_node_packs and not res3.ready


def test_validate_ready_with_windows_style_paths():
    r = get_recipe("mocha_swap")
    files = [
        "WanVideo\\mocha-Q4_K_M.gguf",
        "WanVideo\\Lightx2v\\lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors",
        "Wan2_1_VAE_bf16.safetensors",
        "umt5-xxl-enc-bf16.safetensors",
    ]
    assert check_recipe(r, _object_info(files), profile="mps").ready
