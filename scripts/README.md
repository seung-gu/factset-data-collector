# Scripts

이 폴더에는 OCR 테스트, 시각화, 데이터 수집을 위한 유틸리티 스크립트들이 포함되어 있습니다.

## 디렉토리 구조

- `visualization/`: 시각화 스크립트
- `testing/`: 테스트 스크립트
- `data_collection/`: 데이터 수집 스크립트

## 시각화 스크립트

### `visualization/visualize_bar_classification.py`
막대그래프 분류 결과를 시각화합니다. Q 박스와 숫자 박스를 그리고, 막대그래프 타입에 따라 색상을 구분합니다.

**사용법:**
```bash
uv run python scripts/visualization/visualize_bar_classification.py [이미지명]
```

**예시:**
```bash
uv run python scripts/visualization/visualize_bar_classification.py 20161209-6.png
```

**출력:**
- `output/preprocessing_test/{이미지명}_bar_classification.png`: 분류 결과 시각화

### `visualization/visualize_coordinate_matching.py`
좌표 기반 매칭 결과를 시각화합니다. Q 박스와 숫자 박스를 연결선으로 표시합니다.

**사용법:**
```bash
uv run python scripts/visualization/visualize_coordinate_matching.py
```

**출력:**
- `output/preprocessing_test/20161209-6_coordinate_matching.png`: 매칭 결과 시각화

### `visualization/visualize_image_preprocessing.py`
다양한 이미지 전처리 기법을 적용하고 결과를 저장합니다.

**사용법:**
```bash
uv run python scripts/visualization/visualize_image_preprocessing.py
```

**출력:**
- `output/preprocessing_test/image_preprocessing/`: 14가지 전처리 결과 이미지

### `visualization/visualize_bar_preprocessing.py`
막대그래프 영역에 다양한 전처리 기법을 적용하고 비교합니다.

**사용법:**
```bash
uv run python scripts/visualization/visualize_bar_preprocessing.py
```

**출력:**
- `output/preprocessing_test/bar_preprocessing/`: 각 막대그래프별 전처리 결과

### `visualization/visualize_google_ocr_full.py`
Google Cloud Vision API를 사용하여 전체 이미지에 대해 OCR을 수행하고 결과를 시각화합니다.

**사용법:**
```bash
uv run python scripts/visualization/visualize_google_ocr_full.py
```

**요구사항:**
- `.env` 파일에 `GOOGLE_APPLICATION_CREDENTIALS` 설정 필요

**출력:**
- `output/preprocessing_test/20161209-6_google_ocr_full.png`: Google OCR 결과

## 테스트 스크립트

### `testing/test_coordinate_matching.py`
좌표 기반 매칭 알고리즘을 테스트합니다.

**사용법:**
```bash
uv run python scripts/testing/test_coordinate_matching.py
```

### `testing/test_multiple_methods_classification.py`
3가지 방법을 모두 사용한 막대그래프 분류를 테스트합니다.

**사용법:**
```bash
uv run python scripts/testing/test_multiple_methods_classification.py
```

## 데이터 수집 스크립트

### `data_collection/download_factset_pdfs.py`
FactSet 웹사이트에서 Earnings Insight PDF를 다운로드합니다. 오늘부터 2000년까지 역순으로 검색하여 PDF를 찾고 다운로드합니다.

**사용법:**
```bash
uv run python scripts/data_collection/download_factset_pdfs.py
```

**출력:**
- `output/factset_pdfs/`: 다운로드된 PDF 파일들
- `output/factset_pdfs_index.json`: 다운로드된 PDF 인덱스 (날짜, URL, 크기 등)

**주의사항:**
- Rate limiting이 적용되어 있어 다운로드에 시간이 걸릴 수 있습니다
- 네트워크 연결이 필요합니다

### `data_collection/extract_eps_charts.py`
FactSet PDF 파일에서 Quarterly Bottom-Up EPS 차트 페이지를 추출하여 PNG 이미지로 변환합니다.

**사용법:**
```bash
# 전체 PDF 처리
uv run python scripts/data_collection/extract_eps_charts.py

# 제한된 개수만 처리 (테스트용)
# limit 파라미터를 수정하여 사용
```

**출력:**
- `output/estimates/{YYYYMMDD}-6.png`: 추출된 차트 이미지

**요구사항:**
- `output/factset_pdfs/` 폴더에 PDF 파일이 있어야 합니다
- `pdfplumber` 라이브러리 필요

## Deprecated

`deprecated/` 폴더에는 더 이상 사용하지 않는 스크립트들이 포함되어 있습니다:
- CRAFT 관련 스크립트
- EasyOCR 테스트 스크립트
