# lesson-from-video

영상 한 편으로 **단계별 스크린샷이 담긴 실습 교안**을 만드는 [Claude Code](https://docs.claude.com/en/docs/claude-code) 스킬.

유튜브(또는 로컬) 영상 링크와 "어떤 실습을 다룰지"만 주면:

1. 영상을 내려받아 자막을 전사하고 핵심 장면 프레임을 뽑고
2. 단계마다 화면 캡쳐가 들어간 교안 마크다운을 작성하고
3. 이미지를 base64로 인라인해 **파일 하나로 끝나는 `.md`** 로 출력합니다.
4. (선택) `humanizer` 스킬이 있으면 한국어 문체까지 다듬어 마무리합니다.

## 요구사항

- [Claude Code](https://docs.claude.com/en/docs/claude-code)
- `yt-dlp`, `ffmpeg` — macOS 예시: `brew install yt-dlp ffmpeg`
- (선택) 자막이 없는 영상을 위한 Whisper API 키
- (선택) 한국어 윤문용 `humanizer` 스킬 — 없으면 그 단계만 건너뜁니다

## 설치 (폴더 복사)

이 저장소의 `skills/lesson-from-video` 폴더를 Claude Code 스킬 경로에 복사합니다.

```bash
# 모든 프로젝트에서 쓰려면 (사용자 전역)
cp -R skills/lesson-from-video ~/.claude/skills/

# 특정 프로젝트에서만 쓰려면 (프로젝트 루트에서)
mkdir -p .claude/skills && cp -R skills/lesson-from-video .claude/skills/
```

Claude Code를 다시 열면 `/lesson-from-video` 로 호출할 수 있습니다.

## 사용법

```
/lesson-from-video https://youtu.be/VIDEO_ID 다운로드 폴더 정리
```

또는 그냥 대화로 영상 링크와 원하는 실습을 알려주면 됩니다.

산출물:

- `lessons/<slug>.md` — 공유/업로드용 (이미지 base64 인라인, 외부 링크 0)
- `lessons/<slug>.src.md` — 편집용 (이미지는 `assets/` 상대경로)
- `lessons/assets/<slug>-*.png` — 단계별 캡쳐

## 동작 방식

| 단계 | 내용 |
|---|---|
| 입력 | 영상 URL + 원하는 실습 |
| 분석 | `yt-dlp` 자막 전사 + `ffmpeg` 프레임 추출 (자막 없으면 프레임만) |
| 작성 | 단계마다 캡쳐 1장, 타임스탬프 근거 표기 |
| 출력 | 이미지를 base64로 인라인한 자기완결 `.md` |
| 마무리 | (선택) `humanizer`로 한국어 윤문 |

## 라이선스

MIT. 자유롭게 쓰고 고치고 공유하세요.
