"""EasyOCR 테스트 결과를 파일로 저장하는 스크립트."""

from pathlib import Path
import cv2
import numpy as np
import pandas as pd
import easyocr
from src.chart_ocr_processor.craft_detector import CRAFTDetector


def test_easyocr_and_save(image_path: Path, output_csv: Path, output_image: Path):
    """EasyOCR로 테스트하고 결과를 저장합니다."""
    # 이미지 읽기
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"이미지를 읽을 수 없습니다: {image_path}")
        return
    
    # CRAFT 감지기 초기화
    print("CRAFT 감지기 초기화 중...")
    detector = CRAFTDetector()
    
    # EasyOCR 초기화
    print("EasyOCR 초기화 중...")
    reader = easyocr.Reader(['en'], gpu=False)
    
    # Threshold 설정: text_threshold=0.3, link_threshold=0.15, low_text=0.2
    print("CRAFT 모델로 텍스트 영역 감지 중 (text_threshold=0.3, link_threshold=0.15, low_text=0.2)...")
    text_regions, region_score, affinity_score = detector.detect_text_regions(
        image,
        text_threshold=0.3,
        link_threshold=0.15,
        low_text=0.2
    )
    
    print(f"감지된 텍스트 영역: {len(text_regions)}개")
    
    # EasyOCR 결과 수집
    print("\n=== EasyOCR 처리 중 ===")
    img_result = image.copy()
    ocr_results = []
    
    for i, region in enumerate(text_regions):
        bbox = region['bbox']
        if isinstance(bbox, list):
            bbox = np.array(bbox)
        pts = np.array(bbox, dtype=np.int32)
        
        # 박스 영역 크롭
        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        x_min, x_max = max(0, int(min(x_coords)) - 5), min(image.shape[1], int(max(x_coords)) + 5)
        y_min, y_max = max(0, int(min(y_coords)) - 5), min(image.shape[0], int(max(y_coords)) + 5)
        
        cropped = image[y_min:y_max, x_min:x_max]
        
        if cropped.size > 0:
            # EasyOCR로 OCR 수행
            results = reader.readtext(cropped)
            
            if results:
                text = results[0][1] if results else ''
                confidence = results[0][2] if results else 0.0
            else:
                text = ''
                confidence = 0.0
            
            text = text.strip()
            
            if text:
                # 박스 그리기
                cv2.polylines(img_result, [pts], True, (0, 255, 0), 2)
                
                # 텍스트 표시
                x, y = int(bbox[0][0]), int(bbox[0][1])
                display_text = text[:30] if len(text) > 30 else text
                cv2.putText(img_result, display_text, (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 3)
                
                ocr_results.append({
                    'index': i + 1,
                    'text': text,
                    'confidence': confidence,
                    'x_min': x_min,
                    'y_min': y_min,
                    'x_max': x_max,
                    'y_max': y_max,
                    'area': region['area']
                })
    
    # CSV로 저장
    if ocr_results:
        df = pd.DataFrame(ocr_results)
        df.to_csv(output_csv, index=False)
        print(f"\n결과를 {output_csv}에 저장했습니다. (총 {len(ocr_results)}개)")
    else:
        print("\n인식된 텍스트가 없습니다.")
    
    # 이미지 저장
    cv2.imwrite(str(output_image), img_result)
    print(f"시각화 결과를 {output_image}에 저장했습니다.")
    
    # 결과 요약 출력
    print(f"\n=== EasyOCR 결과 요약 ===")
    print(f"총 {len(ocr_results)}개 텍스트 인식")
    print(f"\n처음 20개 결과:")
    for result in ocr_results[:20]:
        print(f"  {result['index']:3d}. '{result['text']}' (신뢰도: {result['confidence']:.2f})")
    
    if len(ocr_results) > 20:
        print(f"  ... 외 {len(ocr_results) - 20}개 더")


if __name__ == '__main__':
    test_image = Path('output/estimates/20161209-6.png')
    output_csv = Path('output/preprocessing_test/easyocr_test_results.csv')
    output_image = Path('output/preprocessing_test/easyocr_test_visualization.png')
    
    # 출력 디렉토리 생성
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_image.parent.mkdir(parents=True, exist_ok=True)
    
    test_easyocr_and_save(test_image, output_csv, output_image)

