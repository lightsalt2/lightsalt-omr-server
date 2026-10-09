# Lightsalt OMR Server

워드프레스 **빛과소금 악보 편집기 V3.2.23** 전용 PDF → MusicXML 변환 API 예제입니다.

## API 규격 (플러그인 소스와 대조)
- `POST /convert`
- 요청 본문: **PDF 원본 바이너리**, `Content-Type: application/pdf`
- 인증: `Authorization: Bearer <OMR_API_KEY>`
- 성공 응답: `{"musicxml":"<?xml version=...><score-partwise>..."}` (JSON)
- 상태 확인: `GET /health`

## GitHub 업로드
ZIP을 **압축 해제**한 다음 `Dockerfile`, `main.py`, `requirements.txt`,
`.gitignore`, `.env.example`, `README.md` 파일을 GitHub 저장소 루트에 업로드하세요.
GitHub에 ZIP 파일만 올리면 Render가 Dockerfile을 읽을 수 없습니다.

## Render 배포
1. Render 대시보드 > New > Web Service > GitHub 저장소 연결.
2. Runtime: **Docker** (Dockerfile은 저장소 최상위).
3. Environment 변수 `OMR_API_KEY`에 임의의 길고 안전한 문자열 설정.
4. 인스턴스의 메모리/CPU를 고려하여 요금제 선택. Audiveris는 자원 소모가 큽니다.
5. Deploy 후 `https://<서비스명>.onrender.com/health` 확인.
6. WordPress 관리자 > 설정 > 빛과소금 악보:
   - OMR 서버 HTTPS 주소: `https://<서비스명>.onrender.com/convert`
   - OMR API 키: Render의 `OMR_API_KEY`와 **동일한 값**.
7. PDF 업로드 > MusicXML로 변환.

**참고**: Render 주소만 넣으면 안 되고 끝에 `/convert`가 필요합니다.

## 중요 사항
- 이 저장소는 서버 **소스코드**입니다. GitHub 자체에서 변환이 실행되지는 않습니다.
- Docker 빌드 시 Audiveris 공식 GitHub 최신 릴리스의 `.deb`를 다운로드합니다.
  릴리스 파일 이름·구조·의존성이 바뀌면 Dockerfile 수정이 필요할 수 있습니다.
- 이 환경에서는 실제 Render 배포와 PDF 변환 성공까지 검증하지 못했습니다.
- 스캔 악보, 한글 가사, 빨간색 음표의 인식 정확도는 보장되지 않습니다.
  원본과 MusicXML을 대조해 교정해야 합니다.
- WordPress 플러그인의 HTTP 타임아웃은 120초입니다. PDF가 크거나 서버가
  느리면 시간 초과가 발생할 수 있습니다.
- Render에서 서버가 외부에 노출되므로 **API 키 설정은 필수**입니다.
  키를 README, 커밋, 공개 이슈에 올리지 마세요.
- 업로드된 PDF는 요청별 임시 폴더에 보관되고 처리 후 삭제됩니다.
- 라이선스: Audiveris 자체 라이선스 및 배포 조건을 별도로 확인하세요.

## 문제 해결
- 401: Render 환경변수의 키와 WordPress 설정 키가 다름.
- 503: 키 미설정 또는 Audiveris 실행 파일 누락.
- 422: PDF 악보 인식 실패 또는 MusicXML 미생성.
- 504: 서버 변환 시간 초과.
- 502(WordPress): OMR 서버가 HTTP 오류를 반환했거나 연결 불가.
