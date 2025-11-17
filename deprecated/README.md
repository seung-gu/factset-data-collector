# Deprecated Code

이 폴더에는 더 이상 사용하지 않는 코드들이 포함되어 있습니다.

## 포함된 파일들

### CRAFT 관련 파일
- `src/chart_ocr_processor/craft_detector.py` - CRAFT 텍스트 감지 모델
- `src/chart_ocr_processor/craft.py` - CRAFT 모델 정의
- `src/chart_ocr_processor/craft_utils.py` - CRAFT 유틸리티 함수
- `src/chart_ocr_processor/imgproc.py` - 이미지 처리 함수
- `src/chart_ocr_processor/basenet/` - CRAFT 백본 네트워크 (VGG16)
- `craft_mlt_25k.pth` - CRAFT 사전 학습 모델 가중치

### EasyOCR 관련 스크립트
- `scripts/test_easyocr_results.py` - EasyOCR 테스트 스크립트
- `scripts/visualize_craft_ocr.py` - CRAFT + EasyOCR/Tesseract 비교 스크립트

## 현재 사용 중인 솔루션

현재 프로젝트는 **Google Cloud Vision API**를 사용합니다:
- `src/chart_ocr_processor/google_vision_processor.py` - Google Vision API 처리
- `src/chart_ocr_processor/processor.py` - 메인 프로세서
- `scripts/visualize_google_ocr_full.py` - Google OCR 시각화

## 참고

이 파일들은 참고용으로 보관되어 있으며, 향후 필요시 참조할 수 있습니다.

