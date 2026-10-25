# B-025 실제 참조 묶음과 보존 조건

ENC COMPLETED. 첫 sampler 전에 두 참조를 고정하고 common positive T5 1회, IG VAE/CLIP 각1회, Lab VAE/CLIP 0회로 조건을 만들었다. 기존 negative와 driving/noise/scheduler를 재사용했으며 전체 P 재인코딩은0회다.

| 항목 | REF_LAB | REF_IG |
|---|---|---|
| reference RGB SHA256 | e58c7558b0228d9de975bd2bf8b60df40f9a18b130c30b9602f422033e545680 | 494c6e5efafed27e0d0019e3055da0b38b941ae8d392876d340924c0a1858e9d |
| reference mask SHA256 | c9749f6f1060d3e7e00e793a103fbc4ec26cbfdd6f2a5d28e7c0df180129e1de | 66c547c1deee3ac571f25a8fbdf67726fd22fccb0d7375adc6985bf9559fcd77 |
| condition cache SHA256 | 9d825797775caea37324ea0dd3dc67b3e63fffca0ace49cf182d62709c44b0bf | 32a4c1ca7d0b5453cd34ad464f1046658d7150aab15d39d22000d6d0aba285c5 |

원본 IG 파일과 기존 workpack derivative는 서로 다른 hash이며 실제 사용한 원본 hash는 `de4bfe81cb0229d8fdd71a6ea677a09abc4fd64105b7065c86caabe9ae8d0554`다. 기존 support 계보의 원본 resize RGB 일치를 확인했고 개인 경로와 실제 pixel 자료는 비공개 manifest에만 둔다. A 생성 이미지를 참조로 쓰지 않았다.

실제 pair 변화는 t2/t3/t4와 t8/t9/t10이다. 양 CFG의 clip_fea/ref_latents/ref_masks에 대응한다. t0/t1/t5/t6/t7/t11/t12/t13/t14/t15는 동일하며 tree/scalar/device 계약도 보존한다. mask 차이는 허용하지만 반드시 요구하지 않는 검사다. 새 REF_LAB 대 B024는 positive text t1만 변경됐다. [실제 조건 검사](evidence/pair-conditions.json).

공통 caption은 configs/LAB.json과 IG.json에서 byte-identical하며 breed/색/몸통폭을 지시하지 않는다. source·prompt·noise를 고정해도 reference RGB·mask·사진 자세·support가 함께 바뀌므로 순수 identity 단일요인 또는 VAE/CLIP별 효과로 분리할 수 없다.

최초 실제 forward의 참조 묶음 전달,40step80forward와 final latent/decode는 별도 runtime 증거다. ENC 성공만으로 이를 완료했다고 하지 않는다. 두 output의 외형·동작·장면 품질은 RESULTS에서 각각 판정한다.
