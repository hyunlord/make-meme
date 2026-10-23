"""One checked replacement of the pinned official prediction block."""
import ast
from textwrap import dedent
from extract import sample_source

PREDICTION = dedent("""\
                    noise_pred_cond = self.model(
                        latent_model_input, t=timestep, **arg_c)[0].to(
                            torch.device('cpu') if offload_model else self.device)
                    if offload_model:
                        torch.cuda.empty_cache()
                    if guide_scale <= 1.0:
                        noise_pred = noise_pred_cond
                    else:
                        noise_pred_uncond = self.model(
                            latent_model_input, t=timestep, **arg_null)[0].to(
                                torch.device('cpu') if offload_model else self.device)
                        if offload_model:
                            torch.cuda.empty_cache()
                        noise_pred = noise_pred_uncond + guide_scale * (
                            noise_pred_cond - noise_pred_uncond)
""")


def alg_sample_source(source: str) -> str:
    baseline = sample_source(source, separated=True)
    block = ''.join('        ' + line if line.strip() else line for line in PREDICTION.splitlines(keepends=True))
    assert baseline.count(block) == 1
    replacement = '        noise_pred = alg_predict(latent_model_input, timestep, arg_c, arg_null)\n'
    patched = baseline.replace(block, replacement)
    assert patched.count(replacement) == 1
    assert ast.dump(ast.parse(patched.replace(replacement, block))) == ast.dump(ast.parse(baseline))
    return patched
