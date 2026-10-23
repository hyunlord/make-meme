"""Source-only conservative ratio bounds; no fit/alignment or generated output."""
from pathlib import Path
import json,math,sys
root=Path(sys.argv[1]);p=root/'reports/preflight/observability.json';report=json.loads(p.read_text());data=json.loads((root/'annotations/source-landmarks.json').read_text());ratios=[]
for i in [0,4,8,12,16]:
 pts=data['rows'][i]['points'];a=pts['left_front_paw'];b=pts['right_front_paw'];h=pts['nose'];mid=[(a['xy'][k]+b['xy'][k])/2 for k in [0,1]]
 numerator=math.dist(h['xy'],mid);nu=h['uncertainty_radius_px']+(a['uncertainty_radius_px']+b['uncertainty_radius_px'])/2
 denominator=math.dist(a['xy'],b['xy']);du=a['uncertainty_radius_px']+b['uncertainty_radius_px'];assert denominator>du
 ratios.append({'frame':i,'nose_to_frontpaw_midpoint_over_frontpaw_span':numerator/denominator,'conservative_interval':[(max(0,numerator-nu))/(denominator+du),(numerator+nu)/(denominator-du)],'not_a_joint_or_body_root':True})
report['relative_ratio_bounds']=ratios;report['all_relative_ratio_intervals_overlap_f0']=all(max(r['conservative_interval'][0],ratios[0]['conservative_interval'][0])<=min(r['conservative_interval'][1],ratios[0]['conservative_interval'][1]) for r in ratios)
report['judgement']='DIAGNOSTIC_INSUFFICIENT';report['gpu']='NOT_RUN; preflight stop, not sampler failure';report['gain']='UNDEFINED';report['source_points_only']='Visible surface centers; no hidden joints, contacts, inferred coordinates or interpolated tracks.';report['source_geometry_note']='B006 and B007 PNG file bytes differ but all17 decodedRGB arrays match exactly; fixedBICUBIC1592x896 crop(540,0,1052,896) matches actualdecodedMP4 frames exactly.';report['static_quality_note']='17 copiedf0 PNGs deliberately static CPUcontrol; modelgeneratedframesNOT_RUN.'
p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'judgement':report['judgement'],'E_copy_px':report['E_copy_px'],'mean_uncertainty_px':report['mean_uncertainty_px'],'relative_ratio_bounds':ratios},indent=2))
