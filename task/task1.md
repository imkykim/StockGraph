# ChainGraph — Phase 1 프로토타입 작업 지시 (CLI 에이전트용)

> 이 문서는 `ChainGraph` 기초 스펙 문서(섹션 0~7)의 **동반 문서**다.
> 스키마·온톨로지·관계타입·기술스택·Repo구조는 **기초 스펙이 진실의 원천(source of truth)**이고,
> 이 문서는 (a) 실제 업로드 데이터의 구조, (b) 프로토타입 한정 결정, (c) 자주 깨지는 지점만 추가한다.
> 충돌 시: 데이터 사실은 이 문서, 설계 결정은 기초 스펙을 따른다.

---

## 0. 한 줄 작업 정의

업로드된 위클리 docx에서 **최근 5주**를 잘라, 기업 노드 + 방향성·타입드·가중 엣지를 추출해
`data/output/graph.json`으로 떨구고 `viz/inspect.html`(D3 force)로 눈으로 확인한다.
추출기는 **pluggable 2종**(`seed`=키 없이 데모용 / `llm`=프로덕션). 기본 실행은 `seed`로 그래프가 나와야 한다.

---

## 1. 기초 스펙 대비 바뀐 사실 (반드시 먼저 읽을 것)

기초 스펙은 "위클리 1건"을 가정했지만, **실제 파일은 약 100주(≈768K자)가 한 docx에 누적된 시계열 아카이브**다.
맨 위가 최신, 아래로 갈수록 과거다. 따라서:

1. **전체를 LLM 추출하지 마라.** 100주 × 청크 × 토큰이면 비용·시간이 폭증한다(스펙도 extract가 비용 지배점이라 명시). 프로토타입은 **최근 5주만** 처리한다.
2. 시계열 diff는 Phase 1 범위 밖이지만, 데이터가 멀티위크이므로 **각 엣지·노드에 `date`(주차 키)를 반드시 부여**한다. 이게 있어야 나중에 diff가 공짜로 붙는다.
3. 단일 파일이 곧 코퍼스다. ingest는 "파일 1개 → 주차 N개 → 청크 M개" 구조로 짠다.

---

## 2. 프로토타입 한정 결정 (LOCKED for Phase 1)

1. **처리 범위 = 최근 5주.** 파일 상단부터 날짜경계 5개 블록(아래 라인범위 참조). 이 안에 DoD sanity-check 관계가 전부 들어있다.
2. **추출기 pluggable 2종:**
   - `pipeline/extract/seed_extractor.py` — **키 불필요·결정론적.** 최근 5주의 헤드라인 관계를 LLM 출력과 **동일한 스키마**로 내보낸다. 데모 그래프 생성 + 다운스트림 전체 검증용. **기본값.**
   - `pipeline/extract/llm_extractor.py` — 프로덕션. 환경변수 키(`OPENAI_API_KEY` 또는 `ANTHROPIC_API_KEY`)로 호출. 기초 스펙 섹션 7 프롬프트 사용. 키 없으면 친절히 에러내고 종료.
   - 둘은 **같은 함수 시그니처**(`extract(chunks: list[Chunk]) -> ExtractionResult`)를 구현해 `run_phase1.py --extractor {seed|llm}`로 스위치.
3. **`SUPPLIES`를 canonical 방향으로 고정.** `CUSTOMER_OF`는 추출만 허용하고 빌드 직전 즉시 `SUPPLIES`로 접는다(중복 방지).
4. **weight는 2-pass.** Pass1(로컬)은 raw `quantity`/`unit`만 보존하고 `contract_scale_norm`/`weight`는 비워둔다. Pass2(전역)에서 단위 패밀리별로 확정한다(섹션 5 참조).
5. **Phase 2/3 전부 범위 밖:** 크롤러, 금융 API enrichment, Louvain, Neo4j/Chroma, 프론트 편집기, 임베딩 기반 2차 매칭(seed alias 사전 1차 매칭만으로 충분). 단, resolver 인터페이스는 임베딩 단계를 나중에 끼울 수 있게 비워둔다.

---

## 3. 데이터 사실 (에이전트가 헤매지 않도록 정확히)

**파일 경로:** `data/examples/Tech周报_讨论.docx` (업로드본을 여기로 복사해 사용)

**텍스트 추출:** `python-docx`(설치돼 있음)로 직접 읽어라. `extract-text`/pandoc 결과는 JSON로 래핑돼 나올 수 있으니 의존하지 마라. 표(table) 안에 본문이 많으니 **문단 + 표 셀을 모두** 순회해야 한다.

**주차 경계:** 날짜만 단독으로 있는 줄(별표·공백 제거 후 정규식 `^20\d{6}$`)이 주차 스탬프다. 파일 전체에 98개. 이 줄을 기준으로 split → 각 블록이 한 주차. 블록 맨 위 날짜를 그 주차의 `week` 키(YYYYMMDD)로 쓴다. (최상단은 `20251102`와 `20251026`이 연달아 나오는데, 앞을 발행일/주차키로 잡으면 된다.)

**최근 5주 라인 범위(0-indexed, 추출 텍스트 기준 근사):**
| week | line 범위 | 비고 |
|---|---|---|
| 20251102 / 20251026 | 0–224 | NV+Google 광모듈 加单, SNDK/Kioxia, LRCX clean room |
| 20251019 | 225–500 | AVGO–OAI 10GW, SNDK/Kioxia NAND 섹션 |
| 20251012 | 501–685 | AMD–OAI 6GW, 工业富联 |
| 20251005 | 686–724 | Altman 韩 방문, 삼성/Hynix 90만 WPM DRAM (짧음) |
| 20250914 | 725–999 | (5주째 채우기용; 날짜 갭 있음) |

> 라인범위는 가이드일 뿐, **날짜경계 split 결과**를 신뢰하라(추출 방식에 따라 라인이 밀릴 수 있음).

**주차 내부 청크 단위 (chunk):** 각 주차는 대략 이 섹션들로 구성된다 — `市场表现`(시장 코멘트, 헤드라인 관계 밀집) / 기업별 `XXX Review|Preview`(TXN, LRCX, INTC, AAPL, MTK, ASML, TSM, NVDA, AMD, AVGO …) / `股票业绩&操作`(운용 코멘트, 관계 거의 없음 → 추출 스킵 가능). 번호 매겨진 굵은 헤더(`^\d+\.\s+\*\*`)로 섹션을 자른다. 각 청크에 `chunk_id`(예: `20251019#市场表现`), `week` 부여.

**언어/표기 특성 (resolver가 반드시 감당):** 한·중·영 혼재 + ticker 혼용. 예) `旭创`=Innolight, `源杰`=Source Photonics/Eoptolink계열, `海力士`/`Hynix`=SK Hynix, `工业富联`/`FII`/`鸿海`=Foxconn Industrial Internet, `台积电`/`TSM`=TSMC, `联发科`/`MTK`=MediaTek, `OAI`=OpenAI, `老黄`=NVIDIA(Jensen 지칭, 문맥상 NVIDIA로). 수량 단위도 혼재: `GW`, `WPM`(wafers per month, "万 WPM"=만 단위), `亿USD`(=100M USD), `M`(units), `%`.

---

## 4. 빌드 태스크 (기초 스펙 섹션 5 Repo 구조 그대로)

1. `schema/models.py`, `schema/relation_types.py`, `schema/ontology.json` — 기초 스펙 섹션 2 모델 그대로. `RelationEdge.contract_scale_norm`/`weight`는 `float|None`(Pass2 전엔 None).
2. `pipeline/ingest/docx_adapter.py` — python-docx로 문단+표셀 순회 → 날짜경계 split(주차) → 번호헤더 split(청크) → `Chunk{chunk_id, week, section_title, text}` 리스트. `--weeks N`(기본 5)으로 상단 N주만.
3. `prompts/extraction_prompt.py` — 기초 스펙 섹션 7 프롬프트.
4. `pipeline/extract/base.py` — `Extractor` 프로토콜 + `Company`/`Relation`/`ExtractionResult` dataclass(LLM·seed 공용 출력 스키마).
5. `pipeline/extract/seed_extractor.py` — 섹션 6 참조. **기본 추출기.**
6. `pipeline/extract/llm_extractor.py` — OpenAI/Anthropic 키로 청크 배치 호출 → 코드펜스 제거 + 안전 JSON 파싱 → `ExtractionResult`. 키 없으면 즉시 명확한 에러.
7. `pipeline/standardize/alias_dict.py` + `entity_resolver.py` — 섹션 5 alias 최소셋(기초 스펙) seed. 2단계 인터페이스(1차 사전, 2차 임베딩 자리만 비움). `norm_surface()`: NFKC 정규화 + 법인접미사 제거(`Inc.`/`Ltd.`/`株式会社`/`有限公司` 등) + 라틴만 소문자화(CJK는 소문자화 금지).
8. `pipeline/graph/edge_builder.py` + `merge.py` — 방향정규화(CUSTOMER_OF→SUPPLIES), 대칭관계(COMPETES_WITH/CO_MENTION) `frozenset` 키 머지, 2-pass weight.
9. `pipeline/export/to_graph_json.py` + `scripts/run_phase1.py` — end-to-end. `--input`, `--weeks`, `--extractor`.
10. `viz/inspect.html` — graph.json 로드, D3 force. **노드 크기=mention_count, 엣지 두께=weight, 엣지 색=relation_type, 화살표=방향**, hover 시 노드/엣지 상세(`source_chunk_ids`·`evidence` 포함). 단일 파일, CDN D3 허용.

---

## 5. 자주 깨지는 4지점 (여기를 먼저 단단히)

나머지 코드보다 훨씬 자주 깨진다. 테스트와 함께 박아라.

### 5.1 Entity resolver

- 2단계: (1) `norm_surface` 후 alias 사전 O(1) 매칭, (2) [Phase2 자리] 임베딩 후보, (3) 미매칭은 신규 노드 + `merge_candidate` 플래그.
- 함정은 `norm_surface`다. NFKC(전각→반각, `ＮＶＤＡ`→`NVDA`)와 법인접미사 제거를 안 하면 사전이 있어도 변형에서 새 노드가 샌다.
- **idempotency:** `node_store`는 직전 `graph.json`을 로드해 같은 surface→같은 canonical id가 나오게. 주차 증분의 전제.

### 5.2 Weight (2-pass, 단위 패밀리별 log 정규화)

- 크로스유닛 비교 금지: `10 GW` vs `900000 WPM` vs `100 亿USD`는 서로 비교 불가. `UNIT_FAMILY`로 버킷(power/throughput/money/volume…).
- 계약 규모는 heavy-tail → `log1p` 후 패밀리 내 min-max.
- `weight = (mention_count / mc_max) * max(contract_scale_norm, BASE)` (BASE≈0.1). 수량 없는 엣지도 언급량으로 weight를 받게 — 기초 스펙의 `max(_, base)` 유지.

### 5.3 방향 + CO_MENTION 억제

- `CUSTOMER_OF` → 즉시 `(source,target)` swap 후 `SUPPLIES`로.
- 텍스트가 "A加单 from B" / "A买B的X"면 공급방향(B→A SUPPLIES)으로 정규화.
- **CO_MENTION은 추출이 아니라 빌드 마지막에** 방출: 모든 typed 엣지를 만든 뒤 그 페어에 typed 엣지가 0개일 때만. (NVDA–TSMC에 SUPPLIES와 CO_MENTION이 동시에 붙는 것 방지 = 스펙의 "use sparingly"를 코드로 강제.)

### 5.4 Merge 키

- 비대칭: `(source, target, relation_type, date)` / 대칭: `frozenset({source,target})` + type + date.
- 충돌 시 `mention_count += 1`, `source_chunk_ids` 합집합, `confidence`는 max.
- **반드시 canonical id 해소 후** 키를 잡는다.

---

## 6. seed_extractor 명세 (데모 그래프의 정직성)

`seed_extractor`는 최근 5주를 읽어, **사람이 그 텍스트에서 읽어낼 헤드라인 관계**를 LLM 출력과 동일한 스키마로 내보낸다.
랜덤·규칙기반 노이즈를 만들지 말고, **명시적으로 근거 있는 관계만** 넣어라. 각 관계엔 `evidence`(≤15어 원문 스니펫)와 `source_chunk_ids`를 채운다.
구현은 청크 텍스트에서 패턴 매칭(예: `(\d+)\s*GW`, `(\d+)万\s*WPM`, `加单`, `合作`, `签订`)으로 후보를 잡되, 최종 방출 전 화이트리스트 검증을 거친다.

**반드시 포함돼야 할 최소 관계 (= DoD sanity check):**

- `Innolight(旭创) →[SUPPLIES, what_flows=광모듈] NVIDIA`, `源杰 →[SUPPLIES, 광모듈] Google` (NV+Google 加单 맥락)
- `OpenAI →[CONTRACTS_WITH, what_flows=TPU/ASIC, quantity=10, unit=GW] Broadcom`
- `OpenAI →[CONTRACTS_WITH, quantity=6, unit=GW] AMD`
- `OpenAI(Altman) →[CONTRACTS_WITH, what_flows=DRAM, quantity=900000, unit=WPM] 삼성`, `… → SK Hynix` (29CY 90만 WPM)
- `SK Hynix/삼성 →[SUPPLIES, what_flows=HBM]` 관련 + clean room 제약으로 NAND(Kioxia/Sandisk) 맥락이 엣지/`what_flows`로 표현
- (있으면) `TSMC →[SUPPLIES, what_flows=CoWoS/foundry] NVIDIA`, `Foxconn(工业富联) →[SUPPLIES, what_flows=AI server/rack]` 류

같은 기업의 中/英/ticker 표기는 resolver가 **하나의 노드로 병합**해야 한다(검증 항목).

---

## 7. Definition of Done (실행 가능한 인수 기준)

```bash
# 1) 기본(seed) 실행 — 키 없이 그래프가 나와야 함
python scripts/run_phase1.py --input data/examples/Tech周报_讨论.docx --weeks 5 --extractor seed
# → data/output/graph.json 생성

# 2) 검증 스크립트(또는 pytest)
python scripts/verify_dod.py   # 아래 항목 자동 체크
```

`verify_dod.py`가 통과시켜야 할 것:

- [ ] `graph.json`에 nodes/edges 존재, 모든 edge에 `source/target/relation_type/date/weight` 채워짐.
- [ ] DoD 최소 관계(섹션 6)가 방향·타입·정량과 함께 존재.
- [ ] `旭创`/`Innolight`, `海力士`/`Hynix`, `OAI`/`OpenAI` 등이 **각각 단일 canonical 노드**로 병합.
- [ ] `CUSTOMER_OF` 타입 엣지가 최종 그래프에 0개(전부 SUPPLIES로 접힘).
- [ ] 모든 weight ∈ [0,1], 단위 패밀리 섞인 비교 흔적 없음.
- [ ] typed 엣지가 있는 페어엔 CO_MENTION 없음.

수동 확인:

- [ ] `viz/inspect.html`에서 위 관계가 화살표·두께·색으로 보이고, hover 시 evidence/`source_chunk_ids` 표시.
- [ ] `--extractor llm`은 키 있을 때만 동작(키 없으면 명확한 에러로 종료).

---

## 8. 범위 밖 (이번에 절대 하지 말 것)

크롤러 / 금융 API enrichment / Louvain 세그먼트 / Neo4j·Chroma 저장 / 프론트 편집기능 / 임베딩 2차 매칭 구현(인터페이스만) / 시계열 diff 로직(단, `date` 필드는 채움) / 5주 초과 처리.

---

## 9. 시작 순서 제안

1. `data/examples/`로 docx 복사 → `docx_adapter`부터 만들어 **청크가 제대로 잘리는지** 먼저 눈으로 확인(주차 5개 × 섹션들).
2. `schema` + `extract/base.py` → `seed_extractor`로 최소 관계만 먼저 방출.
3. `standardize`(특히 `norm_surface`) → `edge_builder`(2-pass weight, 방향, CO_MENTION 억제) → `export`.
4. `inspect.html`로 확인 → `verify_dod.py` 통과.
5. 마지막에 `llm_extractor`를 seed와 동일 출력 스키마로 끼워 스위치 동작 확인.
