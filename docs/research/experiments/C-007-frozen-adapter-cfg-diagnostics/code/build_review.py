"""C007 offline media and numeric review; no inference, no change to generated MP4s."""
from pathlib import Path
import argparse
import html
import importlib.util
import json
import time

HELPER=Path(__file__).resolve().parents[2]/'C-006-motion-point-adapter-pilot/code/build_review.py'
spec=importlib.util.spec_from_file_location('c006_review_helpers',HELPER)
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
CELLS=('BASE_1','ON_1','BASE_5','ON_5')
STYLE=helpers.STYLE+'table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:8px;border-bottom:1px solid #40516b;text-align:left;white-space:nowrap}.table-scroll{overflow:auto}footer{margin-top:48px}.numeric{font-variant-numeric:tabular-nums}'


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def table(headers: list[str], values: list[list]) -> str:
    def cell(value):
        return f'{value:.6g}' if isinstance(value,float) else ('null' if value is None else html.escape(str(value)))
    return '<div class="table-scroll"><table><thead><tr>'+''.join(f'<th>{html.escape(h)}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{cell(v)}</td>' for v in row)+'</tr>' for row in values)+'</tbody></table></div>'


def line_plot(title: str, series: list, xlabel: str) -> str:
    """Actual numeric SVG plot; linear axes, no smoothing or inferred samples."""
    colors=('#8cceff','#ffb86b','#b7e283','#e6a3ff','#ffd75e','#70dfcf','#ff8f9c','#c1cddd')
    points=[point for _,values in series for point in values]
    if not points:return ''
    xmin=min(x for x,y in points);xmax=max(x for x,y in points);ymax=max(y for x,y in points) or 1
    width,height=960,360;left,right,top,bottom=75,25,35,100
    def px(x):return left+(x-xmin)/max(xmax-xmin,1e-12)*(width-left-right)
    def py(y):return height-bottom-y/ymax*(height-top-bottom)
    svg=f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}" style="width:100%;min-width:960px;background:#1b2431"><title>{html.escape(title)}</title>'
    for i in range(5):
        y=ymax*i/4;svg+=f'<path d="M {left} {py(y)} H {width-right}" stroke="#40516b"/><text x="4" y="{py(y)+5}" fill="#edf3fa" font-size="13">{y:.4g}</text>'
    for x in sorted(set(x for x,y in points)):
        if len(set(x for x,y in points))>10 and x not in (xmin,xmax,25,40,47):continue
        svg+=f'<text x="{px(x)}" y="{height-bottom+20}" fill="#edf3fa" text-anchor="middle" font-size="13">{x:.3g}</text>'
    for i,(name,values) in enumerate(series):
        color=colors[i%len(colors)];coords=' '.join(f'{px(x)},{py(y)}' for x,y in sorted(values))
        svg+=f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"/>'
        for x,y in values:svg+=f'<circle cx="{px(x)}" cy="{py(y)}" r="3" fill="{color}"/>'
        svg+=f'<text x="{left+(i%4)*220}" y="{height-35+(i//4)*20}" fill="{color}" font-size="13">{html.escape(name)}</text>'
    svg+=f'<text x="{width/2}" y="{height-65}" fill="#edf3fa" text-anchor="middle" font-size="14">{html.escape(xlabel)} (linear axis)</text></svg>'
    return f'<h3>{html.escape(title)}</h3><div class="table-scroll" tabindex="0" aria-label="Scrollable numeric plot">'+svg+'</div>'


def numeric_panel(private: Path, out: Path) -> str:
    probe=private/'outputs/probes';panel='<h2>Numerical diagnostics · sigma / sampler step j</h2><p>These rows are model predictions and hidden-state statistics. Their indices are not video frame t. Latent MSE is not a motion or identity score. Negative text is not TRACK_NULL.</p>'
    verification=private/'evidence/input-replay-verification.json'
    if verification.exists():
        helpers.copy(verification,out/'numerics/input-replay-verification.json')
        panel+='<p><strong>Context caveat:</strong> Cached probe VACE context differs from actual rollout context (max_abs6.421875, RMS0.766806). The four videos share the same actual context and text. Therefore probe-to-rollout differences are not a pure state-change comparison; cause remains UNKNOWN; no extra encoding was performed. Frozen-state replay uses actual rollout context and passes its replay comparison. <a href="numerics/input-replay-verification.json">Input/replay evidence</a></p>'
    trajectory=private/'evidence/trajectory-differences.json'
    if trajectory.exists():
        helpers.copy(trajectory,out/'numerics/trajectory-differences.json')
        differences=json.loads(trajectory.read_text())
        panel+=line_plot('ON minus BASE latent distance · accumulated trajectories',[(f'CFG{cfg}',[(r['sampler_step'],r['on_minus_base_latent_rms']) for r in differences if r['cfg']==cfg]) for cfg in (1,5)],'sampler step j, NOT video frame t')
        panel+='<p><a href="numerics/trajectory-differences.json">Original trajectory distance values</a>. This includes prior-step accumulation; it is not same-state prediction delta or target velocity error.</p>'
    probe_rows=rows(probe/'PROBES.jsonl')
    cfg_rows=rows(probe/'CFG_STATS.jsonl')
    block_rows=rows(probe/'BLOCK_STATS.jsonl')
    for clip in ('elephant','goat'):
        series=[]
        for predictor in ('BASE','256_ON'):
            for branch in ('positive','negative'):
                series.append((predictor+' '+branch,[(r['sigma'],r['mse']) for r in probe_rows if r['clip']==clip and r['predictor']==predictor and r['branch']==branch]))
        panel+=line_plot(clip+' · branch latent MSE',series,'exact sigma, not video t')
        panel+=line_plot(clip+' · same-state adapter CFG delta RMS',[(name,[(r['sigma'],r[name]['delta_rms']) for r in cfg_rows if r['clip']==clip and r['predictor']=='256_ON']) for name in ('cfg1','cfg5')],'exact sigma')
        panel+=line_plot(clip+' · ON256 positive support residual/hidden',[(f'block {block}',[(r['sigma'],r['support']['residual_hidden_ratio']) for r in block_rows if r['clip']==clip and r['predictor']=='256_ON' and r['branch']=='positive' and r['dit_block_index']==block]) for block in range(26,30)],'exact sigma')
    schemas=[('PROBES.jsonl',['clip','sigma','predictor','branch','mse','object_mse','background_mse','balanced_loss']),('CFG_STATS.jsonl',['clip','sigma','predictor','delta_plus_rms','delta_minus_rms','delta_difference_rms','delta_cosine'])]
    for filename,keys in schemas:
        data=rows(probe/filename)
        if data:
            helpers.copy(probe/filename,out/'numerics'/filename)
            panel+=f'<details><summary>{filename} · {len(data)} rows</summary><p><a href="numerics/{filename}">Full original numeric JSONL</a></p>'+table(keys,[[r.get(k) for k in keys] for r in data])+'</details>'
    cfg=rows(probe/'CFG_STATS.jsonl')
    if cfg:panel+='<details><summary>Same noisy-state CFG changes (not rollout differences)</summary>'+table(['clip','sigma','predictor','Delta1 RMS','Delta5 RMS','relative CFG1','relative CFG5'],[[r['clip'],r['sigma'],r['predictor'],r['cfg1']['delta_rms'],r['cfg5']['delta_rms'],r['cfg1']['relative_change'],r['cfg5']['relative_change']] for r in cfg])+'</details>'
    blocks=rows(probe/'BLOCK_STATS.jsonl')
    if blocks:
        helpers.copy(probe/'BLOCK_STATS.jsonl',out/'numerics/BLOCK_STATS.jsonl')
        panel+='<details><summary>Residual / hidden · full tokens and point support</summary><p><a href="numerics/BLOCK_STATS.jsonl">Full block statistics including token norm percentiles</a></p>'+table(['clip','sigma','predictor','branch','DiT block','full residual/hidden','support residual/hidden','full effective/hidden'],[[r['clip'],r['sigma'],r['predictor'],r['branch'],r['dit_block_index'],r['full']['residual_hidden_ratio'],r['support']['residual_hidden_ratio'],r['full']['effective_hidden_ratio']] for r in blocks])+'</details>'
    for metric,title in [('latent','Pre-step latent RMS'),('prediction','Guided prediction RMS'),('euler_actual_update','Actual Euler update RMS')]:
        panel+=line_plot(title+' · separate trajectories',[(cell,[(r['sampler_step'],r[metric]['rms']) for r in rows(private/'outputs'/cell/'ROLLOUT_STATS.jsonl')]) for cell in CELLS],'sampler step j, NOT video frame t')
    panel+='<p>Separate-trajectory curves include accumulated history. Their differences are not same-state adapter effects. The frozen-state table below fixes a single trajectory state before comparing BASE and ON.</p>'
    for cell in CELLS:
        path=private/'outputs'/cell/'ROLLOUT_STATS.jsonl';data=rows(path)
        if data:
            helpers.copy(path,out/'numerics'/f'{cell}-ROLLOUT_STATS.jsonl')
            panel+=f'<details><summary>{cell} rollout · sampler j=0..49, not video t=0..32</summary>'+table(['j','sigma','next sigma','latent RMS','prediction RMS','Euler actual update RMS'],[[r['sampler_step'],r['sigma'],r['next_sigma'],r['latent']['rms'],r['prediction']['rms'],r['euler_actual_update']['rms']] for r in data])+'</details>'
    replay=private/'outputs/replay/ROLLOUT_PROBES.jsonl';data=rows(replay)
    if data:
        helpers.copy(replay,out/'numerics/ROLLOUT_PROBES.jsonl')
        panel+='<details><summary>Frozen rollout states · same-state BASE versus ON</summary><p>Each trajectory supplies a fixed pre-step latent. This is not ground-truth FM error.</p>'+table(['trajectory','j','sigma','delta+ RMS','delta− RMS','Delta1 RMS','Delta5 RMS'],[[r['trajectory'],r['sampler_step'],r['sigma'],r['delta_plus_rms'],r['delta_minus_rms'],r['cfg1']['delta_rms'],r['cfg5']['delta_rms']] for r in data])+'</details>'
    else:panel+='<p>Frozen rollout replay: NOT_AVAILABLE in this build.</p>'
    return panel


def sheets(private: Path, source: Path, out: Path) -> None:
    out.mkdir(parents=True,exist_ok=True)
    groups=[('SOURCE',sorted((source/'source').glob('*.png')))]
    for cell in CELLS:
        frames=sorted((private/'outputs'/cell/'frames').glob('*.png'))
        if len(frames)==33:
            groups.append((cell,frames));helpers.all_sheet(cell,frames,out/f'{cell}-all33.jpg')
    helpers.all_sheet('SOURCE',groups[0][1],out/'SOURCE-all33.jpg')
    helpers.sheet(groups,list(range(0,33,4)),out/'fixed9.jpg')
    helpers.sheet(groups,[8,16,28,29,30,31,32],out/'critical.jpg')


def build(private: Path, source: Path, out: Path) -> None:
    start=time.monotonic();out.mkdir(parents=True,exist_ok=False)
    groups=[('SOURCE',sorted((source/'source').glob('*.png')))];cards='';anchors='';hashes={}
    helpers.preview(source/'source/%03d.png',out/'source-derived.mp4')
    cards+=helpers.fig('source-derived.mp4','SOURCE · derived preview16fps',True)
    for cell in CELLS:
        folder=private/'outputs'/cell;frames=sorted((folder/'frames').glob('*.png'))
        assert len(frames)==33 and (folder/'generated.mp4').is_file(),cell
        helpers.copy(folder/'generated.mp4',out/f'{cell}.mp4');hashes[cell]=helpers.sha(out/f'{cell}.mp4')
        groups.append((cell,frames));cards+=helpers.fig(f'{cell}.mp4',f'{cell} · generated result · original MP4 bytes',True)
    for name in ('start','end'):
        helpers.copy(source/'anchors'/f'{name}.png',out/f'{name}.png');anchors+=helpers.fig(f'{name}.png',name.upper()+' anchor · model input')
    condition=private/'outputs/BASE_1/condition';conditions=sorted(condition.glob('*.png'));assert len(conditions)==33
    helpers.preview(condition/'%03d.png',out/'condition-derived.mp4');groups.append(('CONDITION',conditions))
    slider=''
    for label,paths in groups:
        urls=[]
        for i,path in enumerate(paths):
            target=out/label/f'{i:03d}.jpg';target.parent.mkdir(exist_ok=True)
            with helpers.Image.open(path) as image:image.convert('RGB').save(target,quality=92,subsampling=0)
            urls.append(f'{label}/{i:03d}.jpg')
        meaning='model RGB input, not generated result' if label=='CONDITION' else ('source input' if label=='SOURCE' else 'generated result')
        slider+=f'<figure><div class="frame"><a href="{urls[0]}"><img src="{urls[0]}" data-frames="{html.escape(json.dumps(urls),quote=True)}" alt="{label}"></a></div><figcaption>{label} · {meaning} · JPEG review derivative</figcaption></figure>'
    sheets(private,source,out)
    body='<h1>C-007 · Frozen adapter CFG diagnostics</h1><p>Validation elephant only; checkpoint256 frozen. Native BASE versus adapter ON, each at CFG1 and CFG5. No training or automatic default adoption. Compare ON−BASE within the same CFG first.</p><p>Video frame t=0..32 is distinct from sampler step j=0..49 and sigma. Assumed preview16fps; duration2.0625s, endpoint interval2s. Temporal UNVERIFIED. Playback and static inspection are not continuous perceptual review.</p>'
    body+=f'<section><h2>Elephant · actual inputs and generated results</h2><div class="grid">{anchors}</div><button data-play>Play all from selected t · 16fps</button> <button data-pause>Pause all</button><p role="status"></p><div class="grid">{cards}</div><details><summary>Actual common condition RGB · not generated output</summary>{helpers.fig("condition-derived.mp4","Model input · derived preview",True)}</details><h3>Video frame t=<output>0</output>/32</h3><label>Video frame t<input aria-label="video frame t" type="range" min="0" max="32" value="0"></label><button data-zoom>Toggle 2× image zoom</button><div class="grid">{slider}</div><details><summary>Fixed9 and critical-index sheets</summary>{helpers.fig("fixed9.jpg","Same-frame SOURCE / BASE1 / ON1 / BASE5 / ON5")}{helpers.fig("critical.jpg","t=8,16,28,29–32")}</details></section>'
    body+=numeric_panel(private,out)
    reports=Path(__file__).resolve().parent.parent;links=[]
    for name in ('RESULTS.md','METHOD.md','LESSON_KO.md','COSTS.json','REPRODUCE.md','DELIVERY.json'):
        if (reports/name).is_file():helpers.copy(reports/name,out/'reports'/name);links.append(f'<a href="reports/{name}">{name}</a>')
    body+='<footer><h2>Final reports</h2><p>'+(' · '.join(links) or 'Reports pending finalization.')+'</p><p>DELIVERY.json inside this package records the packaging protocol and pending archive checks. Final archive hash/transfer receipt is a separate sidecar to avoid self-hash circularity.</p></footer>'
    (out/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C007 frozen adapter diagnostics</title><style>'+STYLE+'</style></head><body><main>'+body+'</main><script>'+helpers.JS+'</script></body></html>')
    (out/'review-summary.json').write_text(json.dumps({'generated_mp4_sha256':hashes,'temporal':'UNVERIFIED','build_seconds':time.monotonic()-start},indent=2))
    print(out)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('private',type=Path);parser.add_argument('source',type=Path);parser.add_argument('out',type=Path);parser.add_argument('--sheets-only',action='store_true');a=parser.parse_args()
    (sheets if a.sheets_only else build)(a.private.resolve(),a.source.resolve(),a.out.resolve())
