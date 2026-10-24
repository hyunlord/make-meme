# B-024 independent runtime and static review

## Technical verdict: PASS within recorded execution scope

REF/PROBE/S/D each completed once; S actual progress40steps/80modelcalls. First-two actual CFG prehooks verify ref/CLIP/pose objectidentity with verified restored cache; recorded reference hashc3bd8cb2e4a4be6d91f361e26addebe8ba44d581511198eb0f3f339469d8e65a andCLIPhash4d5612e8f89353987bc8a0647ba032052d972dc8b4d6400d98c332783486bc93 match changed cacheleaves t3/t2 andt9/t8. No additional observationforward/copy. Prior connectionaudit independentlyvalidatedall16payloadhashes,4changed12same/exactstructure.

Actual final_latent.safetensors SHA0080a47e9bd63c263d89c2e508ed96ec00ed388ccb611e77fe9207216ff3c27b, F32[16,5,64,112], everyvaluefinite. Metadata40/80, adapterfalse,historyNone,reference_prefix_includedfalse,conditionSHA1c8fc00620527f1fcddb7f380cd35ed70865ec4218420a85b7f6c21797496080 matches derivedcache.

CPU-only actual Spark raw weights_only load confirms F32[3,17,512,896],finite,SHAe33ac003e663f3e2a32c7740f116d4d0dfd6259eff379cc30906e9b6d2562f3b;CUDAuninitialized. Generatedz differsinitialnoise and has[16,5,64,112],versusdriving[16,5,32,56]andreference[16,1,64,112]. Pinnedphase_decode reads only savedfinalx0 throughofficialVAEdecode, no sourceRGB exportbranch. This rules out observed accidentalreference/drivinglatent substitution in tracedpath; media raw-to-PNG fidelity is separately checked by mediaowner.

Terminalrecord: ownedpipeline/watchdogMainPID0/inactive,protected existing service alive,available95,344,111,616bytes,swap0,remainingGPUwork0. S memory.high3031 retained, not labeledOOM; no further GPU/model call byreviewer.

## Actual static second review

Viewed full17frame comparison-all17.png and larger local0/8/16 comparison. B024showsstandingLab onsource-like tiles,rug,rope,toys/window/camera layout; B023showsseatedLab inverticalbedroomwithinventedsidebackground. B024lateframes turnheadtowardsimageleft in samebroadsourceordering. Priorverticalreferenceboundary/headcut isnotvisibleinthese B024sheets. This is clear staticimprovement inpose/scene alignment overB023.

Morphology: face/muzzle andfurappear somewhat smoother than source; exactface/ear/neck detail andindividualidentity fidelity remainUNCERTAIN. All17are preserved; no favorableframeselection. Actualcontinuousnativeplayback notobservedbyreviewer,temporalUNVERIFIED. Staticsequence ordering doesnotestablishfinejointtiming/contactaccuracy.

Source and reference are sameindividual. Source-like output mayreflectdriving/sourcecopy, so actualreference necessity, cross-ID editing,identitytransfer andgeneralization areNOT_ESTABLISHED/NOT_RUN. No claim ofpixel-exactbackground preservation orcommercialquality. Runtimecorrectnessandstaticimprovementdonotresolvetheseconfounds. No additional generation/retraining/audit expansion recommended automatically.
