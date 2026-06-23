---
name: lesson-from-video
description: 유튜브(또는 로컬) 영상 링크와 원하는 실습을 받아, 영상을 분석해 단계별 스크린샷이 담긴 교안(.md)을 만든다. 이미지를 base64로 인라인한 자기완결형 마크다운으로 출력하고, humanizer 스킬이 있으면 문체를 다듬어 마무리한다. 사용자가 "이 영상으로 교안 만들어줘", "영상 기반 실습 가이드", "교안 생성" 등을 요청하고 영상 링크를 줄 때 사용.
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion, Skill
user-invocable: true
---

# lesson-from-video — 영상 기반 교안 생성

유튜브(또는 로컬) 영상 한 편을 분석해, 단계마다 화면 캡쳐가 담긴 실습 교안 마크다운을
만든다. 출력은 자기완결형 `.md`(이미지 base64 인라인)이고, 한국어 교안이면 마지막에
humanizer 로 문체를 다듬는다.

## 준비물

- `yt-dlp`, `ffmpeg` (예: macOS `brew install yt-dlp ffmpeg`)
- (선택) 자막이 전혀 없는 영상용 Whisper 키 — `GROQ_API_KEY`(권장) 또는 `OPENAI_API_KEY`.
  없으면 yt-dlp 자동 자막에 의존하고, 자막도 없으면 프레임만으로 진행
- (선택) 한국어 윤문을 위한 `humanizer` 스킬

## 산출물

- `<slug>.src.md` — 편집용 (이미지는 `assets/` 상대경로 참조)
- `<slug>.md` — 공유/업로드용 (이미지 base64 인라인, 외부 링크 0)
- `assets/<slug>-*.png|jpg` — 단계별 캡쳐

출력 폴더는 사용자가 지정하지 않으면 현재 작업 디렉토리 아래 `lessons/` 로 한다.

## Step 1 — 입력 수집

필요한 두 가지: **영상 URL(또는 로컬 경로)**, **원하는 실습 주제**(예: "다운로드 폴더 정리").
둘 중 하나라도 없으면 사용자에게 물어본다. `slug` 는 영문 kebab-case 로 정한다.

## Step 2 — 영상 분석

작업 파일은 `/tmp` 에 둔다. 자막 우선, 없으면 프레임만으로 진행한다.

```bash
cd /tmp
yt-dlp --print "TITLE: %(title)s | DUR: %(duration)s sec" --skip-download "<URL>"
# 자막(자동/수동). 다른 언어면 --sub-langs 를 바꾼다 (예: en)
yt-dlp --skip-download --write-auto-subs --write-subs --sub-langs ko --sub-format vtt -o "lesson_sub" "<URL>"
# 프레임용 영상 (720p)
yt-dlp -f "bestvideo[height<=720]+bestaudio/best[height<=720]" --merge-output-format mp4 -o "lesson.mp4" "<URL>"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 /tmp/lesson.mp4
```

VTT → 타임스탬프 전사 (롤링 자막 중복 제거):

```bash
python3 - <<'PY'
import re, glob
files = glob.glob('/tmp/lesson_sub*.vtt')
lines = open(files[0], encoding='utf-8').read().splitlines() if files else []
out=[]; cur=None; prev=''
for ln in lines:
    m=re.match(r'(\d{2}:\d{2}:\d{2})\.\d+ -->',ln)
    if m: cur=m.group(1); continue
    if '-->' in ln or not ln.strip() or ln.startswith(('WEBVTT','Kind:','Language:')): continue
    txt=re.sub(r'<[^>]+>','',ln).strip()
    if not txt or txt==prev: continue
    prev=txt; out.append((cur,txt))
open('/tmp/lesson_transcript.txt','w',encoding='utf-8').write('\n'.join(f"[{ts[3:]}] {t}" for ts,t in out))
print('lines:',len(out),'last:',out[-1][0] if out else None)
PY
```

### 자막이 없을 때 — Whisper 폴백

위에서 `/tmp/lesson_sub*.vtt` 가 안 받아졌거나 전사가 비었고, `GROQ_API_KEY`(권장: 저렴·빠름)
또는 `OPENAI_API_KEY` 가 설정돼 있으면 오디오를 추출해 Whisper로 전사한다. 둘 다 없으면
이 단계는 건너뛰고 프레임만으로 진행한다.

```bash
# 모노 16kHz 오디오 추출 (약 0.5MB/분; API 업로드 한도 25MB ≈ 50분)
ffmpeg -y -i /tmp/lesson.mp4 -vn -ac 1 -ar 16000 -b:a 64k /tmp/lesson_audio.mp3 -loglevel error

if [ -n "$GROQ_API_KEY" ]; then
  curl -s https://api.groq.com/openai/v1/audio/transcriptions \
    -H "Authorization: Bearer $GROQ_API_KEY" \
    -F model=whisper-large-v3 -F response_format=verbose_json \
    -F file=@/tmp/lesson_audio.mp3 > /tmp/lesson_whisper.json
else
  curl -s https://api.openai.com/v1/audio/transcriptions \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -F model=whisper-1 -F response_format=verbose_json \
    -F file=@/tmp/lesson_audio.mp3 > /tmp/lesson_whisper.json
fi
```

```bash
# verbose_json 의 segments(start/text) → 타임스탬프 전사
python3 - <<'PY'
import json
seg = json.load(open('/tmp/lesson_whisper.json')).get('segments', [])
def mmss(s): s=int(s); return f"{s//60:02d}:{s%60:02d}"
open('/tmp/lesson_transcript.txt','w',encoding='utf-8').write(
    '\n'.join(f"[{mmss(x['start'])}] {x['text'].strip()}" for x in seg))
print('whisper segments:', len(seg))
PY
```

전사를 **전부 Read** 한다. 사용자가 원한 실습이 다뤄지는 구간을 찾아 단계로 분해한다.
자막도 Whisper도 불가하면(키 없음 등) 프레임만으로 진행하되 사용자에게 알린다.

## Step 3 — 교안 설계

단계마다 캡쳐 한 장이 원칙이다. 권장 골격:

```
---
title: <제목>
video_url: <URL>
---

# <제목>

## 이 과제를 마치면
- 3~4개 학습 목표

## 1부. 먼저 알아둘 것
개념 설명 + 핵심 개념별 이미지 (타임스탬프 인용)

## 2부. 실습: <실습명>
### 준비물
### 따라하기
**1) ...** 설명 + ![alt](assets/<slug>-01-name.png) + *그림 1. 캡션*
(단계마다 한 장)
### 다 됐는지 확인

## 3부. 더 해보기
영상의 다른 구간을 확장 과제로

<!-- 비공개(강사용) 메모는 이 마커로 감싼다 -->
<!-- lms:exclude -->
## 강사 노트
- 운영 팁
<!-- lms:/exclude -->

_출처: 영상 제목/채널, 자막+화면 분석. 괄호 안 숫자는 타임스탬프._
```

원칙: 영상 내용은 **타임스탬프로 근거**를 단다. 이미지 바로 아래 `*그림 N. 설명.*` 캡션.
`<!-- lms:exclude -->…<!-- lms:/exclude -->` 로 감싼 구간은 "학습자 비노출" 표시 — 호스트
LMS 가 이 규칙을 알면 본문에서 제외할 수 있다(없으면 단순 주석처럼 무시됨).

## Step 4 — 단계별 프레임 추출

각 단계/핵심 개념에 대표 타임스탬프를 하나씩 고른다. 추출 → **Read 로 내용 확인** → 필요시 크롭.

```bash
# 1차: 크롭 없이 후보 확인
ffmpeg -y -ss <MM:SS> -i /tmp/lesson.mp4 -frames:v 1 -vf "scale=1000:-1" /tmp/cand.jpg
```

후보를 Read 해서 (1) 의도한 장면이 맞는지, (2) 하단에 자막 띠나 진행자 얼굴 오버레이가
있는지 본다. 있으면 하단을 크롭한다 (예: 720p 기준 하단 64~100px 제거):

```bash
ffmpeg -y -ss <MM:SS> -i /tmp/lesson.mp4 -frames:v 1 \
  -vf "crop=1280:656:0:0,scale=1000:-1" <출력폴더>/assets/<slug>-NN-name.jpg
```

- 자막·얼굴이 없는 깔끔한 화면(인포그래픽 등)은 크롭 없이 `scale=1000:-1` 만.
- 파일명은 **slug 접두사 + 순번 + 설명**으로 충돌을 피한다.
- 정보가 없는 프레임(검은 화면 등)은 버린다.

## Step 5 — `.src.md` 작성

`<출력폴더>/<slug>.src.md` 를 Step 3 골격으로 작성한다. 이미지는 `assets/<파일>` 상대경로.

## Step 6 — base64 자기완결 `.md` 생성

번들 스크립트로 인라인한다. (스킬 폴더 기준 경로)

```bash
python3 "$CLAUDE_SKILL_DIR/scripts/inline_images.py" <출력폴더>/<slug>.src.md
# 또는 스킬 설치 경로를 직접: ~/.claude/skills/lesson-from-video/scripts/inline_images.py
```

`<slug>.md` 가 생성된다 (이미지 base64 인라인, 외부 링크 0).

## Step 7 — humanizer 윤문 (한국어 교안일 때)

`humanizer` 스킬이 설치돼 있고 교안이 한국어면, 그 스킬을 호출해 **본문 산문(text)**의 AI
문체를 다듬는다. 표·코드·프런트매터·타임스탬프·수치·고유명사는 보존한다. 교정을
`.src.md` 에 반영한 뒤 **Step 6 을 다시 실행**해 `.md` 를 재생성한다.
humanizer 가 없으면 이 단계는 건너뛴다.

## Step 8 — 마무리

1. `/tmp/lesson.mp4`, `/tmp/lesson_sub*.vtt`, `/tmp/lesson_transcript.txt`, `/tmp/cand.jpg` 정리.
2. 산출물 경로를 사용자에게 보고: `<출력폴더>/<slug>.md`.

## 참고

- 자막이 안 잡히는 영상이 흔하다. 그래서 watch 류 도구 대신 위 yt-dlp 직접 경로를 기본으로 쓴다.
- 자기완결 `.md` 는 어디서 열어도 이미지가 보인다. 호스트 시스템(LMS 등)에 올릴 때는 그쪽
  포맷에 맞춰 변환하는 임포터를 별도로 두면 된다.
